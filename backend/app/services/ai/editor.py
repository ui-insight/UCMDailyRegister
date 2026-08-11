"""AI Editor orchestrator — coordinates style rules, LLM calls, and post-processing."""

import logging
import re
from dataclasses import dataclass, field

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.style_rule import StyleRule
from app.models.submission import Submission
from app.models.edit_history import EditVersion
from app.services.ai.provider import LLMProvider
from app.services.ai.prompts import build_system_prompt, build_edit_user_prompt
from app.services.ai.diff_generator import generate_word_diff, diff_to_dict
from app.utils.text import (
    to_sentence_case,
    to_title_case,
    detect_first_person,
    detect_exclamation_marks,
    check_event_details,
    is_event_category,
)
from app.utils.hyperlinks import parse_submitter_notes
from app.utils.style_checks import (
    strip_html,
    detect_unabbreviated_month_dates,
    detect_abbreviated_months_without_date,
    detect_nonstandard_meridiems,
    detect_twelve_oclock_meridiems,
    detect_platform_names,
    detect_undefined_acronyms,
    detect_repeated_cta_phrases,
)

logger = logging.getLogger(__name__)

_HTML_OR_ENTITY_TOKEN = re.compile(
    r"(<[^>]*>|&(?:#\d+|#x[0-9a-f]+|[a-z][a-z0-9]+);)",
    re.IGNORECASE,
)


def enforce_no_semicolons_in_prose(body: str) -> tuple[str, bool]:
    """Replace prose semicolons while preserving HTML tags, URLs and entities."""
    parts = _HTML_OR_ENTITY_TOKEN.split(body)
    changed = False

    for index in range(0, len(parts), 2):
        prose = parts[index]
        if ";" not in prose:
            continue
        changed = True
        prose = re.sub(
            r";\s*([a-z])",
            lambda match: f". {match.group(1).upper()}",
            prose,
        )
        parts[index] = prose.replace(";", ".")

    return "".join(parts), changed


class AIEditError(Exception):
    """Raised when the LLM provider cannot produce an edit suggestion."""


@dataclass
class EditResult:
    """Result of an AI edit operation."""
    edited_headline: str
    edited_body: str
    headline_case: str
    changes_made: list[str] = field(default_factory=list)
    flags: list[dict] = field(default_factory=list)
    embedded_links: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    ai_provider: str = ""
    ai_model: str = ""
    headline_diff: dict = field(default_factory=dict)
    body_diff: dict = field(default_factory=dict)


class AIEditor:
    """Orchestrates AI-assisted editing of newsletter submissions."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def load_style_rules(
        self, session: AsyncSession, newsletter_type: str
    ) -> list[dict]:
        """Load active style rules for a newsletter type (shared + type-specific)."""
        result = await session.execute(
            sa.select(StyleRule).where(
                StyleRule.Is_Active == True,  # noqa: E712
                StyleRule.Rule_Set.in_(["shared", newsletter_type]),
            )
        )
        rules = result.scalars().all()
        return [
            {
                "category": r.Category,
                "rule_key": r.Rule_Key,
                "rule_text": r.Rule_Text,
                "severity": r.Severity,
            }
            for r in rules
        ]

    def pre_analyze(
        self, headline: str, body: str, category: str, submitter_notes: str | None
    ) -> list[dict]:
        """Run rule-based pre-analysis before sending to LLM."""
        flags = []

        for text_label, text in [("headline", headline), ("body", body)]:
            findings = detect_first_person(text)
            if findings:
                words = ", ".join(f"'{f['word']}'" for f in findings[:3])
                flags.append({
                    "type": "warning",
                    "rule_key": "third_person",
                    "message": f"First-person usage detected in {text_label}: {words}",
                })

        for text_label, text in [("headline", headline), ("body", body)]:
            findings = detect_exclamation_marks(text)
            if findings:
                flags.append({
                    "type": "warning",
                    "rule_key": "no_exclamation_marks",
                    "message": f"Exclamation mark(s) found in {text_label} ({len(findings)} occurrence(s))",
                })

        if is_event_category(category):
            details = check_event_details(body)
            if details["missing"]:
                missing = ", ".join(details["missing"])
                flags.append({
                    "type": "error",
                    "rule_key": "event_details_required",
                    "message": f"Event listing may be missing: {missing}",
                })

        if submitter_notes:
            parsed_links = parse_submitter_notes(submitter_notes)
            if parsed_links:
                flags.append({
                    "type": "info",
                    "rule_key": "link_embedding",
                    "message": f"Found {len(parsed_links)} link(s) in submitter notes to embed",
                })

        return flags

    def post_analyze(
        self,
        headline: str,
        body: str,
        category: str,
        style_rules: list[dict],
    ) -> list[dict]:
        """Run deterministic rule checks on the AI-edited output.

        Prompt injection alone does not guarantee compliance, so the
        mechanically verifiable rules are re-checked here. Each check runs
        only while its rule is active, so deactivating a rule in the app
        also silences its deterministic check. Exact-match checks flag at
        the rule's severity; heuristic checks always flag as warnings.
        """
        active = {rule["rule_key"]: rule for rule in style_rules}
        flags: list[dict] = []
        text = strip_html(f"{headline}\n{body}")

        def add(rule_key: str, message: str, *, heuristic: bool = False) -> None:
            rule = active.get(rule_key)
            if rule is None:
                return
            flag_type = "warning" if heuristic or rule["severity"] != "error" else "error"
            flags.append({"type": flag_type, "rule_key": rule_key, "message": message})

        for found in detect_unabbreviated_month_dates(text):
            add("ap_style_dates", f"Month should be abbreviated with a specific date: '{found}'")
        for found in detect_abbreviated_months_without_date(text):
            add("ap_style_dates", f"Month without a specific date should be spelled out: '{found}'")

        for found in detect_nonstandard_meridiems(text):
            add("ap_style_times", f"Time should use lowercase a.m./p.m. with periods: '{found}'")
        for found in detect_twelve_oclock_meridiems(text):
            add("ap_style_times", f"Use noon or midnight instead of '{found}'")

        platforms = detect_platform_names(text)
        if platforms:
            names = ", ".join(f"'{name}'" for name in sorted(set(platforms)))
            add(
                "online_not_platform",
                f"Platform name(s) {names} found — use 'online' unless the platform is essential",
                heuristic=True,
            )

        acronyms = detect_undefined_acronyms(strip_html(body))
        if acronyms:
            listed = ", ".join(acronyms[:5])
            add(
                "spell_out_acronyms",
                f"Acronym(s) never defined in the body as Full Name (ACRONYM): {listed}",
                heuristic=True,
            )

        repeated = detect_repeated_cta_phrases(text)
        if repeated:
            listed = ", ".join(f"'{phrase}'" for phrase in repeated)
            add(
                "single_cta",
                f"Call-to-action phrase(s) repeated: {listed}",
                heuristic=True,
            )

        if category == "job_opportunity":
            if re.search(r"\bMoscow\b", text):
                add("job_posting_format", "Jobs listing mentions Moscow — omit the default location")
            if "\n" in body.strip():
                add("job_posting_format", "Jobs listing spans multiple lines — keep it on one line")

        return flags

    async def edit_submission(
        self,
        session: AsyncSession,
        submission: Submission,
        newsletter_type: str,
        editor_instructions: str | None = None,
    ) -> EditResult:
        """Run the full AI editing pipeline on a submission."""
        headline_case = "sentence_case"

        style_rules = await self.load_style_rules(session, newsletter_type)

        pre_flags = self.pre_analyze(
            submission.Original_Headline,
            submission.Original_Body,
            submission.Category,
            submission.Submitter_Notes,
        )

        system_prompt = build_system_prompt(
            newsletter_type=newsletter_type,
            style_rules=style_rules,
            category=submission.Category,
        )

        links = [
            {"url": link.Url, "anchor_text": link.Anchor_Text}
            for link in submission.Links
        ]

        user_prompt = build_edit_user_prompt(
            headline=submission.Original_Headline,
            body=submission.Original_Body,
            submitter_notes=submission.Submitter_Notes,
            links=links if links else None,
            category=submission.Category,
            editor_instructions=editor_instructions,
        )

        try:
            ai_result = await self.llm.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=3000,
            )
        except Exception as e:
            logger.error(f"LLM call failed for submission {submission.Id}: {e}")
            raise AIEditError(f"AI editing failed: {str(e)}") from e

        edited_headline = ai_result.get("edited_headline", submission.Original_Headline)
        edited_body = ai_result.get("edited_body", submission.Original_Body)
        changes_made = list(ai_result.get("changes_made", []) or [])
        ai_flags = ai_result.get("flags", [])
        embedded_links = ai_result.get("embedded_links", [])
        confidence = ai_result.get("confidence", 0.5)

        short_sentence_rule_active = any(
            rule["rule_key"] == "short_sentences" for rule in style_rules
        )
        edited_body, replaced_semicolons = (
            enforce_no_semicolons_in_prose(edited_body)
            if short_sentence_rule_active
            else (edited_body, False)
        )
        if replaced_semicolons:
            cleanup_description = (
                "Replaced semicolons with periods to enforce the short-sentence rule"
            )
            if cleanup_description not in changes_made:
                changes_made.append(cleanup_description)

        if headline_case == "sentence_case":
            edited_headline = to_sentence_case(edited_headline)
        else:
            edited_headline = to_title_case(edited_headline)

        headline_diff = diff_to_dict(
            generate_word_diff(submission.Original_Headline, edited_headline)
        )
        body_diff = diff_to_dict(
            generate_word_diff(submission.Original_Body, edited_body)
        )

        post_flags = self.post_analyze(
            edited_headline, edited_body, submission.Category, style_rules
        )

        all_flags = pre_flags + ai_flags + post_flags

        return EditResult(
            edited_headline=edited_headline,
            edited_body=edited_body,
            headline_case=headline_case,
            changes_made=changes_made,
            flags=all_flags,
            embedded_links=embedded_links,
            confidence=confidence,
            ai_provider=self.llm.__class__.__name__.replace("Provider", "").lower(),
            ai_model=getattr(self.llm, "model", "unknown"),
            headline_diff=headline_diff,
            body_diff=body_diff,
        )

    async def save_edit_versions(
        self,
        session: AsyncSession,
        submission_id: str,
        edit_result: EditResult,
        original_headline: str,
        original_body: str,
        editor_instructions: str | None = None,
    ) -> tuple[EditVersion, EditVersion]:
        """Save the original and AI-suggested versions to the database."""
        existing = await session.execute(
            sa.select(EditVersion).where(
                EditVersion.Submission_Id == submission_id,
                EditVersion.Version_Type == "original",
            )
        )
        original_version = existing.scalar_one_or_none()

        if not original_version:
            original_version = EditVersion(
                Submission_Id=submission_id,
                Version_Type="original",
                Headline=original_headline,
                Body=original_body,
            )
            session.add(original_version)

        ai_version = EditVersion(
            Submission_Id=submission_id,
            Version_Type="ai_suggested",
            Headline=edit_result.edited_headline,
            Body=edit_result.edited_body,
            Headline_Case=edit_result.headline_case,
            Flags=edit_result.flags,
            Changes_Made=edit_result.changes_made,
            AI_Provider=edit_result.ai_provider,
            AI_Model=edit_result.ai_model,
            Editor_Instructions=editor_instructions,
        )
        session.add(ai_version)

        await session.flush()
        return original_version, ai_version

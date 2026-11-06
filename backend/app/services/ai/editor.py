"""AI Editor orchestrator — coordinates style rules, LLM calls, and post-processing."""

import html
import logging
import re
from dataclasses import dataclass, field
from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.style_rule import StyleRule
from app.models.submission import Submission
from app.models.edit_history import EditVersion
from app.services.ai.provider import LLMProvider
from app.services.ai.prompts import (
    build_compliance_repair_prompt,
    build_edit_user_prompt,
    build_system_prompt,
    policy_fingerprint,
)
from app.services.ai.diff_generator import generate_word_diff, diff_to_dict
from app.services.ai.post_checks import CheckContext, run_checks
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
    change_contradicts_final_dates,
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


SEMICOLON_CLEANUP_DESCRIPTION = (
    "Replaced semicolons with periods to enforce the short-sentence rule"
)

CURLY_QUOTES_DESCRIPTION = (
    "Converted straight quotation marks and apostrophes to curly ones"
)

_OPENING_CONTEXT = set(" \t\n\u00a0([{\u2014\u2013-/\u201c\u2018")

# Tags (quoted attribute values may contain ">"), entities and URLs are
# copied through untouched; only the prose between them is converted.
_QUOTE_SAFE_TOKEN = re.compile(
    r"(<(?:[^<>\"']|\"[^\"]*\"|'[^']*')*>"
    r"|&(?:#\d+|#x[0-9a-f]+|[a-z][a-z0-9]+);"
    r"|(?:https?://|www\.)[^\s<>\"]+)",
    re.IGNORECASE,
)


def _curly(char: str, previous: str, following: str) -> str:
    opening = not previous or previous in _OPENING_CONTEXT
    if char == '"':
        return "\u201c" if opening else "\u201d"
    # Apostrophes, closing quotes and '26-style years take the right mark.
    return "\u2018" if opening and not following.isdigit() else "\u2019"


def enforce_curly_quotes(text: str) -> tuple[str, bool]:
    """Convert straight quotes in prose to curly ones (#409).

    HTML tags (attributes included) and URLs are left alone. Entities count
    as the character they display, and encoded straight quotes (&quot;,
    &#39;) are converted like typed ones. Curly marks are never touched.
    """
    parts = _QUOTE_SAFE_TOKEN.split(text)
    changed = False
    previous = ""

    for index, part in enumerate(parts):
        if not part:
            continue
        if index % 2 == 1:
            if part.startswith("<"):
                continue  # a tag doesn't change quote direction
            if part.startswith("&"):
                shown = html.unescape(part)
                if shown in ("\"", "'"):
                    following = parts[index + 1][:1] if index + 1 < len(parts) else ""
                    parts[index] = _curly(shown, previous, following)
                    changed = True
                    previous = parts[index]
                else:
                    previous = shown[-1:] or previous
                continue
            previous = part[-1]  # a URL
            continue
        out: list[str] = []
        for position, char in enumerate(part):
            if char in ("\"", "'"):
                following = part[position + 1] if position + 1 < len(part) else ""
                char = _curly(char, previous, following)
                changed = True
            out.append(char)
            previous = char
        parts[index] = "".join(out)

    return "".join(parts), changed


def strip_headline_exclamations(headline: str) -> tuple[str, bool]:
    """Headlines never end in exclamation marks (#376)."""
    stripped = re.sub(r"\s*!+\s*$", "", headline)
    return stripped, stripped != headline


def _clean_final_copy(
    headline: str,
    body: str,
    active_rule_keys: set[str],
) -> tuple[str, str, bool]:
    """Apply the mechanical policy fixes before the copy is analyzed.

    Running these before post-analysis keeps flags, the repair pass and the
    change notes describing the text that is actually saved.
    """
    if active_rule_keys & {"headline_rules", "no_exclamation_marks"}:
        headline, _ = strip_headline_exclamations(headline)
    if "curly_quotes" not in active_rule_keys:
        return headline, body, False
    headline, headline_quotes = enforce_curly_quotes(headline)
    body, body_quotes = enforce_curly_quotes(body)
    return headline, body, headline_quotes or body_quotes

# Notes about the validation/repair mechanics, not about the copy itself.
_INTERNAL_PROCESS_CHANGE = re.compile(
    r"\b(?:repair pass|compliance (?:repair|findings?|checks?)|"
    r"deterministic (?:style|rule|compliance|validation|findings?|checks?)|"
    r"style[- ]rule validation|(?:first|previous|initial) draft)\b",
    re.IGNORECASE,
)
# "Changed 'X' to 'Y'." / "Replaced X with \"Y\"" — Y is the final wording.
_REPLACEMENT_TARGET = re.compile(
    r"\b(?:to|with)\s+[\"“'‘](?P<target>.+?)[\"”'’]\W*$",
    re.IGNORECASE,
)


def _comparable(text: str) -> str:
    """Normalize text so explanations can be compared with the final copy."""
    text = html.unescape(strip_html(text))
    text = text.translate(str.maketrans("“”‘’", "\"\"''"))
    return " ".join(text.split()).casefold()


def reconcile_changes(changes: list, final_text: str) -> list[str]:
    """Keep only explanations that describe the final saved edit, once each.

    A repair pass can abandon a change the first draft planned, and models
    sometimes narrate the repair process itself. Drop explanations whose
    stated replacement wording is absent from the final copy, drop process
    notes, and collapse duplicates that differ only in case or punctuation.
    """
    final_comparable = _comparable(final_text)
    reconciled: list[str] = []
    seen: set[str] = set()
    for change in changes:
        if not isinstance(change, str) or not change.strip():
            continue
        change = change.strip()
        if _INTERNAL_PROCESS_CHANGE.search(change):
            continue
        target = _REPLACEMENT_TARGET.search(change)
        if target and _comparable(target.group("target")) not in final_comparable:
            continue
        key = _comparable(change).rstrip(".")
        if key in seen:
            continue
        seen.add(key)
        reconciled.append(change)
    return reconciled


def dedupe_flags(flags: list[dict]) -> list[dict]:
    """Drop repeated flags that name the same rule and problem."""
    unique: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for flag in flags:
        key = (
            str(flag.get("type", "")),
            str(flag.get("rule_key", "")),
            _comparable(str(flag.get("message", ""))).rstrip("."),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(flag)
    return unique


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
    policy_fingerprint: str | None = None
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
                "rule_set": r.Rule_Set,
                "rule_key": r.Rule_Key,
                "rule_text": r.Rule_Text,
                "severity": r.Severity,
            }
            for r in rules
        ]

    def pre_analyze(
        self, headline: str, body: str, category: str, submitter_notes: str | None
    ) -> list[dict]:
        """Run the rule-based text checks shared by source and final copy."""
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
        *,
        source_text: str = "",
        source_body: str = "",
        source_comparison_output: str = "",
        reference_date: date | None = None,
        newsletter_type: str | None = None,
    ) -> list[dict]:
        """Run deterministic rule checks on the AI-edited output.

        Prompt injection alone does not guarantee compliance, so the
        mechanically verifiable rules are re-checked here; the checks live
        in ``post_checks``. Each finding is kept only while its rule is
        active, so deactivating a rule in the app also silences its check.
        Exact checks flag at the rule's severity; heuristic checks always
        flag as warnings.
        """
        active = {rule["rule_key"]: rule for rule in style_rules}
        context = CheckContext(
            headline=headline,
            body=body,
            category=category,
            newsletter_type=newsletter_type,
            reference_date=reference_date,
            source_text=source_text,
            source_body=source_body,
            source_comparison_output=source_comparison_output,
        )
        flags = []
        for finding in run_checks(context):
            rule = active.get(finding.rule_key)
            if rule is None:
                continue
            exact_error = not finding.heuristic and rule["severity"] == "error"
            flags.append({
                "type": "error" if exact_error else "warning",
                "rule_key": finding.rule_key,
                "message": finding.message,
            })
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
        # Dates without a year resolve from when the item was submitted (#410).
        submission_date = (
            submission.Created_At.date() if submission.Created_At else date.today()
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
            submission_date=submission_date,
        )

        try:
            ai_result = await self.llm.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=3000,
            )
        except Exception as e:
            logger.error("LLM call failed submission_id=%s error_type=%s", submission.Id, type(e).__name__)
            raise AIEditError("AI editing failed. Try again or contact the maintainer.") from e

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

        if headline_case == "sentence_case":
            edited_headline = to_sentence_case(edited_headline)
        else:
            edited_headline = to_title_case(edited_headline)
        active_rule_keys = {rule["rule_key"] for rule in style_rules}
        edited_headline, edited_body, converted_quotes = _clean_final_copy(
            edited_headline, edited_body, active_rule_keys
        )

        source_parts = [
            submission.Original_Headline,
            submission.Original_Body,
            submission.Submitter_Notes or "",
        ]
        for link in submission.Links:
            source_parts.extend([link.Url, link.Anchor_Text or ""])
        comparison_output_parts = [edited_headline, edited_body]
        for link in embedded_links:
            comparison_output_parts.extend(
                [str(link.get("url", "")), str(link.get("anchor_text", ""))]
            )
        post_flags = self.post_analyze(
            edited_headline,
            edited_body,
            submission.Category,
            style_rules,
            source_text="\n".join(source_parts),
            source_body=submission.Original_Body,
            source_comparison_output="\n".join(comparison_output_parts),
            reference_date=submission_date,
            newsletter_type=newsletter_type,
        )

        mandatory_rule_keys = {
            rule["rule_key"]
            for rule in style_rules
            if rule["severity"] == "error"
        }
        repair_findings = [
            flag for flag in post_flags if flag["rule_key"] in mandatory_rule_keys
        ]
        if repair_findings:
            repair_prompt = build_compliance_repair_prompt(
                user_prompt,
                edited_headline,
                edited_body,
                repair_findings,
            )
            try:
                repair_result = await self.llm.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=repair_prompt,
                    temperature=0.0,
                    max_tokens=3000,
                )
            except Exception as error:
                logger.warning(
                    "Compliance repair failed submission_id=%s error_type=%s",
                    submission.Id,
                    type(error).__name__,
                )
            else:
                edited_headline = repair_result.get(
                    "edited_headline",
                    edited_headline,
                )
                edited_body = repair_result.get("edited_body", edited_body)
                # The repair prompt asks for the complete list for the
                # corrected draft, so it replaces the first draft's list.
                repair_changes = list(repair_result.get("changes_made", []) or [])
                if repair_changes:
                    changes_made = repair_changes
                ai_flags = repair_result.get("flags", [])
                embedded_links = repair_result.get("embedded_links", [])
                confidence = repair_result.get("confidence", confidence)

                edited_body, replaced_repair_semicolons = (
                    enforce_no_semicolons_in_prose(edited_body)
                    if short_sentence_rule_active
                    else (edited_body, False)
                )
                replaced_semicolons = replaced_semicolons or replaced_repair_semicolons

                if headline_case == "sentence_case":
                    edited_headline = to_sentence_case(edited_headline)
                else:
                    edited_headline = to_title_case(edited_headline)
                edited_headline, edited_body, repair_quotes = _clean_final_copy(
                    edited_headline, edited_body, active_rule_keys
                )
                converted_quotes = converted_quotes or repair_quotes

                comparison_output_parts = [edited_headline, edited_body]
                for link in embedded_links:
                    comparison_output_parts.extend(
                        [str(link.get("url", "")), str(link.get("anchor_text", ""))]
                    )
                post_flags = self.post_analyze(
                    edited_headline,
                    edited_body,
                    submission.Category,
                    style_rules,
                    source_text="\n".join(source_parts),
                    source_body=submission.Original_Body,
                    source_comparison_output="\n".join(comparison_output_parts),
                    reference_date=submission_date,
                    newsletter_type=newsletter_type,
                )

        headline_diff = diff_to_dict(
            generate_word_diff(submission.Original_Headline, edited_headline)
        )
        body_diff = diff_to_dict(
            generate_word_diff(submission.Original_Body, edited_body)
        )

        # Explanations and flags must describe the final saved text, not
        # the first draft or the source problems the edit already resolved.
        final_output = "\n".join(comparison_output_parts)
        changes_made = reconcile_changes(changes_made, final_output)
        date_contradictions = [
            change
            for change in changes_made
            if change_contradicts_final_dates(change, final_output)
        ]
        changes_made = [
            change for change in changes_made if change not in date_contradictions
        ]
        if replaced_semicolons and SEMICOLON_CLEANUP_DESCRIPTION not in changes_made:
            changes_made.append(SEMICOLON_CLEANUP_DESCRIPTION)
        if converted_quotes and CURLY_QUOTES_DESCRIPTION not in changes_made:
            changes_made.append(CURLY_QUOTES_DESCRIPTION)

        final_text_flags = self.pre_analyze(
            edited_headline,
            edited_body,
            submission.Category,
            None,
        )
        unembedded_links = [
            link
            for link in parse_submitter_notes(submission.Submitter_Notes or "")
            if link.url not in final_output
        ]
        if unembedded_links:
            final_text_flags.append({
                "type": "info",
                "rule_key": "link_embedding",
                "message": (
                    f"{len(unembedded_links)} link(s) from submitter notes "
                    "are not embedded in the edit"
                ),
            })

        for change in date_contradictions:
            final_text_flags.append({
                "type": "warning",
                "rule_key": "ap_style_dates",
                "message": (
                    "Removed a change note whose weekday contradicts the final "
                    f"date; confirm the date in the edit: '{change}'"
                ),
            })

        all_flags = dedupe_flags(final_text_flags + ai_flags + post_flags)

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
            policy_fingerprint=policy_fingerprint(style_rules),
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
            Policy_Fingerprint=edit_result.policy_fingerprint,
            Editor_Instructions=editor_instructions,
        )
        session.add(ai_version)

        await session.flush()
        return original_version, ai_version

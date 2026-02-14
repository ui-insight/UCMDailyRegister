"""AI Editor orchestrator — coordinates style rules, LLM calls, and post-processing."""

import logging
from dataclasses import dataclass, field

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.style_rule import StyleRule
from app.models.submission import Submission, SubmissionLink
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

logger = logging.getLogger(__name__)


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
                StyleRule.is_active == True,  # noqa: E712
                StyleRule.rule_set.in_(["shared", newsletter_type]),
            )
        )
        rules = result.scalars().all()
        return [
            {
                "category": r.category,
                "rule_key": r.rule_key,
                "rule_text": r.rule_text,
                "severity": r.severity,
            }
            for r in rules
        ]

    def pre_analyze(
        self, headline: str, body: str, category: str, submitter_notes: str | None
    ) -> list[dict]:
        """Run rule-based pre-analysis before sending to LLM.

        Returns flags that can be included in the edit result.
        """
        flags = []

        # Check for first-person usage
        for text_label, text in [("headline", headline), ("body", body)]:
            findings = detect_first_person(text)
            if findings:
                words = ", ".join(f"'{f['word']}'" for f in findings[:3])
                flags.append({
                    "type": "warning",
                    "rule_key": "third_person",
                    "message": f"First-person usage detected in {text_label}: {words}",
                })

        # Check for exclamation marks
        for text_label, text in [("headline", headline), ("body", body)]:
            findings = detect_exclamation_marks(text)
            if findings:
                flags.append({
                    "type": "warning",
                    "rule_key": "no_exclamation_marks",
                    "message": f"Exclamation mark(s) found in {text_label} ({len(findings)} occurrence(s))",
                })

        # Check for required event details
        if is_event_category(category):
            details = check_event_details(body)
            if details["missing"]:
                missing = ", ".join(details["missing"])
                flags.append({
                    "type": "error",
                    "rule_key": "event_details_required",
                    "message": f"Event listing may be missing: {missing}",
                })

        # Parse submitter notes for link instructions
        if submitter_notes:
            parsed_links = parse_submitter_notes(submitter_notes)
            if parsed_links:
                flags.append({
                    "type": "info",
                    "rule_key": "link_embedding",
                    "message": f"Found {len(parsed_links)} link(s) in submitter notes to embed",
                })

        return flags

    async def edit_submission(
        self,
        session: AsyncSession,
        submission: Submission,
        newsletter_type: str,
    ) -> EditResult:
        """Run the full AI editing pipeline on a submission.

        Args:
            session: Database session
            submission: The Submission ORM object
            newsletter_type: "tdr" or "myui"

        Returns:
            EditResult with edited text, flags, and diffs
        """
        headline_case = "sentence_case" if newsletter_type == "tdr" else "title_case"

        # 1. Load active style rules
        style_rules = await self.load_style_rules(session, newsletter_type)

        # 2. Pre-analyze for rule-based issues
        pre_flags = self.pre_analyze(
            submission.original_headline,
            submission.original_body,
            submission.category,
            submission.submitter_notes,
        )

        # 3. Build prompts
        system_prompt = build_system_prompt(
            newsletter_type=newsletter_type,
            style_rules=style_rules,
            category=submission.category,
        )

        links = [
            {"url": link.url, "anchor_text": link.anchor_text}
            for link in submission.links
        ]

        user_prompt = build_edit_user_prompt(
            headline=submission.original_headline,
            body=submission.original_body,
            submitter_notes=submission.submitter_notes,
            links=links if links else None,
            category=submission.category,
        )

        # 4. Call LLM
        try:
            ai_result = await self.llm.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=3000,
            )
        except Exception as e:
            logger.error(f"LLM call failed for submission {submission.id}: {e}")
            # Return a minimal result with error flag
            return EditResult(
                edited_headline=submission.original_headline,
                edited_body=submission.original_body,
                headline_case=headline_case,
                flags=[
                    *pre_flags,
                    {
                        "type": "error",
                        "rule_key": "ai_error",
                        "message": f"AI editing failed: {str(e)}",
                    },
                ],
                confidence=0.0,
                ai_provider="error",
                ai_model="error",
            )

        # 5. Extract and validate AI response
        edited_headline = ai_result.get("edited_headline", submission.original_headline)
        edited_body = ai_result.get("edited_body", submission.original_body)
        changes_made = ai_result.get("changes_made", [])
        ai_flags = ai_result.get("flags", [])
        embedded_links = ai_result.get("embedded_links", [])
        confidence = ai_result.get("confidence", 0.5)

        # 6. Post-process: enforce headline case
        if headline_case == "sentence_case":
            edited_headline = to_sentence_case(edited_headline)
        else:
            edited_headline = to_title_case(edited_headline)

        # 7. Generate diffs
        headline_diff = diff_to_dict(
            generate_word_diff(submission.original_headline, edited_headline)
        )
        body_diff = diff_to_dict(
            generate_word_diff(submission.original_body, edited_body)
        )

        # 8. Merge flags (pre-analysis + AI flags)
        all_flags = pre_flags + ai_flags

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
    ) -> tuple[EditVersion, EditVersion]:
        """Save the original and AI-suggested versions to the database.

        Returns (original_version, ai_version) tuple.
        """
        # Check if original version already exists
        existing = await session.execute(
            sa.select(EditVersion).where(
                EditVersion.submission_id == submission_id,
                EditVersion.version_type == "original",
            )
        )
        original_version = existing.scalar_one_or_none()

        if not original_version:
            original_version = EditVersion(
                submission_id=submission_id,
                version_type="original",
                headline=original_headline,
                body=original_body,
            )
            session.add(original_version)

        ai_version = EditVersion(
            submission_id=submission_id,
            version_type="ai_suggested",
            headline=edit_result.edited_headline,
            body=edit_result.edited_body,
            headline_case=edit_result.headline_case,
            flags=edit_result.flags,
            changes_made=edit_result.changes_made,
            ai_provider=edit_result.ai_provider,
            ai_model=edit_result.ai_model,
        )
        session.add(ai_version)

        await session.flush()
        return original_version, ai_version

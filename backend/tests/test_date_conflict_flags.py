"""Regression coverage for UCM's weekday and date conflict policy (#384, #410)."""

from datetime import date, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa

from app.models.submission import Submission
from app.services.ai.editor import AIEditor
from app.utils.style_checks import (
    detect_changed_source_date_conflicts,
    detect_headline_date_conflicts,
    detect_weekday_date_conflicts,
)


BACKEND = Path(__file__).parents[1]
MIGRATION_PATH = BACKEND / "alembic" / "versions" / "c3e5a7b9d1f4_add_date_conflicts_rule.py"
SEED_PATH = BACKEND / "data" / "style_rules" / "shared_rules.json"

DATE_RULES = [
    {
        "category": "formatting",
        "rule_key": rule_key,
        "rule_text": f"Managed rule {rule_key}.",
        "severity": "error",
    }
    for rule_key in ("ap_style_dates", "date_conflicts")
]


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("date_conflicts_rule", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRuleSeed:
    def test_migration_text_matches_seed(self):
        seeded = {rule["rule_key"]: rule for rule in json.loads(SEED_PATH.read_text())}
        rule = seeded["date_conflicts"]

        assert load_migration().DATE_CONFLICTS_RULE_TEXT == rule["rule_text"]
        assert rule["severity"] == "error"
        assert "keep both exactly as written" in rule["rule_text"]
        assert "keep the body date" in rule["rule_text"]
        assert "after the submission date" in rule["rule_text"]

    def test_upgrade_is_idempotent(self):
        migration = load_migration()
        engine = sa.create_engine("sqlite://")
        metadata = sa.MetaData()
        rules = sa.Table(
            "style_rules",
            metadata,
            sa.Column("Id", sa.String(36), primary_key=True),
            sa.Column("Rule_Set", sa.String(50), nullable=False),
            sa.Column("Category", sa.String(100), nullable=False),
            sa.Column("Rule_Key", sa.String(100), nullable=False),
            sa.Column("Rule_Text", sa.Text, nullable=False),
            sa.Column("Is_Active", sa.Boolean, nullable=False),
            sa.Column("Severity", sa.String(50), nullable=False),
        )
        metadata.create_all(engine)
        with engine.begin() as connection:
            for _ in range(2):
                migration._upsert_rule(
                    connection,
                    rule_set="shared",
                    rule_key="date_conflicts",
                    category="formatting",
                    rule_text=migration.DATE_CONFLICTS_RULE_TEXT,
                    severity="error",
                )
            rows = connection.execute(sa.select(rules)).all()

        assert len(rows) == 1
        assert rows[0].Rule_Text == migration.DATE_CONFLICTS_RULE_TEXT


class TestDetectors:
    def test_conflict_note_states_the_correct_weekday(self):
        assert detect_weekday_date_conflicts(
            "The talk is Tuesday, March 3, 2027.",
            reference_date=date(2027, 2, 1),
        ) == {
            "Tuesday, March 3, 2027": (
                "DATE CONFLICT: MARCH 3, 2027, IS A WEDNESDAY, NOT A TUESDAY"
            )
        }

    def test_conflict_note_names_a_date_that_does_not_exist(self):
        assert detect_weekday_date_conflicts(
            "The talk is Monday, Feb. 30.",
            reference_date=date(2027, 2, 1),
        ) == {"Monday, Feb. 30": "DATE CONFLICT: FEBRUARY 30 DOES NOT EXIST"}

    def test_flags_a_source_conflict_the_edit_corrected(self):
        assert detect_changed_source_date_conflicts(
            "The talk is Tuesday, March 3, 2027.",
            "The talk is Wednesday, March 3, 2027.",
            reference_date=date(2027, 2, 1),
        ) == {
            "Tuesday, March 3, 2027": (
                "DATE CONFLICT: MARCH 3, 2027, IS A WEDNESDAY, NOT A TUESDAY"
            )
        }

    def test_source_conflict_kept_as_written_is_not_a_change(self):
        assert detect_changed_source_date_conflicts(
            "The talk is Tuesday, March 3, 2027.",
            "Hear the talk at 2 p.m. Tuesday, March 3, 2027, in Example Hall.",
            reference_date=date(2027, 2, 1),
        ) == {}

    def test_correct_source_pair_that_the_edit_drops_is_not_judged(self):
        assert detect_changed_source_date_conflicts(
            "The talk is Wednesday, March 3, 2027.",
            "The talk is March 3, 2027.",
            reference_date=date(2027, 2, 1),
        ) == {}

    def test_flags_headline_date_missing_from_body(self):
        assert detect_headline_date_conflicts(
            "Hear the March 4 talk",
            "The talk is 2 p.m. Wednesday, March 3, in Example Hall.",
        ) == ["March 4"]

    def test_headline_date_matching_body_passes(self):
        assert detect_headline_date_conflicts(
            "Hear the Mar. 3 talk",
            "The talk is 2 p.m. Wednesday, March 3, in Example Hall.",
        ) == []

    def test_body_without_a_date_is_not_judged(self):
        assert detect_headline_date_conflicts("Hear the March 4 talk", "Join the talk.") == []


class TestPostAnalyze:
    def _messages(self, headline: str, body: str, source: str, reference: date) -> list[str]:
        flags = AIEditor(llm=None).post_analyze(
            headline,
            body,
            "faculty_staff",
            DATE_RULES,
            source_text=source,
            reference_date=reference,
        )
        return [flag["message"] for flag in flags]

    def test_corrected_source_conflict_is_flagged(self):
        messages = self._messages(
            "Hear a guest talk",
            "The talk is 2 p.m. Wednesday, March 3, 2027.",
            "The talk is Tuesday, March 3, 2027.",
            date(2027, 2, 1),
        )
        assert (
            "Keep the submitted weekday and date as written: 'Tuesday, March 3, 2027' "
            "[DATE CONFLICT: MARCH 3, 2027, IS A WEDNESDAY, NOT A TUESDAY]"
        ) in messages

    def test_headline_conflict_is_flagged(self):
        messages = self._messages(
            "Hear the March 4 talk",
            "The talk is 2 p.m. Wednesday, March 3, 2027.",
            "The talk is Wednesday, March 3, 2027.",
            date(2027, 2, 1),
        )
        assert (
            "Headline date does not appear in the body [DATE CONFLICT: HEADLINE SAYS MARCH 4]"
        ) in messages


class RecordingProvider:
    """Returns the edit unchanged so only deterministic checks add flags."""

    model = "synthetic-model"

    def __init__(self, body: str):
        self.body = body
        self.user_prompts: list[str] = []

    async def complete_json(self, **kwargs):
        self.user_prompts.append(kwargs["user_prompt"])
        return {
            "edited_headline": "Hear a guest talk",
            "edited_body": self.body,
            "changes_made": [],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.9,
        }


@pytest.mark.asyncio
async def test_dates_without_a_year_resolve_from_the_submission_date():
    """Sept. 2 is a Wednesday in 2026 but a Thursday in 2027 (#410)."""
    body = "The talk is 2 p.m. Wednesday, Sept. 2, in Example Hall."
    provider = RecordingProvider(body)
    editor = AIEditor(provider)

    async def no_rules(*_args, **_kwargs):
        return DATE_RULES

    editor.load_style_rules = no_rules
    submission = Submission(
        Id="synthetic-date",
        Category="faculty_staff",
        Target_Newsletter="tdr",
        Original_Headline="Guest talk",
        Original_Body=body,
        Submitter_Name="Synthetic submitter",
        Submitter_Email="synthetic@example.edu",
        Links=[],
        Created_At=datetime(2026, 8, 10, 9, 0),
    )

    result = await editor.edit_submission(None, submission, "tdr")

    assert not [flag for flag in result.flags if "DATE CONFLICT" in flag["message"]]
    # The model resolves yearless dates too, so it must see the same anchor.
    assert provider.user_prompts
    assert "**Submission Date:** Monday, August 10, 2026" in provider.user_prompts[0]


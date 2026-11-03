"""Regression coverage for UCM's acronym order of checks (#381, #399)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa

from app.services.ai.editor import AIEditor
from app.utils.style_checks import (
    detect_undefined_acronyms,
    detect_unneeded_acronym_definitions,
    never_spell_out_acronyms,
)


BACKEND = Path(__file__).parents[1]
MIGRATION_PATH = (
    BACKEND / "alembic" / "versions" / "b2d4f6a8c0e3_apply_acronym_order_of_checks.py"
)
RULES_DIR = BACKEND / "data" / "style_rules"


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("acronym_rules", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seeded_rule(filename: str, rule_key: str) -> dict:
    rules = json.loads((RULES_DIR / filename).read_text())
    return next(rule for rule in rules if rule["rule_key"] == rule_key)


ACRONYM_RULES = [
    {
        "category": "formatting",
        "rule_key": "spell_out_acronyms",
        "rule_text": "Managed acronym rule.",
        "severity": "error",
    }
]


class TestSeedAndMigrationAgree:
    def test_migration_text_matches_seed(self):
        migration = load_migration()
        shared = seeded_rule("shared_rules.json", "spell_out_acronyms")
        myui = seeded_rule("myui_rules.json", "flag_unclear_acronyms")

        assert migration.SHARED_ACRONYM_RULE_TEXT == shared["rule_text"]
        assert migration.MYUI_ACRONYM_RULE_TEXT == myui["rule_text"]

    def test_rule_text_carries_the_approved_lists(self):
        shared = seeded_rule("shared_rules.json", "spell_out_acronyms")["rule_text"]
        myui = seeded_rule("myui_rules.json", "flag_unclear_acronyms")["rule_text"]

        for acronym in ("IMCI", "IRIC", "COBRE", "INBRE", "EPSCoR", "ISUB"):
            assert acronym in shared
        for acronym in ("CALS", "CAA", "ICCU", "LHSOM"):
            assert acronym in myui
            assert acronym not in shared
        assert "only when the acronym appears again" in shared
        assert "When unsure whether an acronym is widely known" in shared

    def test_upsert_is_idempotent_and_leaves_other_rules(self):
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
            connection.execute(
                rules.insert(),
                [
                    {
                        "Id": "stale",
                        "Rule_Set": "shared",
                        "Category": "formatting",
                        "Rule_Key": "spell_out_acronyms",
                        "Rule_Text": "Old acronym wording.",
                        "Is_Active": False,
                        "Severity": "error",
                    },
                    {
                        "Id": "other",
                        "Rule_Set": "shared",
                        "Category": "voice",
                        "Rule_Key": "third_person",
                        "Rule_Text": "Unrelated.",
                        "Is_Active": True,
                        "Severity": "error",
                    },
                ],
            )
            for _ in range(2):
                for rule_set, rule_key, category, text, severity in migration.MANAGED_RULES:
                    migration._upsert_rule(
                        connection,
                        rule_set=rule_set,
                        rule_key=rule_key,
                        category=category,
                        rule_text=text,
                        severity=severity,
                    )
            stored = {
                (row.Rule_Set, row.Rule_Key): row
                for row in connection.execute(sa.select(rules))
            }

        assert len(stored) == 3
        shared = stored[("shared", "spell_out_acronyms")]
        assert shared.Id == "stale"
        assert shared.Is_Active is True
        assert shared.Rule_Text == migration.SHARED_ACRONYM_RULE_TEXT
        assert stored[("myui", "flag_unclear_acronyms")].Rule_Text == (
            migration.MYUI_ACRONYM_RULE_TEXT
        )
        assert stored[("shared", "third_person")].Rule_Text == "Unrelated."


class TestDetectors:
    def test_acronym_used_once_does_not_need_a_parenthetical(self):
        body = "The Example Research Office (ERO) hosts a workshop Tuesday."
        assert detect_unneeded_acronym_definitions("Attend a workshop", body) == ["ERO"]

    def test_acronym_reused_in_body_keeps_its_parenthetical(self):
        body = "The Example Research Office (ERO) hosts a workshop. ERO staff will answer questions."
        assert detect_unneeded_acronym_definitions("Attend a workshop", body) == []

    def test_acronym_reused_only_in_headline_keeps_its_parenthetical(self):
        body = "The Example Research Office (ERO) hosts a workshop Tuesday."
        assert detect_unneeded_acronym_definitions("Join the ERO workshop", body) == []

    def test_never_spell_out_acronym_stands_alone(self):
        standalone = never_spell_out_acronyms("tdr")
        assert detect_undefined_acronyms("IMCI hosts a seminar.", standalone) == []
        body = "The Institute for Modeling Collaboration and Innovation (IMCI) hosts a seminar."
        assert detect_unneeded_acronym_definitions("", body, standalone) == ["IMCI"]

    def test_widely_known_acronyms_are_not_flagged(self):
        assert detect_undefined_acronyms("Learn how AI and GPS tools help NASA.") == []

    def test_myui_list_applies_only_to_my_ui(self):
        body = "CALS students can tour the greenhouse."
        assert detect_undefined_acronyms(body, never_spell_out_acronyms("myui")) == []
        assert detect_undefined_acronyms(body, never_spell_out_acronyms("tdr")) == ["CALS"]


class TestPostAnalyze:
    def _flags(self, headline: str, body: str, newsletter_type: str) -> list[str]:
        flags = AIEditor(llm=None).post_analyze(
            headline,
            body,
            "faculty_staff",
            ACRONYM_RULES,
            newsletter_type=newsletter_type,
        )
        return [flag["message"] for flag in flags if flag["rule_key"] == "spell_out_acronyms"]

    def test_flags_unneeded_and_never_spell_out_definitions(self):
        messages = self._flags(
            "Attend a seminar",
            "The Example Research Office (ERO) and the Idaho Center (COBRE) host a seminar.",
            "tdr",
        )
        assert "Acronym 'ERO' is not used again; write the full name alone" in messages
        assert "Acronym 'COBRE' is on the never-spell-out list; use it alone" in messages

    def test_my_ui_standalone_acronym_passes(self):
        assert self._flags("Tour the greenhouse", "LHSOM students can tour the greenhouse.", "myui") == []

"""Regression coverage for the make official event names survive sentence-case headlines migration."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "d1f4b6c8e2a7_event_name_capitalization_precedence.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("event_name_precedence", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def style_rules_table(metadata: sa.MetaData) -> sa.Table:
    return sa.Table(
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


def test_rule_upserts_are_idempotent_and_preserve_unrelated_rules():
    migration = load_migration()
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    rules = style_rules_table(metadata)
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            rules.insert(),
            [
                {
                    "Id": "stale",
                    "Rule_Set": "shared",
                    "Category": "voice",
                    "Rule_Key": "preserve_event_title_case",
                    "Rule_Text": "Old wording.",
                    "Is_Active": False,
                    "Severity": "info",
                },
                {
                    "Id": "custom",
                    "Rule_Set": "shared",
                    "Category": "voice",
                    "Rule_Key": "staff_custom",
                    "Rule_Text": "Keep this staff rule.",
                    "Is_Active": True,
                    "Severity": "info",
                },
            ],
        )

        for _ in range(2):
            migration._upsert_rule(
                connection,
                rule_set="shared",
                rule_key="preserve_event_title_case",
                category="formatting",
                rule_text=migration.PRESERVE_EVENT_TITLE_RULE_TEXT,
                severity="error",
            )
            migration._upsert_rule(
                connection,
                rule_set="tdr",
                rule_key="sentence_case",
                category="headlines",
                rule_text=migration.TDR_SENTENCE_CASE_RULE_TEXT,
                severity="error",
            )
            migration._upsert_rule(
                connection,
                rule_set="myui",
                rule_key="sentence_case",
                category="headlines",
                rule_text=migration.MYUI_SENTENCE_CASE_RULE_TEXT,
                severity="error",
            )

        rows = connection.execute(sa.select(rules)).mappings().all()

    by_key = {(row["Rule_Set"], row["Rule_Key"]): row for row in rows}
    assert by_key[("shared", "preserve_event_title_case")]["Rule_Text"] == (
        migration.PRESERVE_EVENT_TITLE_RULE_TEXT
    )
    assert by_key[("shared", "preserve_event_title_case")]["Category"] == "formatting"
    assert by_key[("shared", "preserve_event_title_case")]["Severity"] == "error"
    assert by_key[("shared", "preserve_event_title_case")]["Is_Active"] is True
    assert by_key[("tdr", "sentence_case")]["Rule_Text"] == (
        migration.TDR_SENTENCE_CASE_RULE_TEXT
    )
    assert by_key[("tdr", "sentence_case")]["Category"] == "headlines"
    assert by_key[("tdr", "sentence_case")]["Severity"] == "error"
    assert by_key[("tdr", "sentence_case")]["Is_Active"] is True
    assert by_key[("myui", "sentence_case")]["Rule_Text"] == (
        migration.MYUI_SENTENCE_CASE_RULE_TEXT
    )
    assert by_key[("myui", "sentence_case")]["Category"] == "headlines"
    assert by_key[("myui", "sentence_case")]["Severity"] == "error"
    assert by_key[("myui", "sentence_case")]["Is_Active"] is True
    assert by_key[("shared", "staff_custom")]["Rule_Text"] == "Keep this staff rule."
    assert len(rows) == 4


def test_migration_values_match_style_rule_seeds():
    migration = load_migration()
    seed_dir = Path(__file__).parents[1] / "data" / "style_rules"
    seeded_shared = {
        rule["rule_key"]: rule
        for rule in json.loads((seed_dir / "shared_rules.json").read_text())
    }
    seeded_myui = {
        rule["rule_key"]: rule
        for rule in json.loads((seed_dir / "myui_rules.json").read_text())
    }
    seeded_tdr = {
        rule["rule_key"]: rule
        for rule in json.loads((seed_dir / "tdr_rules.json").read_text())
    }

    # The rule-conflict resolution migration supersedes this text with a
    # composition-title exception; test_editorial_rule_conflicts_migration
    # verifies the latest seed value.
    assert seeded_shared["preserve_event_title_case"]["rule_text"] != migration.PRESERVE_EVENT_TITLE_RULE_TEXT
    assert seeded_shared["preserve_event_title_case"]["rule_text"].startswith(
        migration.PRESERVE_EVENT_TITLE_RULE_TEXT
    )
    assert seeded_shared["preserve_event_title_case"]["severity"] == "error"
    assert seeded_shared["preserve_event_title_case"]["category"] == "formatting"
    assert seeded_tdr["sentence_case"]["rule_text"] == migration.TDR_SENTENCE_CASE_RULE_TEXT
    assert seeded_tdr["sentence_case"]["severity"] == "error"
    assert seeded_tdr["sentence_case"]["category"] == "headlines"
    assert seeded_myui["sentence_case"]["rule_text"] == migration.MYUI_SENTENCE_CASE_RULE_TEXT
    assert seeded_myui["sentence_case"]["severity"] == "error"
    assert seeded_myui["sentence_case"]["category"] == "headlines"

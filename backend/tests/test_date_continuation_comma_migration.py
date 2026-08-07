"""Regression coverage for the require date continuation commas migration."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "e4b7c9d2a1f8_require_date_continuation_commas.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("date_continuation_comma", MIGRATION_PATH)
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
                    "Rule_Key": "ap_style_dates",
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
                rule_key="ap_style_dates",
                category="formatting",
                rule_text=migration.AP_DATES_RULE_TEXT,
                severity="warning",
            )

        rows = connection.execute(sa.select(rules)).mappings().all()

    by_key = {row["Rule_Key"]: row for row in rows}
    assert by_key["ap_style_dates"]["Rule_Text"] == migration.AP_DATES_RULE_TEXT
    assert by_key["ap_style_dates"]["Category"] == "formatting"
    assert by_key["ap_style_dates"]["Severity"] == "warning"
    assert by_key["ap_style_dates"]["Is_Active"] is True
    assert by_key["staff_custom"]["Rule_Text"] == "Keep this staff rule."
    assert len(rows) == 2


def test_migration_values_match_style_rule_seeds():
    migration = load_migration()
    seed_dir = Path(__file__).parents[1] / "data" / "style_rules"
    seeded_shared = {
        rule["rule_key"]: rule
        for rule in json.loads((seed_dir / "shared_rules.json").read_text())
    }

    assert seeded_shared["ap_style_dates"]["rule_text"] == migration.AP_DATES_RULE_TEXT
    assert seeded_shared["ap_style_dates"]["severity"] == "warning"
    assert seeded_shared["ap_style_dates"]["category"] == "formatting"

"""Regression coverage for the all-near-term-dates weekday rule migration."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "e2c4a6b8d0f1_extend_weekday_rule_to_all_dates.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("near_term_weekday_rule", MIGRATION_PATH)
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


def test_rule_upsert_is_idempotent_and_preserves_unrelated_rules():
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
                    "Category": "formatting",
                    "Rule_Key": "day_of_week_with_dates",
                    "Rule_Text": "Events only.",
                    "Is_Active": False,
                    "Severity": "warning",
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

        migration._upsert_rule(connection)
        migration._upsert_rule(connection)
        rows = connection.execute(sa.select(rules)).mappings().all()

    by_key = {row["Rule_Key"]: row for row in rows}
    updated = by_key["day_of_week_with_dates"]
    assert updated["Rule_Text"] == migration.DAY_OF_WEEK_RULE_TEXT
    assert updated["Category"] == "formatting"
    assert updated["Severity"] == "error"
    assert updated["Is_Active"] is True
    assert by_key["staff_custom"]["Rule_Text"] == "Keep this staff rule."
    assert len(rows) == 2


def test_migration_matches_the_seeded_rule():
    migration = load_migration()
    seed_path = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"
    seeded = {
        rule["rule_key"]: rule
        for rule in json.loads(seed_path.read_text())
    }

    rule = seeded["day_of_week_with_dates"]
    assert rule["rule_text"] == migration.DAY_OF_WEEK_RULE_TEXT
    assert rule["category"] == "formatting"
    assert rule["severity"] == "error"

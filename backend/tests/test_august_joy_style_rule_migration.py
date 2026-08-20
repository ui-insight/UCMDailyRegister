"""Regression coverage for the August Joy style-rule migration."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "a5d7e9f1b3c2_apply_august_joy_style_rules.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("august_joy_rules", MIGRATION_PATH)
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
                    "Id": "event-order",
                    "Rule_Set": "shared",
                    "Category": "formatting",
                    "Rule_Key": "event_detail_ordering",
                    "Rule_Text": "Old event order wording.",
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

        for _ in range(2):
            migration._upsert_rule(
                connection,
                rule_key="event_detail_ordering",
                category="formatting",
                rule_text=migration.EVENT_RULE_TEXT,
                severity="error",
            )
            migration._upsert_rule(
                connection,
                rule_key="vandal_gear_capitalization",
                category="terminology",
                rule_text=migration.VANDAL_GEAR_RULE_TEXT,
                severity="error",
            )

        rows = connection.execute(sa.select(rules)).mappings().all()

    by_key = {row["Rule_Key"]: row for row in rows}
    assert by_key["event_detail_ordering"]["Rule_Text"] == migration.EVENT_RULE_TEXT
    assert by_key["event_detail_ordering"]["Severity"] == "error"
    assert by_key["event_detail_ordering"]["Is_Active"] is True
    assert by_key["vandal_gear_capitalization"]["Rule_Text"] == (
        migration.VANDAL_GEAR_RULE_TEXT
    )
    assert by_key["vandal_gear_capitalization"]["Severity"] == "error"
    assert by_key["staff_custom"]["Rule_Text"] == "Keep this staff rule."
    assert len(rows) == 3


def test_migration_values_match_shared_style_rule_seed():
    migration = load_migration()
    seed_path = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"
    seeded = {rule["rule_key"]: rule for rule in json.loads(seed_path.read_text())}

    # The Aug. 20 clarification supersedes this wording and makes the
    # time-first constraint explicit. Its focused migration test verifies
    # exact seed parity.
    assert seeded["event_detail_ordering"]["rule_text"] != migration.EVENT_RULE_TEXT
    assert "Never place the day or date before the time" in (
        seeded["event_detail_ordering"]["rule_text"]
    )
    assert seeded["event_detail_ordering"]["severity"] == "error"
    assert seeded["vandal_gear_capitalization"]["rule_text"] == (
        migration.VANDAL_GEAR_RULE_TEXT
    )
    assert seeded["vandal_gear_capitalization"]["severity"] == "error"

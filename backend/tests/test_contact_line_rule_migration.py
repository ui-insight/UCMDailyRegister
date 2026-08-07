"""Regression coverage for the contact-line format style-rule migration."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "d8f2a6c4e9b3_add_contact_line_format_rule.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("contact_line_rule", MIGRATION_PATH)
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
                    "Id": "stale-contact",
                    "Rule_Set": "shared",
                    "Category": "voice",
                    "Rule_Key": "contact_line_format",
                    "Rule_Text": "Old contact wording.",
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
                rule_key="contact_line_format",
                category="formatting",
                rule_text=migration.CONTACT_LINE_RULE_TEXT,
                severity="error",
            )

        rows = connection.execute(sa.select(rules)).mappings().all()

    by_key = {row["Rule_Key"]: row for row in rows}
    assert by_key["contact_line_format"]["Rule_Text"] == (
        migration.CONTACT_LINE_RULE_TEXT
    )
    assert by_key["contact_line_format"]["Category"] == "formatting"
    assert by_key["contact_line_format"]["Severity"] == "error"
    assert by_key["contact_line_format"]["Is_Active"] is True
    assert by_key["staff_custom"]["Rule_Text"] == "Keep this staff rule."
    assert len(rows) == 2


def test_migration_values_match_shared_style_rule_seed():
    migration = load_migration()
    seed_path = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"
    seeded = {rule["rule_key"]: rule for rule in json.loads(seed_path.read_text())}

    assert seeded["contact_line_format"]["rule_text"] == (
        migration.CONTACT_LINE_RULE_TEXT
    )
    assert seeded["contact_line_format"]["severity"] == "error"
    assert seeded["contact_line_format"]["category"] == "formatting"

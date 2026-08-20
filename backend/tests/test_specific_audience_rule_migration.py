"""Regression coverage for the specific-audience language rule migration."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "a4c6e8f0b2d3_preserve_specific_audience_language.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "preserve_specific_audience_language", MIGRATION_PATH
    )
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
                    "Rule_Key": "cta_structure",
                    "Rule_Text": "Old wording.",
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

        migration._upsert_rules(connection)
        migration._upsert_rules(connection)
        rows = connection.execute(sa.select(rules)).mappings().all()

    by_key = {row["Rule_Key"]: row for row in rows}
    assert len(rows) == len(migration.RULES) + 1
    assert by_key["staff_custom"]["Rule_Text"] == "Keep this staff rule."
    for category, rule_key, rule_text, severity in migration.RULES:
        updated = by_key[rule_key]
        assert updated["Category"] == category
        assert updated["Rule_Text"] == rule_text
        assert updated["Severity"] == severity
        assert updated["Is_Active"] is True


def test_migration_matches_seeded_rules():
    migration = load_migration()
    seed_path = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"
    seeded = {rule["rule_key"]: rule for rule in json.loads(seed_path.read_text())}

    for category, rule_key, rule_text, severity in migration.RULES:
        rule = seeded[rule_key]
        assert rule["category"] == category
        if rule_key == "preserve_audience_scope":
            # The Aug. 20 clarification adds the channel-metadata prohibition.
            assert rule["rule_text"] != rule_text
        else:
            assert rule["rule_text"] == rule_text
        assert rule["severity"] == severity

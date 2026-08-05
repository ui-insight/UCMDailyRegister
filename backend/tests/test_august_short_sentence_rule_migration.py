"""Regression coverage for the mandatory short-sentence rule migration."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "b6e8f0a2c4d1_enforce_short_complete_sentences.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("short_sentence_rule", MIGRATION_PATH)
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
                    "Id": "short-sentences",
                    "Rule_Set": "shared",
                    "Category": "voice",
                    "Rule_Key": "short_sentences",
                    "Rule_Text": "Old sentence wording.",
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

        migration._upsert_short_sentence_rule(connection)
        migration._upsert_short_sentence_rule(connection)
        rows = connection.execute(sa.select(rules)).mappings().all()

    by_key = {row["Rule_Key"]: row for row in rows}
    assert by_key["short_sentences"]["Rule_Text"] == migration.SHORT_SENTENCE_RULE_TEXT
    assert by_key["short_sentences"]["Severity"] == "error"
    assert by_key["short_sentences"]["Is_Active"] is True
    assert by_key["staff_custom"]["Rule_Text"] == "Keep this staff rule."
    assert len(rows) == 2


def test_rule_upsert_inserts_once_when_the_seed_row_is_missing():
    migration = load_migration()
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    rules = style_rules_table(metadata)
    metadata.create_all(engine)

    with engine.begin() as connection:
        migration._upsert_short_sentence_rule(connection)
        migration._upsert_short_sentence_rule(connection)
        rows = connection.execute(sa.select(rules)).mappings().all()

    assert len(rows) == 1
    assert rows[0]["Id"]
    assert rows[0]["Rule_Key"] == "short_sentences"
    assert rows[0]["Severity"] == "error"


def test_migration_values_match_shared_style_rule_seed():
    migration = load_migration()
    seed_path = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"
    seeded = {rule["rule_key"]: rule for rule in json.loads(seed_path.read_text())}

    assert seeded["short_sentences"]["rule_text"] == migration.SHORT_SENTENCE_RULE_TEXT
    assert seeded["short_sentences"]["severity"] == "error"

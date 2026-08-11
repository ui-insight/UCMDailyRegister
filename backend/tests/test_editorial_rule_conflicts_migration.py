"""Regression coverage for the editorial rule-conflict resolution migration."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "c5e7a9b1d3f6_resolve_editorial_rule_conflicts.py"
)
SEED_PATH = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rule_conflicts", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seeded_rules() -> dict[str, dict]:
    return {rule["rule_key"]: rule for rule in json.loads(SEED_PATH.read_text())}


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
                    "Category": "content_filtering",
                    "Rule_Key": "no_fabricated_content",
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

        for _ in range(2):
            migration._apply_style_rule_updates(connection)

        rows = connection.execute(sa.select(rules)).mappings().all()

    by_key = {row["Rule_Key"]: row for row in rows}
    assert len(rows) == len(migration.STYLE_RULE_UPDATES) + 1
    assert by_key["staff_custom"]["Rule_Text"] == "Keep this staff rule."
    assert by_key["no_fabricated_content"]["Id"] == "stale"
    assert by_key["no_fabricated_content"]["Is_Active"] is True


def test_migration_matches_shared_seed_values():
    migration = load_migration()
    seeded = seeded_rules()

    for rule in migration.STYLE_RULE_UPDATES:
        seed = seeded[rule["rule_key"]]
        assert rule["rule_text"] == seed["rule_text"]
        assert rule["category"] == seed["category"]
        assert rule["severity"] == seed["severity"]


def test_acronym_expansions_are_authorized_and_flagged_for_review():
    rule_text = seeded_rules()["no_fabricated_content"]["rule_text"]

    assert "standard full name of an acronym" in rule_text
    assert "warning flag naming spell_out_acronyms" in rule_text


def test_composition_titles_take_precedence_over_event_title_rules():
    seeded = seeded_rules()

    assert "takes precedence over event-title preservation" in (
        seeded["composition_title_format"]["rule_text"]
    )
    assert "format it under the composition-title rule instead" in (
        seeded["preserve_event_title_case"]["rule_text"]
    )
    assert "quote it per the composition-title rule" in (
        seeded["no_event_name_quotes"]["rule_text"]
    )

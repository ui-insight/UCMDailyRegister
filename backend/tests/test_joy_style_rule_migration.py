"""Regression coverage for the targeted Joy style-rule data migration."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "c4f8a2d6e9b1_apply_joy_style_rule_updates.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("joy_style_rule_migration", MIGRATION_PATH)
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


def test_migration_repairs_drift_without_touching_unrelated_staff_rules():
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
                    "Id": "stale-title-case",
                    "Rule_Set": "myui",
                    "Category": "headlines",
                    "Rule_Key": "title_case",
                    "Rule_Text": "Headlines must be title case.",
                    "Is_Active": True,
                    "Severity": "error",
                },
                {
                    "Id": "old-sentence-case",
                    "Rule_Set": "myui",
                    "Category": "headlines",
                    "Rule_Key": "sentence_case",
                    "Rule_Text": "Old sentence-case text.",
                    "Is_Active": True,
                    "Severity": "warning",
                },
                {
                    "Id": "custom-staff-rule",
                    "Rule_Set": "shared",
                    "Category": "voice",
                    "Rule_Key": "staff_custom",
                    "Rule_Text": "A staff-authored rule that must survive.",
                    "Is_Active": False,
                    "Severity": "info",
                },
            ],
        )

        migration._apply_style_rule_updates(connection)
        # The helper should be safe if a migration is retried during recovery.
        migration._apply_style_rule_updates(connection)

        rows = connection.execute(sa.select(rules)).mappings().all()

    by_key = {(row["Rule_Set"], row["Rule_Key"]): row for row in rows}
    assert ("myui", "title_case") not in by_key

    expected = {
        (rule["rule_set"], rule["rule_key"]): rule
        for rule in migration.STYLE_RULE_UPDATES
    }
    for key, rule in expected.items():
        assert by_key[key]["Rule_Text"] == rule["rule_text"]
        assert by_key[key]["Category"] == rule["category"]
        assert by_key[key]["Severity"] == rule["severity"]
        assert by_key[key]["Is_Active"] is True

    custom = by_key[("shared", "staff_custom")]
    assert custom["Rule_Text"] == "A staff-authored rule that must survive."
    assert custom["Is_Active"] is False
    assert len(rows) == len(expected) + 1


def test_migration_values_match_the_style_rule_seed_files():
    migration = load_migration()
    data_dir = Path(__file__).parents[1] / "data" / "style_rules"
    seeded = {}
    for rule_set in ("shared", "tdr", "myui"):
        rules = json.loads((data_dir / f"{rule_set}_rules.json").read_text())
        seeded.update({(rule_set, rule["rule_key"]): rule for rule in rules})

    for rule in migration.STYLE_RULE_UPDATES:
        key = (rule["rule_set"], rule["rule_key"])
        assert seeded[key]["category"] == rule["category"]
        assert seeded[key]["rule_text"] == rule["rule_text"]
        assert seeded[key]["severity"] == rule["severity"]

    assert ("myui", "title_case") not in seeded

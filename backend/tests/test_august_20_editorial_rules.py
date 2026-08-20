"""Regression coverage for Joy's Aug. 20 editorial-rule clarifications."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


SEED_PATH = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"
MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "c7e9a1b3d5f2_align_august_20_editorial_rules.py"
)


def seeded_rules() -> dict[str, dict]:
    return {rule["rule_key"]: rule for rule in json.loads(SEED_PATH.read_text())}


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("august_20_rules", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_clarified_rules_are_mandatory_and_unambiguous():
    rules = seeded_rules()
    required_fragments = {
        "today_tomorrow": "Never replace or remove the calendar date",
        "ap_style_times": "when a range crosses a.m. and p.m.",
        "event_detail_ordering": "Never place the day or date before the time",
        "ampersand_to_and": "except Q&A",
        "preserve_event_title_case": "ampersand rule is the sole wording exception",
        "preserve_audience_scope": "distribution metadata, never source content",
    }

    for rule_key, fragment in required_fragments.items():
        assert fragment in rules[rule_key]["rule_text"]
        assert rules[rule_key]["severity"] == "error"


def test_migration_is_idempotent_and_matches_shared_seed():
    migration = load_migration()
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
    engine = sa.create_engine("sqlite://")
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            rules.insert().values(
                Id="stale-rule",
                Rule_Set="shared",
                Category="formatting",
                Rule_Key="ampersand_to_and",
                Rule_Text="Old text",
                Is_Active=False,
                Severity="warning",
            )
        )
        for _ in range(2):
            migration._apply_style_rule_updates(connection)
        rows = connection.execute(sa.select(rules)).mappings().all()

    seeded = seeded_rules()
    assert len(rows) == len(migration.STYLE_RULE_UPDATES)
    for row in rows:
        seed = seeded[row["Rule_Key"]]
        assert row["Rule_Text"] == seed["rule_text"]
        assert row["Category"] == seed["category"]
        assert row["Severity"] == seed["severity"]
        assert row["Is_Active"] is True

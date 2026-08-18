"""Regression coverage for Joy's Aug. 10 AI editorial-rule feedback."""

import json
import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


SEED_PATH = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"
MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "a7c9e1f3b5d2_apply_august_10_joy_rules.py"
)


def seeded_rules() -> dict[str, dict]:
    return {rule["rule_key"]: rule for rule in json.loads(SEED_PATH.read_text())}


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("august_10_joy_rules", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_august_10_rules_are_seeded_as_mandatory_contracts():
    rules = seeded_rules()
    required_fragments = {
        "spell_out_acronyms": "No acronym may appear before",
        "ap_style_dates": "When a month appears without a specific date",
        "ap_style_times": "lowercase a.m. and p.m. with periods",
        "single_cta": "Each call to action must appear only once",
        "online_not_platform": "Use the word 'online' instead of platform names",
        "preserve_audience_scope": "Do not narrow, broaden or genericize",
        "composition_title_format": "single quotation marks in headlines",
        "building_room_order": "building name first",
        "approved_off_campus_addresses": "Kenworthy Performing Arts Centre, 508 S. Main St.",
        "preserve_purpose_contact_titles": "Preserve the purpose",
    }

    for rule_key, fragment in required_fragments.items():
        assert fragment in rules[rule_key]["rule_text"]
        assert rules[rule_key]["severity"] == "error"


def test_cta_rule_does_not_require_a_duplicate_closing_action():
    rule = seeded_rules()["cta_structure"]

    assert "close with an explicit final call to action" not in rule["rule_text"]
    assert "Edit user-supplied linked text" in rule["rule_text"]
    assert rule["severity"] == "error"


def test_canonical_addresses_are_an_explicit_no_fabrication_exception():
    rule = seeded_rules()["no_fabricated_content"]

    assert "approved canonical expansions or addresses" in rule["rule_text"]


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
        for _ in range(2):
            migration._apply_style_rule_updates(connection)
        rows = connection.execute(sa.select(rules)).mappings().all()

    seeded = seeded_rules()
    assert len(rows) == len(migration.STYLE_RULE_UPDATES)
    # Later focused migrations supersede these original texts; their own
    # migration tests verify the latest seed values.
    superseded = {
        "cta_structure",
        "no_fabricated_content",
        "composition_title_format",
        "preserve_audience_scope",
        "preserve_purpose_contact_titles",
    }
    for row in rows:
        seed = seeded[row["Rule_Key"]]
        if row["Rule_Key"] in superseded:
            assert row["Rule_Text"] != seed["rule_text"]
        else:
            assert row["Rule_Text"] == seed["rule_text"]
        assert row["Category"] == seed["category"]
        assert row["Severity"] == seed["severity"]
        assert row["Is_Active"] is True

"""Official forms of U of I Vandal terms (#480): seed, migration and check.

All copy here is synthetic.
"""

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa

from app.services.ai.editor import AIEditor
from app.utils.style_checks import (
    OFFICIAL_VANDAL_TERMS,
    detect_changed_official_names,
    detect_vandal_term_variants,
    normalize_vandal_terms,
)

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "78a5d8e23c00_add_vandal_terms_rule.py"
)
SHARED_SEED = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"
VANDAL_RULES = [
    {"rule_key": "vandal_terms", "severity": "error", "category": "terminology", "rule_text": "x"},
]

# Joy's nine official forms, each with variants a submitter might write.
VARIANTS = {
    "Vandal Alert": ["VandalAlert", "Vandal alert", "vandal alert", "Vandal-Alert"],
    "VandalCard": ["Vandal Card", "Vandalcard", "vandalcard", "Vandal card", "VANDALCARD"],
    "VandalCARE": ["Vandal Care", "VandalCare", "Vandal CARE", "vandalcare", "Vandal-CARE"],
    "VandalChat": ["Vandal Chat", "Vandalchat", "vandal chat"],
    "Vandal Connect": ["VandalConnect", "Vandal connect", "vandal connect"],
    "Vandal Family": ["VandalFamily", "Vandal family", "vandal family"],
    "Vandal Gear": ["VandalGear", "Vandal gear", "vandal gear"],
    "VandalMail": ["Vandal Mail", "Vandalmail", "vandalmail", "Vandal mail"],
    "VandalStore": ["Vandal Store", "Vandalstore", "Vandal store", "vandal store"],
}


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("vandal_terms_rule", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_official_form_has_variant_cases():
    assert set(VARIANTS) == set(OFFICIAL_VANDAL_TERMS)
    assert len(OFFICIAL_VANDAL_TERMS) == 9


@pytest.mark.parametrize("official", OFFICIAL_VANDAL_TERMS)
def test_official_forms_are_not_flagged(official):
    text = f"Students can learn more about {official} this week. {official}'s team will help."
    assert detect_vandal_term_variants(text) == []
    assert normalize_vandal_terms(text) == text


@pytest.mark.parametrize(
    ("official", "variant"),
    [(official, variant) for official, variants in VARIANTS.items() for variant in variants],
)
def test_variants_are_flagged_and_normalized(official, variant):
    text = f"Students can learn more about {variant} at the Example Hall table."
    assert detect_vandal_term_variants(text) == [(variant, official)]
    assert normalize_vandal_terms(text) == (
        f"Students can learn more about {official} at the Example Hall table."
    )


def test_web_and_email_addresses_are_left_alone():
    text = (
        "Email vandalcard@example.edu or visit example.edu/vandalstore and "
        "vandalmail.example.edu for help."
    )
    assert detect_vandal_term_variants(text) == []
    assert normalize_vandal_terms(text) == text


def test_html_is_stripped_and_longer_words_do_not_match():
    text = (
        '<p>Load funds on your <a href="https://example.edu/vandal-card">Vandal Card</a>.</p>'
        "<p>The Vandal mailing list and Vandal Storefront Gallery are separate.</p>"
    )
    assert detect_vandal_term_variants(text) == [("Vandal Card", "VandalCard")]


def test_repeated_variants_are_reported_once():
    text = "Use your Vandal Card at lunch. Lost your Vandal Card? Replace it."
    assert detect_vandal_term_variants(text) == [("Vandal Card", "VandalCard")]


def test_correcting_a_submitted_variant_is_not_a_changed_official_name():
    source = "Pick up a Vandal Card at the Example Office."
    edited = "Pick up a VandalCard at the Example Office."
    assert "Vandal Card" not in detect_changed_official_names(source, edited)


def test_post_analyze_flags_a_remaining_variant_as_an_error():
    flags = AIEditor(None).post_analyze(
        "Check your Vandalmail",
        "Sign up for Vandal Alert and check your Vandalmail by Friday.",
        "faculty_staff",
        VANDAL_RULES,
    )
    assert flags == [
        {
            "type": "error",
            "rule_key": "vandal_terms",
            "message": "Write 'VandalMail' instead of 'Vandalmail'",
        }
    ]


def test_inactive_rule_silences_the_flag():
    assert AIEditor(None).post_analyze(
        "", "Use your Vandal Card.", "faculty_staff", []
    ) == []


@pytest.mark.asyncio
async def test_a_remaining_variant_sends_the_model_into_one_repair():
    from app.models.submission import Submission

    drafts = [
        {"edited_headline": "", "edited_body": "Use your Vandal Card at the Example Cafe.", "flags": []},
        {"edited_headline": "", "edited_body": "Use your VandalCard at the Example Cafe.", "flags": []},
    ]
    calls = []

    class ScriptedProvider:
        model = "scripted"

        async def complete_json(self, **kwargs):
            calls.append(kwargs)
            return drafts[len(calls) - 1]

    class Editor(AIEditor):
        async def load_style_rules(self, session, newsletter_type):
            return VANDAL_RULES

    submission = Submission(
        Id="synthetic",
        Category="faculty_staff",
        Target_Newsletter="tdr",
        Original_Headline="",
        Original_Body="Use your Vandal Card at the Example Cafe.",
        Submitter_Name="Synthetic",
        Submitter_Email="synthetic@example.edu",
        Created_At=datetime(2026, 11, 16, 9, tzinfo=timezone.utc),
        Links=[],
    )
    result = await Editor(ScriptedProvider()).edit_submission(None, submission, "tdr")
    assert len(calls) == 2
    assert "Write 'VandalCard' instead of 'Vandal Card'" in calls[1]["user_prompt"]
    assert result.edited_body == "Use your VandalCard at the Example Cafe."
    assert not any(flag["rule_key"] == "vandal_terms" for flag in result.flags)


# --- Seed and migration ----------------------------------------------------


def test_seed_matches_migration_and_names_every_term():
    migration = load_migration()
    seeded = {rule["rule_key"]: rule for rule in json.loads(SHARED_SEED.read_text())}
    rule = seeded["vandal_terms"]
    assert rule["rule_text"] == migration.RULE_TEXT
    assert rule["category"] == migration.CATEGORY
    assert rule["severity"] == migration.SEVERITY
    assert "vandal_gear_capitalization" not in seeded
    for official in OFFICIAL_VANDAL_TERMS:
        assert f"'{official}'" in rule["rule_text"]


def _rules_table(metadata: sa.MetaData) -> sa.Table:
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


def _run(rows: list[dict], *steps) -> dict[str, dict]:
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    rules = _rules_table(metadata)
    metadata.create_all(engine)
    with engine.begin() as connection:
        if rows:
            connection.execute(rules.insert(), rows)
        for step in steps:
            step(connection)
        found = connection.execute(sa.select(rules)).mappings().all()
    return {row["Rule_Key"]: dict(row) for row in found}


def _old_rule(migration, **overrides) -> dict:
    return {
        "Id": "gear",
        "Rule_Set": "shared",
        "Category": "terminology",
        "Rule_Key": "vandal_gear_capitalization",
        "Rule_Text": migration.SUPERSEDED_RULE_TEXT,
        "Is_Active": True,
        "Severity": "error",
        **overrides,
    }


STAFF_RULE = {
    "Id": "staff",
    "Rule_Set": "shared",
    "Category": "voice",
    "Rule_Key": "staff_custom",
    "Rule_Text": "Keep me.",
    "Is_Active": True,
    "Severity": "info",
}


def test_upgrade_renames_the_vandal_gear_rule_idempotently():
    migration = load_migration()
    by_key = _run(
        [_old_rule(migration), STAFF_RULE],
        migration.apply_vandal_terms_rule,
        migration.apply_vandal_terms_rule,
    )
    assert set(by_key) == {"vandal_terms", "staff_custom"}
    assert by_key["vandal_terms"]["Id"] == "gear"
    assert by_key["vandal_terms"]["Rule_Text"] == migration.RULE_TEXT
    assert by_key["vandal_terms"]["Severity"] == "error"
    assert by_key["vandal_terms"]["Is_Active"] is True
    assert by_key["staff_custom"]["Rule_Text"] == "Keep me."


def test_upgrade_adds_the_rule_when_vandal_gear_is_missing():
    migration = load_migration()
    by_key = _run([], migration.apply_vandal_terms_rule)
    assert by_key["vandal_terms"]["Rule_Text"] == migration.RULE_TEXT


def test_upgrade_deactivates_vandal_gear_when_both_rules_exist():
    migration = load_migration()
    seeded_new = _old_rule(
        migration, Id="new", Rule_Key="vandal_terms", Rule_Text="Old wording."
    )
    by_key = _run([_old_rule(migration), seeded_new], migration.apply_vandal_terms_rule)
    assert by_key["vandal_terms"]["Rule_Text"] == migration.RULE_TEXT
    assert by_key["vandal_gear_capitalization"]["Is_Active"] is False


def test_downgrade_restores_the_vandal_gear_rule():
    migration = load_migration()
    by_key = _run(
        [_old_rule(migration)],
        migration.apply_vandal_terms_rule,
        migration.restore_vandal_gear_rule,
    )
    assert set(by_key) == {"vandal_gear_capitalization"}
    assert by_key["vandal_gear_capitalization"]["Id"] == "gear"
    assert by_key["vandal_gear_capitalization"]["Rule_Text"] == migration.SUPERSEDED_RULE_TEXT

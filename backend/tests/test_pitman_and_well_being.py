"""Bruce M. Pitman Center on first reference, and "well-being" hyphenated (#529).

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
    detect_changed_official_names,
    detect_pitman_center_reference_issues,
    detect_well_being_variants,
    normalize_pitman_center,
    normalize_well_being,
)

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "d2b4f6a8c0e1_add_pitman_and_well_being_rules.py"
)
SHARED_SEED = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"
RULES = [
    {"rule_key": "pitman_center_first_reference", "severity": "error", "category": "terminology", "rule_text": "x"},
    {"rule_key": "well_being_hyphenated", "severity": "error", "category": "terminology", "rule_text": "x"},
]


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pitman_well_being_rules", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- Bruce M. Pitman Center ------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        "Meet in the Bruce M. Pitman Center International Ballroom.",
        "Meet in the Bruce M. Pitman Center. The Pitman Center opens at 8 a.m.",
        "No building named here.",
        # Addresses aren't references.
        "See example.edu/pitman-center or the Bruce M. Pitman Center.",
    ],
)
def test_correct_references_are_not_flagged(body):
    assert detect_pitman_center_reference_issues(body) == []


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Meet in the Pitman Center Vandal Ballroom.", ["Pitman Center"]),
        ("Meet in the pitman center lobby.", ["pitman center"]),
        ("Meet in the Bruce Pitman Center.", ["Bruce Pitman Center"]),
        ("Meet in the Bruce M Pitman Center.", ["Bruce M Pitman Center"]),
        # A later "Bruce ..." form must still be the full name.
        (
            "Meet in the Bruce M. Pitman Center. Then the Bruce Pitman Center lobby.",
            ["Bruce Pitman Center"],
        ),
        # The first reference is the one that matters; reported once.
        ("The Pitman Center hosts. The Pitman Center closes.", ["Pitman Center"]),
        ("Meet in the <b>Pitman Center</b> lobby.", ["Pitman Center"]),
    ],
)
def test_wrong_first_references_are_flagged(body, expected):
    assert detect_pitman_center_reference_issues(body) == expected


def test_normalize_fills_in_bruce_forms_but_leaves_the_short_form():
    text = "The Bruce Pitman Center and the Pitman Center."
    assert normalize_pitman_center(text) == "The Bruce M. Pitman Center and the Pitman Center."


def test_post_analyze_flags_a_short_first_reference_in_the_body():
    flags = AIEditor(None).post_analyze(
        "Pitman Center open house",
        "Join us 3-4 p.m. Wednesday, Nov. 18, in the Pitman Center Vandal Ballroom.",
        "faculty_staff",
        RULES,
    )
    assert flags == [
        {
            "type": "error",
            "rule_key": "pitman_center_first_reference",
            "message": "Write 'Bruce M. Pitman Center' instead of 'Pitman Center' on first reference",
        }
    ]


def test_correcting_to_the_full_name_is_not_a_changed_official_name():
    source = "Visit the Bruce Pitman Center Example Lounge."
    edited = "Visit the Bruce M. Pitman Center Example Lounge."
    assert detect_changed_official_names(source, edited) == []


# --- well-being ------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Support employee well being this winter.", [("well being", "well-being")]),
        ("Support employee wellbeing this winter.", [("wellbeing", "well-being")]),
        ("Wellbeing matters.", [("Wellbeing", "Well-being")]),
        ("Well being matters.", [("Well being", "Well-being")]),
        ("WELLBEING WEEK", [("WELLBEING", "WELL-BEING")]),
        ("Support well–being.", [("well–being", "well-being")]),
        ("Wellbeing and wellbeing.", [("Wellbeing", "Well-being"), ("wellbeing", "well-being")]),
    ],
)
def test_unhyphenated_forms_are_flagged(text, expected):
    assert detect_well_being_variants(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Support employee well-being this winter.",
        "Well-being matters.",
        "Write to wellbeing@example.edu or visit example.edu/wellbeing.",
        "It went as well being outside as inside.",
    ],
)
def test_correct_forms_and_addresses_are_not_flagged(text):
    assert detect_well_being_variants(text) == []
    assert normalize_well_being(text) == text


def test_normalize_keeps_a_leading_capital():
    assert normalize_well_being("Wellbeing tips for well being.") == (
        "Well-being tips for well-being."
    )


def test_post_analyze_flags_wellbeing_in_the_headline_too():
    flags = AIEditor(None).post_analyze(
        "Wellbeing workshop", "Learn about well-being.", "faculty_staff", RULES
    )
    assert flags == [
        {
            "type": "error",
            "rule_key": "well_being_hyphenated",
            "message": "Write 'Well-being' instead of 'Wellbeing'",
        }
    ]


def test_inactive_rules_silence_the_flags():
    assert AIEditor(None).post_analyze(
        "Wellbeing", "Meet in the Pitman Center.", "faculty_staff", []
    ) == []


def test_hyphenating_a_name_is_not_a_changed_official_name():
    source = "The Employee Wellbeing Program offers coaching."
    edited = "The Employee Well-being Program offers coaching."
    assert "Employee Wellbeing Program" not in detect_changed_official_names(source, edited)


@pytest.mark.asyncio
async def test_a_remaining_issue_sends_the_model_into_one_repair():
    from app.models.submission import Submission

    drafts = [
        {"edited_headline": "", "edited_body": "Wellbeing hour in the Pitman Center.", "flags": []},
        {"edited_headline": "", "edited_body": "Well-being hour in the Bruce M. Pitman Center.", "flags": []},
    ]
    calls = []

    class ScriptedProvider:
        model = "scripted"

        async def complete_json(self, **kwargs):
            calls.append(kwargs)
            return drafts[len(calls) - 1]

    class Editor(AIEditor):
        async def load_style_rules(self, session, newsletter_type):
            return RULES

    submission = Submission(
        Id="synthetic",
        Category="faculty_staff",
        Target_Newsletter="tdr",
        Original_Headline="",
        Original_Body="Wellbeing hour in the Pitman Center.",
        Submitter_Name="Synthetic",
        Submitter_Email="synthetic@example.edu",
        Created_At=datetime(2026, 11, 17, 9, tzinfo=timezone.utc),
        Links=[],
    )
    result = await Editor(ScriptedProvider()).edit_submission(None, submission, "tdr")
    assert len(calls) == 2
    assert "Write 'Well-being' instead of 'Wellbeing'" in calls[1]["user_prompt"]
    assert "Write 'Bruce M. Pitman Center' instead of 'Pitman Center'" in calls[1]["user_prompt"]
    assert result.edited_body == "Well-being hour in the Bruce M. Pitman Center."
    assert not any(
        flag["rule_key"] in {"well_being_hyphenated", "pitman_center_first_reference"}
        for flag in result.flags
    )


# --- Seed and migration ----------------------------------------------------


def _seeded() -> dict[str, dict]:
    return {rule["rule_key"]: rule for rule in json.loads(SHARED_SEED.read_text())}


def test_seed_matches_migration():
    migration = load_migration()
    seeded = _seeded()
    for rule_key, rule_text in migration.NEW_RULES.items():
        assert seeded[rule_key]["rule_text"] == rule_text
        assert seeded[rule_key]["category"] == migration.CATEGORY
        assert seeded[rule_key]["severity"] == migration.SEVERITY
    event_rule = seeded["event_detail_ordering"]["rule_text"]
    assert migration.NEW_EXAMPLE in event_rule
    assert "the Pitman Center" not in event_rule


def _run(rows: list[dict], *steps) -> dict[str, dict]:
    engine = sa.create_engine("sqlite://")
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
    metadata.create_all(engine)
    with engine.begin() as connection:
        if rows:
            connection.execute(rules.insert(), rows)
        for step in steps:
            step(connection)
        found = connection.execute(sa.select(rules)).mappings().all()
    return {row["Rule_Key"]: dict(row) for row in found}


EVENT_RULE = {
    "Id": "event",
    "Rule_Set": "shared",
    "Category": "formatting",
    "Rule_Key": "event_detail_ordering",
    "Rule_Text": "Start with the time. Example: '3-4 p.m. Wednesday, Feb. 12, in the Pitman Center Vandal Ballroom.' Staff note.",
    "Is_Active": True,
    "Severity": "error",
}


def test_upgrade_adds_rules_and_fixes_the_example_idempotently():
    migration = load_migration()
    by_key = _run([EVENT_RULE], migration.apply_rules, migration.apply_rules)
    assert set(by_key) == {
        "event_detail_ordering",
        "pitman_center_first_reference",
        "well_being_hyphenated",
    }
    assert by_key["event_detail_ordering"]["Rule_Text"] == (
        "Start with the time. Example: '3-4 p.m. Wednesday, Feb. 12, in the "
        "Bruce M. Pitman Center Vandal Ballroom.' Staff note."
    )
    for rule_key, rule_text in migration.NEW_RULES.items():
        assert by_key[rule_key]["Rule_Text"] == rule_text
        assert by_key[rule_key]["Is_Active"] is True


def test_upgrade_refreshes_an_existing_row():
    migration = load_migration()
    stale = {**EVENT_RULE, "Id": "w", "Rule_Key": "well_being_hyphenated", "Rule_Text": "Old.", "Is_Active": False}
    by_key = _run([stale], migration.apply_rules)
    assert by_key["well_being_hyphenated"]["Id"] == "w"
    assert by_key["well_being_hyphenated"]["Rule_Text"] == migration.WELL_BEING_RULE_TEXT
    assert by_key["well_being_hyphenated"]["Is_Active"] is True


def test_downgrade_restores_the_previous_state():
    migration = load_migration()
    by_key = _run([EVENT_RULE], migration.apply_rules, migration.remove_rules)
    assert set(by_key) == {"event_detail_ordering"}
    assert by_key["event_detail_ordering"]["Rule_Text"] == EVENT_RULE["Rule_Text"]

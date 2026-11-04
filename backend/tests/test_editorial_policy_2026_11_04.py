"""Editorial policy 2026-11-04: migration, seeds and prompt stay in step (#409)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa

from app.services.ai.prompts import build_edit_user_prompt, build_system_prompt


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "d6e8f0a2b4c7_editorial_policy_2026_11_04.py"
)
SEED_DIR = Path(__file__).parents[1] / "data" / "style_rules"
SEED_FILES = {"shared": "shared_rules.json", "tdr": "tdr_rules.json", "myui": "myui_rules.json"}


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("editorial_policy", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seeded(rule_set: str) -> dict[str, dict]:
    rules = json.loads((SEED_DIR / SEED_FILES[rule_set]).read_text(encoding="utf-8"))
    return {rule["rule_key"]: rule for rule in rules}


def test_migration_matches_seeds():
    for rule_set, rule_key, category, rule_text, severity in load_migration().MANAGED_RULES:
        seed = seeded(rule_set)[rule_key]
        assert seed["rule_text"] == rule_text, rule_key
        assert seed["category"] == category, rule_key
        assert seed["severity"] == severity, rule_key


def test_migration_upserts_are_idempotent_and_keep_staff_rules():
    migration = load_migration()
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
        connection.execute(rules.insert(), [
            {"Id": "old", "Rule_Set": "shared", "Category": "voice",
             "Rule_Key": "no_exclamation_marks", "Rule_Text": "Old.",
             "Is_Active": True, "Severity": "warning"},
            {"Id": "staff", "Rule_Set": "shared", "Category": "voice",
             "Rule_Key": "staff_custom", "Rule_Text": "Keep me.",
             "Is_Active": True, "Severity": "info"},
        ])
        for _ in range(2):
            for rule_set, rule_key, category, rule_text, severity in migration.MANAGED_RULES:
                migration._upsert_rule(
                    connection,
                    rule_set=rule_set,
                    rule_key=rule_key,
                    category=category,
                    rule_text=rule_text,
                    severity=severity,
                )
        rows = connection.execute(sa.select(rules)).mappings().all()

    by_key = {(row["Rule_Set"], row["Rule_Key"]): row for row in rows}
    assert len(rows) == len(migration.MANAGED_RULES) + 1
    assert by_key[("shared", "no_exclamation_marks")]["Severity"] == "error"
    assert by_key[("shared", "staff_custom")]["Rule_Text"] == "Keep me."


def test_policy_rules_carry_the_decisions():
    shared = seeded("shared")
    assert "already clear and concise" in shared["conservative_rewording"]["rule_text"]
    assert "[NAME VARIES IN SUBMISSION: CONFIRM OFFICIAL NAME]" in shared["protected_names"]["rule_text"]
    assert "[CONFIRM VENUE NAME]" in shared["protected_names"]["rule_text"]
    assert "never comes before the event details" in shared["item_sentence_order"]["rule_text"]
    assert "unless the submitter notes ask to keep it" in shared["trim_outside_quotes"]["rule_text"]
    headline = shared["headline_rules"]["rule_text"]
    for phrase in ("specific action", "complete phrase", "same wording", "sentence case", "exclamation"):
        assert phrase in headline
    assert "'can', not 'may'" in shared["direct_action_wording"]["rule_text"]
    assert "also will give" in shared["adverb_placement"]["rule_text"]


def test_hard_coded_prompt_follows_headline_and_rewording_decisions():
    prompt = build_system_prompt("tdr", [], "calendar_event")
    assert "Keep it short" not in prompt
    assert '"Attend..."' not in prompt
    assert "already clear and concise" in prompt
    assert "flags list" in prompt

    user_prompt = build_edit_user_prompt("Headline", "Body", None, None, "news")
    assert 'AFTER headline: "Vandal Health Clinic closure"' not in user_prompt


def test_curly_quotes_convert_prose_and_leave_html_alone():
    from app.services.ai.editor import enforce_curly_quotes

    text, changed = enforce_curly_quotes(
        "Don't miss \"Example\" at <a href='https://example.edu/a'>the class of '26 show</a>."
    )
    assert changed
    assert text == (
        "Don’t miss “Example” at <a href='https://example.edu/a'>the class of ’26 show</a>."
    )
    assert enforce_curly_quotes("“Already curly” and ’26") == ("“Already curly” and ’26", False)


def test_headline_exclamations_are_stripped():
    from app.services.ai.editor import strip_headline_exclamations

    assert strip_headline_exclamations("Buy tickets to the Example Gala!!") == (
        "Buy tickets to the Example Gala",
        True,
    )
    assert strip_headline_exclamations("Register for the workshop") == (
        "Register for the workshop",
        False,
    )


def test_review_notes_and_echoed_headlines_are_detected():
    from app.utils.style_checks import detect_headline_echoes_lead, detect_review_notes_in_copy

    assert detect_review_notes_in_copy("Meet in [CONFIRM VENUE NAME] at noon.") == [
        "[CONFIRM VENUE NAME]"
    ]
    assert detect_review_notes_in_copy("A citation [sic] stays.") == []
    assert detect_headline_echoes_lead(
        "Sign up for the sustainability newsletter",
        "<p>Sign up for the sustainability newsletter to get monthly updates.</p>",
    )
    assert not detect_headline_echoes_lead(
        "Buy handmade pottery at the Example Center sale",
        "The Example Center will hold its pottery sale Saturday.",
    )


def test_policy_fingerprint_names_version_and_tracks_rule_changes():
    from app.services.ai.prompts import EDITORIAL_POLICY_VERSION, policy_fingerprint

    rules = [{"rule_set": "shared", "rule_key": "a", "severity": "error", "rule_text": "One."}]
    first = policy_fingerprint(rules)
    assert first.startswith(f"{EDITORIAL_POLICY_VERSION}:")
    assert len(first) <= 64
    assert policy_fingerprint(list(reversed(rules))) == first
    assert policy_fingerprint([{**rules[0], "rule_text": "Two."}]) != first

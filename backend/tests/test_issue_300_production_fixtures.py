"""Production-derived regression fixtures for Joy's Aug. 10 feedback (#300)."""

import json
from pathlib import Path

import pytest

from app.models.submission import Submission
from app.services.ai.editor import AIEditor


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "joy_august_10_editorial.json"
SEED_PATH = Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json"


class UnusedProvider:
    """Provider placeholder for exercising deterministic post-validation."""


class RepairSequenceProvider:
    """Return a reported bad draft, then the corresponding compliant repair."""

    model = "fixture-model"

    def __init__(self, fixture: dict):
        self.fixture = fixture
        self.prompts: list[str] = []

    async def complete_json(self, **kwargs):
        self.prompts.append(kwargs["user_prompt"])
        prefix = "edited" if len(self.prompts) == 1 else "compliant"
        return {
            "edited_headline": self.fixture[f"{prefix}_headline"],
            "edited_body": self.fixture[f"{prefix}_body"],
            "changes_made": [],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.9,
        }


class FailedRepairProvider(RepairSequenceProvider):
    """Return the reported bad draft, then simulate a provider failure."""

    async def complete_json(self, **kwargs):
        if self.prompts:
            self.prompts.append(kwargs["user_prompt"])
            raise RuntimeError("repair unavailable")
        return await super().complete_json(**kwargs)


class StubbornProvider(RepairSequenceProvider):
    """Return the same noncompliant draft for the initial and repair calls."""

    async def complete_json(self, **kwargs):
        self.prompts.append(kwargs["user_prompt"])
        return {
            "edited_headline": self.fixture["edited_headline"],
            "edited_body": self.fixture["edited_body"],
            "changes_made": [],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.5,
        }


def load_fixtures() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text())


def load_active_rules() -> list[dict]:
    return [
        {
            "category": rule["category"],
            "rule_key": rule["rule_key"],
            "rule_text": rule["rule_text"],
            "severity": rule["severity"],
        }
        for rule in json.loads(SEED_PATH.read_text())
    ]


@pytest.mark.parametrize("fixture", load_fixtures(), ids=lambda item: item["name"])
def test_reported_noncompliant_edits_are_detected(fixture: dict):
    editor = AIEditor(UnusedProvider())
    flags = editor.post_analyze(
        fixture["edited_headline"],
        fixture["edited_body"],
        fixture["category"],
        load_active_rules(),
        source_text=f'{fixture["source_headline"]}\n{fixture["source_body"]}',
        source_body=fixture["source_body"],
    )

    flagged_rules = {flag["rule_key"] for flag in flags}
    assert set(fixture["expected_rule_keys"]).issubset(flagged_rules)


def test_ignored_active_rule_is_distinct_from_missing_rule():
    fixture = next(
        item for item in load_fixtures() if item["name"] == "tumbbad_screening"
    )
    active_rules = load_active_rules()
    editor = AIEditor(UnusedProvider())

    active_flags = editor.post_analyze(
        fixture["edited_headline"],
        fixture["edited_body"],
        fixture["category"],
        active_rules,
        source_text=f'{fixture["source_headline"]}\n{fixture["source_body"]}',
        source_body=fixture["source_body"],
    )
    without_address_rule = [
        rule
        for rule in active_rules
        if rule["rule_key"] != "approved_off_campus_addresses"
    ]
    missing_rule_flags = editor.post_analyze(
        fixture["edited_headline"],
        fixture["edited_body"],
        fixture["category"],
        without_address_rule,
        source_text=f'{fixture["source_headline"]}\n{fixture["source_body"]}',
        source_body=fixture["source_body"],
    )

    assert "approved_off_campus_addresses" in {
        flag["rule_key"] for flag in active_flags
    }
    assert "approved_off_campus_addresses" not in {
        flag["rule_key"] for flag in missing_rule_flags
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("fixture", load_fixtures(), ids=lambda item: item["name"])
async def test_active_must_rule_violations_trigger_one_compliance_repair(fixture: dict):
    provider = RepairSequenceProvider(fixture)
    editor = AIEditor(provider)

    async def load_fixture_rules(*_args, **_kwargs):
        return load_active_rules()

    editor.load_style_rules = load_fixture_rules
    submission = Submission(
        Id=fixture["id"],
        Category=fixture["category"],
        Target_Newsletter="myui" if fixture["category"] == "student" else "tdr",
        Original_Headline=fixture["source_headline"],
        Original_Body=fixture["source_body"],
        Submitter_Name="Production fixture",
        Submitter_Email="fixture@example.edu",
        Links=[],
    )

    result = await editor.edit_submission(
        None,
        submission,
        submission.Target_Newsletter,
    )

    assert len(provider.prompts) == 2
    assert "Deterministic compliance findings" in provider.prompts[1]
    assert result.edited_headline == fixture["compliant_headline"]
    assert result.edited_body == fixture["compliant_body"]
    assert not (
        set(fixture["expected_rule_keys"])
        & {flag["rule_key"] for flag in result.flags}
    )


def make_submission(fixture: dict) -> Submission:
    return Submission(
        Id=fixture["id"],
        Category=fixture["category"],
        Target_Newsletter="myui" if fixture["category"] == "student" else "tdr",
        Original_Headline=fixture["source_headline"],
        Original_Body=fixture["source_body"],
        Submitter_Name="Production fixture",
        Submitter_Email="fixture@example.edu",
        Links=[],
    )


@pytest.mark.asyncio
async def test_failed_repair_preserves_initial_draft_and_findings():
    fixture = load_fixtures()[0]
    provider = FailedRepairProvider(fixture)
    editor = AIEditor(provider)

    async def load_fixture_rules(*_args, **_kwargs):
        return load_active_rules()

    editor.load_style_rules = load_fixture_rules
    result = await editor.edit_submission(
        None,
        make_submission(fixture),
        "tdr",
    )

    assert len(provider.prompts) == 2
    assert result.edited_body == fixture["edited_body"]
    assert set(fixture["expected_rule_keys"]).issubset(
        {flag["rule_key"] for flag in result.flags}
    )


@pytest.mark.asyncio
async def test_noncompliant_repair_is_not_retried_indefinitely():
    fixture = load_fixtures()[0]
    provider = StubbornProvider(fixture)
    editor = AIEditor(provider)

    async def load_fixture_rules(*_args, **_kwargs):
        return load_active_rules()

    editor.load_style_rules = load_fixture_rules
    result = await editor.edit_submission(
        None,
        make_submission(fixture),
        "tdr",
    )

    assert len(provider.prompts) == 2
    assert set(fixture["expected_rule_keys"]).issubset(
        {flag["rule_key"] for flag in result.flags}
    )

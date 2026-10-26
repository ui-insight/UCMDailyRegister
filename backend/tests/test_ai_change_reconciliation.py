"""Change logs and flags describe the final saved edit (#440).

All copy is synthetic. The provider is stubbed, so these tests cover the
pipeline's reconciliation, not representative model acceptance.
"""

import asyncio

import pytest
from httpx import AsyncClient

from app.models.submission import Submission
from app.services.ai.editor import AIEditor, reconcile_changes
from tests.conftest import TestSession, make_submission_data


SOURCE_HEADLINE = "Science & Society lecture"
SOURCE_BODY = (
    "Join us for the Science & Society lecture at 6 p.m. Wednesday, Oct. 28, "
    "in the Example Building. Bring a friend!"
)
ACTIVE_RULES = [
    {
        "category": "punctuation",
        "rule_key": "ampersand_to_and",
        "rule_text": "Use 'and' instead of '&'.",
        "severity": "error",
    },
    {
        "category": "voice",
        "rule_key": "third_person",
        "rule_text": "Write in third person.",
        "severity": "error",
    },
    {
        "category": "punctuation",
        "rule_key": "no_exclamation_marks",
        "rule_text": "Do not use exclamation marks.",
        "severity": "warning",
    },
]


class ReversedChangeProvider:
    """First draft moves the date; the repair restores it and fixes '&'."""

    model = "fixture-model"

    def __init__(self):
        self.calls = 0

    async def complete_json(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return {
                "edited_headline": "Attend the Science & Society lecture",
                "edited_body": (
                    "The Science & Society lecture is at 6 p.m. Thursday, Oct. 29, "
                    "in the Example Building."
                ),
                "changes_made": [
                    "Changed 'Oct. 28' to 'Oct. 29'",
                    "Removed the exclamation mark",
                    "Rewrote the opening in third person",
                ],
                "flags": [
                    {
                        "type": "warning",
                        "rule_key": "ap_style_dates",
                        "message": "Changed the event date; confirm with the submitter",
                    }
                ],
                "embedded_links": [],
                "confidence": 0.8,
            }
        return {
            "edited_headline": "Attend the Science and Society lecture",
            "edited_body": (
                "The Science and Society lecture is at 6 p.m. Wednesday, Oct. 28, "
                "in the Example Building."
            ),
            "changes_made": [
                "Changed 'Oct. 28' to 'Oct. 29'",
                "Replaced '&' with 'and'",
                "Removed the exclamation mark",
                "removed the exclamation mark.",
                "Rewrote the opening in third person",
                "Deleted the closing invitation sentence",
                "Revised the first draft after the compliance findings",
            ],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.9,
        }


class UnresolvedExclamationProvider:
    """Single pass that keeps the source exclamation mark."""

    model = "fixture-model"

    async def complete_json(self, **kwargs):
        return {
            "edited_headline": "Attend the Science and Society lecture",
            "edited_body": (
                "The Science and Society lecture is at 6 p.m. Wednesday, Oct. 28, "
                "in the Example Building. Bring a friend!"
            ),
            "changes_made": ["Replaced '&' with 'and'"],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.9,
        }


def make_editor(provider) -> AIEditor:
    editor = AIEditor(provider)

    async def load_rules(*_args, **_kwargs):
        return ACTIVE_RULES

    editor.load_style_rules = load_rules
    return editor


def make_submission() -> Submission:
    return Submission(
        Id="synthetic-440",
        Category="faculty_staff",
        Target_Newsletter="tdr",
        Original_Headline=SOURCE_HEADLINE,
        Original_Body=SOURCE_BODY,
        Submitter_Notes=None,
        Submitter_Name="Synthetic submitter",
        Submitter_Email="synthetic@example.edu",
        Links=[],
    )


def test_reconcile_changes_keeps_final_edits_once():
    final = "The Science and Society lecture is Wednesday, Oct. 28. It is free."

    assert reconcile_changes(
        [
            "Changed 'Oct. 28' to 'Oct. 29'",
            "Changed “Tuesday” to “Wednesday”",
            "Replaced '&' with 'and'",
            "Merged the two event sentences into one",
            "Split the long admission sentence",
            "Deleted the duplicate registration sentence",
            "Split the long admission sentence.",
            "Corrected the draft after deterministic style-rule validation",
            "Applied the repair pass",
            "",
        ],
        final,
    ) == [
        "Changed “Tuesday” to “Wednesday”",
        "Replaced '&' with 'and'",
        "Merged the two event sentences into one",
        "Split the long admission sentence",
        "Deleted the duplicate registration sentence",
    ]


@pytest.mark.asyncio
async def test_repair_that_reverses_a_planned_change_drops_its_explanation():
    provider = ReversedChangeProvider()
    result = await make_editor(provider).edit_submission(None, make_submission(), "tdr")

    assert provider.calls == 2
    assert "Oct. 28" in result.edited_body
    assert result.changes_made == [
        "Replaced '&' with 'and'",
        "Removed the exclamation mark",
        "Rewrote the opening in third person",
        "Deleted the closing invitation sentence",
    ]
    flag_rules = {flag["rule_key"] for flag in result.flags}
    # Source problems the final text no longer has are not flagged.
    assert "no_exclamation_marks" not in flag_rules
    assert "third_person" not in flag_rules
    assert "ampersand_to_and" not in flag_rules
    # The first draft's flag about its own abandoned date change is gone.
    assert "ap_style_dates" not in flag_rules


@pytest.mark.asyncio
async def test_unresolved_final_text_problem_remains_flagged_once():
    result = await make_editor(UnresolvedExclamationProvider()).edit_submission(
        None, make_submission(), "tdr"
    )

    exclamation_flags = [
        flag for flag in result.flags if flag["rule_key"] == "no_exclamation_marks"
    ]
    assert len(exclamation_flags) == 1
    assert "body" in exclamation_flags[0]["message"]


@pytest.mark.asyncio
async def test_saved_version_reloads_the_reconciled_explanations(
    client: AsyncClient,
    staff_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    from app.services import ai_edit_service as ai_edits

    async def load_rules(*_args, **_kwargs):
        return ACTIVE_RULES

    monkeypatch.setattr(ai_edits, "async_session_factory", TestSession)
    provider = ReversedChangeProvider()
    monkeypatch.setattr(ai_edits, "get_llm_provider", lambda settings: provider)
    monkeypatch.setattr(AIEditor, "load_style_rules", load_rules)

    submission = await client.post(
        "/api/v1/submissions/",
        json=make_submission_data(
            Original_Headline=SOURCE_HEADLINE,
            Original_Body=SOURCE_BODY,
        ),
    )
    submission_id = submission.json()["Id"]
    resp = await client.post(
        f"/api/v1/ai-edits/{submission_id}/edit",
        json={"Newsletter_Type": "tdr"},
        headers=staff_headers,
    )
    task_id = resp.json()["Task_Id"]
    for _ in range(10):
        task = (
            await client.get(f"/api/v1/ai-edits/tasks/{task_id}", headers=staff_headers)
        ).json()
        if task["Status"] in {"succeeded", "failed"}:
            break
        await asyncio.sleep(0)
    assert task["Status"] == "succeeded"

    versions = (
        await client.get(f"/api/v1/ai-edits/{submission_id}/versions", headers=staff_headers)
    ).json()
    saved = next(v for v in versions if v["Version_Type"] == "ai_suggested")

    assert saved["Body"] == task["Result"]["Edited_Body"]
    assert saved["Changes_Made"] == task["Result"]["Changes_Made"]
    assert "Changed 'Oct. 28' to 'Oct. 29'" not in saved["Changes_Made"]
    assert not any("draft" in change.lower() for change in saved["Changes_Made"])

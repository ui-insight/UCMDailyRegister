"""Curled quotes and apostrophes are not changes to names (#512).

The editor curls straight quotes in the model's draft before the
deterministic checks run, while the source keeps what the submitter typed.
Checks that compare the two as strings must treat ' and ’ (and " and “ ”) as
the same mark. All names and copy here are synthetic.
"""

from datetime import datetime, timezone

import pytest

from app.evals.editorial import SeedRulesEditor
from app.services.ai.editor import enforce_curly_quotes
from app.utils.style_checks import (
    detect_changed_official_names,
    detect_missing_protected_organizations,
    detect_new_contact_names,
    detect_unformatted_composition_titles,
    straight_quotes,
)

SOURCE = (
    "The Women's Center hosts an open house in D'Angelo Hall. "
    "Contact Pat O'Brien at pat@example.edu."
)


def curled(text: str) -> str:
    return enforce_curly_quotes(text)[0]


def uncurled(text: str) -> str:
    return text.replace("’", "'")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("O’Brien", "O'Brien"),
        ("‘Example’ and “Example”", "'Example' and \"Example\""),
        ("O&#39;Brien and O&rsquo;Brien", "O'Brien and O'Brien"),
        ("&ldquo;Example&rdquo; &quot;Example&quot;", '"Example" "Example"'),
        ("Smith&apos;s", "Smith's"),
        ("Fish &amp; Chips&nbsp;", "Fish &amp; Chips&nbsp;"),
        ("O'Brien", "O'Brien"),
    ],
)
def test_straight_quotes(text, expected):
    assert straight_quotes(text) == expected


@pytest.mark.parametrize(
    ("source", "edited"),
    [(SOURCE, curled(SOURCE)), (curled(SOURCE), uncurled(curled(SOURCE)))],
    ids=["straight source, curled edit", "curled source, straight edit"],
)
def test_curling_is_not_a_change(source, edited):
    assert detect_changed_official_names(source, edited) == []
    assert detect_missing_protected_organizations(source, edited) == []
    assert detect_new_contact_names(source, edited) == []


def test_a_curled_composition_title_with_an_apostrophe_is_quoted():
    source = 'Attend a screening of the film "A Neighbor\'s Tale" on Friday.'
    headline = curled("Screening of 'A Neighbor's Tale'")
    assert detect_unformatted_composition_titles(source, headline, curled(source)) == []


def test_an_unquoted_composition_title_with_an_apostrophe_is_still_flagged():
    source = 'Attend a screening of the film "A Neighbor\'s Tale" on Friday.'
    edited = curled("Attend a screening of the film A Neighbor's Tale on Friday.")
    assert detect_unformatted_composition_titles(source, "Film screening", edited) == [
        "A Neighbor's Tale"
    ]


def test_real_changes_are_still_flagged():
    edited = curled(
        "The Womens Center hosts an open house in D'Angelo Hall. "
        "Contact Pat O'Bryan at pat@example.edu."
    )
    assert "Women's Center" in detect_changed_official_names(SOURCE, edited)
    assert detect_new_contact_names(SOURCE, edited) == ["Pat O’Bryan"]


def test_a_dropped_possessive_sponsor_is_still_missing():
    source = "The Smith's Example Institute offers free coaching this fall."
    edited = curled("Free coaching is offered this fall.")
    assert detect_missing_protected_organizations(source, edited) == [
        "The Smith's Example Institute"
    ]


@pytest.mark.asyncio
async def test_a_faithful_edit_with_apostrophes_gets_no_flags_and_one_call():
    from app.models.submission import Submission

    headline = "Women's Center offers free coaching"
    body = (
        "The Women's Center offers free coaching for faculty and staff in "
        "D'Angelo Hall. Contact Pat O'Brien at pat@example.edu."
    )
    calls = []

    class ScriptedProvider:
        model = "scripted"

        async def complete_json(self, **kwargs):
            calls.append(kwargs)
            return {"edited_headline": headline, "edited_body": body, "flags": []}

    submission = Submission(
        Id="synthetic",
        Category="news_release",
        Target_Newsletter="tdr",
        Original_Headline=headline,
        Original_Body=body,
        Submitter_Name="Synthetic",
        Submitter_Email="synthetic@example.edu",
        Created_At=datetime(2026, 11, 17, 9, tzinfo=timezone.utc),
        Links=[],
    )
    result = await SeedRulesEditor(ScriptedProvider()).edit_submission(
        None, submission, "tdr"
    )

    assert len(calls) == 1
    assert result.flags == []
    assert result.edited_body == curled(body)
    assert "O’Brien" in result.edited_body

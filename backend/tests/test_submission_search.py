"""Dashboard search over submitted and edited text (issue #534).

All data here is synthetic.
"""

import pytest

from app.schemas.submission import SubmissionCreate
from app.services import editorial_content, submission_service
from tests.conftest import make_submission_data


async def _create(db, **overrides):
    return await submission_service.create_submission(
        db, SubmissionCreate(**make_submission_data(**overrides))
    )


async def _edit(db, submission, headline: str, body: str | None = None):
    submission = await submission_service.get_submission(db, submission.Id)
    await editorial_content.save_final(
        db,
        submission,
        headline=headline,
        body=body if body is not None else submission.Original_Body,
        headline_case=None,
        approve=True,
    )
    await db.commit()


async def _search_ids(db, term: str) -> tuple[set[str], int]:
    items, total = await submission_service.list_submissions(db, search=term)
    return {item.Id for item in items}, total


@pytest.mark.asyncio
async def test_search_matches_edited_headline(db):
    edited = await _create(db, Original_Headline="Widget Workshop 101")
    await _create(db, Original_Headline="Unrelated campus notice")
    await _edit(db, edited, "Build sturdy widgets with the Widget Workshop")

    ids, total = await _search_ids(db, "build sturdy widgets")
    assert ids == {edited.Id}
    assert total == 1

    # The original title still finds it.
    ids, total = await _search_ids(db, "Widget Workshop 101")
    assert ids == {edited.Id}
    assert total == 1


@pytest.mark.asyncio
async def test_search_matches_edited_body(db):
    edited = await _create(db, Original_Body="Short original text.")
    await _create(db, Original_Body="Something else entirely.")
    await _edit(db, edited, "Edited headline", body="Rewritten body mentions zephyr gardens.")

    ids, _ = await _search_ids(db, "ZEPHYR GARDENS")
    assert ids == {edited.Id}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "term",
    [
        '"Widget Workshop 101"',
        "“Widget Workshop 101”",
        "‘Widget Workshop 101’",
        '  "Widget Workshop 101"  ',
        "“Widget Workshop 101\"",
    ],
)
async def test_search_strips_surrounding_quotes(db, term):
    match = await _create(db, Original_Headline="Widget Workshop 101")
    await _create(db, Original_Headline="Gadget Workshop 202")

    ids, total = await _search_ids(db, term)
    assert ids == {match.Id}
    assert total == 1


@pytest.mark.asyncio
async def test_search_treats_like_wildcards_literally(db):
    match = await _create(db, Original_Headline="Save 100% on parking")
    await _create(db, Original_Headline="Save 100 dollars on parking")

    ids, _ = await _search_ids(db, "100%")
    assert ids == {match.Id}


@pytest.mark.asyncio
async def test_search_without_match_returns_nothing(db):
    await _create(db, Original_Headline="Campus forum")

    ids, total = await _search_ids(db, "no such phrase anywhere")
    assert ids == set()
    assert total == 0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ""),
        ("   ", ""),
        ('""', ""),
        ("Widget", "Widget"),
        ('"Widget Workshop 101"', "Widget Workshop 101"),
        ("“Widget”", "Widget"),
        ('Say "hello" twice', 'Say "hello" twice'),
        ("students'", "students'"),
    ],
)
def test_normalize_search_term(raw, expected):
    assert submission_service.normalize_search_term(raw) == expected


@pytest.mark.asyncio
async def test_list_endpoint_returns_edited_headline(client, db, staff_headers):
    edited = await _create(db, Original_Headline="Widget Workshop 101")
    untouched = await _create(db, Original_Headline="Plain notice")
    await _edit(db, edited, "Build sturdy widgets with the Widget Workshop")

    resp = await client.get(
        "/api/v1/submissions/", params={"search": "sturdy"}, headers=staff_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["Total"] == 1
    assert [item["Id"] for item in body["Items"]] == [edited.Id]
    assert body["Items"][0]["Edited_Headline"] == "Build sturdy widgets with the Widget Workshop"
    assert body["Items"][0]["Original_Headline"] == "Widget Workshop 101"

    resp = await client.get(
        "/api/v1/submissions/", params={"search": "Plain notice"}, headers=staff_headers
    )
    assert resp.json()["Items"][0]["Id"] == untouched.Id
    assert resp.json()["Items"][0]["Edited_Headline"] is None

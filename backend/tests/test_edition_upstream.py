"""Tests for edition copy versus later approved revisions (#407).

An assembled item is a snapshot. When staff approve a newer revision, the
Builder must show it as an upstream change and let staff refresh the copy or
keep the edition's own text; reassembly must never overwrite either choice.
"""

import io

import pytest
from docx import Document
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.section import NewsletterSection
from tests.conftest import make_submission_data

PUBLISH_DATE = "2026-11-02"


@pytest.fixture
async def employee_news(db: AsyncSession):
    db.add(
        NewsletterSection(
            Newsletter_Type="tdr",
            Name="Employee News",
            Slug="employee-news",
            Display_Order=1,
            Is_Active=True,
        )
    )
    await db.commit()


async def _approve(client: AsyncClient, headers: dict[str, str], submission_id: str, text: str):
    resp = await client.post(
        f"/api/v1/ai-edits/{submission_id}/finalize",
        json={"Headline": f"{text} headline", "Body": f"{text} body", "Approve_For_Newsletter": True},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["Id"]


async def _assemble(client: AsyncClient, headers: dict[str, str]) -> dict:
    resp = await client.post(
        "/api/v1/newsletters/assemble",
        json={"Newsletter_Type": "tdr", "Publish_Date": PUBLISH_DATE},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


async def _item(client: AsyncClient, headers: dict[str, str], newsletter_id: str) -> dict:
    resp = await client.get(f"/api/v1/newsletters/{newsletter_id}", headers=headers)
    (item,) = resp.json()["Items"]
    return item


async def _export_text(client: AsyncClient, headers: dict[str, str], newsletter_id: str) -> str:
    resp = await client.get(f"/api/v1/newsletters/{newsletter_id}/export", headers=headers)
    assert resp.status_code == 200
    return "\n".join(p.text for p in Document(io.BytesIO(resp.content)).paragraphs)


@pytest.fixture
async def assembled(client: AsyncClient, staff_headers: dict[str, str], employee_news):
    """One submission approved as v1 and assembled into an edition."""
    resp = await client.post(
        "/api/v1/submissions/",
        json=make_submission_data(Schedule_Requests=[{"Requested_Date": PUBLISH_DATE}]),
        headers=staff_headers,
    )
    submission_id = resp.json()["Id"]
    v1 = await _approve(client, staff_headers, submission_id, "First")
    newsletter = await _assemble(client, staff_headers)
    return {"submission_id": submission_id, "newsletter_id": newsletter["Id"], "v1": v1}


@pytest.mark.asyncio
class TestUpstreamChange:
    async def test_fresh_item_has_no_upstream_change(self, client, staff_headers, assembled):
        item = await _item(client, staff_headers, assembled["newsletter_id"])
        assert item["Source_Version_Id"] == assembled["v1"]
        assert item["Edition_Edited"] is False
        assert item["Upstream_Change"] is None

    async def test_later_approval_shows_upstream_and_survives_reassembly(
        self, client, staff_headers, assembled
    ):
        v2 = await _approve(client, staff_headers, assembled["submission_id"], "Second")
        await _assemble(client, staff_headers)

        item = await _item(client, staff_headers, assembled["newsletter_id"])
        assert item["Final_Body"] == "First body"
        assert item["Upstream_Change"] == {
            "Id": v2,
            "Headline": "Second headline",
            "Body": "Second body",
        }

    async def test_refresh_uses_the_approved_revision_in_the_export(
        self, client, staff_headers, assembled
    ):
        v2 = await _approve(client, staff_headers, assembled["submission_id"], "Second")
        nl_id = assembled["newsletter_id"]
        item = await _item(client, staff_headers, nl_id)

        resp = await client.post(
            f"/api/v1/newsletters/{nl_id}/items/{item['Id']}/refresh-from-approved",
            headers=staff_headers,
        )
        assert resp.status_code == 200

        item = await _item(client, staff_headers, nl_id)
        assert item["Final_Body"] == "Second body"
        assert item["Source_Version_Id"] == v2
        assert item["Upstream_Change"] is None
        text = await _export_text(client, staff_headers, nl_id)
        assert "Second body" in text and "First body" not in text

    async def test_keeping_an_edition_edit_survives_reassembly_and_export(
        self, client, staff_headers, assembled
    ):
        nl_id = assembled["newsletter_id"]
        item = await _item(client, staff_headers, nl_id)
        resp = await client.patch(
            f"/api/v1/newsletters/{nl_id}/items/{item['Id']}",
            json={"Final_Body": "Edition-only body"},
            headers=staff_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["Edition_Edited"] is True

        await _approve(client, staff_headers, assembled["submission_id"], "Second")
        item = await _item(client, staff_headers, nl_id)
        assert item["Upstream_Change"]["Body"] == "Second body"

        resp = await client.post(
            f"/api/v1/newsletters/{nl_id}/items/{item['Id']}/keep-edition-copy",
            headers=staff_headers,
        )
        assert resp.status_code == 200
        await _assemble(client, staff_headers)

        item = await _item(client, staff_headers, nl_id)
        assert item["Final_Body"] == "Edition-only body"
        assert item["Edition_Edited"] is True
        assert item["Upstream_Change"] is None
        text = await _export_text(client, staff_headers, nl_id)
        assert "Edition-only body" in text and "Second body" not in text

    async def test_a_newer_approval_after_keeping_is_flagged_again(
        self, client, staff_headers, assembled
    ):
        nl_id = assembled["newsletter_id"]
        await _approve(client, staff_headers, assembled["submission_id"], "Second")
        item = await _item(client, staff_headers, nl_id)
        await client.post(
            f"/api/v1/newsletters/{nl_id}/items/{item['Id']}/keep-edition-copy",
            headers=staff_headers,
        )

        v3 = await _approve(client, staff_headers, assembled["submission_id"], "Third")
        item = await _item(client, staff_headers, nl_id)
        assert item["Upstream_Change"]["Id"] == v3

    async def test_saving_identical_text_is_not_an_edition_edit(
        self, client, staff_headers, assembled
    ):
        nl_id = assembled["newsletter_id"]
        item = await _item(client, staff_headers, nl_id)
        resp = await client.patch(
            f"/api/v1/newsletters/{nl_id}/items/{item['Id']}",
            json={"Final_Headline": item["Final_Headline"], "Final_Body": item["Final_Body"]},
            headers=staff_headers,
        )
        assert resp.json()["Edition_Edited"] is False

    async def test_refresh_without_an_approved_revision_is_a_conflict(
        self, client, staff_headers, assembled
    ):
        nl_id = assembled["newsletter_id"]
        # A later draft clears the approval.
        await client.post(
            f"/api/v1/ai-edits/{assembled['submission_id']}/finalize",
            json={"Headline": "Draft", "Body": "Draft body", "Approve_For_Newsletter": False},
            headers=staff_headers,
        )
        item = await _item(client, staff_headers, nl_id)
        assert item["Upstream_Change"] is None
        for action in ("refresh-from-approved", "keep-edition-copy"):
            resp = await client.post(
                f"/api/v1/newsletters/{nl_id}/items/{item['Id']}/{action}",
                headers=staff_headers,
            )
            assert resp.status_code == 409

    async def test_public_cannot_refresh_or_keep(self, client, assembled):
        nl_id = assembled["newsletter_id"]
        for action in ("refresh-from-approved", "keep-edition-copy"):
            resp = await client.post(f"/api/v1/newsletters/{nl_id}/items/any/{action}")
            assert resp.status_code == 403

"""Tests for Newsletter CRUD and assembly endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import make_newsletter_data, make_submission_data


@pytest.mark.asyncio
class TestNewsletterCRUD:
    async def test_create_newsletter(self, client: AsyncClient):
        resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        assert resp.status_code == 201
        body = resp.json()
        assert body["Newsletter_Type"] == "tdr"
        assert body["Status"] == "draft"
        assert body["Id"]

    async def test_list_newsletters(self, client: AsyncClient):
        await client.post("/api/v1/newsletters", json=make_newsletter_data(Publish_Date="2026-03-01"))
        await client.post("/api/v1/newsletters", json=make_newsletter_data(Publish_Date="2026-03-02"))

        resp = await client.get("/api/v1/newsletters")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_list_newsletters_filter_type(self, client: AsyncClient):
        await client.post("/api/v1/newsletters", json=make_newsletter_data(Newsletter_Type="tdr"))
        await client.post("/api/v1/newsletters", json=make_newsletter_data(Newsletter_Type="myui"))

        resp = await client.get("/api/v1/newsletters?newsletter_type=myui")
        assert resp.status_code == 200
        nls = resp.json()
        assert len(nls) == 1
        assert nls[0]["Newsletter_Type"] == "myui"

    async def test_get_newsletter(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = create_resp.json()["Id"]

        resp = await client.get(f"/api/v1/newsletters/{nl_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["Id"] == nl_id
        assert "Items" in body

    async def test_update_newsletter_status(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = create_resp.json()["Id"]

        resp = await client.patch(f"/api/v1/newsletters/{nl_id}/status?status=in_progress")
        assert resp.status_code == 200
        assert resp.json()["Status"] == "in_progress"

    async def test_delete_newsletter(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = create_resp.json()["Id"]

        resp = await client.delete(f"/api/v1/newsletters/{nl_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/v1/newsletters/{nl_id}")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestNewsletterItems:
    async def test_add_item(self, client: AsyncClient):
        # Create newsletter and submission
        nl_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = nl_resp.json()["Id"]
        sub_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = sub_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/newsletters/{nl_id}/items",
            json={
                "Submission_Id": sub_id,
                "Section_Id": "fake-section-id",
                "Position": 0,
                "Final_Headline": "Test headline",
                "Final_Body": "Test body",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["Final_Headline"] == "Test headline"

    async def test_remove_item(self, client: AsyncClient):
        nl_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = nl_resp.json()["Id"]
        sub_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = sub_resp.json()["Id"]

        item_resp = await client.post(
            f"/api/v1/newsletters/{nl_id}/items",
            json={
                "Submission_Id": sub_id,
                "Section_Id": "sec-1",
                "Position": 0,
                "Final_Headline": "Remove me",
                "Final_Body": "Body",
            },
        )
        item_id = item_resp.json()["Id"]

        resp = await client.delete(f"/api/v1/newsletters/{nl_id}/items/{item_id}")
        assert resp.status_code == 204

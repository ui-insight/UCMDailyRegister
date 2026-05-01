"""Tests for in-app product feedback capture and staff review."""

import pytest
from httpx import AsyncClient


def make_feedback_payload(**overrides) -> dict:
    payload = {
        "Feedback_Type": "bug",
        "Summary": "The dashboard filter is confusing",
        "Details": "I expected the status filter to keep my selection after refresh.",
        "Contact_Email": "editor@uidaho.edu",
        "Submitter_Role": "staff",
        "Route": "/dashboard",
        "App_Environment": "test",
        "Host": "localhost:5173",
        "Browser": "pytest",
        "Viewport": "1280x720",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
class TestProductFeedback:
    async def test_public_user_can_create_feedback(
        self,
        client: AsyncClient,
    ):
        resp = await client.post("/api/v1/feedback", json=make_feedback_payload())

        assert resp.status_code == 201
        data = resp.json()
        assert data["Feedback_Type"] == "bug"
        assert data["Summary"] == "The dashboard filter is confusing"
        assert data["Status"] == "new"
        assert data["GitHub_URL"] is None

    async def test_public_user_cannot_list_feedback(
        self,
        client: AsyncClient,
    ):
        resp = await client.get("/api/v1/feedback")

        assert resp.status_code == 403

    async def test_staff_can_list_update_and_export_feedback(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        create_resp = await client.post(
            "/api/v1/feedback",
            json=make_feedback_payload(
                Feedback_Type="idea",
                Summary="Add saved dashboard views",
                Details="It would help to save a filter set for morning triage.",
                Contact_Email="",
            ),
        )
        assert create_resp.status_code == 201
        feedback_id = create_resp.json()["Id"]

        list_resp = await client.get("/api/v1/feedback", headers=staff_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        export_resp = await client.get(
            f"/api/v1/feedback/{feedback_id}/github-export",
            headers=staff_headers,
        )
        assert export_resp.status_code == 200
        export_data = export_resp.json()
        assert export_data["Title"] == "Idea: Add saved dashboard views"
        assert "## User Report" in export_data["Body"]
        assert "Contact email provided: no" in export_data["Body"]
        assert "Sensitive submission body text" in export_data["Body"]

        update_resp = await client.patch(
            f"/api/v1/feedback/{feedback_id}",
            json={
                "Status": "exported",
                "GitHub_URL": "https://github.com/ui-insight/UCMDailyRegister/issues/999",
            },
            headers=staff_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["Status"] == "exported"
        assert update_resp.json()["GitHub_URL"].endswith("/999")

"""Tests for API authorization boundaries."""

import pytest
from httpx import AsyncClient

from tests.conftest import make_newsletter_data, make_submission_data


@pytest.mark.asyncio
class TestTrustedRoleAuthorization:
    async def test_rejects_client_controlled_user_role_header(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/newsletters",
            json=make_newsletter_data(),
            headers={"X-User-Role": "staff"},
        )

        assert resp.status_code == 400
        assert "not accepted" in resp.json()["detail"]

    async def test_rejects_trusted_role_without_valid_secret(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/newsletters",
            json=make_newsletter_data(),
            headers={
                "X-Trusted-User-Role": "staff",
                "X-Trusted-Auth-Secret": "wrong-secret",
            },
        )

        assert resp.status_code == 403
        assert "verification failed" in resp.json()["detail"]

    async def test_public_cannot_create_update_delete_assemble_or_export_newsletters(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        assert create_resp.status_code == 403

        staff_create_resp = await client.post(
            "/api/v1/newsletters",
            json=make_newsletter_data(),
            headers=staff_headers,
        )
        assert staff_create_resp.status_code == 201
        newsletter_id = staff_create_resp.json()["Id"]

        update_resp = await client.patch(
            f"/api/v1/newsletters/{newsletter_id}/status?status=in_progress"
        )
        assert update_resp.status_code == 403

        assemble_resp = await client.post(
            "/api/v1/newsletters/assemble",
            json={"Newsletter_Type": "tdr", "Publish_Date": "2026-03-02"},
        )
        assert assemble_resp.status_code == 403

        export_resp = await client.get(f"/api/v1/newsletters/{newsletter_id}/export")
        assert export_resp.status_code == 403

        delete_resp = await client.delete(f"/api/v1/newsletters/{newsletter_id}")
        assert delete_resp.status_code == 403

    async def test_public_cannot_trigger_ai_edit(self, client: AsyncClient):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_resp.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
        )

        assert resp.status_code == 403

    async def test_public_cannot_list_or_read_submissions(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        list_resp = await client.get("/api/v1/submissions/")
        assert list_resp.status_code == 403

        detail_resp = await client.get(f"/api/v1/submissions/{submission_id}")
        assert detail_resp.status_code == 403

        staff_list_resp = await client.get("/api/v1/submissions/", headers=staff_headers)
        assert staff_list_resp.status_code == 200
        staff_item = staff_list_resp.json()["Items"][0]
        assert staff_item["Submitter_Name"] == "Test User"
        assert staff_item["Submitter_Email"] == "test@uidaho.edu"

        staff_detail_resp = await client.get(
            f"/api/v1/submissions/{submission_id}",
            headers=staff_headers,
        )
        assert staff_detail_resp.status_code == 200
        assert staff_detail_resp.json()["Submitter_Email"] == "test@uidaho.edu"

    async def test_slc_calendar_feed_redacts_submitter_pii(
        self,
        client: AsyncClient,
        slc_headers: dict[str, str],
    ):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Target_Newsletter="none",
                Show_In_SLC_Calendar=True,
                Submitter_Name="Sensitive Submitter",
                Submitter_Email="sensitive@uidaho.edu",
                Submitter_Notes="Private note",
            ),
        )
        assert submission_resp.status_code == 201

        resp = await client.get(
            "/api/v1/submissions/?slc_calendar_only=true",
            headers=slc_headers,
        )

        assert resp.status_code == 200
        item = resp.json()["Items"][0]
        assert item["Submitter_Name"] == ""
        assert item["Submitter_Email"] == ""
        assert item["Submitter_Notes"] is None

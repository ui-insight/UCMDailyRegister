"""Tests for in-app product feedback capture and staff review."""

from dataclasses import asdict
import hashlib
import json

import pytest
from httpx import AsyncClient

from app.main import app as fastapi_app
from app.services.feedback_notifications import (
    FeedbackNotificationPayload,
    get_feedback_notifier,
)


class RecordingFeedbackNotifier:
    name = "recording-test"
    enabled = True

    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail
        self.payloads: list[FeedbackNotificationPayload] = []

    async def send(self, payload: FeedbackNotificationPayload) -> None:
        self.payloads.append(payload)
        if self.should_fail:
            raise RuntimeError("Test notification channel unavailable")


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
    async def test_raw_export_is_not_available_without_review(self, client, staff_headers):
        created = await client.post(
            "/api/v1/feedback",
            json=make_feedback_payload(Details="Synthetic contact: example@example.com"),
        )
        response = await client.get(
            f"/api/v1/feedback/{created.json()['Id']}/github-export", headers=staff_headers
        )
        assert response.status_code == 410
        assert "example@example.com" not in response.text

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
        assert data["Notification_Status"] == "disabled"
        assert data["Notification_Attempts"] == 0
        assert data["Notification_Sent_At"] is None
        assert data["Notification_Last_Error"] is None

    async def test_enabled_notifier_receives_only_sanitized_context(
        self,
        client: AsyncClient,
    ):
        notifier = RecordingFeedbackNotifier()
        fastapi_app.dependency_overrides[get_feedback_notifier] = lambda: notifier

        resp = await client.post("/api/v1/feedback", json=make_feedback_payload())

        assert resp.status_code == 201
        data = resp.json()
        assert data["Notification_Status"] == "sent"
        assert data["Notification_Attempts"] == 1
        assert data["Notification_Sent_At"] is not None
        assert data["Notification_Last_Error"] is None

        assert len(notifier.payloads) == 1
        payload = asdict(notifier.payloads[0])
        assert payload == {
            "Feedback_Id": data["Id"],
            "Feedback_Type": "bug",
            "Summary": "The dashboard filter is confusing",
            "Route": "/dashboard",
            "App_Environment": "test",
            "Submitted_At": notifier.payloads[0].Submitted_At,
            "Contact_Email": "editor@uidaho.edu",
        }
        assert "Details" not in payload
        assert "Browser" not in payload
        assert "Host" not in payload
        assert "Viewport" not in payload

    async def test_notification_failure_does_not_lose_feedback(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        notifier = RecordingFeedbackNotifier(should_fail=True)
        fastapi_app.dependency_overrides[get_feedback_notifier] = lambda: notifier

        create_resp = await client.post(
            "/api/v1/feedback",
            json=make_feedback_payload(Details="Private details stay in the application."),
        )

        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["Notification_Status"] == "failed"
        assert created["Notification_Attempts"] == 1
        assert created["Notification_Sent_At"] is None
        assert created["Notification_Last_Error"] == "RuntimeError"
        assert "Private details" not in created["Notification_Last_Error"]

        list_resp = await client.get("/api/v1/feedback", headers=staff_headers)
        assert list_resp.status_code == 200
        assert [item["Id"] for item in list_resp.json()] == [created["Id"]]

    async def test_staff_can_retry_a_failed_notification(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        notifier = RecordingFeedbackNotifier(should_fail=True)
        fastapi_app.dependency_overrides[get_feedback_notifier] = lambda: notifier
        create_resp = await client.post("/api/v1/feedback", json=make_feedback_payload())
        feedback_id = create_resp.json()["Id"]

        notifier.should_fail = False
        retry_resp = await client.post(
            f"/api/v1/feedback/{feedback_id}/notification/retry",
            headers=staff_headers,
        )

        assert retry_resp.status_code == 200
        retried = retry_resp.json()
        assert retried["Notification_Status"] == "sent"
        assert retried["Notification_Attempts"] == 2
        assert retried["Notification_Sent_At"] is not None
        assert retried["Notification_Last_Error"] is None

    async def test_notification_retry_and_summary_require_staff(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        create_resp = await client.post("/api/v1/feedback", json=make_feedback_payload())
        feedback_id = create_resp.json()["Id"]

        public_summary_resp = await client.get("/api/v1/feedback/summary")
        public_retry_resp = await client.post(
            f"/api/v1/feedback/{feedback_id}/notification/retry"
        )
        staff_summary_resp = await client.get(
            "/api/v1/feedback/summary",
            headers=staff_headers,
        )

        assert public_summary_resp.status_code == 403
        assert public_retry_resp.status_code == 403
        assert staff_summary_resp.status_code == 200
        assert staff_summary_resp.json() == {
            "New_Count": 1,
            "Failed_Notification_Count": 0,
            "Pending_Notification_Count": 0,
        }

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
            f"/api/v1/feedback/{feedback_id}/github-export/preview",
            headers=staff_headers,
        )
        assert export_resp.status_code == 200
        export_data = export_resp.json()
        assert export_data["Title"] == "Idea: Add saved dashboard views"
        assert "## User Report" in export_data["Body"]
        assert "Contact email provided: no" in export_data["Body"]
        assert export_data["Warnings"] == []
        prepared = await client.post(
            f"/api/v1/feedback/{feedback_id}/github-export",
            headers=staff_headers,
            json={"Title": export_data["Title"], "Body": export_data["Body"],
                  "Review_Confirmed": True},
        )
        assert prepared.status_code == 200
        assert "reviewed by staff" in prepared.json()["Body"]

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

    async def test_reviewed_export_preserves_original_and_records_exact_artifact(
        self, client, staff_headers
    ):
        created = (await client.post("/api/v1/feedback", json=make_feedback_payload(
            Summary="Synthetic contact example@example.com",
            Details="Call 208-555-0100 or example@example.com about this synthetic report.",
            Route="/edit/synthetic-private-reference",
        ))).json()
        url = f"/api/v1/feedback/{created['Id']}/github-export"
        preview = await client.get(url + "/preview", headers=staff_headers)
        assert preview.status_code == 200
        assert len(preview.json()["Warnings"]) == 2
        for confirmation in (False, None):
            payload = {"Title": "Reviewed issue", "Body": "Safe synthetic details."}
            if confirmation is not None:
                payload["Review_Confirmed"] = confirmation
            assert (await client.post(url, headers=staff_headers, json=payload)).status_code == 422
        (before,) = (await client.get("/api/v1/feedback", headers=staff_headers)).json()
        assert before["GitHub_Export_Reviewed_At"] is None
        assert before["GitHub_Export_SHA256"] is None
        payload = {"Title": "Reviewed issue", "Body": "Safe synthetic details.",
                   "Review_Confirmed": True}
        assert (await client.post(url, json=payload)).status_code == 403
        assert (await client.get(url + "/preview")).status_code == 403
        assert (await client.post("/api/v1/feedback/missing/github-export",
                                  headers=staff_headers, json=payload)).status_code == 404
        response = await client.post(url, headers=staff_headers, json=payload)
        assert response.status_code == 200
        artifact = response.json()
        assert artifact["Title"] == payload["Title"]
        assert artifact["Body"].startswith(payload["Body"])
        assert "example@example.com" not in json.dumps(artifact)
        assert "synthetic-private-reference" not in json.dumps(artifact)
        (stored,) = (await client.get("/api/v1/feedback", headers=staff_headers)).json()
        assert stored["Summary"] == created["Summary"]
        assert stored["Details"] == created["Details"]
        assert stored["Status"] == created["Status"]
        assert stored["GitHub_Export_Reviewed_At"] is not None
        assert stored["GitHub_Export_SHA256"] == hashlib.sha256(
            json.dumps(artifact, sort_keys=True).encode()
        ).hexdigest()

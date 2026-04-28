"""Tests for AI edit task handling and failure behavior."""

import asyncio

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edit_history import EditVersion
from app.models.submission import Submission
from tests.conftest import TestSession, make_submission_data


@pytest.fixture(autouse=True)
def configure_ai_edit_tasks(monkeypatch: pytest.MonkeyPatch):
    from app.api.v1 import ai_edits

    ai_edits._ai_edit_tasks.clear()
    monkeypatch.setattr(ai_edits, "async_session_factory", TestSession)
    yield
    ai_edits._ai_edit_tasks.clear()


class SuccessfulProvider:
    model = "test-model"

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        return {
            "edited_headline": "Edited headline",
            "edited_body": "Edited body.",
            "changes_made": ["Shortened headline"],
            "flags": [],
            "embedded_links": [],
            "confidence": 0.95,
        }


class FailingProvider:
    model = "test-model"

    async def complete(self, *args, **kwargs):  # pragma: no cover - unused interface method
        raise NotImplementedError

    async def complete_json(self, *args, **kwargs):
        raise RuntimeError("provider unavailable")


async def wait_for_task(
    client: AsyncClient,
    task_id: str,
    staff_headers: dict[str, str],
) -> dict:
    for _ in range(10):
        resp = await client.get(f"/api/v1/ai-edits/tasks/{task_id}", headers=staff_headers)
        assert resp.status_code == 200
        task = resp.json()
        if task["Status"] in {"succeeded", "failed"}:
            return task
        await asyncio.sleep(0)
    raise AssertionError("AI edit task did not finish")


@pytest.mark.asyncio
class TestAIEditTasks:
    async def test_staff_ai_edit_runs_as_task_and_saves_successful_result(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: SuccessfulProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )

        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "succeeded"
        assert task["Result"]["Edited_Headline"] == "Edited headline"
        assert task["Result"]["Edit_Version_Id"]

        versions_resp = await client.get(
            f"/api/v1/ai-edits/{submission_id}/versions",
            headers=staff_headers,
        )
        assert versions_resp.status_code == 200
        assert [version["Version_Type"] for version in versions_resp.json()] == [
            "original",
            "ai_suggested",
        ]

        submission_detail_resp = await client.get(
            f"/api/v1/submissions/{submission_id}",
            headers=staff_headers,
        )
        assert submission_detail_resp.status_code == 200
        assert submission_detail_resp.json()["Status"] == "ai_edited"

    async def test_provider_failure_does_not_save_ai_version_or_mark_ai_edited(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(
            "app.api.v1.ai_edits.get_llm_provider",
            lambda settings: FailingProvider(),
        )
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )

        assert resp.status_code == 202
        task = await wait_for_task(client, resp.json()["Task_Id"], staff_headers)
        assert task["Status"] == "failed"
        assert task["Result"] is None
        assert "provider unavailable" in task["Error_Message"]

        versions = (
            await db.execute(
                sa.select(EditVersion).where(EditVersion.Submission_Id == submission_id)
            )
        ).scalars().all()
        assert versions == []

        submission = (
            await db.execute(sa.select(Submission).where(Submission.Id == submission_id))
        ).scalar_one()
        assert submission.Status == "new"

    async def test_public_cannot_access_ai_edit_task_or_version_endpoints(
        self,
        client: AsyncClient,
    ):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        task_resp = await client.get("/api/v1/ai-edits/tasks/not-a-task")
        assert task_resp.status_code == 403

        versions_resp = await client.get(f"/api/v1/ai-edits/{submission_id}/versions")
        assert versions_resp.status_code == 403

        version_resp = await client.get(
            f"/api/v1/ai-edits/{submission_id}/versions/not-a-version"
        )
        assert version_resp.status_code == 403

        finalize_resp = await client.post(
            f"/api/v1/ai-edits/{submission_id}/finalize",
            json={"Headline": "Final", "Body": "Final body."},
        )
        assert finalize_resp.status_code == 403

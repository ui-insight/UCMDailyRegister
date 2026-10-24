"""Durable task recovery, replay safety, capacity and source-revision guards."""

import asyncio

import pytest
import sqlalchemy as sa
from fastapi import BackgroundTasks
from httpx import AsyncClient

from app.main import app
from app.models.ai_edit_task import AIEditTask
from app.models.edit_history import EditVersion
from app.models.submission import Submission
from app.services import ai_edit_service as service
from app.services.ai.editor import AIEditor
from tests.conftest import TestSession, make_submission_data
from tests.test_ai_edits import SuccessfulProvider
from tests.test_concurrent_editing import BlockingProvider


@pytest.fixture(autouse=True)
def configure_tasks(monkeypatch):
    monkeypatch.setattr(service, "async_session_factory", TestSession)
    monkeypatch.setattr(service, "get_llm_provider", lambda settings: SuccessfulProvider())
    monkeypatch.setattr(service, "_admission_lock", asyncio.Lock())
    monkeypatch.setattr(service, "_execution_slots", asyncio.Semaphore(2))


async def queued(client, staff_headers, monkeypatch, *, instructions=None):
    submission = await client.post("/api/v1/submissions/", json=make_submission_data())
    submission_id = submission.json()["Id"]
    # Simulate an accepted response whose background work never got to finish.
    with monkeypatch.context() as context:
        context.setattr(BackgroundTasks, "add_task", lambda *args, **kwargs: None)
        response = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr", "Editor_Instructions": instructions},
            headers=staff_headers,
        )
    assert response.status_code == 202
    assert response.json()["Status"] == "queued"
    return submission_id, response.json()["Task_Id"]


async def state(client, staff_headers, task_id):
    response = await client.get(f"/api/v1/ai-edits/tasks/{task_id}", headers=staff_headers)
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("initial", ["queued", "running"])
async def test_startup_recovers_interrupted_work_and_retry_is_idempotent(
    client: AsyncClient,
    staff_headers,
    monkeypatch,
    initial,
):
    submission_id, task_id = await queued(
        client, staff_headers, monkeypatch, instructions="Keep it short."
    )
    async with TestSession() as session:
        task = await session.get(AIEditTask, task_id)
        task.Status = initial
        task.Run_Id = "interrupted-attempt" if initial == "running" else None
        await session.commit()

    # Run the actual FastAPI startup hook using fresh database sessions.
    async with app.router.lifespan_context(app):
        recovered = await state(client, staff_headers, task_id)
        assert recovered["Status"] == "failed"
        assert "interrupted" in recovered["Error_Message"]
        assert recovered["Result"] is None
        for _ in range(2):
            response = await client.post(
                f"/api/v1/ai-edits/tasks/{task_id}/retry", headers=staff_headers
            )
            assert response.status_code == 202
            assert response.json()["Task_Id"] == task_id
        completed = await state(client, staff_headers, task_id)
        assert completed["Status"] == "succeeded"
        version_id = completed["Result"]["Edit_Version_Id"]
    async with TestSession() as session:
        versions = (
            await session.scalars(
                sa.select(EditVersion).where(
                    EditVersion.Submission_Id == submission_id,
                    EditVersion.Version_Type == "ai_suggested",
                )
            )
        ).all()
        assert len(versions) == 1 and versions[0].Id == version_id
        assert versions[0].Editor_Instructions == "Keep it short."
    await service.recover_interrupted_tasks()
    assert (await state(client, staff_headers, task_id))["Result"] == completed["Result"]


@pytest.mark.asyncio
async def test_active_request_deduplicates_and_queue_capacity_is_enforced(
    client, staff_headers, monkeypatch
):
    monkeypatch.setattr(service.settings, "ai_edit_max_pending", 1)
    submission_id, task_id = await queued(client, staff_headers, monkeypatch)
    with monkeypatch.context() as context:
        scheduled = []
        context.setattr(BackgroundTasks, "add_task", lambda *args: scheduled.append(args))
        duplicate = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert duplicate.status_code == 202 and duplicate.json()["Task_Id"] == task_id
        assert not scheduled
        different = await client.post(
            f"/api/v1/ai-edits/{submission_id}/edit",
            json={"Newsletter_Type": "tdr", "Editor_Instructions": "Different request"},
            headers=staff_headers,
        )
        assert different.status_code == 409
        other = await client.post("/api/v1/submissions/", json=make_submission_data())
        full = await client.post(
            f"/api/v1/ai-edits/{other.json()['Id']}/edit",
            json={"Newsletter_Type": "tdr"},
            headers=staff_headers,
        )
        assert full.status_code == 503 and full.headers["Retry-After"] == "5"


@pytest.mark.asyncio
async def test_duplicate_worker_and_late_attempt_cannot_save_twice(
    client, staff_headers, monkeypatch
):
    submission_id, task_id = await queued(client, staff_headers, monkeypatch)
    provider = BlockingProvider()
    monkeypatch.setattr(service, "get_llm_provider", lambda settings: provider)
    worker = asyncio.create_task(service.process_task(task_id))
    await asyncio.wait_for(provider.started.wait(), 5)
    try:
        await service.process_task(task_id)  # already claimed: must not call the provider
        await service.recover_interrupted_tasks()  # invalidate this old worker
        async with TestSession() as session:
            retried, accepted = await service.retry(session, task_id)
            assert accepted and retried.Status == "queued"
        provider.release.set()
        await asyncio.wait_for(worker, 5)
        # The old attempt must not mark the new attempt succeeded OR failed.
        assert (await state(client, staff_headers, task_id))["Status"] == "queued"
        async with TestSession() as session:
            assert (
                await session.scalar(
                    sa.select(sa.func.count())
                    .select_from(EditVersion)
                    .where(EditVersion.Submission_Id == submission_id)
                )
                == 0
            )
        await service.process_task(task_id)
        assert (await state(client, staff_headers, task_id))["Status"] == "succeeded"
    finally:
        provider.release.set()
        if not worker.done():
            worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("during_run", [False, True])
async def test_changed_source_is_not_saved_or_retried(
    client, staff_headers, monkeypatch, during_run
):
    submission_id, task_id = await queued(client, staff_headers, monkeypatch)
    provider = BlockingProvider()
    monkeypatch.setattr(service, "get_llm_provider", lambda settings: provider)
    worker = None
    if during_run:
        worker = asyncio.create_task(service.process_task(task_id))
        await asyncio.wait_for(provider.started.wait(), 5)
    try:
        async with TestSession() as session:
            await session.execute(
                sa.update(Submission)
                .where(Submission.Id == submission_id)
                .values(Original_Body="Changed synthetic source.")
            )
            await session.commit()
        provider.release.set()
        if worker:
            await asyncio.wait_for(worker, 5)
        else:
            await service.process_task(task_id)
        failed = await state(client, staff_headers, task_id)
        assert failed["Status"] == "failed" and "changed" in failed["Error_Message"]
        retry = await client.post(f"/api/v1/ai-edits/tasks/{task_id}/retry", headers=staff_headers)
        assert retry.status_code == 409
        async with TestSession() as session:
            assert (
                await session.scalar(
                    sa.select(sa.func.count())
                    .select_from(EditVersion)
                    .where(EditVersion.Submission_Id == submission_id)
                )
                == 0
            )
    finally:
        provider.release.set()
        if worker and not worker.done():
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)


@pytest.mark.asyncio
async def test_failed_result_save_rolls_back_versions_before_retry(
    client, staff_headers, monkeypatch
):
    submission_id, task_id = await queued(client, staff_headers, monkeypatch)
    original = AIEditor.save_edit_versions

    async def fail_after_flush(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise RuntimeError("synthetic-private-marker")

    with monkeypatch.context() as context:
        context.setattr(AIEditor, "save_edit_versions", fail_after_flush)
        await service.process_task(task_id)
    failed = await state(client, staff_headers, task_id)
    assert failed["Status"] == "failed" and failed["Result"] is None
    assert "synthetic-private-marker" not in failed["Error_Message"]
    async with TestSession() as session:
        assert (
            await session.scalar(
                sa.select(sa.func.count())
                .select_from(EditVersion)
                .where(EditVersion.Submission_Id == submission_id)
            )
            == 0
        )
    retry = await client.post(f"/api/v1/ai-edits/tasks/{task_id}/retry", headers=staff_headers)
    assert retry.status_code == 202
    assert (await state(client, staff_headers, task_id))["Status"] == "succeeded"


@pytest.mark.asyncio
async def test_staff_approval_survives_a_durable_task_completion(
    client, staff_headers, monkeypatch
):
    submission_id, task_id = await queued(client, staff_headers, monkeypatch)
    provider = BlockingProvider()
    monkeypatch.setattr(service, "get_llm_provider", lambda settings: provider)
    worker = asyncio.create_task(service.process_task(task_id))
    await asyncio.wait_for(provider.started.wait(), 5)
    try:
        approved = await client.post(
            f"/api/v1/ai-edits/{submission_id}/finalize",
            json={
                "Headline": "Approved headline",
                "Body": "Approved body.",
                "Approve_For_Newsletter": True,
            },
            headers=staff_headers,
        )
        assert approved.status_code == 200
        provider.release.set()
        await asyncio.wait_for(worker, 5)
        detail = (
            await client.get(f"/api/v1/submissions/{submission_id}", headers=staff_headers)
        ).json()
        assert detail["Status"] == "approved"
        assert (
            detail["Approved_Version_Id"] == detail["Working_Version_Id"] == approved.json()["Id"]
        )
        assert (await state(client, staff_headers, task_id))["Status"] == "succeeded"
    finally:
        provider.release.set()
        if not worker.done():
            worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)


@pytest.mark.asyncio
async def test_deleted_submission_removes_task_copy_and_retry_requires_staff(
    client, staff_headers, monkeypatch
):
    submission_id, task_id = await queued(client, staff_headers, monkeypatch)
    denied = await client.post(f"/api/v1/ai-edits/tasks/{task_id}/retry")
    assert denied.status_code == 403
    deleted = await client.delete(f"/api/v1/submissions/{submission_id}", headers=staff_headers)
    assert deleted.status_code == 204
    missing = await client.get(f"/api/v1/ai-edits/tasks/{task_id}", headers=staff_headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_execution_concurrency_is_bounded(client, staff_headers, monkeypatch):
    tasks = [await queued(client, staff_headers, monkeypatch) for _ in range(3)]

    class CountingProvider(BlockingProvider):
        def __init__(self):
            super().__init__()
            self.calls = 0

        async def complete_json(self, *args, **kwargs):
            self.calls += 1
            return await super().complete_json(*args, **kwargs)

    provider = CountingProvider()
    monkeypatch.setattr(service, "get_llm_provider", lambda settings: provider)
    monkeypatch.setattr(service, "_execution_slots", asyncio.Semaphore(1))
    workers = [asyncio.create_task(service.process_task(task_id)) for _, task_id in tasks]
    try:
        await asyncio.wait_for(provider.started.wait(), 5)
        await asyncio.sleep(0)
        assert provider.calls == 1
        provider.release.set()
        await asyncio.wait_for(asyncio.gather(*workers), 5)
        assert provider.calls == 3
        for _, task_id in tasks:
            assert (await state(client, staff_headers, task_id))["Status"] == "succeeded"
    finally:
        provider.release.set()
        for worker in workers:
            if not worker.done():
                worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)


@pytest.mark.asyncio
async def test_cancelled_model_call_is_visible_and_retryable(client, staff_headers, monkeypatch):
    _, task_id = await queued(client, staff_headers, monkeypatch)
    provider = BlockingProvider()
    monkeypatch.setattr(service, "get_llm_provider", lambda settings: provider)
    worker = asyncio.create_task(service.process_task(task_id))
    await asyncio.wait_for(provider.started.wait(), 5)
    worker.cancel()
    await asyncio.gather(worker, return_exceptions=True)
    assert (await state(client, staff_headers, task_id))["Status"] == "failed"
    provider.release.set()
    response = await client.post(f"/api/v1/ai-edits/tasks/{task_id}/retry", headers=staff_headers)
    assert response.status_code == 202
    assert (await state(client, staff_headers, task_id))["Status"] == "succeeded"

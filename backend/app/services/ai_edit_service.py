"""Durable AI edit requests, bounded execution, and restart recovery.

The deployed backend is a single process. Admission is serialized inside that
process, while unique active keys and conditional attempt updates also prevent
duplicate requests/late workers from saving competing results. Startup marks
unfinished work failed for an explicit staff retry, never silently replays a
possibly completed external call. Completed state and edit versions commit in
one transaction. Only bounded pending work lives in the background executor.
"""

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.engine import async_session_factory
from app.models.ai_edit_task import AIEditTask
from app.models.edit_history import EditVersion
from app.models.submission import Submission
from app.schemas.ai_edit import (
    AIEditRequest,
    AIEditResponse,
    AIEditTaskResponse,
    AIEditFlag,
    AIEditLink,
    TextDiffResponse,
    DiffSegment,
)
from app.services.ai.editor import AIEditor, AIEditError, EditResult
from app.services.ai.factory import get_llm_provider

_admission_lock = asyncio.Lock()
_execution_slots = asyncio.Semaphore(settings.ai_edit_max_concurrency)
INTERRUPTED = "AI editing was interrupted by a server restart. Retry this edit."
SOURCE_CHANGED = (
    "The submission changed after this AI edit was requested. Reload and start a new edit."
)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def serialize_task(task: AIEditTask) -> AIEditTaskResponse:
    return AIEditTaskResponse(
        Task_Id=task.Id,
        Submission_Id=task.Submission_Id,
        Newsletter_Type=task.Newsletter_Type,
        Status=task.Status,
        Result=AIEditResponse.model_validate(task.Result_JSON) if task.Result_JSON else None,
        Error_Message=task.Error_Message,
        Created_At=task.Created_At,
        Updated_At=task.Updated_At,
    )


def source_fingerprint(submission: Submission) -> str:
    # AIEditor edits the submitted source. Staff finals remain authoritative
    # independently of this fingerprint, as defined by editorial_content.
    source = [
        submission.Original_Headline,
        submission.Original_Body,
        submission.Category,
        submission.Target_Newsletter,
        submission.Submitter_Notes,
        sorted((link.Url, link.Anchor_Text or "", link.Display_Order) for link in submission.Links),
    ]
    return hashlib.sha256(json.dumps(source, ensure_ascii=False).encode()).hexdigest()


async def _submission(session: AsyncSession, submission_id: str, *, lock=False) -> Submission:
    query = (
        sa.select(Submission)
        .where(Submission.Id == submission_id)
        .execution_options(populate_existing=True)
        .options(selectinload(Submission.Links), selectinload(Submission.Edit_Versions))
    )
    if lock:
        query = query.with_for_update()
    submission = (await session.execute(query)).scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


async def get_task(session: AsyncSession, task_id: str) -> AIEditTask:
    task = await session.get(AIEditTask, task_id, populate_existing=True)
    if task is None:
        raise HTTPException(status_code=404, detail="AI edit task not found")
    return task


async def _capacity(session: AsyncSession) -> None:
    count = await session.scalar(
        sa.select(sa.func.count())
        .select_from(AIEditTask)
        .where(AIEditTask.Status.in_(("queued", "running")))
    )
    if count >= settings.ai_edit_max_pending:
        raise HTTPException(
            status_code=503,
            detail="AI edit queue is full. Try again shortly.",
            headers={"Retry-After": "5"},
        )


async def enqueue(
    session: AsyncSession, submission_id: str, request: AIEditRequest
) -> tuple[AIEditTask, bool]:
    async with _admission_lock:
        submission = await _submission(session, submission_id)
        if submission.Target_Newsletter not in (request.Newsletter_Type, "both"):
            raise HTTPException(
                status_code=400, detail="Submission does not target this newsletter"
            )
        key = submission_id + ":" + request.Newsletter_Type
        active = await session.scalar(sa.select(AIEditTask).where(AIEditTask.Active_Key == key))
        fingerprint = source_fingerprint(submission)
        if active:
            if (
                active.Source_Fingerprint != fingerprint
                or active.Editor_Instructions != request.Editor_Instructions
            ):
                raise HTTPException(
                    status_code=409,
                    detail="An AI edit is already pending. Wait for it before requesting a different edit.",
                )
            return active, False
        await _capacity(session)
        task = AIEditTask(
            Submission_Id=submission_id,
            Newsletter_Type=request.Newsletter_Type,
            Editor_Instructions=request.Editor_Instructions,
            Status="queued",
            Source_Fingerprint=fingerprint,
            Active_Key=key,
        )
        session.add(task)
        await session.commit()
        return task, True


async def retry(session: AsyncSession, task_id: str) -> tuple[AIEditTask, bool]:
    async with _admission_lock:
        task = await get_task(session, task_id)
        # Repeated retries of an active or completed request reuse its ID/result.
        if task.Status != "failed":
            return task, False
        submission = await _submission(session, task.Submission_Id)
        if source_fingerprint(submission) != task.Source_Fingerprint:
            raise HTTPException(status_code=409, detail=SOURCE_CHANGED)
        key = task.Submission_Id + ":" + task.Newsletter_Type
        active = await session.scalar(sa.select(AIEditTask).where(AIEditTask.Active_Key == key))
        if active:
            # Do not return another request's result/instructions as this retry.
            raise HTTPException(
                status_code=409, detail="Another AI edit is already pending for this submission."
            )
        await _capacity(session)
        task.Status, task.Active_Key = "queued", key
        task.Run_Id, task.Result_JSON, task.Error_Message = None, None, None
        task.Updated_At = _now()
        await session.commit()
        return task, True


async def recover_interrupted_tasks() -> None:
    """Run before accepting requests in the single-process backend."""
    async with async_session_factory() as session:
        await session.execute(
            sa.update(AIEditTask)
            .where(AIEditTask.Status.in_(("queued", "running")))
            .values(
                Status="failed",
                Active_Key=None,
                Run_Id=None,
                Result_JSON=None,
                Error_Message=INTERRUPTED,
                Updated_At=_now(),
            )
        )
        await session.commit()


def _build_response(
    submission_id: str,
    newsletter_type: str,
    edit_result: EditResult,
    ai_version: EditVersion,
) -> AIEditResponse:
    return AIEditResponse(
        Submission_Id=submission_id,
        Newsletter_Type=newsletter_type,
        Edited_Headline=edit_result.edited_headline,
        Edited_Body=edit_result.edited_body,
        Headline_Case=edit_result.headline_case,
        Changes_Made=edit_result.changes_made,
        Flags=[AIEditFlag(**f) for f in edit_result.flags],
        Embedded_Links=[AIEditLink(**link_data) for link_data in edit_result.embedded_links],
        Confidence=edit_result.confidence,
        AI_Provider=edit_result.ai_provider,
        AI_Model=edit_result.ai_model,
        Headline_Diff=TextDiffResponse(
            segments=[DiffSegment(**s) for s in edit_result.headline_diff.get("segments", [])],
            change_count=edit_result.headline_diff.get("change_count", 0),
            similarity_ratio=edit_result.headline_diff.get("similarity_ratio", 1.0),
        ),
        Body_Diff=TextDiffResponse(
            segments=[DiffSegment(**s) for s in edit_result.body_diff.get("segments", [])],
            change_count=edit_result.body_diff.get("change_count", 0),
            similarity_ratio=edit_result.body_diff.get("similarity_ratio", 1.0),
        ),
        Edit_Version_Id=ai_version.Id,
    )


async def run_edit(
    session: AsyncSession,
    submission_id: str,
    newsletter_type: str,
    editor_instructions: str | None = None,
    *,
    task: AIEditTask | None = None,
) -> AIEditResponse:
    submission = await _submission(session, submission_id)
    fingerprint = source_fingerprint(submission)
    if task and fingerprint != task.Source_Fingerprint:
        raise HTTPException(status_code=409, detail=SOURCE_CHANGED)
    if submission.Target_Newsletter not in (newsletter_type, "both"):
        raise HTTPException(status_code=400, detail="Submission does not target this newsletter")
    base_staff = submission.Staff_Revision_Id
    try:
        llm = get_llm_provider(settings)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="AI provider is not configured.") from exc
    editor = AIEditor(llm)
    result = await editor.edit_submission(
        session=session,
        submission=submission,
        newsletter_type=newsletter_type,
        editor_instructions=editor_instructions,
    )

    if task:
        # Claim a write lock on this exact attempt before saving any versions.
        # Recovery/retry invalidates Run_Id, so a late old worker saves nothing.
        owned = await session.execute(
            sa.update(AIEditTask)
            .where(
                AIEditTask.Id == task.Id,
                AIEditTask.Status == "running",
                AIEditTask.Run_Id == task.Run_Id,
            )
            .values(Updated_At=_now())
        )
        if owned.rowcount != 1:
            raise HTTPException(status_code=409, detail="This AI edit attempt is no longer active.")
    current = await _submission(session, submission_id, lock=True)
    if source_fingerprint(current) != fingerprint:
        raise HTTPException(status_code=409, detail=SOURCE_CHANGED)
    if current.Staff_Revision_Id != base_staff:
        result.flags.append(
            {
                "type": "info",
                "rule_key": "staff_revision_changed",
                "message": "Staff saved newer copy while AI was running. This suggestion is history; staff copy remains authoritative.",
            }
        )
    _, version = await editor.save_edit_versions(
        session=session,
        submission_id=submission_id,
        edit_result=result,
        original_headline=current.Original_Headline,
        original_body=current.Original_Body,
        editor_instructions=editor_instructions,
    )
    await session.execute(
        sa.update(Submission)
        .where(
            Submission.Id == submission_id,
            Submission.Status.in_(("new", "ai_edited")),
        )
        .values(Status="ai_edited")
    )
    response = _build_response(submission_id, newsletter_type, result, version)
    if task:
        task.Status, task.Active_Key, task.Run_Id = "succeeded", None, None
        task.Result_JSON, task.Error_Message = response.model_dump(mode="json"), None
        task.Updated_At = _now()
    await session.commit()
    return response


async def _fail_attempt(task_id: str, run_id: str, message: str) -> None:
    async with async_session_factory() as session:
        await session.execute(
            sa.update(AIEditTask)
            .where(
                AIEditTask.Id == task_id,
                AIEditTask.Status == "running",
                AIEditTask.Run_Id == run_id,
            )
            .values(
                Status="failed",
                Active_Key=None,
                Run_Id=None,
                Error_Message=message,
                Updated_At=_now(),
            )
        )
        await session.commit()


async def process_task(task_id: str) -> None:
    # At most AI_EDIT_MAX_PENDING requests are admitted, with only this many
    # model calls running concurrently. Completed records are never cached.
    async with _execution_slots:
        run_id = str(uuid.uuid4())
        async with async_session_factory() as session:
            claimed = await session.execute(
                sa.update(AIEditTask)
                .where(
                    AIEditTask.Id == task_id,
                    AIEditTask.Status == "queued",
                )
                .values(Status="running", Run_Id=run_id, Updated_At=_now())
            )
            await session.commit()
            if claimed.rowcount != 1:
                return
        try:
            async with async_session_factory() as session:
                task = await get_task(session, task_id)
                if task.Status != "running" or task.Run_Id != run_id:
                    return
                await run_edit(
                    session,
                    task.Submission_Id,
                    task.Newsletter_Type,
                    task.Editor_Instructions,
                    task=task,
                )
        except asyncio.CancelledError:
            await _fail_attempt(task_id, run_id, INTERRUPTED)
            raise
        except AIEditError:
            await _fail_attempt(task_id, run_id, "AI editing failed. Retry this edit.")
        except HTTPException as exc:
            # Only controlled application messages; never provider error text.
            await _fail_attempt(task_id, run_id, str(exc.detail))
        except Exception:
            await _fail_attempt(task_id, run_id, "AI editing failed unexpectedly. Retry this edit.")

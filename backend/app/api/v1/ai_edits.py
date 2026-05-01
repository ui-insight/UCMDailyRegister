"""AI editing API endpoints."""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.api.deps import get_db, require_staff
from app.db.engine import async_session_factory
from app.models.submission import Submission
from app.models.edit_history import EditVersion
from app.services.ai.factory import get_llm_provider
from app.services.ai.editor import AIEditor, AIEditError, EditResult
from app.schemas.ai_edit import (
    AIEditRequest,
    AIEditResponse,
    AIEditTaskResponse,
    AIEditFlag,
    AIEditLink,
    TextDiffResponse,
    DiffSegment,
    EditVersionResponse,
    EditorFinalCreate,
)

router = APIRouter(prefix="/ai-edits", tags=["ai-edits"])

AIEditTaskStatus = Literal["queued", "running", "succeeded", "failed"]


@dataclass
class AIEditTaskState:
    Task_Id: str
    Submission_Id: str
    Newsletter_Type: str
    Editor_Instructions: str | None
    Status: AIEditTaskStatus
    Created_At: datetime
    Updated_At: datetime
    Result: AIEditResponse | None = None
    Error_Message: str | None = None


_ai_edit_tasks: dict[str, AIEditTaskState] = {}
_ai_edit_semaphore = asyncio.Semaphore(settings.ai_edit_max_concurrency)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _serialize_task(task: AIEditTaskState) -> AIEditTaskResponse:
    return AIEditTaskResponse(
        Task_Id=task.Task_Id,
        Submission_Id=task.Submission_Id,
        Newsletter_Type=task.Newsletter_Type,
        Status=task.Status,
        Result=task.Result,
        Error_Message=task.Error_Message,
        Created_At=task.Created_At,
        Updated_At=task.Updated_At,
    )


def _build_ai_edit_response(
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


async def _run_ai_edit(
    session: AsyncSession,
    submission_id: str,
    newsletter_type: str,
    editor_instructions: str | None = None,
) -> AIEditResponse:
    result = await session.execute(
        sa.select(Submission)
        .where(Submission.Id == submission_id)
        .options(selectinload(Submission.Links))
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission.Target_Newsletter not in (newsletter_type, "both"):
        raise HTTPException(
            status_code=400,
            detail=f"Submission targets '{submission.Target_Newsletter}', not '{newsletter_type}'",
        )

    try:
        llm = get_llm_provider(settings)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    editor = AIEditor(llm)
    edit_result = await editor.edit_submission(
        session=session,
        submission=submission,
        newsletter_type=newsletter_type,
        editor_instructions=editor_instructions,
    )

    _original_version, ai_version = await editor.save_edit_versions(
        session=session,
        submission_id=submission_id,
        edit_result=edit_result,
        original_headline=submission.Original_Headline,
        original_body=submission.Original_Body,
        editor_instructions=editor_instructions,
    )

    submission.Status = "ai_edited"
    await session.commit()
    await session.refresh(ai_version)

    return _build_ai_edit_response(
        submission_id=submission_id,
        newsletter_type=newsletter_type,
        edit_result=edit_result,
        ai_version=ai_version,
    )


async def _process_ai_edit_task(task_id: str) -> None:
    task = _ai_edit_tasks[task_id]

    try:
        async with _ai_edit_semaphore:
            task.Status = "running"
            task.Updated_At = _utcnow()
            async with async_session_factory() as session:
                task.Result = await _run_ai_edit(
                    session=session,
                    submission_id=task.Submission_Id,
                    newsletter_type=task.Newsletter_Type,
                    editor_instructions=task.Editor_Instructions,
                )
        task.Status = "succeeded"
        task.Error_Message = None
    except AIEditError as e:
        task.Status = "failed"
        task.Error_Message = str(e)
    except HTTPException as e:
        task.Status = "failed"
        task.Error_Message = str(e.detail)
    except Exception:
        task.Status = "failed"
        task.Error_Message = "AI editing failed unexpectedly."
    finally:
        task.Updated_At = _utcnow()


@router.post(
    "/{submission_id}/edit",
    response_model=AIEditTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_ai_edit(
    submission_id: str,
    request: AIEditRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """Trigger AI editing on a submission for a specific newsletter type.

    This queues an AI edit task. A successful task creates an 'original'
    EditVersion (if not exists) and an 'ai_suggested' EditVersion.
    """
    result = await session.execute(
        sa.select(Submission.Id, Submission.Target_Newsletter).where(Submission.Id == submission_id)
    )
    submission = result.one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission.Target_Newsletter not in (request.Newsletter_Type, "both"):
        raise HTTPException(
            status_code=400,
            detail=f"Submission targets '{submission.Target_Newsletter}', not '{request.Newsletter_Type}'",
        )

    now = _utcnow()
    task = AIEditTaskState(
        Task_Id=str(uuid.uuid4()),
        Submission_Id=submission_id,
        Newsletter_Type=request.Newsletter_Type,
        Editor_Instructions=request.Editor_Instructions,
        Status="queued",
        Created_At=now,
        Updated_At=now,
    )
    _ai_edit_tasks[task.Task_Id] = task
    background_tasks.add_task(_process_ai_edit_task, task.Task_Id)

    return _serialize_task(task)


@router.get("/tasks/{task_id}", response_model=AIEditTaskResponse)
async def get_ai_edit_task(
    task_id: str,
    _staff: None = Depends(require_staff),
):
    """Get the status and result of an AI edit task."""
    task = _ai_edit_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="AI edit task not found")
    return _serialize_task(task)


@router.get("/{submission_id}/versions", response_model=list[EditVersionResponse])
async def list_edit_versions(
    submission_id: str,
    session: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """List all edit versions for a submission."""
    result = await session.execute(
        sa.select(EditVersion)
        .where(EditVersion.Submission_Id == submission_id)
        .order_by(EditVersion.Created_At)
    )
    versions = result.scalars().all()
    if not versions:
        raise HTTPException(status_code=404, detail="No edit versions found")
    return versions


@router.get("/{submission_id}/versions/{version_id}", response_model=EditVersionResponse)
async def get_edit_version(
    submission_id: str,
    version_id: str,
    session: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """Get a specific edit version."""
    result = await session.execute(
        sa.select(EditVersion).where(
            EditVersion.Id == version_id,
            EditVersion.Submission_Id == submission_id,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Edit version not found")
    return version


@router.post("/{submission_id}/finalize", response_model=EditVersionResponse)
async def save_editor_final(
    submission_id: str,
    data: EditorFinalCreate,
    session: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """Save the editor's final version of a submission.

    This creates an 'editor_final' EditVersion and updates the submission status.
    """
    # Verify submission exists
    result = await session.execute(
        sa.select(Submission).where(Submission.Id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Create final version
    version = EditVersion(
        Submission_Id=submission_id,
        Version_Type="editor_final",
        Headline=data.Headline,
        Body=data.Body,
        Headline_Case=data.Headline_Case,
    )
    session.add(version)

    # Persist the edited content on the submission so it is reflected everywhere
    submission.Original_Headline = data.Headline
    submission.Original_Body = data.Body
    submission.Status = "in_review"
    await session.commit()
    await session.refresh(version)
    return version

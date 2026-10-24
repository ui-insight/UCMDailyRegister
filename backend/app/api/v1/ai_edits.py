"""AI editing API endpoints."""

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_staff
from app.models.submission import Submission, SubmissionLink
from app.models.edit_history import EditVersion
from app.services import editorial_content, ai_edit_service
from app.schemas.ai_edit import (
    AIEditRequest, AIEditTaskResponse, EditVersionResponse, EditorFinalCreate,
)

router = APIRouter(prefix="/ai-edits", tags=["ai-edits"])


@router.post("/{submission_id}/edit", response_model=AIEditTaskResponse,
             status_code=status.HTTP_202_ACCEPTED)
async def trigger_ai_edit(
    submission_id: str, request: AIEditRequest, background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db), _staff: None = Depends(require_staff),
):
    """Commit a durable request before scheduling bounded background work."""
    task, scheduled = await ai_edit_service.enqueue(session, submission_id, request)
    response = ai_edit_service.serialize_task(task)
    if scheduled:
        background_tasks.add_task(ai_edit_service.process_task, task.Id)
    return response


@router.get("/tasks/{task_id}", response_model=AIEditTaskResponse)
async def get_ai_edit_task(
    task_id: str, session: AsyncSession = Depends(get_db), _staff: None = Depends(require_staff),
):
    return ai_edit_service.serialize_task(await ai_edit_service.get_task(session, task_id))


@router.post("/tasks/{task_id}/retry", response_model=AIEditTaskResponse,
             status_code=status.HTTP_202_ACCEPTED)
async def retry_ai_edit_task(
    task_id: str, background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db), _staff: None = Depends(require_staff),
):
    """Retry an interrupted/failed request without changing its durable ID."""
    task, scheduled = await ai_edit_service.retry(session, task_id)
    response = ai_edit_service.serialize_task(task)
    if scheduled:
        background_tasks.add_task(ai_edit_service.process_task, task.Id)
    return response


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
        .order_by(EditVersion.Created_At, EditVersion.Id)
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

    Creates an 'editor_final' EditVersion and, in the same transaction, either
    approves that exact revision or leaves the submission in review with
    nothing approved (see editorial_content.save_final). The submitted
    Original_Headline/Original_Body are never modified.
    """
    result = await session.execute(
        sa.select(Submission).where(Submission.Id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.Category != "job_opportunity" and not data.Headline.strip():
        raise HTTPException(
            status_code=422,
            detail="Headline is required for non-Jobs submissions",
        )

    try:
        version = await editorial_content.save_final(
            session,
            submission,
            headline="" if submission.Category == "job_opportunity" else data.Headline.strip(),
            body=data.Body,
            headline_case=data.Headline_Case,
            approve=data.Approve_For_Newsletter,
            base_revision_id=data.Base_Staff_Revision_Id,
            check_base="Base_Staff_Revision_Id" in data.model_fields_set,
        )
    except editorial_content.StaleRevision as stale:
        current = stale.current
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Someone saved a newer version while you were editing. "
                    "Nothing was saved; compare it with your text before saving again."
                ),
                "Status": submission.Status,
                "Current_Revision": None if current is None else {
                    "Id": current.Id,
                    "Headline": current.Headline,
                    "Body": current.Body,
                    "Approved": current.Id == submission.Approved_Version_Id,
                },
            },
        ) from stale

    if data.Links is not None:
        await session.execute(
            sa.delete(SubmissionLink).where(
                SubmissionLink.Submission_Id == submission_id,
            )
        )
        for index, link_data in enumerate(data.Links):
            session.add(
                SubmissionLink(
                    Submission_Id=submission_id,
                    Url=link_data.Url,
                    Anchor_Text=link_data.Anchor_Text,
                    Display_Order=link_data.Display_Order or index,
                )
            )

    await session.commit()
    await session.refresh(version)
    return version

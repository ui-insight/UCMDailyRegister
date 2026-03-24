"""AI editing API endpoints."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.api.deps import get_db
from app.models.submission import Submission
from app.models.edit_history import EditVersion
from app.services.ai.factory import get_llm_provider
from app.services.ai.editor import AIEditor
from app.schemas.ai_edit import (
    AIEditRequest,
    AIEditResponse,
    AIEditFlag,
    AIEditLink,
    TextDiffResponse,
    DiffSegment,
    EditVersionResponse,
    EditorFinalCreate,
)

router = APIRouter(prefix="/ai-edits", tags=["ai-edits"])


@router.post("/{submission_id}/edit", response_model=AIEditResponse)
async def trigger_ai_edit(
    submission_id: str,
    request: AIEditRequest,
    session: AsyncSession = Depends(get_db),
):
    """Trigger AI editing on a submission for a specific newsletter type.

    This creates an 'original' EditVersion (if not exists) and an 'ai_suggested' EditVersion.
    """
    # Load submission with links
    result = await session.execute(
        sa.select(Submission)
        .where(Submission.Id == submission_id)
        .options(selectinload(Submission.Links))
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Validate newsletter type matches submission target
    if submission.Target_Newsletter not in (request.Newsletter_Type, "both"):
        raise HTTPException(
            status_code=400,
            detail=f"Submission targets '{submission.Target_Newsletter}', not '{request.Newsletter_Type}'",
        )

    # Get LLM provider
    try:
        llm = get_llm_provider(settings)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Run AI editing pipeline
    editor = AIEditor(llm)
    edit_result = await editor.edit_submission(
        session=session,
        submission=submission,
        newsletter_type=request.Newsletter_Type,
    )

    # Save edit versions
    _original_version, ai_version = await editor.save_edit_versions(
        session=session,
        submission_id=submission_id,
        edit_result=edit_result,
        original_headline=submission.Original_Headline,
        original_body=submission.Original_Body,
    )

    # Update submission status
    submission.Status = "ai_edited"
    await session.commit()
    await session.refresh(ai_version)

    # Build response
    return AIEditResponse(
        Submission_Id=submission_id,
        Newsletter_Type=request.Newsletter_Type,
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


@router.get("/{submission_id}/versions", response_model=list[EditVersionResponse])
async def list_edit_versions(
    submission_id: str,
    session: AsyncSession = Depends(get_db),
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

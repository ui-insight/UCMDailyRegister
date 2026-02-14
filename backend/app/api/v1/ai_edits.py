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
        .where(Submission.id == submission_id)
        .options(selectinload(Submission.links))
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Validate newsletter type matches submission target
    if submission.target_newsletter not in (request.newsletter_type, "both"):
        raise HTTPException(
            status_code=400,
            detail=f"Submission targets '{submission.target_newsletter}', not '{request.newsletter_type}'",
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
        newsletter_type=request.newsletter_type,
    )

    # Save edit versions
    _original_version, ai_version = await editor.save_edit_versions(
        session=session,
        submission_id=submission_id,
        edit_result=edit_result,
        original_headline=submission.original_headline,
        original_body=submission.original_body,
    )

    # Update submission status
    submission.status = "ai_edited"
    await session.commit()
    await session.refresh(ai_version)

    # Build response
    return AIEditResponse(
        submission_id=submission_id,
        newsletter_type=request.newsletter_type,
        edited_headline=edit_result.edited_headline,
        edited_body=edit_result.edited_body,
        headline_case=edit_result.headline_case,
        changes_made=edit_result.changes_made,
        flags=[AIEditFlag(**f) for f in edit_result.flags],
        embedded_links=[AIEditLink(**l) for l in edit_result.embedded_links],
        confidence=edit_result.confidence,
        ai_provider=edit_result.ai_provider,
        ai_model=edit_result.ai_model,
        headline_diff=TextDiffResponse(
            segments=[DiffSegment(**s) for s in edit_result.headline_diff.get("segments", [])],
            change_count=edit_result.headline_diff.get("change_count", 0),
            similarity_ratio=edit_result.headline_diff.get("similarity_ratio", 1.0),
        ),
        body_diff=TextDiffResponse(
            segments=[DiffSegment(**s) for s in edit_result.body_diff.get("segments", [])],
            change_count=edit_result.body_diff.get("change_count", 0),
            similarity_ratio=edit_result.body_diff.get("similarity_ratio", 1.0),
        ),
        edit_version_id=ai_version.id,
    )


@router.get("/{submission_id}/versions", response_model=list[EditVersionResponse])
async def list_edit_versions(
    submission_id: str,
    session: AsyncSession = Depends(get_db),
):
    """List all edit versions for a submission."""
    result = await session.execute(
        sa.select(EditVersion)
        .where(EditVersion.submission_id == submission_id)
        .order_by(EditVersion.created_at)
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
            EditVersion.id == version_id,
            EditVersion.submission_id == submission_id,
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
        sa.select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Create final version
    version = EditVersion(
        submission_id=submission_id,
        version_type="editor_final",
        headline=data.headline,
        body=data.body,
        headline_case=data.headline_case,
    )
    session.add(version)

    # Update submission status
    submission.status = "in_review"
    await session.commit()
    await session.refresh(version)
    return version

"""In-app product feedback API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_staff
from app.schemas.feedback import (
    ProductFeedbackCreate,
    ProductFeedbackExportResponse,
    ProductFeedbackResponse,
    ProductFeedbackUpdate,
)
from app.services import feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=ProductFeedbackResponse, status_code=201)
async def create_feedback(
    data: ProductFeedbackCreate,
    db: AsyncSession = Depends(get_db),
):
    """Capture a user-submitted bug report or product idea."""
    return await feedback_service.create_feedback(db, data)


@router.get("", response_model=list[ProductFeedbackResponse])
async def list_feedback(
    status: str | None = None,
    feedback_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """List product feedback for staff review."""
    return await feedback_service.list_feedback(
        db,
        status=status,
        feedback_type=feedback_type,
    )


@router.patch("/{feedback_id}", response_model=ProductFeedbackResponse)
async def update_feedback(
    feedback_id: str,
    data: ProductFeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """Update staff review metadata for a feedback item."""
    feedback = await feedback_service.update_feedback(
        db,
        feedback_id,
        **data.model_dump(exclude_unset=True),
    )
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback item not found")
    return feedback


@router.get("/{feedback_id}/github-export", response_model=ProductFeedbackExportResponse)
async def export_feedback_to_github_markdown(
    feedback_id: str,
    db: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """Return a GitHub-ready title and Markdown body for staff export."""
    feedback = await feedback_service.get_feedback(db, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback item not found")
    title, body = feedback_service.build_github_export(feedback)
    return ProductFeedbackExportResponse(Title=title, Body=body)

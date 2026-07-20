"""In-app product feedback API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_staff
from app.schemas.feedback import (
    ProductFeedbackCreate,
    ProductFeedbackExportResponse,
    ProductFeedbackResponse,
    ProductFeedbackSummaryResponse,
    ProductFeedbackUpdate,
)
from app.services import feedback_service
from app.services.feedback_notifications import FeedbackNotifier, get_feedback_notifier

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=ProductFeedbackResponse, status_code=201)
async def create_feedback(
    data: ProductFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    notifier: FeedbackNotifier = Depends(get_feedback_notifier),
):
    """Capture a user-submitted bug report or product idea."""
    return await feedback_service.create_feedback(db, data, notifier)


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


@router.get("/summary", response_model=ProductFeedbackSummaryResponse)
async def get_feedback_summary(
    db: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """Return lightweight feedback and notification counts for staff surfaces."""
    return await feedback_service.get_feedback_summary(db)


@router.post("/{feedback_id}/notification/retry", response_model=ProductFeedbackResponse)
async def retry_feedback_notification(
    feedback_id: str,
    db: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
    notifier: FeedbackNotifier = Depends(get_feedback_notifier),
):
    """Retry delivery through the currently configured notification adapter."""
    feedback = await feedback_service.get_feedback(db, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback item not found")
    return await feedback_service.attempt_feedback_notification(db, feedback, notifier)


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

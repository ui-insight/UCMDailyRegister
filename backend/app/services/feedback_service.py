"""Business logic for in-app product feedback."""

import logging
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import ProductFeedback
from app.schemas.feedback import ProductFeedbackCreate
from app.services.feedback_notifications import (
    FeedbackNotifier,
    build_feedback_notification_payload,
)


logger = logging.getLogger(__name__)
MAX_NOTIFICATION_ERROR_LENGTH = 2000


async def create_feedback(
    db: AsyncSession,
    data: ProductFeedbackCreate,
    notifier: FeedbackNotifier,
) -> ProductFeedback:
    feedback = ProductFeedback(**data.model_dump())
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    await attempt_feedback_notification(db, feedback, notifier)
    return feedback


async def attempt_feedback_notification(
    db: AsyncSession,
    feedback: ProductFeedback,
    notifier: FeedbackNotifier,
) -> ProductFeedback:
    """Attempt delivery after persistence and record the operational outcome."""

    if not notifier.enabled:
        feedback.Notification_Status = "disabled"
        feedback.Notification_Last_Error = None
        await db.commit()
        await db.refresh(feedback)
        return feedback

    feedback.Notification_Status = "pending"
    feedback.Notification_Attempts += 1
    feedback.Notification_Last_Error = None

    try:
        payload = build_feedback_notification_payload(feedback)
        await notifier.send(payload)
    except Exception as exc:  # transport adapters define their own exception types
        feedback.Notification_Status = "failed"
        feedback.Notification_Last_Error = str(exc)[:MAX_NOTIFICATION_ERROR_LENGTH]
        logger.exception(
            "Feedback notification failed feedback_id=%s notifier=%s",
            feedback.Id,
            notifier.name,
        )
    else:
        feedback.Notification_Status = "sent"
        feedback.Notification_Sent_At = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(feedback)
    return feedback


async def list_feedback(
    db: AsyncSession,
    *,
    status: str | None = None,
    feedback_type: str | None = None,
) -> list[ProductFeedback]:
    query = sa.select(ProductFeedback).order_by(ProductFeedback.Created_At.desc())
    if status:
        query = query.where(ProductFeedback.Status == status)
    if feedback_type:
        query = query.where(ProductFeedback.Feedback_Type == feedback_type)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_feedback_summary(db: AsyncSession) -> dict[str, int]:
    """Return staff dashboard counts without loading feedback report contents."""

    result = await db.execute(
        sa.select(
            sa.func.sum(sa.case((ProductFeedback.Status == "new", 1), else_=0)),
            sa.func.sum(
                sa.case((ProductFeedback.Notification_Status == "failed", 1), else_=0)
            ),
            sa.func.sum(
                sa.case((ProductFeedback.Notification_Status == "pending", 1), else_=0)
            ),
        )
    )
    new_count, failed_count, pending_count = result.one()
    return {
        "New_Count": int(new_count or 0),
        "Failed_Notification_Count": int(failed_count or 0),
        "Pending_Notification_Count": int(pending_count or 0),
    }


async def get_feedback(
    db: AsyncSession,
    feedback_id: str,
) -> ProductFeedback | None:
    result = await db.execute(
        sa.select(ProductFeedback).where(ProductFeedback.Id == feedback_id)
    )
    return result.scalar_one_or_none()


async def update_feedback(
    db: AsyncSession,
    feedback_id: str,
    **kwargs,
) -> ProductFeedback | None:
    feedback = await get_feedback(db, feedback_id)
    if not feedback:
        return None

    for key, value in kwargs.items():
        if value is not None or key == "GitHub_URL":
            setattr(feedback, key, value)

    await db.commit()
    await db.refresh(feedback)
    return feedback


def build_github_export(feedback: ProductFeedback) -> tuple[str, str]:
    title_prefix = "Bug" if feedback.Feedback_Type == "bug" else "Idea"
    title = f"{title_prefix}: {feedback.Summary}"
    body = "\n".join(
        [
            "## User Report",
            "",
            feedback.Details,
            "",
            "## Reporter Context",
            "",
            f"- Submitted: {feedback.Created_At.isoformat()}",
            f"- Type: {feedback.Feedback_Type}",
            f"- Mode: {feedback.Submitter_Role}",
            f"- Route: {feedback.Route}",
            f"- Environment: {feedback.App_Environment}",
            f"- Host: {feedback.Host}",
            f"- Viewport: {feedback.Viewport}",
            f"- Browser: {feedback.Browser}",
            f"- Contact email provided: {'yes' if feedback.Contact_Email else 'no'}",
            "",
            "_Imported from UCM Daily Register in-app feedback. Sensitive submission body text, submitter contact details from newsletter records, and editorial notes were not collected automatically._",
        ]
    )
    return title, body

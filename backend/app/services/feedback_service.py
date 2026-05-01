"""Business logic for in-app product feedback."""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import ProductFeedback
from app.schemas.feedback import ProductFeedbackCreate


async def create_feedback(
    db: AsyncSession,
    data: ProductFeedbackCreate,
) -> ProductFeedback:
    feedback = ProductFeedback(**data.model_dump())
    db.add(feedback)
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

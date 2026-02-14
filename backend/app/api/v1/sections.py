"""Newsletter sections API endpoints."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.section import NewsletterSection
from app.schemas.newsletter import SectionResponse

router = APIRouter(prefix="/sections", tags=["sections"])


@router.get("", response_model=list[SectionResponse])
async def list_sections(
    newsletter_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List newsletter sections, optionally filtered by newsletter type."""
    query = sa.select(NewsletterSection).order_by(
        NewsletterSection.newsletter_type,
        NewsletterSection.display_order,
    )
    if newsletter_type:
        query = query.where(NewsletterSection.newsletter_type == newsletter_type)
    result = await db.execute(query)
    return result.scalars().all()

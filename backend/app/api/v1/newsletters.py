"""Newsletter CRUD and assembly API endpoints."""

from datetime import date

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.newsletter import Newsletter, NewsletterItem
from app.models.section import NewsletterSection
from app.services import newsletter_service
from app.schemas.newsletter import (
    NewsletterCreate,
    NewsletterResponse,
    NewsletterDetailResponse,
    NewsletterItemCreate,
    NewsletterItemUpdate,
    NewsletterItemResponse,
    AssembleRequest,
)
from app.utils.export import export_newsletter_docx

router = APIRouter(prefix="/newsletters", tags=["newsletters"])


@router.post("", response_model=NewsletterResponse, status_code=201)
async def create_newsletter(data: NewsletterCreate, db: AsyncSession = Depends(get_db)):
    """Create a new newsletter draft."""
    newsletter = await newsletter_service.create_newsletter(
        db, data.Newsletter_Type, data.Publish_Date
    )
    return newsletter


@router.get("", response_model=list[NewsletterResponse])
async def list_newsletters(
    newsletter_type: str | None = None,
    status: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List newsletters."""
    return await newsletter_service.list_newsletters(db, newsletter_type, status, limit)


@router.get("/{newsletter_id}", response_model=NewsletterDetailResponse)
async def get_newsletter(newsletter_id: str, db: AsyncSession = Depends(get_db)):
    """Get a newsletter with all its items."""
    newsletter = await newsletter_service.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    return newsletter


@router.patch("/{newsletter_id}/status", response_model=NewsletterResponse)
async def update_status(
    newsletter_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
):
    """Update newsletter status."""
    newsletter = await newsletter_service.update_newsletter_status(db, newsletter_id, status)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    return newsletter


@router.delete("/{newsletter_id}", status_code=204)
async def delete_newsletter(newsletter_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a newsletter."""
    if not await newsletter_service.delete_newsletter(db, newsletter_id):
        raise HTTPException(status_code=404, detail="Newsletter not found")


# --- Items ---


@router.post("/{newsletter_id}/items", response_model=NewsletterItemResponse, status_code=201)
async def add_item(
    newsletter_id: str,
    data: NewsletterItemCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add an item to a newsletter."""
    newsletter = await newsletter_service.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    item = await newsletter_service.add_item(
        db,
        newsletter_id=newsletter_id,
        submission_id=data.Submission_Id,
        section_id=data.Section_Id,
        final_headline=data.Final_Headline,
        final_body=data.Final_Body,
        position=data.Position,
        run_number=data.Run_Number,
    )
    return item


@router.patch("/{newsletter_id}/items/{item_id}", response_model=NewsletterItemResponse)
async def update_item(
    newsletter_id: str,
    item_id: str,
    data: NewsletterItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a newsletter item."""
    update_data = data.model_dump(exclude_unset=True)
    item = await newsletter_service.update_item(db, item_id, **update_data)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/{newsletter_id}/items/{item_id}", status_code=204)
async def remove_item(
    newsletter_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove an item from a newsletter."""
    if not await newsletter_service.remove_item(db, item_id):
        raise HTTPException(status_code=404, detail="Item not found")


@router.put("/{newsletter_id}/reorder")
async def reorder_items(
    newsletter_id: str,
    positions: list[dict],
    db: AsyncSession = Depends(get_db),
):
    """Reorder items in a newsletter. Body: [{"id": "...", "position": 0, "section_id": "..."}]"""
    await newsletter_service.reorder_items(db, newsletter_id, positions)
    return {"status": "ok"}


# --- Assembly ---


@router.post("/assemble", response_model=NewsletterDetailResponse)
async def assemble_newsletter(data: AssembleRequest, db: AsyncSession = Depends(get_db)):
    """Auto-populate a newsletter from approved submissions."""
    newsletter = await newsletter_service.assemble_newsletter(
        db, data.Newsletter_Type, data.Publish_Date
    )
    return newsletter


# --- Export ---


@router.get("/{newsletter_id}/export")
async def export_newsletter(newsletter_id: str, db: AsyncSession = Depends(get_db)):
    """Export a newsletter as a Word document."""
    newsletter = await newsletter_service.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    # Load sections for ordering
    sections_result = await db.execute(
        sa.select(NewsletterSection)
        .where(
            NewsletterSection.Newsletter_Type == newsletter.Newsletter_Type,
            NewsletterSection.Is_Active == True,  # noqa: E712
        )
        .order_by(NewsletterSection.Display_Order)
    )
    sections = list(sections_result.scalars().all())
    section_map = {s.Id: s for s in sections}

    # Organize items by section
    export_sections = []
    for section in sections:
        section_items = sorted(
            [it for it in newsletter.Items if it.Section_Id == section.Id],
            key=lambda it: it.Position,
        )
        if section_items:
            export_sections.append({
                "name": section.Name,
                "items": [
                    {"Final_Headline": it.Final_Headline, "Final_Body": it.Final_Body}
                    for it in section_items
                ],
            })

    buffer = export_newsletter_docx(
        newsletter_type=newsletter.Newsletter_Type,
        publish_date=newsletter.Publish_Date,
        sections=export_sections,
    )

    filename = f"{newsletter.Newsletter_Type}_{newsletter.Publish_Date.isoformat()}.docx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

"""Newsletter CRUD and assembly API endpoints."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SubmitterRole, get_db, get_submitter_role
from app.models.section import NewsletterSection
from app.services import (
    calendar_event_service,
    job_posting_service,
    newsletter_service,
    recurring_message_service,
    schedule_service,
)
from app.schemas.newsletter import (
    CalendarEventCandidateResponse,
    CalendarEventImportRequest,
    JobPostingCandidateResponse,
    JobPostingImportRequest,
    NewsletterCreate,
    NewsletterDetailResponse,
    NewsletterExternalItemResponse,
    NewsletterExternalItemUpdate,
    NewsletterItemCreate,
    NewsletterItemResponse,
    NewsletterItemUpdate,
    NewsletterResponse,
    AssembleRequest,
)
from app.schemas.recurring_message import RecurringMessageIssueCandidateResponse
from app.utils.export import export_newsletter_docx

router = APIRouter(prefix="/newsletters", tags=["newsletters"])


def _require_staff(submission_role: SubmitterRole) -> None:
    if submission_role != "staff":
        raise HTTPException(
            status_code=403,
            detail="This action is available to staff editors only.",
        )


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


@router.get(
    "/{newsletter_id}/recurring-messages",
    response_model=list[RecurringMessageIssueCandidateResponse],
)
async def list_recurring_message_candidates(
    newsletter_id: str,
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    """Fetch recurring message candidates for a newsletter issue."""
    _require_staff(submission_role)
    newsletter = await newsletter_service.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    return await recurring_message_service.list_issue_candidates(db, newsletter)


@router.post(
    "/{newsletter_id}/recurring-messages/{recurring_message_id}",
    response_model=NewsletterExternalItemResponse,
    status_code=201,
)
async def add_recurring_message(
    newsletter_id: str,
    recurring_message_id: str,
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    """Add a recurring message to a newsletter issue."""
    _require_staff(submission_role)
    newsletter = await newsletter_service.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    item = await recurring_message_service.add_recurring_message_to_newsletter(
        db,
        newsletter,
        recurring_message_id,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Recurring message not found")
    return item


@router.post("/{newsletter_id}/recurring-messages/{recurring_message_id}/skip", status_code=204)
async def skip_recurring_message(
    newsletter_id: str,
    recurring_message_id: str,
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    """Skip a recurring message for a specific newsletter issue."""
    _require_staff(submission_role)
    newsletter = await newsletter_service.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    if not await recurring_message_service.skip_recurring_message_for_newsletter(
        db,
        newsletter,
        recurring_message_id,
    ):
        raise HTTPException(status_code=404, detail="Recurring message not found")


@router.get(
    "/{newsletter_id}/calendar-events",
    response_model=list[CalendarEventCandidateResponse],
)
async def list_calendar_events(
    newsletter_id: str,
    extra_days: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Fetch candidate calendar events for a newsletter issue.

    The day-of-week import logic determines which dates to include:
      - Mon-Thu: events for today and tomorrow
      - Friday: events for Fri, Sat, Sun, and Mon
      - Weekly editions (summer/holiday): entire week + following Monday

    Use extra_days to include additional days beyond the default range.
    """
    newsletter = await newsletter_service.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    selected_source_ids = [
        item.Source_Id
        for item in newsletter.External_Items
        if item.Source_Type == "calendar_event"
    ]

    # Determine if this is a weekly edition by checking the schedule config
    config = await schedule_service.get_active_config(
        db, newsletter.Newsletter_Type, newsletter.Publish_Date
    )
    is_weekly = config is not None and not config.Is_Daily

    return await calendar_event_service.fetch_calendar_events(
        publish_date=newsletter.Publish_Date,
        newsletter_type=newsletter.Newsletter_Type,
        selected_source_ids=selected_source_ids,
        is_weekly=is_weekly,
        extra_days=extra_days,
    )


@router.get(
    "/{newsletter_id}/job-postings",
    response_model=list[JobPostingCandidateResponse],
)
async def list_job_postings(
    newsletter_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch candidate job postings for a newsletter issue."""
    newsletter = await newsletter_service.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    selected_source_ids = [
        item.Source_Id
        for item in newsletter.External_Items
        if item.Source_Type == "job_posting"
    ]
    return await job_posting_service.fetch_job_postings(
        selected_source_ids=selected_source_ids,
    )


@router.post(
    "/{newsletter_id}/calendar-events",
    response_model=NewsletterExternalItemResponse,
    status_code=201,
)
async def add_calendar_event(
    newsletter_id: str,
    data: CalendarEventImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import a calendar event into a newsletter section."""
    newsletter = await newsletter_service.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    existing = next(
        (
            item for item in newsletter.External_Items
            if item.Source_Type == "calendar_event" and item.Source_Id == data.Source_Id
        ),
        None,
    )
    if existing:
        return existing

    section_slug = newsletter_service.get_calendar_section_slug(newsletter.Newsletter_Type)
    section_result = await db.execute(
        sa.select(NewsletterSection).where(
            NewsletterSection.Newsletter_Type == newsletter.Newsletter_Type,
            NewsletterSection.Slug == section_slug,
        )
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=422, detail="Calendar section is not configured")

    event = calendar_event_service.CalendarEvent(
        source_id=data.Source_Id,
        source_type="calendar_event",
        url=data.Url,
        title=data.Title,
        description=data.Description,
        location=data.Location,
        event_start=data.Event_Start,
        event_end=data.Event_End,
    )
    item = await newsletter_service.add_external_item(
        db,
        newsletter_id=newsletter_id,
        section_id=section.Id,
        source_type=event.source_type,
        source_id=event.source_id,
        source_url=event.url,
        event_start=event.event_start,
        event_end=event.event_end,
        location=event.location,
        final_headline=event.title,
        final_body=calendar_event_service.build_event_body(event),
    )
    return item


@router.post(
    "/{newsletter_id}/job-postings",
    response_model=NewsletterExternalItemResponse,
    status_code=201,
)
async def add_job_posting(
    newsletter_id: str,
    data: JobPostingImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import a job posting into a newsletter section."""
    newsletter = await newsletter_service.get_newsletter(db, newsletter_id)
    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    existing = next(
        (
            item for item in newsletter.External_Items
            if item.Source_Type == "job_posting" and item.Source_Id == data.Source_Id
        ),
        None,
    )
    if existing:
        return existing

    section_slug = newsletter_service.get_job_postings_section_slug(newsletter.Newsletter_Type)
    section_result = await db.execute(
        sa.select(NewsletterSection).where(
            NewsletterSection.Newsletter_Type == newsletter.Newsletter_Type,
            NewsletterSection.Slug == section_slug,
        )
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=422, detail="Job postings section is not configured")

    posting = job_posting_service.JobPosting(
        source_id=data.Source_Id,
        source_type="job_posting",
        url=data.Url,
        title=data.Title,
        department=data.Department,
        posting_number=data.Posting_Number,
        location=data.Location,
        closing_date=data.Closing_Date,
        summary=data.Summary,
    )
    item = await newsletter_service.add_external_item(
        db,
        newsletter_id=newsletter_id,
        section_id=section.Id,
        source_type=posting.source_type,
        source_id=posting.source_id,
        source_url=posting.url,
        event_start=None,
        event_end=None,
        location=posting.location,
        final_headline=job_posting_service.build_job_headline(posting),
        final_body=job_posting_service.build_job_body(posting),
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


@router.patch(
    "/{newsletter_id}/external-items/{item_id}",
    response_model=NewsletterExternalItemResponse,
)
async def update_external_item(
    newsletter_id: str,
    item_id: str,
    data: NewsletterExternalItemUpdate,
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    """Update an imported external item."""
    _require_staff(submission_role)
    update_data = data.model_dump(exclude_unset=True)
    item = await newsletter_service.update_external_item(db, item_id, **update_data)
    if not item:
        raise HTTPException(status_code=404, detail="External item not found")
    return item


@router.delete("/{newsletter_id}/external-items/{item_id}", status_code=204)
async def remove_external_item(
    newsletter_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove an imported external item from a newsletter."""
    if not await newsletter_service.remove_external_item(db, item_id):
        raise HTTPException(status_code=404, detail="External item not found")


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

    # Organize items by section
    export_sections = []
    for section in sections:
        section_items = sorted(
            [
                *[it for it in newsletter.Items if it.Section_Id == section.Id],
                *[it for it in newsletter.External_Items if it.Section_Id == section.Id],
            ],
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

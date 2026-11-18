"""Newsletter CRUD and assembly service."""

import logging
from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.newsletter import Newsletter, NewsletterExternalItem, NewsletterItem
from app.models.section import NewsletterSection
from app.models.submission import Submission
from app.services import editorial_content, recurring_message_service, submission_service
from app.utils.actionable_dates import UNTIMED, earliest_actionable_moment

logger = logging.getLogger(__name__)


async def create_newsletter(
    db: AsyncSession,
    newsletter_type: str,
    publish_date: date,
) -> Newsletter:
    """Create a new newsletter draft."""
    newsletter = Newsletter(
        Newsletter_Type=newsletter_type,
        Publish_Date=publish_date,
        Status="draft",
    )
    db.add(newsletter)
    await db.commit()
    await db.refresh(newsletter)
    return newsletter


async def get_newsletter(db: AsyncSession, newsletter_id: str) -> Newsletter | None:
    result = await db.execute(
        sa.select(Newsletter)
        .where(Newsletter.Id == newsletter_id)
        .options(
            selectinload(Newsletter.Items),
            selectinload(Newsletter.External_Items),
        )
    )
    return result.scalar_one_or_none()


async def list_newsletters(
    db: AsyncSession,
    newsletter_type: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[Newsletter]:
    query = sa.select(Newsletter).options(
        selectinload(Newsletter.Items),
        selectinload(Newsletter.External_Items),
    )
    if newsletter_type:
        query = query.where(Newsletter.Newsletter_Type == newsletter_type)
    if status:
        query = query.where(Newsletter.Status == status)
    query = query.order_by(Newsletter.Publish_Date.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_newsletter_status(
    db: AsyncSession, newsletter_id: str, status: str
) -> Newsletter | None:
    newsletter = await get_newsletter(db, newsletter_id)
    if not newsletter:
        return None
    newsletter.Status = status
    await db.commit()
    await db.refresh(newsletter)
    return newsletter


async def delete_newsletter(db: AsyncSession, newsletter_id: str) -> bool:
    newsletter = await get_newsletter(db, newsletter_id)
    if not newsletter:
        return False
    await db.delete(newsletter)
    await db.commit()
    return True


# --- Item management ---


def section_order_key(item: NewsletterItem | NewsletterExternalItem) -> tuple[int, str, str]:
    """The one order rule for a section's items, in the Builder and the Word export.

    Submissions and imported items share one position sequence per section
    (#509). Positions are renumbered 0..n-1 whenever a section changes, so the
    headline and Id only break ties left in data written before that. The
    Builder sorts with the same rule.
    """
    return (item.Position, item.Final_Headline or "", item.Id)


async def _section_items(
    db: AsyncSession,
    newsletter_id: str,
    section_id: str,
) -> list[NewsletterItem | NewsletterExternalItem]:
    items: list[NewsletterItem | NewsletterExternalItem] = []
    for model in (NewsletterItem, NewsletterExternalItem):
        result = await db.execute(
            sa.select(model).where(
                model.Newsletter_Id == newsletter_id,
                model.Section_Id == section_id,
            )
        )
        items.extend(result.scalars().all())
    return items


async def renumber_section(db: AsyncSession, newsletter_id: str, section_id: str) -> None:
    """Give a section's items positions 0..n-1 in their current order."""
    items = await _section_items(db, newsletter_id, section_id)
    for index, item in enumerate(sorted(items, key=section_order_key)):
        item.Position = index


async def _next_section_position(db: AsyncSession, newsletter_id: str, section_id: str) -> int:
    """The position after every item in the section, submissions and imports alike."""
    items = await _section_items(db, newsletter_id, section_id)
    return max((item.Position for item in items), default=-1) + 1


def _next_position_in(
    newsletter: Newsletter,
    section_id: str,
    *,
    exclude: NewsletterItem | None = None,
) -> int:
    """`_next_section_position` over a newsletter's loaded items.

    Compares objects, not Ids: items added during assembly have no Id yet.
    """
    positions = [
        item.Position
        for item in (*newsletter.Items, *newsletter.External_Items)
        if item.Section_Id == section_id and item is not exclude
    ]
    return max(positions, default=-1) + 1


async def add_item(
    db: AsyncSession,
    newsletter_id: str,
    submission_id: str,
    section_id: str,
    final_headline: str,
    final_body: str,
    position: int = 0,
    run_number: int = 1,
) -> NewsletterItem:
    item = NewsletterItem(
        Newsletter_Id=newsletter_id,
        Submission_Id=submission_id,
        Section_Id=section_id,
        Final_Headline=final_headline,
        Final_Body=final_body,
        Position=position,
        Run_Number=run_number,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def add_external_item(
    db: AsyncSession,
    newsletter_id: str,
    section_id: str,
    source_type: str,
    source_id: str,
    source_url: str | None,
    event_start,
    event_end,
    location: str | None,
    final_headline: str,
    final_body: str,
    commit: bool = True,
) -> NewsletterExternalItem:
    # A maximum of 0 is a real position, not "no items" (#509).
    position = await _next_section_position(db, newsletter_id, section_id)
    item = NewsletterExternalItem(
        Newsletter_Id=newsletter_id,
        Section_Id=section_id,
        Source_Type=source_type,
        Source_Id=source_id,
        Source_Url=source_url,
        Event_Start=event_start,
        Event_End=event_end,
        Location=location,
        Position=position,
        Final_Headline=final_headline,
        Final_Body=final_body,
    )
    db.add(item)
    await db.flush()
    if commit:
        await db.commit()
        await db.refresh(item)
    return item


async def update_item(
    db: AsyncSession,
    newsletter_id: str,
    item_id: str,
    **kwargs,
) -> NewsletterItem | None:
    result = await db.execute(
        sa.select(NewsletterItem).where(
            NewsletterItem.Id == item_id,
            NewsletterItem.Newsletter_Id == newsletter_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return None
    new_section_id = kwargs.get("Section_Id")
    if new_section_id is not None and new_section_id != item.Section_Id:
        item.Manually_Placed = True
    if any(
        kwargs.get(field) is not None and kwargs[field] != getattr(item, field)
        for field in ("Final_Headline", "Final_Body")
    ):
        # Staff changed this edition's copy; reassembly and upstream
        # refreshes only replace it when staff choose to.
        item.Edition_Edited = True
    for key, value in kwargs.items():
        if value is not None:
            setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def _get_item(db: AsyncSession, newsletter_id: str, item_id: str) -> NewsletterItem | None:
    result = await db.execute(
        sa.select(NewsletterItem).where(
            NewsletterItem.Id == item_id,
            NewsletterItem.Newsletter_Id == newsletter_id,
        )
    )
    return result.scalar_one_or_none()


async def refresh_item_from_approved(
    db: AsyncSession, newsletter_id: str, item_id: str
) -> NewsletterItem | None:
    """Replace an item's copy with the submission's approved revision.

    Raises editorial_content.NoApprovedRevision when there is none.
    """
    item = await _get_item(db, newsletter_id, item_id)
    if item is None:
        return None
    editorial_content.refresh_from_approved(item)
    await db.commit()
    await db.refresh(item)
    return item


async def keep_item_edition_copy(
    db: AsyncSession, newsletter_id: str, item_id: str
) -> NewsletterItem | None:
    """Keep an item's copy and stop flagging its current approved revision."""
    item = await _get_item(db, newsletter_id, item_id)
    if item is None:
        return None
    editorial_content.keep_edition_copy(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_external_item(
    db: AsyncSession,
    newsletter_id: str,
    item_id: str,
    **kwargs,
) -> NewsletterExternalItem | None:
    result = await db.execute(
        sa.select(NewsletterExternalItem).where(
            NewsletterExternalItem.Id == item_id,
            NewsletterExternalItem.Newsletter_Id == newsletter_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def remove_item(db: AsyncSession, newsletter_id: str, item_id: str) -> bool:
    result = await db.execute(
        sa.select(NewsletterItem).where(
            NewsletterItem.Id == item_id,
            NewsletterItem.Newsletter_Id == newsletter_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True


async def remove_external_item(
    db: AsyncSession, newsletter_id: str, item_id: str
) -> bool:
    result = await db.execute(
        sa.select(NewsletterExternalItem).where(
            NewsletterExternalItem.Id == item_id,
            NewsletterExternalItem.Newsletter_Id == newsletter_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True


async def reorder_items(
    db: AsyncSession,
    newsletter_id: str,
    item_positions: list[dict],
) -> None:
    """Update positions for multiple items.

    Submissions may change section. Imported items (events, jobs, recurring
    messages, academic dates) are listed so a move keeps its place among
    them; they keep their section (#509).
    """
    touched_sections: set[str] = set()
    for pos in item_positions:
        item_id = pos.get("Id") or pos.get("id")
        position = pos.get("Position", pos.get("position"))
        section_id = pos.get("Section_Id") or pos.get("section_id")
        result = await db.execute(
            sa.select(NewsletterItem).where(
                NewsletterItem.Id == item_id,
                NewsletterItem.Newsletter_Id == newsletter_id,
            )
        )
        item = result.scalar_one_or_none()
        if item:
            touched_sections.add(item.Section_Id)
            if position is not None:
                item.Position = position
            if section_id:
                if section_id != item.Section_Id:
                    item.Manually_Placed = True
                item.Section_Id = section_id
            touched_sections.add(item.Section_Id)
            continue
        external = await db.execute(
            sa.select(NewsletterExternalItem).where(
                NewsletterExternalItem.Id == item_id,
                NewsletterExternalItem.Newsletter_Id == newsletter_id,
            )
        )
        external_item = external.scalar_one_or_none()
        if external_item and position is not None:
            external_item.Position = position
            touched_sections.add(external_item.Section_Id)
    await db.flush()
    for section_id in touched_sections:
        await renumber_section(db, newsletter_id, section_id)
    await db.commit()


# --- Assembly ---


async def assemble_newsletter(
    db: AsyncSession,
    newsletter_type: str,
    publish_date: date,
) -> Newsletter:
    """Auto-populate a newsletter from approved submissions."""
    result = await db.execute(
        sa.select(Newsletter)
        .where(
            Newsletter.Newsletter_Type == newsletter_type,
            Newsletter.Publish_Date == publish_date,
        )
        .options(
            selectinload(Newsletter.Items),
            selectinload(Newsletter.External_Items),
        )
    )
    newsletter = result.scalar_one_or_none()

    if not newsletter:
        newsletter = Newsletter(
            Newsletter_Type=newsletter_type,
            Publish_Date=publish_date,
            Status="draft",
        )
        newsletter.Items = []
        newsletter.External_Items = []
        db.add(newsletter)
        await db.flush()

    target_filter = sa.or_(
        Submission.Target_Newsletter == newsletter_type,
        Submission.Target_Newsletter == "both",
    )
    subs_result = await db.execute(
        sa.select(Submission)
        .where(
            Submission.Status.in_(["approved", "scheduled"]),
            target_filter,
        )
        .options(
            selectinload(Submission.Edit_Versions),
            selectinload(Submission.Schedule_Requests),
        )
        .order_by(Submission.Created_At.asc())
    )
    submissions = _in_default_order(list(subs_result.scalars().all()), publish_date)

    existing_items_by_sub = {item.Submission_Id: item for item in newsletter.Items}

    sections_result = await db.execute(
        sa.select(NewsletterSection)
        .where(NewsletterSection.Newsletter_Type == newsletter_type, NewsletterSection.Is_Active == True)  # noqa: E712
        .order_by(NewsletterSection.Display_Order)
    )
    sections = list(sections_result.scalars().all())
    section_map = {s.Slug: s for s in sections}
    category_section_map = _get_category_section_map(newsletter_type)
    occurrence_cache = submission_service.OccurrenceFilterCache()

    for sub in submissions:
        existing_item = existing_items_by_sub.get(sub.Id)
        if existing_item is None:
            occurrence_dates = await submission_service.get_submission_occurrence_dates(
                db,
                sub,
                publish_date,
                publish_date,
                newsletter_type=newsletter_type,
                occurrence_cache=occurrence_cache,
            )
            if publish_date not in occurrence_dates:
                continue

        section_slug = category_section_map.get(sub.Category)
        section = section_map.get(section_slug) if section_slug else None
        if not section:
            logger.warning(
                "No section mapping for category '%s' (submission %s), defaulting to employee-news",
                sub.Category,
                sub.Id,
            )
            section = section_map.get("employee-news") or (sections[0] if sections else None)
        if not section:
            continue

        if existing_item is not None:
            # Re-sync auto-placed items to the current category mapping;
            # placements staff moved by hand are left alone.
            if not existing_item.Manually_Placed and existing_item.Section_Id != section.Id:
                existing_item.Position = _next_position_in(
                    newsletter, section.Id, exclude=existing_item
                )
                existing_item.Section_Id = section.Id
            continue

        headline, body, source_version_id = editorial_content.publishable_text(sub)
        section_items = [it for it in newsletter.Items if it.Section_Id == section.Id]
        if sub.Category == "job_opportunity":
            # Jobs are ordered newest-first. The query walks oldest-first so each
            # newly encountered job is prepended ahead of existing job listings.
            for item in section_items:
                item.Position += 1
            for item in newsletter.External_Items:
                if item.Section_Id == section.Id:
                    item.Position += 1
            position = 0
        else:
            # After every item already in the section, imports included (#509).
            position = _next_position_in(newsletter, section.Id)

        item = NewsletterItem(
            Newsletter_Id=newsletter.Id,
            Submission_Id=sub.Id,
            Section_Id=section.Id,
            Final_Headline=headline,
            Final_Body=body,
            Position=position,
            Run_Number=1,
            Source_Version_Id=source_version_id,
        )
        db.add(item)
        newsletter.Items.append(item)

    await recurring_message_service.sync_newsletter_recurring_messages(db, newsletter)
    await db.flush()
    for section in sections:
        await renumber_section(db, newsletter.Id, section.Id)
    await db.commit()
    return await get_newsletter(db, newsletter.Id)


def _in_default_order(submissions: list[Submission], publish_date: date) -> list[Submission]:
    """Order submissions for placement by earliest actionable date and time.

    ``submissions`` arrive oldest-first. Items whose copy names an upcoming
    event date or deadline go in by that date (#388), then by start time
    within the day, untimed items first (#531); items with no date go last.
    Ties keep submission order. Job listings keep their oldest-first walk, which the
    assembly loop turns into newest-first.

    This only decides where newly placed items go. Assembly never moves
    items already in the edition, so staff reordering is kept.
    """
    jobs = [sub for sub in submissions if sub.Category == "job_opportunity"]
    others = [sub for sub in submissions if sub.Category != "job_opportunity"]

    def actionable(sub: Submission) -> tuple[bool, date, int]:
        headline, body, _ = editorial_content.publishable_text(sub)
        earliest = earliest_actionable_moment(
            (headline, body), publish_date, known_dates=(sub.Survey_End_Date,)
        )
        # Undated items go after every dated one (Joy, 2026-11-16).
        if earliest is None:
            return (True, publish_date, UNTIMED)
        return (False, *earliest)

    return sorted(others, key=actionable) + jobs


def _get_category_section_map(newsletter_type: str) -> dict[str, str]:
    """Map submission categories to section slugs."""
    if newsletter_type == "tdr":
        return {
            "faculty_staff": "employee-news",
            "employee_announcement": "employee-announcements",
            "survey": "employee-news",
            "ucm_feature_story": "feature-stories",
            "calendar_event": "todays-events",
            "kudos": "kudos",
            "news_release": "news-releases",
            "in_memoriam": "in-memoriam",
            "job_opportunity": "job-opportunities",
            "student": "employee-news",
        }
    else:
        return {
            "student": "news-and-updates",
            "calendar_event": "weekly-events",
            "faculty_staff": "news-and-updates",
            "employee_announcement": "news-and-updates",
            "survey": "news-and-updates",
            "ucm_feature_story": "news-and-updates",
            "kudos": "news-and-updates",
            "news_release": "news-and-updates",
            "job_opportunity": "help-wanted",
            "in_memoriam": "news-and-updates",
        }


def get_calendar_section_slug(newsletter_type: str) -> str:
    """Return the section slug used for imported calendar events."""
    return "todays-events" if newsletter_type == "tdr" else "weekly-events"


def get_job_postings_section_slug(newsletter_type: str) -> str:
    """Return the section slug used for imported job postings."""
    return "job-opportunities" if newsletter_type == "tdr" else "help-wanted"


def get_academic_dates_section_slug() -> str:
    """Return the My UI section slug used for manually imported registrar dates."""
    return "academic-dates-and-deadlines"

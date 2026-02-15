"""Newsletter CRUD and assembly service."""

from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.newsletter import Newsletter, NewsletterItem
from app.models.section import NewsletterSection
from app.models.submission import Submission
from app.models.edit_history import EditVersion


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
        .options(selectinload(Newsletter.Items))
    )
    return result.scalar_one_or_none()


async def list_newsletters(
    db: AsyncSession,
    newsletter_type: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[Newsletter]:
    query = sa.select(Newsletter).options(selectinload(Newsletter.Items))
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


async def update_item(
    db: AsyncSession,
    item_id: str,
    **kwargs,
) -> NewsletterItem | None:
    result = await db.execute(
        sa.select(NewsletterItem).where(NewsletterItem.Id == item_id)
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


async def remove_item(db: AsyncSession, item_id: str) -> bool:
    result = await db.execute(
        sa.select(NewsletterItem).where(NewsletterItem.Id == item_id)
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
    """Update positions for multiple items."""
    for pos in item_positions:
        item_id = pos.get("Id") or pos.get("id")
        result = await db.execute(
            sa.select(NewsletterItem).where(
                NewsletterItem.Id == item_id,
                NewsletterItem.Newsletter_Id == newsletter_id,
            )
        )
        item = result.scalar_one_or_none()
        if item:
            item.Position = pos.get("Position", pos.get("position", item.Position))
            section_id = pos.get("Section_Id") or pos.get("section_id")
            if section_id:
                item.Section_Id = section_id
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
        .options(selectinload(Newsletter.Items))
    )
    newsletter = result.scalar_one_or_none()

    if not newsletter:
        newsletter = Newsletter(
            Newsletter_Type=newsletter_type,
            Publish_Date=publish_date,
            Status="draft",
        )
        newsletter.Items = []
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
    submissions = list(subs_result.scalars().all())

    existing_sub_ids = {item.Submission_Id for item in newsletter.Items}

    sections_result = await db.execute(
        sa.select(NewsletterSection)
        .where(NewsletterSection.Newsletter_Type == newsletter_type, NewsletterSection.Is_Active == True)  # noqa: E712
        .order_by(NewsletterSection.Display_Order)
    )
    sections = list(sections_result.scalars().all())
    section_map = {s.Slug: s for s in sections}
    category_section_map = _get_category_section_map(newsletter_type)

    for sub in submissions:
        if sub.Id in existing_sub_ids:
            continue

        headline, body = _get_best_text(sub)
        section_slug = category_section_map.get(sub.Category)
        section = section_map.get(section_slug) if section_slug else None
        if not section:
            section = sections[0] if sections else None
        if not section:
            continue

        section_items = [it for it in newsletter.Items if it.Section_Id == section.Id]
        position = len(section_items)

        item = NewsletterItem(
            Newsletter_Id=newsletter.Id,
            Submission_Id=sub.Id,
            Section_Id=section.Id,
            Final_Headline=headline,
            Final_Body=body,
            Position=position,
            Run_Number=1,
        )
        db.add(item)
        newsletter.Items.append(item)

    await db.commit()
    return await get_newsletter(db, newsletter.Id)


def _get_category_section_map(newsletter_type: str) -> dict[str, str]:
    """Map submission categories to section slugs."""
    if newsletter_type == "tdr":
        return {
            "faculty_staff": "employee-news",
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
            "kudos": "news-and-updates",
            "news_release": "news-and-updates",
            "job_opportunity": "help-wanted",
            "in_memoriam": "news-and-updates",
        }


def _get_best_text(submission: Submission) -> tuple[str, str]:
    """Get the best available headline/body from edit versions."""
    if submission.Edit_Versions:
        for vtype in ("editor_final", "ai_suggested", "original"):
            for v in submission.Edit_Versions:
                if v.Version_Type == vtype:
                    return v.Headline, v.Body

    return submission.Original_Headline, submission.Original_Body

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
        newsletter_type=newsletter_type,
        publish_date=publish_date,
        status="draft",
    )
    db.add(newsletter)
    await db.commit()
    await db.refresh(newsletter)
    return newsletter


async def get_newsletter(db: AsyncSession, newsletter_id: str) -> Newsletter | None:
    result = await db.execute(
        sa.select(Newsletter)
        .where(Newsletter.id == newsletter_id)
        .options(selectinload(Newsletter.items))
    )
    return result.scalar_one_or_none()


async def list_newsletters(
    db: AsyncSession,
    newsletter_type: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[Newsletter]:
    query = sa.select(Newsletter).options(selectinload(Newsletter.items))
    if newsletter_type:
        query = query.where(Newsletter.newsletter_type == newsletter_type)
    if status:
        query = query.where(Newsletter.status == status)
    query = query.order_by(Newsletter.publish_date.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_newsletter_status(
    db: AsyncSession, newsletter_id: str, status: str
) -> Newsletter | None:
    newsletter = await get_newsletter(db, newsletter_id)
    if not newsletter:
        return None
    newsletter.status = status
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
        newsletter_id=newsletter_id,
        submission_id=submission_id,
        section_id=section_id,
        final_headline=final_headline,
        final_body=final_body,
        position=position,
        run_number=run_number,
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
        sa.select(NewsletterItem).where(NewsletterItem.id == item_id)
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
        sa.select(NewsletterItem).where(NewsletterItem.id == item_id)
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
    """Update positions for multiple items. item_positions: [{"id": "...", "position": 0}, ...]"""
    for pos in item_positions:
        result = await db.execute(
            sa.select(NewsletterItem).where(
                NewsletterItem.id == pos["id"],
                NewsletterItem.newsletter_id == newsletter_id,
            )
        )
        item = result.scalar_one_or_none()
        if item:
            item.position = pos["position"]
            if "section_id" in pos:
                item.section_id = pos["section_id"]
    await db.commit()


# --- Assembly ---


async def assemble_newsletter(
    db: AsyncSession,
    newsletter_type: str,
    publish_date: date,
) -> Newsletter:
    """Auto-populate a newsletter from approved submissions.

    Steps:
    1. Create or get existing newsletter for this type+date
    2. Find approved submissions targeting this newsletter type
    3. Get the best available text (editor_final > ai_suggested > original)
    4. Map submissions to sections based on category
    5. Order chronologically within each section
    6. Skip submissions already in this newsletter (dedup)
    """
    # 1. Get or create newsletter
    result = await db.execute(
        sa.select(Newsletter)
        .where(
            Newsletter.newsletter_type == newsletter_type,
            Newsletter.publish_date == publish_date,
        )
        .options(selectinload(Newsletter.items))
    )
    newsletter = result.scalar_one_or_none()

    if not newsletter:
        newsletter = Newsletter(
            newsletter_type=newsletter_type,
            publish_date=publish_date,
            status="draft",
        )
        newsletter.items = []  # Initialize to avoid lazy load in async
        db.add(newsletter)
        await db.flush()

    # 2. Find approved submissions
    target_filter = sa.or_(
        Submission.target_newsletter == newsletter_type,
        Submission.target_newsletter == "both",
    )
    subs_result = await db.execute(
        sa.select(Submission)
        .where(
            Submission.status.in_(["approved", "scheduled"]),
            target_filter,
        )
        .options(
            selectinload(Submission.edit_versions),
            selectinload(Submission.schedule_requests),
        )
        .order_by(Submission.created_at.asc())
    )
    submissions = list(subs_result.scalars().all())

    # 3. Get existing item submission IDs for dedup
    existing_sub_ids = {item.submission_id for item in newsletter.items}

    # 4. Load sections for mapping
    sections_result = await db.execute(
        sa.select(NewsletterSection)
        .where(NewsletterSection.newsletter_type == newsletter_type, NewsletterSection.is_active == True)  # noqa: E712
        .order_by(NewsletterSection.display_order)
    )
    sections = list(sections_result.scalars().all())
    section_map = {s.slug: s for s in sections}

    # Category -> section slug mapping
    category_section_map = _get_category_section_map(newsletter_type)

    # 5. Add submissions
    for sub in submissions:
        if sub.id in existing_sub_ids:
            continue

        # Get best text
        headline, body = _get_best_text(sub)

        # Determine section
        section_slug = category_section_map.get(sub.category)
        section = section_map.get(section_slug) if section_slug else None
        if not section:
            # Default to first section
            section = sections[0] if sections else None
        if not section:
            continue

        # Count existing items in this section for positioning
        section_items = [it for it in newsletter.items if it.section_id == section.id]
        position = len(section_items)

        item = NewsletterItem(
            newsletter_id=newsletter.id,
            submission_id=sub.id,
            section_id=section.id,
            final_headline=headline,
            final_body=body,
            position=position,
            run_number=1,
        )
        db.add(item)
        newsletter.items.append(item)

    await db.commit()
    return await get_newsletter(db, newsletter.id)


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
    else:  # myui
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
    """Get the best available headline/body from edit versions.

    Priority: editor_final > ai_suggested > original
    """
    if submission.edit_versions:
        # Sort by priority
        for vtype in ("editor_final", "ai_suggested", "original"):
            for v in submission.edit_versions:
                if v.version_type == vtype:
                    return v.headline, v.body

    return submission.original_headline, submission.original_body

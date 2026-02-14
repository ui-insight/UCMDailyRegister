from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.submission import Submission, SubmissionLink, SubmissionScheduleRequest
from app.schemas.submission import SubmissionCreate, SubmissionUpdate


async def create_submission(db: AsyncSession, data: SubmissionCreate) -> Submission:
    submission = Submission(
        category=data.category,
        target_newsletter=data.target_newsletter,
        original_headline=data.original_headline,
        original_body=data.original_body,
        submitter_name=data.submitter_name,
        submitter_email=data.submitter_email,
        submitter_notes=data.submitter_notes,
    )
    db.add(submission)
    await db.flush()

    for i, link_data in enumerate(data.links):
        link = SubmissionLink(
            submission_id=submission.id,
            url=link_data.url,
            anchor_text=link_data.anchor_text,
            display_order=link_data.display_order or i,
        )
        db.add(link)

    for sched_data in data.schedule_requests:
        sched = SubmissionScheduleRequest(
            submission_id=submission.id,
            requested_date=sched_data.requested_date,
            repeat_count=sched_data.repeat_count,
            repeat_note=sched_data.repeat_note,
        )
        db.add(sched)

    await db.commit()
    return await get_submission(db, submission.id)


async def get_submission(db: AsyncSession, submission_id: str) -> Submission | None:
    result = await db.execute(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(
            selectinload(Submission.links),
            selectinload(Submission.schedule_requests),
            selectinload(Submission.edit_versions),
        )
    )
    return result.scalar_one_or_none()


async def list_submissions(
    db: AsyncSession,
    status: str | None = None,
    category: str | None = None,
    target_newsletter: str | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Submission], int]:
    query = select(Submission).options(
        selectinload(Submission.links),
        selectinload(Submission.schedule_requests),
    )
    count_query = select(func.count()).select_from(Submission)

    if status:
        query = query.where(Submission.status == status)
        count_query = count_query.where(Submission.status == status)
    if category:
        query = query.where(Submission.category == category)
        count_query = count_query.where(Submission.category == category)
    if target_newsletter:
        query = query.where(Submission.target_newsletter == target_newsletter)
        count_query = count_query.where(Submission.target_newsletter == target_newsletter)
    if search:
        pattern = f"%{search}%"
        search_filter = Submission.original_headline.ilike(pattern) | Submission.original_body.ilike(pattern) | Submission.submitter_name.ilike(pattern)
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    query = query.order_by(Submission.created_at.desc()).offset(offset).limit(limit)

    total = (await db.execute(count_query)).scalar()
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def update_submission(
    db: AsyncSession, submission_id: str, data: SubmissionUpdate
) -> Submission | None:
    submission = await get_submission(db, submission_id)
    if not submission:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(submission, field, value)

    await db.commit()
    await db.refresh(submission)
    return await get_submission(db, submission_id)


async def delete_submission(db: AsyncSession, submission_id: str) -> bool:
    submission = await get_submission(db, submission_id)
    if not submission:
        return False
    await db.delete(submission)
    await db.commit()
    return True


# --- Link management ---


async def add_link(
    db: AsyncSession, submission_id: str, url: str, anchor_text: str | None = None, display_order: int = 0
) -> SubmissionLink | None:
    submission = await get_submission(db, submission_id)
    if not submission:
        return None
    link = SubmissionLink(
        submission_id=submission_id,
        url=url,
        anchor_text=anchor_text,
        display_order=display_order,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def delete_link(db: AsyncSession, link_id: str) -> bool:
    result = await db.execute(select(SubmissionLink).where(SubmissionLink.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        return False
    await db.delete(link)
    await db.commit()
    return True


# --- Schedule request management ---


async def add_schedule_request(
    db: AsyncSession,
    submission_id: str,
    requested_date=None,
    repeat_count: int = 1,
    repeat_note: str | None = None,
) -> SubmissionScheduleRequest | None:
    submission = await get_submission(db, submission_id)
    if not submission:
        return None
    sched = SubmissionScheduleRequest(
        submission_id=submission_id,
        requested_date=requested_date,
        repeat_count=repeat_count,
        repeat_note=repeat_note,
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)
    return sched


async def delete_schedule_request(db: AsyncSession, schedule_id: str) -> bool:
    result = await db.execute(
        select(SubmissionScheduleRequest).where(SubmissionScheduleRequest.id == schedule_id)
    )
    sched = result.scalar_one_or_none()
    if not sched:
        return False
    await db.delete(sched)
    await db.commit()
    return True


# --- Image management ---


async def set_image(db: AsyncSession, submission_id: str, image_path: str) -> Submission | None:
    submission = await get_submission(db, submission_id)
    if not submission:
        return None
    submission.has_image = True
    submission.image_path = image_path
    await db.commit()
    return await get_submission(db, submission_id)

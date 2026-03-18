"""Submission CRUD and related operations."""

from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.submission import Submission, SubmissionLink, SubmissionScheduleRequest
from app.schemas.submission import SubmissionCreate, SubmissionUpdate


async def create_submission(db: AsyncSession, data: SubmissionCreate) -> Submission:
    submission = Submission(
        Category=data.Category,
        Target_Newsletter=data.Target_Newsletter,
        Original_Headline=data.Original_Headline,
        Original_Body=data.Original_Body,
        Submitter_Name=data.Submitter_Name,
        Submitter_Email=data.Submitter_Email,
        Submitter_Notes=data.Submitter_Notes,
    )
    db.add(submission)
    await db.flush()

    for i, link_data in enumerate(data.Links):
        link = SubmissionLink(
            Submission_Id=submission.Id,
            Url=link_data.Url,
            Anchor_Text=link_data.Anchor_Text,
            Display_Order=link_data.Display_Order or i,
        )
        db.add(link)

    for sched_data in data.Schedule_Requests:
        sched = SubmissionScheduleRequest(
            Submission_Id=submission.Id,
            Requested_Date=sched_data.Requested_Date,
            Repeat_Count=sched_data.Repeat_Count,
            Repeat_Note=sched_data.Repeat_Note,
        )
        db.add(sched)

    await db.commit()
    return await get_submission(db, submission.Id)


async def get_submission(db: AsyncSession, submission_id: str) -> Submission | None:
    result = await db.execute(
        select(Submission)
        .where(Submission.Id == submission_id)
        .options(
            selectinload(Submission.Links),
            selectinload(Submission.Schedule_Requests),
            selectinload(Submission.Edit_Versions),
        )
    )
    return result.scalar_one_or_none()


async def list_submissions(
    db: AsyncSession,
    status: str | None = None,
    category: str | None = None,
    target_newsletter: str | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Submission], int]:
    query = select(Submission).options(
        selectinload(Submission.Links),
        selectinload(Submission.Schedule_Requests),
    )
    count_query = select(func.count()).select_from(Submission)

    if status:
        query = query.where(Submission.Status == status)
        count_query = count_query.where(Submission.Status == status)
    if category:
        query = query.where(Submission.Category == category)
        count_query = count_query.where(Submission.Category == category)
    if target_newsletter:
        query = query.where(Submission.Target_Newsletter == target_newsletter)
        count_query = count_query.where(Submission.Target_Newsletter == target_newsletter)
    if search:
        pattern = f"%{search}%"
        search_filter = Submission.Original_Headline.ilike(pattern) | Submission.Original_Body.ilike(pattern) | Submission.Submitter_Name.ilike(pattern)
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    if date_from or date_to:
        date_filter = Submission.Schedule_Requests.any(
            *([SubmissionScheduleRequest.Requested_Date >= date_from] if date_from else []),
            *([SubmissionScheduleRequest.Requested_Date <= date_to] if date_to else []),
        )
        query = query.where(date_filter)
        count_query = count_query.where(date_filter)

    query = query.order_by(Submission.Created_At.desc()).offset(offset).limit(limit)

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
        Submission_Id=submission_id,
        Url=url,
        Anchor_Text=anchor_text,
        Display_Order=display_order,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def delete_link(db: AsyncSession, link_id: str) -> bool:
    result = await db.execute(select(SubmissionLink).where(SubmissionLink.Id == link_id))
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
        Submission_Id=submission_id,
        Requested_Date=requested_date,
        Repeat_Count=repeat_count,
        Repeat_Note=repeat_note,
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)
    return sched


async def delete_schedule_request(db: AsyncSession, schedule_id: str) -> bool:
    result = await db.execute(
        select(SubmissionScheduleRequest).where(SubmissionScheduleRequest.Id == schedule_id)
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
    submission.Has_Image = True
    submission.Image_Path = image_path
    await db.commit()
    return await get_submission(db, submission_id)

"""Submission CRUD and related operations."""

from datetime import date, timedelta

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.submission import Submission, SubmissionLink, SubmissionScheduleRequest
from app.schemas.submission import SubmissionCreate, SubmissionUpdate
from app.services import recurrence_service, schedule_service


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
            Second_Requested_Date=sched_data.Second_Requested_Date,
            Repeat_Count=sched_data.Repeat_Count,
            Repeat_Note=sched_data.Repeat_Note,
            Is_Flexible=sched_data.Is_Flexible,
            Flexible_Deadline=sched_data.Flexible_Deadline,
            Recurrence_Type=sched_data.Recurrence_Type,
            Recurrence_Interval=sched_data.Recurrence_Interval,
            Recurrence_End_Date=sched_data.Recurrence_End_Date,
            Excluded_Dates=[excluded.isoformat() for excluded in sched_data.Excluded_Dates],
        )
        db.add(sched)

    await db.commit()
    return await get_submission(db, submission.Id)


async def get_submission(db: AsyncSession, submission_id: str) -> Submission | None:
    result = await db.execute(
        select(Submission)
        .execution_options(populate_existing=True)
        .where(Submission.Id == submission_id)
        .options(
            selectinload(Submission.Links),
            selectinload(Submission.Schedule_Requests),
            selectinload(Submission.Edit_Versions),
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        return None

    preview_from = date.today()
    preview_to = preview_from + timedelta(days=365)
    await hydrate_submission_occurrences(db, submission, preview_from, preview_to)
    return submission


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
    query = query.order_by(Submission.Created_At.desc())

    if date_from or date_to:
        effective_from = date_from or date.today()
        effective_to = date_to or effective_from
        recurrence_filter = Submission.Schedule_Requests.any(
            sa.and_(
                SubmissionScheduleRequest.Requested_Date <= effective_to,
                sa.or_(
                    SubmissionScheduleRequest.Recurrence_End_Date.is_(None),
                    SubmissionScheduleRequest.Recurrence_End_Date >= effective_from,
                ),
            )
        )
        query = query.where(recurrence_filter)
        candidates = list((await db.execute(query)).scalars().all())
        filtered_items: list[Submission] = []
        for submission in candidates:
            occurrence_dates = await get_submission_occurrence_dates(
                db,
                submission,
                effective_from,
                effective_to,
                newsletter_type=target_newsletter,
            )
            if occurrence_dates:
                await hydrate_submission_occurrences(
                    db,
                    submission,
                    effective_from,
                    effective_to,
                    newsletter_type=target_newsletter,
                )
                filtered_items.append(submission)
        total = len(filtered_items)
        return filtered_items[offset:offset + limit], total

    total = (await db.execute(count_query)).scalar() or 0
    items = list((await db.execute(query.offset(offset).limit(limit))).scalars().all())

    preview_from = date.today()
    preview_to = preview_from + timedelta(days=180)
    for submission in items:
        await hydrate_submission_occurrences(
            db,
            submission,
            preview_from,
            preview_to,
            newsletter_type=target_newsletter,
            max_occurrences=3,
        )

    return items, total


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
    second_requested_date=None,
    repeat_count: int = 1,
    repeat_note: str | None = None,
    is_flexible: bool = False,
    flexible_deadline: str | None = None,
    recurrence_type: str = "once",
    recurrence_interval: int = 1,
    recurrence_end_date: date | None = None,
    excluded_dates: list[date] | None = None,
) -> SubmissionScheduleRequest | None:
    submission = await get_submission(db, submission_id)
    if not submission:
        return None
    sched = SubmissionScheduleRequest(
        Submission_Id=submission_id,
        Requested_Date=requested_date,
        Second_Requested_Date=second_requested_date,
        Repeat_Count=repeat_count,
        Repeat_Note=repeat_note,
        Is_Flexible=is_flexible,
        Flexible_Deadline=flexible_deadline,
        Recurrence_Type=recurrence_type,
        Recurrence_Interval=recurrence_interval,
        Recurrence_End_Date=recurrence_end_date,
        Excluded_Dates=[excluded.isoformat() for excluded in (excluded_dates or [])],
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


async def get_schedule_request(
    db: AsyncSession, submission_id: str, schedule_id: str
) -> SubmissionScheduleRequest | None:
    result = await db.execute(
        select(SubmissionScheduleRequest).where(
            SubmissionScheduleRequest.Id == schedule_id,
            SubmissionScheduleRequest.Submission_Id == submission_id,
        )
    )
    return result.scalar_one_or_none()


async def skip_schedule_occurrence(
    db: AsyncSession,
    submission_id: str,
    schedule_id: str,
    occurrence_date: date,
) -> SubmissionScheduleRequest | None:
    schedule_request = await get_schedule_request(db, submission_id, schedule_id)
    if not schedule_request:
        return None

    excluded_dates = set(schedule_request.Excluded_Dates or [])
    excluded_dates.add(occurrence_date.isoformat())
    schedule_request.Excluded_Dates = sorted(excluded_dates)
    await db.commit()
    await db.refresh(schedule_request)
    return schedule_request


async def reschedule_schedule_occurrence(
    db: AsyncSession,
    submission_id: str,
    schedule_id: str,
    occurrence_date: date,
    new_date: date,
) -> SubmissionScheduleRequest | None:
    schedule_request = await skip_schedule_occurrence(
        db, submission_id, schedule_id, occurrence_date
    )
    if not schedule_request:
        return None

    return await add_schedule_request(
        db,
        submission_id,
        requested_date=new_date,
        repeat_count=1,
        repeat_note=f"Rescheduled from {occurrence_date.isoformat()}",
    )


async def get_submission_occurrence_dates(
    db: AsyncSession,
    submission: Submission,
    from_date: date,
    to_date: date,
    newsletter_type: str | None = None,
) -> list[date]:
    """Return valid occurrence dates for a submission within a range."""
    if from_date > to_date:
        return []

    candidate_dates: set[date] = set()
    for schedule_request in submission.Schedule_Requests:
        candidate_dates.update(
            recurrence_service.expand_schedule_request(
                schedule_request,
                from_date,
                to_date,
            )
        )

    if not candidate_dates:
        return []

    relevant_newsletters = (
        [newsletter_type]
        if newsletter_type
        else (
            ["tdr", "myui"]
            if submission.Target_Newsletter == "both"
            else [submission.Target_Newsletter]
        )
    )
    relevant_newsletters = [nl for nl in relevant_newsletters if nl]

    if not relevant_newsletters:
        return sorted(candidate_dates)

    has_configs = False
    valid_dates: set[date] = set()
    for nl_type in relevant_newsletters:
        configs = await schedule_service.list_configs(db, nl_type)
        if not configs:
            continue
        has_configs = True
        valid_for_newsletter = await schedule_service.get_valid_publication_dates(
            db,
            from_date,
            to_date,
            nl_type,
        )
        valid_dates.update(item["date"] for item in valid_for_newsletter)

    if not has_configs:
        return sorted(candidate_dates)

    return sorted(candidate_dates & valid_dates)


async def hydrate_submission_occurrences(
    db: AsyncSession,
    submission: Submission,
    from_date: date,
    to_date: date,
    newsletter_type: str | None = None,
    max_occurrences: int | None = None,
) -> Submission:
    """Attach occurrence previews to a submission and each schedule request."""
    all_occurrences: list[date] = []
    for schedule_request in submission.Schedule_Requests:
        occurrences = recurrence_service.expand_schedule_request(
            schedule_request,
            from_date,
            to_date,
        )
        valid_occurrences = await get_submission_occurrence_dates_for_request(
            db,
            submission,
            schedule_request,
            occurrences,
            from_date,
            to_date,
            newsletter_type=newsletter_type,
        )
        if max_occurrences is not None:
            valid_occurrences = valid_occurrences[:max_occurrences]
        schedule_request.Occurrence_Dates = [
            occurrence.isoformat() for occurrence in valid_occurrences
        ]
        all_occurrences.extend(valid_occurrences)

    unique_occurrences = sorted(set(all_occurrences))
    if max_occurrences is not None:
        unique_occurrences = unique_occurrences[:max_occurrences]
    submission.Occurrence_Dates = [
        occurrence.isoformat() for occurrence in unique_occurrences
    ]
    return submission


async def get_submission_occurrence_dates_for_request(
    db: AsyncSession,
    submission: Submission,
    schedule_request: SubmissionScheduleRequest,
    candidate_dates: list[date],
    from_date: date,
    to_date: date,
    newsletter_type: str | None = None,
) -> list[date]:
    """Filter occurrence candidates to valid publication dates."""
    if not candidate_dates:
        return []

    relevant_newsletters = (
        [newsletter_type]
        if newsletter_type
        else (
            ["tdr", "myui"]
            if submission.Target_Newsletter == "both"
            else [submission.Target_Newsletter]
        )
    )
    relevant_newsletters = [nl for nl in relevant_newsletters if nl]

    if not relevant_newsletters:
        return sorted(candidate_dates)

    has_configs = False
    valid_dates: set[date] = set()
    for nl_type in relevant_newsletters:
        configs = await schedule_service.list_configs(db, nl_type)
        if not configs:
            continue
        has_configs = True
        valid_for_newsletter = await schedule_service.get_valid_publication_dates(
            db,
            from_date,
            to_date,
            nl_type,
        )
        valid_dates.update(item["date"] for item in valid_for_newsletter)

    if not has_configs:
        return sorted(candidate_dates)

    return sorted(date_value for date_value in candidate_dates if date_value in valid_dates)


# --- Image management ---


async def set_image(db: AsyncSession, submission_id: str, image_path: str) -> Submission | None:
    submission = await get_submission(db, submission_id)
    if not submission:
        return None
    submission.Has_Image = True
    submission.Image_Path = image_path
    await db.commit()
    return await get_submission(db, submission_id)

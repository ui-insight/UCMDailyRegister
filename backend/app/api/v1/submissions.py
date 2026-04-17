import os
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SubmitterRole, get_db, get_submitter_role
from app.config import settings
from app.schemas.submission import (
    LinkCreate,
    LinkResponse,
    ScheduleOccurrenceRescheduleRequest,
    ScheduleOccurrenceSkipRequest,
    ScheduleRequestCreate,
    ScheduleRequestResponse,
    SubmissionCreate,
    SubmissionListResponse,
    SubmissionResponse,
    SubmissionUpdate,
)
from app.services import allowed_value_service, schedule_service, submission_service
from app.services.image_service import ImageProcessingError, save_upload, validate_image

router = APIRouter(prefix="/submissions", tags=["submissions"])


def _to_submission_response(
    submission,
    submission_role: SubmitterRole,
) -> SubmissionResponse:
    response = SubmissionResponse.model_validate(submission)
    if submission_role != "staff":
        response.Assigned_Editor = None
        response.Editorial_Notes = None
    return response


def _to_submission_list_response(
    submissions: list,
    total: int,
    submission_role: SubmitterRole,
) -> SubmissionListResponse:
    return SubmissionListResponse(
        Items=[
            _to_submission_response(submission, submission_role)
            for submission in submissions
        ],
        Total=total,
    )


def _ensure_staff_only_recurrence(
    submission_role: SubmitterRole,
    schedule_request: ScheduleRequestCreate,
) -> None:
    is_recurring = schedule_request.Recurrence_Type != "once"
    if is_recurring and submission_role != "staff":
        raise HTTPException(
            status_code=403,
            detail="Recurring scheduling is available to staff editors only.",
        )


def _ensure_staff_only_editorial_fields(
    submission_role: SubmitterRole,
    data: SubmissionUpdate,
) -> None:
    if (
        submission_role != "staff"
        and (
            "Assigned_Editor" in data.model_fields_set
            or "Editorial_Notes" in data.model_fields_set
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="Only staff editors can update assignment or internal editorial notes.",
        )


async def _validate_schedule_request(
    db: AsyncSession,
    target_newsletter: str,
    schedule_request: ScheduleRequestCreate,
) -> None:
    if target_newsletter == "both":
        # For "both": Requested_Date is for TDR, Second_Requested_Date is for My UI
        if schedule_request.Requested_Date:
            error = await schedule_service.validate_requested_date(
                db, schedule_request.Requested_Date, "tdr"
            )
            if error:
                raise HTTPException(status_code=422, detail=error)
        if schedule_request.Second_Requested_Date:
            error = await schedule_service.validate_requested_date(
                db, schedule_request.Second_Requested_Date, "myui"
            )
            if error:
                raise HTTPException(status_code=422, detail=error)
    elif schedule_request.Requested_Date:
        error = await schedule_service.validate_requested_date(
            db, schedule_request.Requested_Date, target_newsletter
        )
        if error:
            raise HTTPException(status_code=422, detail=error)


@router.post("/", response_model=SubmissionResponse, status_code=201)
async def create_submission(
    data: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    if not await allowed_value_service.is_submission_category_allowed(
        db, data.Category, submission_role
    ):
        raise HTTPException(
            status_code=422,
            detail="Announcement type is not available for this submitter role.",
        )
    for sched in data.Schedule_Requests:
        _ensure_staff_only_recurrence(submission_role, sched)
        await _validate_schedule_request(db, data.Target_Newsletter, sched)
    submission = await submission_service.create_submission(db, data)
    return _to_submission_response(submission, submission_role)


@router.get("/", response_model=SubmissionListResponse)
async def list_submissions(
    status: str | None = None,
    category: str | None = None,
    target_newsletter: str | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    items, total = await submission_service.list_submissions(
        db, status=status, category=category, target_newsletter=target_newsletter,
        search=search, date_from=date_from, date_to=date_to,
        offset=offset, limit=limit,
    )
    return _to_submission_list_response(items, total, submission_role)


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    submission = await submission_service.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _to_submission_response(submission, submission_role)


@router.patch("/{submission_id}", response_model=SubmissionResponse)
async def update_submission(
    submission_id: str,
    data: SubmissionUpdate,
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    if data.Category and not await allowed_value_service.is_submission_category_allowed(
        db, data.Category, submission_role
    ):
        raise HTTPException(
            status_code=422,
            detail="Announcement type is not available for this submitter role.",
        )
    _ensure_staff_only_editorial_fields(submission_role, data)
    submission = await submission_service.update_submission(db, submission_id, data)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _to_submission_response(submission, submission_role)


@router.delete("/{submission_id}", status_code=204)
async def delete_submission(submission_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await submission_service.delete_submission(db, submission_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Submission not found")


# --- Links ---


@router.post("/{submission_id}/links", response_model=LinkResponse, status_code=201)
async def add_link(
    submission_id: str, data: LinkCreate, db: AsyncSession = Depends(get_db)
):
    link = await submission_service.add_link(
        db, submission_id, url=data.Url, anchor_text=data.Anchor_Text, display_order=data.Display_Order,
    )
    if not link:
        raise HTTPException(status_code=404, detail="Submission not found")
    return link


@router.delete("/{submission_id}/links/{link_id}", status_code=204)
async def delete_link(submission_id: str, link_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await submission_service.delete_link(db, link_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Link not found")


# --- Schedule Requests ---


@router.post("/{submission_id}/schedule", response_model=ScheduleRequestResponse, status_code=201)
async def add_schedule_request(
    submission_id: str,
    data: ScheduleRequestCreate,
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    submission = await submission_service.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    _ensure_staff_only_recurrence(submission_role, data)
    await _validate_schedule_request(db, submission.Target_Newsletter, data)

    sched = await submission_service.add_schedule_request(
        db, submission_id,
        requested_date=data.Requested_Date,
        second_requested_date=data.Second_Requested_Date,
        repeat_count=data.Repeat_Count,
        repeat_note=data.Repeat_Note,
        is_flexible=data.Is_Flexible,
        flexible_deadline=data.Flexible_Deadline,
        recurrence_type=data.Recurrence_Type,
        recurrence_interval=data.Recurrence_Interval,
        recurrence_end_date=data.Recurrence_End_Date,
        excluded_dates=data.Excluded_Dates,
    )
    if not sched:
        raise HTTPException(status_code=404, detail="Submission not found")
    refreshed_submission = await submission_service.get_submission(db, submission_id)
    if not refreshed_submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    refreshed_schedule = next(
        (schedule for schedule in refreshed_submission.Schedule_Requests if schedule.Id == sched.Id),
        None,
    )
    if not refreshed_schedule:
        raise HTTPException(status_code=404, detail="Schedule request not found")
    return refreshed_schedule


@router.post(
    "/{submission_id}/schedule/{schedule_id}/skip",
    response_model=ScheduleRequestResponse,
)
async def skip_schedule_occurrence(
    submission_id: str,
    schedule_id: str,
    data: ScheduleOccurrenceSkipRequest,
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    if submission_role != "staff":
        raise HTTPException(
            status_code=403,
            detail="Only staff editors can change scheduled occurrences.",
        )
    sched = await submission_service.skip_schedule_occurrence(
        db, submission_id, schedule_id, data.Occurrence_Date
    )
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule request not found")
    refreshed_submission = await submission_service.get_submission(db, submission_id)
    if not refreshed_submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    refreshed_schedule = next(
        (schedule for schedule in refreshed_submission.Schedule_Requests if schedule.Id == schedule_id),
        None,
    )
    if not refreshed_schedule:
        raise HTTPException(status_code=404, detail="Schedule request not found")
    return refreshed_schedule


@router.post(
    "/{submission_id}/schedule/{schedule_id}/reschedule",
    response_model=ScheduleRequestResponse,
    status_code=201,
)
async def reschedule_schedule_occurrence(
    submission_id: str,
    schedule_id: str,
    data: ScheduleOccurrenceRescheduleRequest,
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    if submission_role != "staff":
        raise HTTPException(
            status_code=403,
            detail="Only staff editors can change scheduled occurrences.",
        )
    submission = await submission_service.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    nl_types = (
        ["tdr", "myui"]
        if submission.Target_Newsletter == "both"
        else [submission.Target_Newsletter]
    )
    for nl_type in nl_types:
        error = await schedule_service.validate_requested_date(db, data.New_Date, nl_type)
        if error:
            raise HTTPException(status_code=422, detail=error)

    sched = await submission_service.reschedule_schedule_occurrence(
        db, submission_id, schedule_id, data.Occurrence_Date, data.New_Date
    )
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule request not found")
    refreshed_submission = await submission_service.get_submission(db, submission_id)
    if not refreshed_submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    refreshed_schedule = next(
        (schedule for schedule in refreshed_submission.Schedule_Requests if schedule.Id == sched.Id),
        None,
    )
    if not refreshed_schedule:
        raise HTTPException(status_code=404, detail="Schedule request not found")
    return refreshed_schedule


@router.delete("/{submission_id}/schedule/{schedule_id}", status_code=204)
async def delete_schedule_request(
    submission_id: str, schedule_id: str, db: AsyncSession = Depends(get_db)
):
    deleted = await submission_service.delete_schedule_request(db, schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule request not found")


# --- Image ---


@router.post("/{submission_id}/image", response_model=SubmissionResponse)
async def upload_image(
    submission_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    content = await file.read()
    error = validate_image(file.filename or "unknown", len(content))
    if error:
        raise HTTPException(status_code=400, detail=error)

    try:
        filename = await save_upload(file.filename or "image.png", content)
    except ImageProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    submission = await submission_service.set_image(db, submission_id, filename)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _to_submission_response(submission, submission_role)


@router.get("/{submission_id}/image")
async def get_image(submission_id: str, db: AsyncSession = Depends(get_db)):
    submission = await submission_service.get_submission(db, submission_id)
    if not submission or not submission.Image_Path:
        raise HTTPException(status_code=404, detail="Image not found")
    filepath = os.path.join(settings.upload_dir, submission.Image_Path)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(filepath)

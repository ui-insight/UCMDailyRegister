import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.schemas.submission import (
    LinkCreate,
    LinkResponse,
    ScheduleRequestCreate,
    ScheduleRequestResponse,
    SubmissionCreate,
    SubmissionListResponse,
    SubmissionResponse,
    SubmissionUpdate,
)
from app.services import submission_service
from app.services.image_service import save_upload, validate_image

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("/", response_model=SubmissionResponse, status_code=201)
async def create_submission(data: SubmissionCreate, db: AsyncSession = Depends(get_db)):
    submission = await submission_service.create_submission(db, data)
    return submission


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
):
    items, total = await submission_service.list_submissions(
        db, status=status, category=category, target_newsletter=target_newsletter,
        search=search, date_from=date_from, date_to=date_to,
        offset=offset, limit=limit,
    )
    return SubmissionListResponse(Items=items, Total=total)


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(submission_id: str, db: AsyncSession = Depends(get_db)):
    submission = await submission_service.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.patch("/{submission_id}", response_model=SubmissionResponse)
async def update_submission(
    submission_id: str, data: SubmissionUpdate, db: AsyncSession = Depends(get_db)
):
    submission = await submission_service.update_submission(db, submission_id, data)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


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
    submission_id: str, data: ScheduleRequestCreate, db: AsyncSession = Depends(get_db)
):
    sched = await submission_service.add_schedule_request(
        db, submission_id,
        requested_date=data.Requested_Date,
        repeat_count=data.Repeat_Count,
        repeat_note=data.Repeat_Note,
    )
    if not sched:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sched


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
):
    content = await file.read()
    error = validate_image(file.filename or "unknown", len(content))
    if error:
        raise HTTPException(status_code=400, detail=error)

    filename = await save_upload(file.filename or "image.png", content)
    submission = await submission_service.set_image(db, submission_id, filename)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.get("/{submission_id}/image")
async def get_image(submission_id: str, db: AsyncSession = Depends(get_db)):
    submission = await submission_service.get_submission(db, submission_id)
    if not submission or not submission.Image_Path:
        raise HTTPException(status_code=404, detail="Image not found")
    filepath = os.path.join(settings.upload_dir, submission.Image_Path)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(filepath)

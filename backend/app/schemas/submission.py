from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


# --- Enums as literals for Pydantic ---

SubmissionCategory = str  # faculty_staff, student, job_opportunity, kudos, etc.
TargetNewsletter = str  # tdr, myui, both
SubmissionStatus = str  # new, ai_edited, in_review, approved, scheduled, published, rejected


# --- Link schemas ---


class LinkCreate(BaseModel):
    url: str
    anchor_text: str | None = None
    display_order: int = 0


class LinkResponse(BaseModel):
    id: str
    url: str
    anchor_text: str | None
    display_order: int

    model_config = {"from_attributes": True}


# --- Schedule request schemas ---


class ScheduleRequestCreate(BaseModel):
    requested_date: date | None = None
    repeat_count: int = 1
    repeat_note: str | None = None


class ScheduleRequestResponse(BaseModel):
    id: str
    requested_date: date | None
    repeat_count: int
    repeat_note: str | None

    model_config = {"from_attributes": True}


# --- Submission schemas ---


class SubmissionCreate(BaseModel):
    category: str = Field(..., pattern=r"^(faculty_staff|student|job_opportunity|kudos|in_memoriam|news_release|calendar_event)$")
    target_newsletter: str = Field(..., pattern=r"^(tdr|myui|both)$")
    original_headline: str = Field(..., min_length=1, max_length=500)
    original_body: str = Field(..., min_length=1)
    submitter_name: str = Field(..., min_length=1, max_length=255)
    submitter_email: str = Field(..., max_length=255)
    submitter_notes: str | None = None
    links: list[LinkCreate] = []
    schedule_requests: list[ScheduleRequestCreate] = []


class SubmissionUpdate(BaseModel):
    status: str | None = Field(None, pattern=r"^(new|ai_edited|in_review|approved|scheduled|published|rejected)$")
    original_headline: str | None = None
    original_body: str | None = None
    submitter_notes: str | None = None
    category: str | None = Field(None, pattern=r"^(faculty_staff|student|job_opportunity|kudos|in_memoriam|news_release|calendar_event)$")
    target_newsletter: str | None = Field(None, pattern=r"^(tdr|myui|both)$")


class SubmissionResponse(BaseModel):
    id: str
    category: str
    target_newsletter: str
    original_headline: str
    original_body: str
    submitter_name: str
    submitter_email: str
    submitter_notes: str | None
    has_image: bool
    image_path: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    links: list[LinkResponse]
    schedule_requests: list[ScheduleRequestResponse]

    model_config = {"from_attributes": True}


class SubmissionListResponse(BaseModel):
    items: list[SubmissionResponse]
    total: int

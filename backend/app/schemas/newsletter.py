"""Pydantic schemas for newsletters, sections, and schedule."""

from datetime import date, datetime, time

from pydantic import BaseModel, Field


# --- Section schemas ---

class SectionResponse(BaseModel):
    id: str
    newsletter_type: str
    name: str
    slug: str
    display_order: int
    description: str | None
    requires_image: bool
    image_dimensions: str | None
    is_active: bool

    model_config = {"from_attributes": True}


# --- Newsletter schemas ---

class NewsletterCreate(BaseModel):
    newsletter_type: str = Field(..., pattern=r"^(tdr|myui)$")
    publish_date: date


class NewsletterResponse(BaseModel):
    id: str
    newsletter_type: str
    publish_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NewsletterItemCreate(BaseModel):
    submission_id: str
    section_id: str
    position: int = 0
    final_headline: str = Field(..., min_length=1)
    final_body: str = Field(..., min_length=1)
    run_number: int = 1


class NewsletterItemUpdate(BaseModel):
    section_id: str | None = None
    position: int | None = None
    final_headline: str | None = None
    final_body: str | None = None
    run_number: int | None = None


class NewsletterItemResponse(BaseModel):
    id: str
    newsletter_id: str
    submission_id: str
    section_id: str
    position: int
    final_headline: str
    final_body: str
    run_number: int

    model_config = {"from_attributes": True}


class NewsletterDetailResponse(BaseModel):
    id: str
    newsletter_type: str
    publish_date: date
    status: str
    created_at: datetime
    updated_at: datetime
    items: list[NewsletterItemResponse]

    model_config = {"from_attributes": True}


# --- Schedule config schemas ---

class ScheduleConfigResponse(BaseModel):
    id: str
    newsletter_type: str
    mode: str
    submission_deadline_description: str
    deadline_day_of_week: int | None
    deadline_time: time
    publish_day_of_week: int | None
    is_daily: bool
    active_start_month: int | None
    active_end_month: int | None

    model_config = {"from_attributes": True}


# --- Assembly request ---

class AssembleRequest(BaseModel):
    """Request to auto-populate a newsletter from approved submissions."""
    newsletter_type: str = Field(..., pattern=r"^(tdr|myui)$")
    publish_date: date

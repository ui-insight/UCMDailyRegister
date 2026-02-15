"""Pydantic schemas for newsletters, sections, and schedule."""

from datetime import date, datetime, time

from pydantic import BaseModel, Field


# --- Section schemas ---

class SectionResponse(BaseModel):
    Id: str
    Newsletter_Type: str
    Name: str
    Slug: str
    Display_Order: int
    Description: str | None
    Requires_Image: bool
    Image_Dimensions: str | None
    Is_Active: bool

    model_config = {"from_attributes": True}


# --- Newsletter schemas ---

class NewsletterCreate(BaseModel):
    Newsletter_Type: str = Field(..., pattern=r"^(tdr|myui)$")
    Publish_Date: date


class NewsletterResponse(BaseModel):
    Id: str
    Newsletter_Type: str
    Publish_Date: date
    Status: str
    Created_At: datetime
    Updated_At: datetime

    model_config = {"from_attributes": True}


class NewsletterItemCreate(BaseModel):
    Submission_Id: str
    Section_Id: str
    Position: int = 0
    Final_Headline: str = Field(..., min_length=1)
    Final_Body: str = Field(..., min_length=1)
    Run_Number: int = 1


class NewsletterItemUpdate(BaseModel):
    Section_Id: str | None = None
    Position: int | None = None
    Final_Headline: str | None = None
    Final_Body: str | None = None
    Run_Number: int | None = None


class NewsletterItemResponse(BaseModel):
    Id: str
    Newsletter_Id: str
    Submission_Id: str
    Section_Id: str
    Position: int
    Final_Headline: str
    Final_Body: str
    Run_Number: int

    model_config = {"from_attributes": True}


class NewsletterDetailResponse(BaseModel):
    Id: str
    Newsletter_Type: str
    Publish_Date: date
    Status: str
    Created_At: datetime
    Updated_At: datetime
    Items: list[NewsletterItemResponse]

    model_config = {"from_attributes": True}


# --- Schedule config schemas ---

class ScheduleConfigResponse(BaseModel):
    Id: str
    Newsletter_Type: str
    Mode: str
    Submission_Deadline_Description: str
    Deadline_Day_Of_Week: int | None
    Deadline_Time: time
    Publish_Day_Of_Week: int | None
    Is_Daily: bool
    Active_Start_Month: int | None
    Active_End_Month: int | None

    model_config = {"from_attributes": True}


# --- Assembly request ---

class AssembleRequest(BaseModel):
    """Request to auto-populate a newsletter from approved submissions."""
    Newsletter_Type: str = Field(..., pattern=r"^(tdr|myui)$")
    Publish_Date: date

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


# --- Link schemas ---


class LinkCreate(BaseModel):
    Url: str
    Anchor_Text: str | None = None
    Display_Order: int = 0


class LinkResponse(BaseModel):
    Id: str
    Url: str
    Anchor_Text: str | None
    Display_Order: int

    model_config = {"from_attributes": True}


# --- Schedule request schemas ---


class ScheduleRequestCreate(BaseModel):
    Requested_Date: date
    Second_Requested_Date: date | None = None
    Repeat_Count: int = Field(1, ge=1, le=2)
    Repeat_Note: str | None = None
    Is_Flexible: bool = False
    Flexible_Deadline: str | None = None
    Recurrence_Type: str = Field(
        "once",
        pattern=r"^(once|weekly|monthly_date|monthly_nth_weekday)$",
    )
    Recurrence_Interval: int = Field(1, ge=1, le=12)
    Recurrence_End_Date: date | None = None
    Excluded_Dates: list[date] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_recurrence_range(self) -> "ScheduleRequestCreate":
        if self.Recurrence_End_Date and self.Recurrence_End_Date < self.Requested_Date:
            raise ValueError("Recurrence_End_Date cannot be before Requested_Date")
        return self


class ScheduleRequestResponse(BaseModel):
    Id: str
    Requested_Date: date | None
    Second_Requested_Date: date | None = None
    Repeat_Count: int
    Repeat_Note: str | None
    Is_Flexible: bool
    Flexible_Deadline: str | None
    Recurrence_Type: str
    Recurrence_Interval: int
    Recurrence_End_Date: date | None
    Excluded_Dates: list[date] = Field(default_factory=list)
    Occurrence_Dates: list[date] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ScheduleOccurrenceSkipRequest(BaseModel):
    Occurrence_Date: date


class ScheduleOccurrenceRescheduleRequest(BaseModel):
    Occurrence_Date: date
    New_Date: date


# --- Submission schemas ---


class SubmissionCreate(BaseModel):
    Category: str = Field(..., min_length=1, max_length=100)
    Target_Newsletter: str = Field(..., pattern=r"^(tdr|myui|both|none)$")
    Original_Headline: str = Field(..., min_length=1, max_length=500)
    Original_Body: str = Field(..., min_length=1)
    Submitter_Name: str = Field(..., min_length=1, max_length=255)
    Submitter_Email: str = Field(..., max_length=255)
    Submitter_Notes: str | None = None
    Survey_End_Date: date | None = None
    Show_In_SLC_Calendar: bool = False
    Event_Classification: str | None = Field(None, pattern=r"^(strategic|signature)$")
    Links: list[LinkCreate] = []
    Schedule_Requests: list[ScheduleRequestCreate] = Field(..., min_length=1)


class SubmissionUpdate(BaseModel):
    Status: str | None = Field(None, pattern=r"^(new|ai_edited|in_review|approved|scheduled|published|rejected|pending_info)$")
    Original_Headline: str | None = None
    Original_Body: str | None = None
    Submitter_Notes: str | None = None
    Survey_End_Date: date | None = None
    Assigned_Editor: str | None = Field(None, max_length=255)
    Editorial_Notes: str | None = None
    Category: str | None = Field(None, min_length=1, max_length=100)
    Target_Newsletter: str | None = Field(None, pattern=r"^(tdr|myui|both|none)$")
    Show_In_SLC_Calendar: bool | None = None
    Event_Classification: str | None = Field(None, pattern=r"^(strategic|signature)$")


class SubmissionResponse(BaseModel):
    Id: str
    Category: str
    Target_Newsletter: str
    Original_Headline: str
    Original_Body: str
    Submitter_Name: str
    Submitter_Email: str
    Submitter_Notes: str | None
    Assigned_Editor: str | None
    Editorial_Notes: str | None
    Survey_End_Date: date | None
    Has_Image: bool
    Image_Path: str | None
    Status: str
    Show_In_SLC_Calendar: bool = False
    Event_Classification: str | None = None
    Created_At: datetime
    Updated_At: datetime
    Links: list[LinkResponse]
    Schedule_Requests: list[ScheduleRequestResponse]
    Occurrence_Dates: list[date] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SubmissionListResponse(BaseModel):
    Items: list[SubmissionResponse]
    Total: int

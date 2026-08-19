import re
from datetime import date, datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator


# --- Link schemas ---

EMAIL_ADDRESS_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


class LinkCreate(BaseModel):
    Url: str = Field(..., min_length=1, max_length=2048)
    Anchor_Text: str | None = Field(None, max_length=500)
    Display_Order: int = 0

    @field_validator("Url", mode="before")
    @classmethod
    def validate_and_normalize_url(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Link destination must be a URL or email address")

        normalized = value.strip()
        if EMAIL_ADDRESS_PATTERN.fullmatch(normalized):
            return f"mailto:{normalized}"

        parsed = urlsplit(normalized)
        if parsed.scheme == "https" and parsed.netloc and not (
            parsed.username or parsed.password
        ):
            return normalized
        if (
            parsed.scheme == "mailto"
            and EMAIL_ADDRESS_PATTERN.fullmatch(parsed.path)
            and not parsed.query
            and not parsed.fragment
        ):
            return f"mailto:{parsed.path}"

        raise ValueError("Link destination must use https:// or be an email address")


class LinkResponse(BaseModel):
    Id: str
    Url: str
    Anchor_Text: str | None
    Display_Order: int

    model_config = {"from_attributes": True}


# --- Schedule request schemas ---


class ScheduleRequestCreate(BaseModel):
    Requested_Date: date | None = None
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
        requested_dates = [
            requested_date
            for requested_date in (self.Requested_Date, self.Second_Requested_Date)
            if requested_date is not None
        ]
        if not requested_dates:
            raise ValueError("At least one requested publication date is required")
        recurrence_anchor = self.Requested_Date or self.Second_Requested_Date
        if (
            self.Recurrence_End_Date
            and recurrence_anchor
            and self.Recurrence_End_Date < recurrence_anchor
        ):
            raise ValueError(
                "Recurrence_End_Date cannot be before the recurrence start date"
            )
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
    Links: list[LinkCreate] = Field(default_factory=list, max_length=3)
    Schedule_Requests: list[ScheduleRequestCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def require_primary_dates_on_submission(self) -> "SubmissionCreate":
        if any(
            schedule_request.Requested_Date is None
            for schedule_request in self.Schedule_Requests
        ):
            raise ValueError("Requested_Date is required when creating a submission")
        return self


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

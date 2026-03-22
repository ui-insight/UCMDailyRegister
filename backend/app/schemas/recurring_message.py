"""Pydantic schemas for recurring editorial content."""

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


RECURRENCE_PATTERN = r"^(once|weekly|monthly_date|monthly_nth_weekday|date_range)$"


class RecurringMessageCreate(BaseModel):
    Newsletter_Type: str = Field(..., pattern=r"^(tdr|myui)$")
    Section_Id: str
    Headline: str = Field(..., min_length=1)
    Body: str = Field(..., min_length=1)
    Start_Date: date
    Recurrence_Type: str = Field("once", pattern=RECURRENCE_PATTERN)
    Recurrence_Interval: int = Field(1, ge=1, le=12)
    End_Date: date | None = None
    Excluded_Dates: list[date] = Field(default_factory=list)
    Is_Active: bool = True

    @model_validator(mode="after")
    def validate_range(self) -> "RecurringMessageCreate":
        if self.End_Date and self.End_Date < self.Start_Date:
            raise ValueError("End_Date cannot be before Start_Date")
        if self.Recurrence_Type == "date_range" and self.End_Date is None:
            raise ValueError("End_Date is required for date_range recurrence")
        return self


class RecurringMessageUpdate(BaseModel):
    Newsletter_Type: str | None = Field(None, pattern=r"^(tdr|myui)$")
    Section_Id: str | None = None
    Headline: str | None = Field(None, min_length=1)
    Body: str | None = Field(None, min_length=1)
    Start_Date: date | None = None
    Recurrence_Type: str | None = Field(None, pattern=RECURRENCE_PATTERN)
    Recurrence_Interval: int | None = Field(None, ge=1, le=12)
    End_Date: date | None = None
    Excluded_Dates: list[date] | None = None
    Is_Active: bool | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "RecurringMessageUpdate":
        if (
            self.Start_Date is not None
            and self.End_Date is not None
            and self.End_Date < self.Start_Date
        ):
            raise ValueError("End_Date cannot be before Start_Date")
        return self


class RecurringMessageResponse(BaseModel):
    Id: str
    Newsletter_Type: str
    Section_Id: str
    Headline: str
    Body: str
    Start_Date: date
    Recurrence_Type: str
    Recurrence_Interval: int
    End_Date: date | None
    Excluded_Dates: list[date] = Field(default_factory=list)
    Is_Active: bool
    Created_At: datetime
    Updated_At: datetime

    model_config = {"from_attributes": True}


class RecurringMessageIssueCandidateResponse(BaseModel):
    Id: str
    Newsletter_Type: str
    Section_Id: str
    Headline: str
    Body: str
    Start_Date: date
    Recurrence_Type: str
    Recurrence_Interval: int
    End_Date: date | None
    Excluded_Dates: list[date] = Field(default_factory=list)
    Is_Active: bool
    Selected: bool
    Skipped: bool

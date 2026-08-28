"""Pydantic schemas for harvested external calendar events."""

from datetime import datetime

from pydantic import BaseModel


class HarvestedEventResponse(BaseModel):
    Id: str
    Source_Type: str
    Source_Id: str
    Series_Id: str | None
    Source_Url: str | None
    Title: str
    Description: str
    Location: str | None
    Event_Start: datetime
    Event_End: datetime | None
    All_Day: bool
    Category_Path: str | None
    Is_Canceled: bool
    SLC_Review_Status: str
    First_Seen_At: datetime
    Last_Seen_At: datetime

    model_config = {"from_attributes": True}


class HarvestedEventListResponse(BaseModel):
    Items: list[HarvestedEventResponse]
    Total: int


class HarvestSummaryResponse(BaseModel):
    Fetched: int
    Created: int
    Updated: int
    Unchanged: int
    Skipped: int

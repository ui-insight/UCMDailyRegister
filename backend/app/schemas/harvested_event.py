"""Pydantic schemas for harvested external calendar events."""

from datetime import datetime

from pydantic import BaseModel, Field


class HarvestedEventUpdate(BaseModel):
    SLC_Review_Status: str = Field(pattern="^(new|flagged|dismissed)$")
    # Only applied when flagging; carried onto the promoted submission.
    Event_Classification: str | None = Field(
        default=None, pattern="^(strategic|signature)$"
    )


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
    # Set when a re-harvest finds the upstream event edited, canceled, or
    # missing from the feed while this event is flagged; cleared on
    # acknowledge or un-flag.
    Upstream_Changed_At: datetime | None
    Promoted_Submission_Id: str | None
    # Mirrors the promoted submission's Event_Classification; None when the
    # event is not flagged. Populated by the route, not the ORM row.
    Promoted_Classification: str | None = None
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

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


class OpsEventUpdate(BaseModel):
    Ops_Review_Status: str = Field(pattern="^(new|reviewed|dismissed)$")


class OpsNeedResponse(BaseModel):
    Need: str
    # None for staff-added needs; confidence only describes AI suggestions.
    Confidence: str | None
    Rationale: str
    Verdict: str
    Source: str

    model_config = {"from_attributes": True}


class OpsNeedCreate(BaseModel):
    # Validated against the Ops_Need_Type vocabulary in the service.
    Need: str = Field(min_length=1, max_length=50)


class OpsNeedVerdictUpdate(BaseModel):
    Verdict: str = Field(pattern="^(suggested|confirmed|rejected)$")


class OpsEventResponse(BaseModel):
    """A harvested event through the Event Services (ops) triage lens.

    Deliberately excludes the SLC lens's fields (review status, promotion,
    upstream-change bookkeeping) — the two workflows share rows but neither
    surface exposes the other's state.
    """

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
    Ops_Review_Status: str
    # AI-suggested operational needs; populated by the route from the
    # assessment rows, not the ORM row itself.
    Needs: list[OpsNeedResponse] = []
    # True once the classifier has assessed this event's current content
    # version; False means an assessment is still owed (or content changed).
    Needs_Assessed: bool = False
    First_Seen_At: datetime
    Last_Seen_At: datetime

    model_config = {"from_attributes": True}


class OpsEventListResponse(BaseModel):
    Items: list[OpsEventResponse]
    Total: int


class HarvestSummaryResponse(BaseModel):
    Fetched: int
    Created: int
    Updated: int
    Unchanged: int
    Skipped: int
    # Existing events newly canceled by this harvest; a subset of Updated.
    Canceled: int

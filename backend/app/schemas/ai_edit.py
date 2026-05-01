"""Pydantic schemas for AI editing API."""

from datetime import datetime

from pydantic import BaseModel, Field


class AIEditRequest(BaseModel):
    """Request to trigger AI editing on a submission."""
    Newsletter_Type: str = Field(..., pattern=r"^(tdr|myui)$")
    Editor_Instructions: str | None = Field(None, max_length=2000)


class AIEditFlag(BaseModel):
    type: str  # error, warning, info
    rule_key: str
    message: str


class AIEditLink(BaseModel):
    url: str
    anchor_text: str


class DiffSegment(BaseModel):
    type: str  # equal, insert, delete, replace
    original: str
    modified: str


class TextDiffResponse(BaseModel):
    segments: list[DiffSegment]
    change_count: int
    similarity_ratio: float


class AIEditResponse(BaseModel):
    """Response from an AI edit operation."""
    Submission_Id: str
    Newsletter_Type: str
    Edited_Headline: str
    Edited_Body: str
    Headline_Case: str
    Changes_Made: list[str]
    Flags: list[AIEditFlag]
    Embedded_Links: list[AIEditLink]
    Confidence: float
    AI_Provider: str
    AI_Model: str
    Headline_Diff: TextDiffResponse
    Body_Diff: TextDiffResponse
    Edit_Version_Id: str


class AIEditTaskResponse(BaseModel):
    """Status response for an asynchronous AI edit task."""
    Task_Id: str
    Submission_Id: str
    Newsletter_Type: str
    Status: str = Field(..., pattern=r"^(queued|running|succeeded|failed)$")
    Result: AIEditResponse | None = None
    Error_Message: str | None = None
    Created_At: datetime
    Updated_At: datetime


class EditVersionResponse(BaseModel):
    Id: str
    Submission_Id: str
    Version_Type: str
    Headline: str
    Body: str
    Headline_Case: str | None
    Flags: list | None
    Changes_Made: list | None
    AI_Provider: str | None
    AI_Model: str | None
    Editor_Instructions: str | None
    Created_At: datetime

    model_config = {"from_attributes": True}


class EditorFinalCreate(BaseModel):
    """Request to save the editor's final version."""
    Headline: str = Field(..., min_length=1)
    Body: str = Field(..., min_length=1)
    Headline_Case: str | None = Field(None, pattern=r"^(sentence_case|title_case)$")


# --- Style rules schemas ---


class StyleRuleResponse(BaseModel):
    Id: str
    Rule_Set: str
    Category: str
    Rule_Key: str
    Rule_Text: str
    Is_Active: bool
    Severity: str

    model_config = {"from_attributes": True}


class StyleRuleCreate(BaseModel):
    Rule_Set: str = Field(..., pattern=r"^(shared|tdr|myui)$")
    Category: str = Field(..., min_length=1, max_length=100)
    Rule_Key: str = Field(..., min_length=1, max_length=100)
    Rule_Text: str = Field(..., min_length=1)
    Severity: str = Field("warning", pattern=r"^(error|warning|info)$")


class StyleRuleUpdate(BaseModel):
    Rule_Text: str | None = None
    Is_Active: bool | None = None
    Severity: str | None = Field(None, pattern=r"^(error|warning|info)$")
    Category: str | None = None

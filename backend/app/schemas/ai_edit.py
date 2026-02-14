"""Pydantic schemas for AI editing API."""

from datetime import datetime

from pydantic import BaseModel, Field


class AIEditRequest(BaseModel):
    """Request to trigger AI editing on a submission."""
    newsletter_type: str = Field(..., pattern=r"^(tdr|myui)$")


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
    submission_id: str
    newsletter_type: str
    edited_headline: str
    edited_body: str
    headline_case: str
    changes_made: list[str]
    flags: list[AIEditFlag]
    embedded_links: list[AIEditLink]
    confidence: float
    ai_provider: str
    ai_model: str
    headline_diff: TextDiffResponse
    body_diff: TextDiffResponse
    edit_version_id: str


class EditVersionResponse(BaseModel):
    id: str
    submission_id: str
    version_type: str
    headline: str
    body: str
    headline_case: str | None
    flags: list | None
    changes_made: list | None
    ai_provider: str | None
    ai_model: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EditorFinalCreate(BaseModel):
    """Request to save the editor's final version."""
    headline: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    headline_case: str | None = Field(None, pattern=r"^(sentence_case|title_case)$")


# --- Style rules schemas ---


class StyleRuleResponse(BaseModel):
    id: str
    rule_set: str
    category: str
    rule_key: str
    rule_text: str
    is_active: bool
    severity: str

    model_config = {"from_attributes": True}


class StyleRuleCreate(BaseModel):
    rule_set: str = Field(..., pattern=r"^(shared|tdr|myui)$")
    category: str = Field(..., min_length=1, max_length=100)
    rule_key: str = Field(..., min_length=1, max_length=100)
    rule_text: str = Field(..., min_length=1)
    severity: str = Field("warning", pattern=r"^(error|warning|info)$")


class StyleRuleUpdate(BaseModel):
    rule_text: str | None = None
    is_active: bool | None = None
    severity: str | None = Field(None, pattern=r"^(error|warning|info)$")
    category: str | None = None

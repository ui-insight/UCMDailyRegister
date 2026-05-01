"""Pydantic schemas for in-app product feedback."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


FEEDBACK_TYPE_PATTERN = r"^(bug|idea)$"
FEEDBACK_STATUS_PATTERN = r"^(new|reviewed|exported|closed)$"
ROLE_PATTERN = r"^(public|staff|slc)$"


class ProductFeedbackCreate(BaseModel):
    Feedback_Type: str = Field(..., pattern=FEEDBACK_TYPE_PATTERN)
    Summary: str = Field(..., min_length=3, max_length=240)
    Details: str = Field(..., min_length=5, max_length=5000)
    Contact_Email: str | None = Field(None, max_length=320)
    Submitter_Role: str = Field(..., pattern=ROLE_PATTERN)
    Route: str = Field(..., min_length=1, max_length=500)
    App_Environment: str = Field("unknown", max_length=100)
    Host: str = Field("unknown", max_length=255)
    Browser: str = Field("unknown", max_length=1000)
    Viewport: str = Field("unknown", max_length=50)

    @field_validator("Contact_Email")
    @classmethod
    def normalize_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if "@" not in cleaned or " " in cleaned:
            raise ValueError("Contact_Email must be a valid email address")
        return cleaned


class ProductFeedbackUpdate(BaseModel):
    Status: str | None = Field(None, pattern=FEEDBACK_STATUS_PATTERN)
    GitHub_URL: str | None = Field(None, max_length=500)

    @field_validator("GitHub_URL")
    @classmethod
    def normalize_github_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ProductFeedbackResponse(BaseModel):
    Id: str
    Feedback_Type: str
    Summary: str
    Details: str
    Contact_Email: str | None
    Submitter_Role: str
    Route: str
    App_Environment: str
    Host: str
    Browser: str
    Viewport: str
    Status: str
    GitHub_URL: str | None
    Created_At: datetime
    Updated_At: datetime

    model_config = {"from_attributes": True}


class ProductFeedbackExportResponse(BaseModel):
    Title: str
    Body: str

"""Submission intake models for the UCM Newsletter Builder.

A Submission represents a single piece of content submitted by a university
department, faculty member, or student organization for inclusion in one or
both UCM newsletters (The Daily Register and My UI). Submissions flow through
a multi-stage pipeline: intake, AI editing, human review, scheduling, and
finally publication in a built newsletter edition.

Each submission captures the original headline and body text, submitter contact
information, an optional image, and metadata about the target newsletter and
content category. Category and status values are governed by the AllowedValue
table rather than hard-coded enums, allowing administrators to extend the
vocabulary without code changes.

SubmissionLink stores hyperlinks that should be embedded in the published item.
SubmissionScheduleRequest lets submitters indicate preferred publication dates
and repeat-run preferences.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.edit_history import EditVersion


class Submission(Base):
    """A content submission destined for one or both UCM newsletters."""

    __tablename__ = "submissions"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Category: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Target_Newsletter: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Original_Headline: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Original_Body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Submitter_Name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    Submitter_Email: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    Submitter_Notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Has_Image: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    Image_Path: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    Survey_End_Date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    Status: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="new")
    Created_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )
    Updated_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()
    )

    Links: Mapped[list["SubmissionLink"]] = relationship(
        back_populates="Submission_Rel", cascade="all, delete-orphan", lazy="selectin"
    )
    Schedule_Requests: Mapped[list["SubmissionScheduleRequest"]] = relationship(
        back_populates="Submission_Rel", cascade="all, delete-orphan", lazy="selectin"
    )
    Edit_Versions: Mapped[list["EditVersion"]] = relationship(
        back_populates="Submission_Rel", cascade="all, delete-orphan", lazy="selectin"
    )


class SubmissionLink(Base):
    """A hyperlink associated with a submission for embedding in the published item."""

    __tablename__ = "submission_links"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Submission_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("submissions.Id"), nullable=False
    )
    Url: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Anchor_Text: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    Display_Order: Mapped[int] = mapped_column(sa.Integer, default=0)

    Submission_Rel: Mapped["Submission"] = relationship(
        back_populates="Links", lazy="selectin"
    )


class SubmissionScheduleRequest(Base):
    """A submitter's preferred publication date and repeat-run preferences."""

    __tablename__ = "submission_schedule_requests"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Submission_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("submissions.Id"), nullable=False
    )
    Requested_Date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    Repeat_Count: Mapped[int] = mapped_column(sa.Integer, default=1)
    Repeat_Note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Is_Flexible: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    Flexible_Deadline: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    Submission_Rel: Mapped["Submission"] = relationship(
        back_populates="Schedule_Requests", lazy="selectin"
    )

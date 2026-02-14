import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.edit_history import EditVersion


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    category: Mapped[str] = mapped_column(
        sa.Enum(
            "faculty_staff",
            "student",
            "job_opportunity",
            "kudos",
            "in_memoriam",
            "news_release",
            "calendar_event",
            name="submission_category",
            native_enum=False,
        ),
        nullable=False,
    )
    target_newsletter: Mapped[str] = mapped_column(
        sa.Enum("tdr", "myui", "both", name="target_newsletter", native_enum=False),
        nullable=False,
    )
    original_headline: Mapped[str] = mapped_column(sa.Text, nullable=False)
    original_body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    submitter_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    submitter_email: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    submitter_notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    has_image: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    image_path: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        sa.Enum(
            "new",
            "ai_edited",
            "in_review",
            "approved",
            "scheduled",
            "published",
            "rejected",
            name="submission_status",
            native_enum=False,
        ),
        nullable=False,
        default="new",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()
    )

    links: Mapped[list["SubmissionLink"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )
    schedule_requests: Mapped[list["SubmissionScheduleRequest"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )
    edit_versions: Mapped[list["EditVersion"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class SubmissionLink(Base):
    __tablename__ = "submission_links"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    submission_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("submissions.id"), nullable=False
    )
    url: Mapped[str] = mapped_column(sa.Text, nullable=False)
    anchor_text: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    display_order: Mapped[int] = mapped_column(sa.Integer, default=0)

    submission: Mapped["Submission"] = relationship(back_populates="links")


class SubmissionScheduleRequest(Base):
    __tablename__ = "submission_schedule_requests"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    submission_id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("submissions.id"), nullable=False
    )
    requested_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    repeat_count: Mapped[int] = mapped_column(sa.Integer, default=1)
    repeat_note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="schedule_requests")

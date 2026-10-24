"""Durable work records for staff-requested AI newsletter edits.

An accepted request is committed before model work starts. Its status and
result remain available after a backend restart. Interrupted requests fail
visibly and can be retried against the same source without duplicate versions.

Instructions and result JSON may contain unpublished copy or personal data.
They share the submission's handling and lifecycle, never enter logs, and are
deleted with the submission. Status is a code-validated workflow discriminator.
Active_Key is unique while work is pending; Run_Id fences a worker attempt so
an interrupted or superseded attempt cannot commit after recovery or retry.
"""

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIEditTask(Base):
    __tablename__ = "ai_edit_tasks"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Submission_Id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("submissions.Id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    Newsletter_Type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Editor_Instructions: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Status: Mapped[str] = mapped_column(sa.String(50), nullable=False, index=True)
    Source_Fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    Active_Key: Mapped[str | None] = mapped_column(sa.String(73), nullable=True, unique=True)
    Run_Id: Mapped[str | None] = mapped_column(sa.String(36), nullable=True)
    Result_JSON: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    Error_Message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    Updated_At: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

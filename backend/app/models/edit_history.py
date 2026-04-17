"""Edit version tracking for the UCM Newsletter Builder.

Every submission passes through an editing pipeline that produces multiple
versions of its headline and body text. The EditVersion model captures each
snapshot: the original text as submitted, one or more AI-suggested revisions,
and the final editor-approved version. This immutable audit trail lets editors
compare drafts, revert to earlier versions, and review what the AI changed.

Version_Type, Headline_Case, and AI_Provider values are governed by the
AllowedValue table rather than hard-coded enums, keeping the vocabulary
extensible without code changes. The Flags and Changes_Made columns store
structured JSON produced by the AI pipeline (e.g., style-rule violations
detected, diff summaries).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.submission import Submission


class EditVersion(Base):
    """An immutable snapshot of a submission's headline and body at one stage of editing."""

    __tablename__ = "edit_versions"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Submission_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("submissions.Id"), nullable=False, index=True
    )
    Version_Type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Headline: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Headline_Case: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    Flags: Mapped[str | None] = mapped_column(sa.JSON, nullable=True)
    Changes_Made: Mapped[str | None] = mapped_column(sa.JSON, nullable=True)
    AI_Provider: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    AI_Model: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    Created_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )

    Submission_Rel: Mapped["Submission"] = relationship(
        back_populates="Edit_Versions", lazy="selectin"
    )

"""Recurring editorial content models for centrally managed newsletter copy.

Recurring messages represent reusable editorial blocks that are authored and
maintained by UCM staff rather than submitted through the public intake form.
They cover content that should surface on a predictable cadence, such as weekly
spirit reminders, monthly process notices, or limited-run campaign messaging.

Unlike one-off submissions, these records are directly assigned to a newsletter
type and section, and they carry recurrence metadata that determines which
issues they should appear in. Issue-level override rows preserve editorial
exceptions, allowing staff to skip a recurring message for a specific
newsletter edition without deleting the underlying library record.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.newsletter import Newsletter
    from app.models.section import NewsletterSection


class RecurringMessage(Base):
    """A centrally managed editorial message that can recur across newsletter issues."""

    __tablename__ = "recurring_messages"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Newsletter_Type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Section_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("newsletter_sections.Id"), nullable=False, index=True
    )
    Headline: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Start_Date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    Recurrence_Type: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="once"
    )
    Recurrence_Interval: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    End_Date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    Excluded_Dates: Mapped[list[str]] = mapped_column(
        sa.JSON, nullable=False, default=list
    )
    Is_Active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    Created_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )
    Updated_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()
    )

    Section_Rel: Mapped["NewsletterSection"] = relationship(lazy="selectin")
    Issue_Overrides: Mapped[list["RecurringMessageIssueOverride"]] = relationship(
        back_populates="Recurring_Message_Rel",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RecurringMessageIssueOverride(Base):
    """An issue-specific exception for a recurring message, such as skipping one run."""

    __tablename__ = "recurring_message_issue_overrides"

    __table_args__ = (
        sa.UniqueConstraint(
            "Recurring_Message_Id",
            "Newsletter_Id",
            name="uq_recurring_message_issue_override",
        ),
    )

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Recurring_Message_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("recurring_messages.Id"), nullable=False, index=True
    )
    Newsletter_Id: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("newsletters.Id"), nullable=False, index=True
    )
    Override_Action: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="skip"
    )
    Created_At: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.now()
    )

    Recurring_Message_Rel: Mapped["RecurringMessage"] = relationship(
        back_populates="Issue_Overrides", lazy="selectin"
    )
    Newsletter_Rel: Mapped["Newsletter"] = relationship(lazy="selectin")

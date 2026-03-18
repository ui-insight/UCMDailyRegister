"""Blackout dates for the UCM Newsletter Builder.

University holidays, closures, and other dates when newsletters should not
be published. A blackout date can apply to a specific newsletter type (e.g.
only TDR) or to all newsletters when Newsletter_Type is null.

The schedule service consults these records when computing valid publication
dates and validating submitter-requested run dates. Editors and admins can
manage blackout dates through the schedule API.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BlackoutDate(Base):
    """A date when one or all newsletters should not be published."""

    __tablename__ = "blackout_dates"
    __table_args__ = (
        sa.UniqueConstraint("Blackout_Date", "Newsletter_Type", name="uq_blackout_date_newsletter"),
    )

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Blackout_Date: Mapped[sa.Date] = mapped_column(sa.Date, nullable=False)
    Newsletter_Type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    Description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Is_Active: Mapped[bool] = mapped_column(sa.Boolean, default=True)

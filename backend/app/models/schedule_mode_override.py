"""Schedule mode overrides for the UCM Newsletter Builder.

The ScheduleConfig model determines which schedule mode (academic_year,
summer, winter_break) is active based on the month of the year. However,
exact transition dates vary year to year, and editors sometimes need to
activate winter break or summer mode on specific dates rather than relying
on the month-based auto-detection.

A ScheduleModeOverride lets an editor manually set the active schedule mode
for a newsletter type during a specific date range. When an override exists
for a given date, it takes priority over the month-based mode detection in
ScheduleConfig.
"""

import uuid
from datetime import date as date_type, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScheduleModeOverride(Base):
    """A manual override for the active schedule mode during a date range."""

    __tablename__ = "schedule_mode_overrides"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Newsletter_Type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Override_Mode: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Start_Date: Mapped[date_type] = mapped_column(sa.Date, nullable=False)
    End_Date: Mapped[date_type] = mapped_column(sa.Date, nullable=False)
    Description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow
    )

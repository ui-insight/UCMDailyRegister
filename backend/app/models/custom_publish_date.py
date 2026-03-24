"""Custom publish dates for winter break and other ad-hoc schedules.

During winter break and other periods where the newsletter schedule is at
the editor's discretion, these manually set dates replace the automatic
cadence from ScheduleConfig. Editors add specific dates they intend to
publish, and the schedule service includes them in valid publication date
calculations.

Each record ties a newsletter type to a specific date. The Description
field captures the editor's reason (e.g. "Last edition before break" or
"First post-holiday edition").
"""

import uuid
from datetime import date as date_type, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomPublishDate(Base):
    """A manually set publication date for ad-hoc schedule periods."""

    __tablename__ = "custom_publish_dates"
    __table_args__ = (
        sa.UniqueConstraint(
            "Newsletter_Type", "Publish_Date", name="uq_custom_publish_date"
        ),
    )

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Newsletter_Type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Publish_Date: Mapped[date_type] = mapped_column(sa.Date, nullable=False)
    Description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Created_At: Mapped[datetime] = mapped_column(
        sa.DateTime, default=datetime.utcnow
    )

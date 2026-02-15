"""Schedule configuration for the UCM Newsletter Builder.

Each newsletter type operates on a distinct publication cadence. The Daily
Register publishes every weekday during the academic year, while My UI
publishes weekly on Mondays. Summer schedules may differ. The ScheduleConfig
model captures these rules so the system can calculate upcoming deadlines,
auto-create draft newsletter shells, and enforce submission windows.

Each config row pairs a Newsletter_Type with a Mode (academic_year or summer)
and records the submission deadline (day-of-week and time), the publish
day-of-week, whether the newsletter runs daily, and the active month range
for that mode.

Newsletter_Type and Mode values are governed by the AllowedValue table rather
than hard-coded enums.
"""

import uuid
from datetime import time

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScheduleConfig(Base):
    """Publication cadence and deadline rules for a newsletter type and schedule mode."""

    __tablename__ = "schedule_configs"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Newsletter_Type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Mode: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    Submission_Deadline_Description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Deadline_Day_Of_Week: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    Deadline_Time: Mapped[time] = mapped_column(sa.Time, nullable=False)
    Publish_Day_Of_Week: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    Is_Daily: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    Active_Start_Month: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    Active_End_Month: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

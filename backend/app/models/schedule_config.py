import uuid
from datetime import time

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScheduleConfig(Base):
    __tablename__ = "schedule_configs"

    id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    newsletter_type: Mapped[str] = mapped_column(
        sa.Enum("tdr", "myui", name="newsletter_type_sched", native_enum=False),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(
        sa.Enum("academic_year", "summer", name="schedule_mode", native_enum=False),
        nullable=False,
    )
    submission_deadline_description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    deadline_day_of_week: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    deadline_time: Mapped[time] = mapped_column(sa.Time, nullable=False)
    publish_day_of_week: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    is_daily: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    active_start_month: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    active_end_month: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

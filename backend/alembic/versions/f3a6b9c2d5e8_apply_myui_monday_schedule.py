"""apply My UI Monday schedule

Revision ID: f3a6b9c2d5e8
Revises: e7a1c3f5b9d2
Create Date: 2026-07-21 11:00:00.000000

Scope the seeded university closure calendar to The Daily Register, keep My UI
on Mondays through holidays and summer, and enforce its academic-year noon
Wednesday submission deadline in existing databases.
"""

from collections.abc import Sequence
from datetime import date, time

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a6b9c2d5e8"
down_revision: str | Sequence[str] | None = "e7a1c3f5b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEEDED_BLACKOUTS = (
    (date(2025, 9, 1), "Labor Day"),
    (date(2025, 11, 24), "Thanksgiving Break"),
    (date(2025, 11, 25), "Thanksgiving Break"),
    (date(2025, 11, 26), "Thanksgiving Break"),
    (date(2025, 11, 27), "Thanksgiving Day"),
    (date(2025, 11, 28), "Thanksgiving Break"),
    (date(2025, 12, 22), "Winter Break"),
    (date(2025, 12, 23), "Winter Break"),
    (date(2025, 12, 24), "Christmas Eve"),
    (date(2025, 12, 25), "Christmas Day"),
    (date(2025, 12, 26), "Winter Break"),
    (date(2025, 12, 29), "Winter Break"),
    (date(2025, 12, 30), "Winter Break"),
    (date(2025, 12, 31), "New Year's Eve"),
    (date(2026, 1, 1), "New Year's Day"),
    (date(2026, 1, 2), "Winter Break"),
    (date(2026, 1, 19), "Martin Luther King Jr. Day"),
    (date(2026, 2, 16), "Presidents' Day"),
    (date(2026, 3, 23), "Spring Break"),
    (date(2026, 3, 24), "Spring Break"),
    (date(2026, 3, 25), "Spring Break"),
    (date(2026, 3, 26), "Spring Break"),
    (date(2026, 3, 27), "Spring Break"),
    (date(2026, 5, 25), "Memorial Day"),
    (date(2026, 7, 3), "Independence Day (observed)"),
    (date(2026, 9, 7), "Labor Day"),
)

MYUI_DEADLINE_DESCRIPTION = (
    "Submissions due by noon Wednesday for Monday's edition"
)


blackout_dates = sa.table(
    "blackout_dates",
    sa.column("Id", sa.String),
    sa.column("Blackout_Date", sa.Date),
    sa.column("Newsletter_Type", sa.String),
    sa.column("Description", sa.Text),
)

schedule_configs = sa.table(
    "schedule_configs",
    sa.column("Newsletter_Type", sa.String),
    sa.column("Mode", sa.String),
    sa.column("Submission_Deadline_Description", sa.Text),
    sa.column("Deadline_Day_Of_Week", sa.Integer),
    sa.column("Deadline_Time", sa.Time),
    sa.column("Publish_Day_Of_Week", sa.Integer),
    sa.column("Is_Daily", sa.Boolean),
    sa.column("Active_Start_Month", sa.Integer),
    sa.column("Active_End_Month", sa.Integer),
    sa.column("Holiday_Shift_Enabled", sa.Boolean),
)


def _move_seeded_blackouts(
    bind: sa.Connection,
    source_type: str | None,
    target_type: str | None,
) -> None:
    """Move only the known seed rows, avoiding newsletter/date conflicts."""
    for blackout_date, description in SEEDED_BLACKOUTS:
        source_id = bind.execute(
            sa.select(blackout_dates.c.Id).where(
                blackout_dates.c.Blackout_Date == blackout_date,
                blackout_dates.c.Newsletter_Type.is_(source_type)
                if source_type is None
                else blackout_dates.c.Newsletter_Type == source_type,
                blackout_dates.c.Description == description,
            )
        ).scalar_one_or_none()
        if source_id is None:
            continue

        target_id = bind.execute(
            sa.select(blackout_dates.c.Id).where(
                blackout_dates.c.Blackout_Date == blackout_date,
                blackout_dates.c.Newsletter_Type.is_(target_type)
                if target_type is None
                else blackout_dates.c.Newsletter_Type == target_type,
            )
        ).scalar_one_or_none()
        if target_id is not None:
            bind.execute(
                sa.delete(blackout_dates).where(blackout_dates.c.Id == source_id)
            )
            continue

        bind.execute(
            sa.update(blackout_dates)
            .where(blackout_dates.c.Id == source_id)
            .values(Newsletter_Type=target_type)
        )


def upgrade() -> None:
    bind = op.get_bind()

    _move_seeded_blackouts(bind, source_type=None, target_type="tdr")

    bind.execute(
        sa.update(schedule_configs)
        .where(
            schedule_configs.c.Newsletter_Type == "myui",
            schedule_configs.c.Mode == "academic_year",
        )
        .values(
            Submission_Deadline_Description=MYUI_DEADLINE_DESCRIPTION,
            Deadline_Day_Of_Week=2,
            Deadline_Time=time(12, 0),
            Publish_Day_Of_Week=0,
            Is_Daily=False,
            Active_Start_Month=8,
            Active_End_Month=5,
            Holiday_Shift_Enabled=False,
        )
    )
    bind.execute(
        sa.update(schedule_configs)
        .where(
            schedule_configs.c.Newsletter_Type == "myui",
            schedule_configs.c.Mode == "summer",
        )
        .values(
            Submission_Deadline_Description=MYUI_DEADLINE_DESCRIPTION,
            Deadline_Day_Of_Week=2,
            Deadline_Time=time(12, 0),
            Publish_Day_Of_Week=0,
            Is_Daily=False,
            Active_Start_Month=6,
            Active_End_Month=7,
            Holiday_Shift_Enabled=False,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()

    _move_seeded_blackouts(bind, source_type="tdr", target_type=None)

    bind.execute(
        sa.update(schedule_configs)
        .where(
            schedule_configs.c.Newsletter_Type == "myui",
            schedule_configs.c.Mode == "academic_year",
        )
        .values(Holiday_Shift_Enabled=True)
    )
    bind.execute(
        sa.update(schedule_configs)
        .where(
            schedule_configs.c.Newsletter_Type == "myui",
            schedule_configs.c.Mode == "summer",
        )
        .values(
            Submission_Deadline_Description="My UI is not published during summer break",
            Deadline_Day_Of_Week=None,
            Deadline_Time=time(12, 0),
            Publish_Day_Of_Week=None,
            Is_Daily=False,
            Active_Start_Month=None,
            Active_End_Month=None,
            Holiday_Shift_Enabled=False,
        )
    )

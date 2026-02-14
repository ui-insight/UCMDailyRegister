"""Schedule service for deadline calculations."""

from datetime import date, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule_config import ScheduleConfig


async def get_active_config(
    db: AsyncSession,
    newsletter_type: str,
    for_date: date | None = None,
) -> ScheduleConfig | None:
    """Get the active schedule config for a newsletter type based on the date.

    Determines if we're in academic year or summer mode based on the month.
    """
    if for_date is None:
        for_date = date.today()

    month = for_date.month

    # Load all configs for this newsletter type
    result = await db.execute(
        sa.select(ScheduleConfig).where(
            ScheduleConfig.newsletter_type == newsletter_type,
        )
    )
    configs = list(result.scalars().all())

    for config in configs:
        if config.active_start_month is None or config.active_end_month is None:
            continue
        start = config.active_start_month
        end = config.active_end_month
        if start <= end:
            if start <= month <= end:
                return config
        else:
            # Wraps around year (e.g., Aug-May = 8-5)
            if month >= start or month <= end:
                return config

    # Fallback: return the first one
    return configs[0] if configs else None


def get_next_publish_date(
    config: ScheduleConfig,
    from_date: date | None = None,
) -> date:
    """Calculate the next publish date based on the schedule config."""
    if from_date is None:
        from_date = date.today()

    if config.is_daily:
        # Daily: next weekday (skip weekends)
        next_day = from_date + timedelta(days=1)
        while next_day.weekday() >= 5:  # Saturday=5, Sunday=6
            next_day += timedelta(days=1)
        return next_day

    if config.publish_day_of_week is not None:
        # Weekly: find next occurrence of publish_day_of_week
        days_ahead = config.publish_day_of_week - from_date.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return from_date + timedelta(days=days_ahead)

    # Fallback: tomorrow
    return from_date + timedelta(days=1)


def get_submission_deadline(
    config: ScheduleConfig,
    publish_date: date,
) -> datetime:
    """Calculate the submission deadline for a given publish date."""
    if config.is_daily:
        # Deadline is the day before at the configured time
        deadline_date = publish_date - timedelta(days=1)
        return datetime.combine(deadline_date, config.deadline_time)

    if config.deadline_day_of_week is not None:
        # Find the deadline day before the publish date
        days_back = publish_date.weekday() - config.deadline_day_of_week
        if days_back <= 0:
            days_back += 7
        deadline_date = publish_date - timedelta(days=days_back)
        return datetime.combine(deadline_date, config.deadline_time)

    # Fallback: day before at the configured time
    return datetime.combine(publish_date - timedelta(days=1), config.deadline_time)


async def list_configs(
    db: AsyncSession,
    newsletter_type: str | None = None,
) -> list[ScheduleConfig]:
    """List all schedule configs, optionally filtered by newsletter type."""
    query = sa.select(ScheduleConfig)
    if newsletter_type:
        query = query.where(ScheduleConfig.newsletter_type == newsletter_type)
    result = await db.execute(query.order_by(ScheduleConfig.newsletter_type, ScheduleConfig.mode))
    return list(result.scalars().all())

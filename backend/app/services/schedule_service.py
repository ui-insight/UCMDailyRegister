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
    """Get the active schedule config for a newsletter type based on the date."""
    if for_date is None:
        for_date = date.today()

    month = for_date.month

    result = await db.execute(
        sa.select(ScheduleConfig).where(
            ScheduleConfig.Newsletter_Type == newsletter_type,
        )
    )
    configs = list(result.scalars().all())

    for config in configs:
        if config.Active_Start_Month is None or config.Active_End_Month is None:
            continue
        start = config.Active_Start_Month
        end = config.Active_End_Month
        if start <= end:
            if start <= month <= end:
                return config
        else:
            if month >= start or month <= end:
                return config

    return configs[0] if configs else None


def get_next_publish_date(
    config: ScheduleConfig,
    from_date: date | None = None,
) -> date:
    """Calculate the next publish date based on the schedule config."""
    if from_date is None:
        from_date = date.today()

    if config.Is_Daily:
        next_day = from_date + timedelta(days=1)
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        return next_day

    if config.Publish_Day_Of_Week is not None:
        days_ahead = config.Publish_Day_Of_Week - from_date.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return from_date + timedelta(days=days_ahead)

    return from_date + timedelta(days=1)


def get_submission_deadline(
    config: ScheduleConfig,
    publish_date: date,
) -> datetime:
    """Calculate the submission deadline for a given publish date."""
    if config.Is_Daily:
        deadline_date = publish_date - timedelta(days=1)
        return datetime.combine(deadline_date, config.Deadline_Time)

    if config.Deadline_Day_Of_Week is not None:
        days_back = publish_date.weekday() - config.Deadline_Day_Of_Week
        if days_back <= 0:
            days_back += 7
        deadline_date = publish_date - timedelta(days=days_back)
        return datetime.combine(deadline_date, config.Deadline_Time)

    return datetime.combine(publish_date - timedelta(days=1), config.Deadline_Time)


async def list_configs(
    db: AsyncSession,
    newsletter_type: str | None = None,
) -> list[ScheduleConfig]:
    """List all schedule configs, optionally filtered by newsletter type."""
    query = sa.select(ScheduleConfig)
    if newsletter_type:
        query = query.where(ScheduleConfig.Newsletter_Type == newsletter_type)
    result = await db.execute(query.order_by(ScheduleConfig.Newsletter_Type, ScheduleConfig.Mode))
    return list(result.scalars().all())

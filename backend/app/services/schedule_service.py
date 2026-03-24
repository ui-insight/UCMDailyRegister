"""Schedule service for deadline calculations and publication date validation."""

from datetime import date, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blackout_date import BlackoutDate
from app.models.custom_publish_date import CustomPublishDate
from app.models.schedule_config import ScheduleConfig
from app.models.schedule_mode_override import ScheduleModeOverride
from app.schemas.newsletter import BlackoutDateCreate


# ---------------------------------------------------------------------------
# Mode override helpers
# ---------------------------------------------------------------------------


async def get_active_override(
    db: AsyncSession,
    newsletter_type: str,
    for_date: date | None = None,
) -> ScheduleModeOverride | None:
    """Return the active mode override for a newsletter type on a given date."""
    if for_date is None:
        for_date = date.today()
    result = await db.execute(
        sa.select(ScheduleModeOverride).where(
            ScheduleModeOverride.Newsletter_Type == newsletter_type,
            ScheduleModeOverride.Start_Date <= for_date,
            ScheduleModeOverride.End_Date >= for_date,
        )
    )
    return result.scalar_one_or_none()


async def list_mode_overrides(
    db: AsyncSession,
    newsletter_type: str | None = None,
) -> list[ScheduleModeOverride]:
    """List all mode overrides, optionally filtered by newsletter type."""
    query = sa.select(ScheduleModeOverride)
    if newsletter_type:
        query = query.where(ScheduleModeOverride.Newsletter_Type == newsletter_type)
    result = await db.execute(query.order_by(ScheduleModeOverride.Start_Date))
    return list(result.scalars().all())


async def create_mode_override(
    db: AsyncSession,
    newsletter_type: str,
    override_mode: str,
    start_date: date,
    end_date: date,
    description: str | None = None,
) -> ScheduleModeOverride:
    """Create a new schedule mode override."""
    record = ScheduleModeOverride(
        Newsletter_Type=newsletter_type,
        Override_Mode=override_mode,
        Start_Date=start_date,
        End_Date=end_date,
        Description=description,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def delete_mode_override(
    db: AsyncSession,
    override_id: str,
) -> bool:
    """Delete a mode override by ID."""
    result = await db.execute(
        sa.select(ScheduleModeOverride).where(ScheduleModeOverride.Id == override_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return False
    await db.delete(record)
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Schedule config resolution
# ---------------------------------------------------------------------------


async def get_active_config(
    db: AsyncSession,
    newsletter_type: str,
    for_date: date | None = None,
) -> ScheduleConfig | None:
    """Get the active schedule config for a newsletter type based on the date.

    Checks for mode overrides first, then falls back to month-based detection.
    """
    if for_date is None:
        for_date = date.today()

    # Check for manual mode override
    override = await get_active_override(db, newsletter_type, for_date)

    result = await db.execute(
        sa.select(ScheduleConfig).where(
            ScheduleConfig.Newsletter_Type == newsletter_type,
        )
    )
    configs = list(result.scalars().all())

    if override:
        for config in configs:
            if config.Mode == override.Override_Mode:
                return config

    month = for_date.month
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


# ---------------------------------------------------------------------------
# Blackout date CRUD
# ---------------------------------------------------------------------------


async def list_blackout_dates(
    db: AsyncSession,
    newsletter_type: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[BlackoutDate]:
    """List active blackout dates, optionally filtered by newsletter type and range."""
    query = sa.select(BlackoutDate).where(BlackoutDate.Is_Active == True)  # noqa: E712
    if newsletter_type:
        query = query.where(
            sa.or_(
                BlackoutDate.Newsletter_Type == newsletter_type,
                BlackoutDate.Newsletter_Type.is_(None),
            )
        )
    if from_date:
        query = query.where(BlackoutDate.Blackout_Date >= from_date)
    if to_date:
        query = query.where(BlackoutDate.Blackout_Date <= to_date)
    result = await db.execute(query.order_by(BlackoutDate.Blackout_Date))
    return list(result.scalars().all())


async def create_blackout_date(
    db: AsyncSession,
    data: BlackoutDateCreate,
) -> BlackoutDate:
    """Create a new blackout date."""
    record = BlackoutDate(
        Blackout_Date=data.Blackout_Date,
        Newsletter_Type=data.Newsletter_Type,
        Description=data.Description,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def delete_blackout_date(
    db: AsyncSession,
    blackout_id: str,
) -> bool:
    """Delete a blackout date by ID. Returns True if found and deleted."""
    result = await db.execute(
        sa.select(BlackoutDate).where(BlackoutDate.Id == blackout_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return False
    await db.delete(record)
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Custom publish dates CRUD
# ---------------------------------------------------------------------------


async def list_custom_publish_dates(
    db: AsyncSession,
    newsletter_type: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[CustomPublishDate]:
    """List custom publish dates, optionally filtered."""
    query = sa.select(CustomPublishDate)
    if newsletter_type:
        query = query.where(CustomPublishDate.Newsletter_Type == newsletter_type)
    if from_date:
        query = query.where(CustomPublishDate.Publish_Date >= from_date)
    if to_date:
        query = query.where(CustomPublishDate.Publish_Date <= to_date)
    result = await db.execute(query.order_by(CustomPublishDate.Publish_Date))
    return list(result.scalars().all())


async def create_custom_publish_date(
    db: AsyncSession,
    newsletter_type: str,
    publish_date: date,
    description: str | None = None,
) -> CustomPublishDate:
    """Create a new custom publish date."""
    record = CustomPublishDate(
        Newsletter_Type=newsletter_type,
        Publish_Date=publish_date,
        Description=description,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def delete_custom_publish_date(
    db: AsyncSession,
    custom_date_id: str,
) -> bool:
    """Delete a custom publish date by ID."""
    result = await db.execute(
        sa.select(CustomPublishDate).where(CustomPublishDate.Id == custom_date_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return False
    await db.delete(record)
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Valid publication dates
# ---------------------------------------------------------------------------


def _is_valid_publish_day(config: ScheduleConfig, d: date) -> bool:
    """Check if a date is a valid publication day for the given config."""
    if config.Is_Daily:
        return d.weekday() < 5  # Mon-Fri
    if config.Publish_Day_Of_Week is not None:
        return d.weekday() == config.Publish_Day_Of_Week
    return False


def _month_in_range(month: int, start: int | None, end: int | None) -> bool:
    """Check if a month falls within a start–end range (wraps around year boundary)."""
    if start is None or end is None:
        return False
    if start <= end:
        return start <= month <= end
    return month >= start or month <= end


def _is_blacked_out(
    d: date,
    nl_type: str,
    blackout_set: dict[str | None, set[date]],
) -> bool:
    """Check if a date is blacked out for a newsletter type."""
    if d in blackout_set.get(None, set()):
        return True
    if d in blackout_set.get(nl_type, set()):
        return True
    return False


async def get_valid_publication_dates(
    db: AsyncSession,
    from_date: date,
    to_date: date,
    newsletter_type: str | None = None,
) -> list[dict]:
    """Return valid publication dates in a range for one or both newsletter types.

    Handles holiday shift logic: if a scheduled publish day is blacked out and the
    config has Holiday_Shift_Enabled, the next weekday is offered as a replacement.

    Also includes custom publish dates for winter_break (or any override) modes.

    Returns a list of dicts: [{"date": date, "newsletters": ["tdr", "myui"]}, ...]
    """
    newsletter_types = [newsletter_type] if newsletter_type else ["tdr", "myui"]

    # Load all configs we might need
    result = await db.execute(sa.select(ScheduleConfig))
    all_configs = list(result.scalars().all())

    # Load mode overrides
    result = await db.execute(sa.select(ScheduleModeOverride))
    all_overrides = list(result.scalars().all())

    # Load blackout dates in range (with some buffer for shift calculation)
    buffer_start = from_date - timedelta(days=7)
    blackouts = await list_blackout_dates(db, from_date=buffer_start, to_date=to_date)
    blackout_set: dict[str | None, set[date]] = {}
    for b in blackouts:
        blackout_set.setdefault(b.Newsletter_Type, set()).add(b.Blackout_Date)

    # Load custom publish dates in range
    custom_dates = await list_custom_publish_dates(db, from_date=from_date, to_date=to_date)
    custom_date_map: dict[str, set[date]] = {}
    for cd in custom_dates:
        custom_date_map.setdefault(cd.Newsletter_Type, set()).add(cd.Publish_Date)

    def _get_override_mode(nl_type: str, d: date) -> str | None:
        for o in all_overrides:
            if o.Newsletter_Type == nl_type and o.Start_Date <= d <= o.End_Date:
                return o.Override_Mode
        return None

    def _get_config(nl_type: str, mode: str) -> ScheduleConfig | None:
        for c in all_configs:
            if c.Newsletter_Type == nl_type and c.Mode == mode:
                return c
        return None

    # Build result
    dates_map: dict[date, list[str]] = {}
    current = from_date
    while current <= to_date:
        for nl_type in newsletter_types:
            # Determine active mode for this date
            override_mode = _get_override_mode(nl_type, current)
            config = None

            if override_mode:
                config = _get_config(nl_type, override_mode)
            else:
                # Month-based detection
                for c in all_configs:
                    if c.Newsletter_Type != nl_type:
                        continue
                    if _month_in_range(current.month, c.Active_Start_Month, c.Active_End_Month):
                        config = c
                        break

            if not config:
                continue

            # Winter break / custom mode: only custom dates are valid
            if config.Mode == "winter_break":
                if current in custom_date_map.get(nl_type, set()):
                    if not _is_blacked_out(current, nl_type, blackout_set):
                        dates_map.setdefault(current, []).append(nl_type)
                continue

            if not _is_valid_publish_day(config, current):
                continue

            if _is_blacked_out(current, nl_type, blackout_set):
                # Holiday shift: if enabled, offer next weekday
                if config.Holiday_Shift_Enabled:
                    shifted = current + timedelta(days=1)
                    while shifted.weekday() >= 5:
                        shifted += timedelta(days=1)
                    if (
                        shifted <= to_date
                        and not _is_blacked_out(shifted, nl_type, blackout_set)
                        and nl_type not in dates_map.get(shifted, [])
                    ):
                        dates_map.setdefault(shifted, []).append(nl_type)
                continue

            dates_map.setdefault(current, []).append(nl_type)

        current += timedelta(days=1)

    return [{"date": d, "newsletters": nls} for d, nls in sorted(dates_map.items())]


async def validate_requested_date(
    db: AsyncSession,
    requested_date: date,
    newsletter_type: str,
) -> str | None:
    """Validate a submitter's requested publication date.

    Returns an error message string if the date is invalid, or None if valid.
    If no schedule configs exist, validation is skipped (graceful degradation).
    """
    # If no schedule configs exist, skip validation (e.g., test environments)
    all_configs = await list_configs(db, newsletter_type)
    if not all_configs:
        return None

    valid_dates = await get_valid_publication_dates(
        db, requested_date, requested_date, newsletter_type
    )
    if valid_dates:
        return None

    # Determine why it's invalid for a helpful error message
    config = await get_active_config(db, newsletter_type, requested_date)
    if not config:
        return f"No active publication schedule for {newsletter_type} on {requested_date}"

    # Check blackout
    blackouts = await list_blackout_dates(
        db, newsletter_type=newsletter_type,
        from_date=requested_date, to_date=requested_date,
    )
    if blackouts:
        desc = blackouts[0].Description or "university closure"
        return f"{requested_date} is a blackout date ({desc})"

    if requested_date.weekday() >= 5:
        return f"{requested_date} falls on a weekend"

    if config.Mode == "winter_break":
        return f"{requested_date} is not a scheduled custom publish date during winter break"

    if config.Publish_Day_Of_Week is not None and requested_date.weekday() != config.Publish_Day_Of_Week:
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return f"{newsletter_type.upper()} publishes on {day_names[config.Publish_Day_Of_Week]}s only"

    return f"{requested_date} is not a valid publication date for {newsletter_type}"

"""Helpers for expanding recurring schedules into concrete issue dates."""

from __future__ import annotations

from datetime import date, timedelta

from app.models.submission import SubmissionScheduleRequest


def expand_schedule_request(
    schedule_request: SubmissionScheduleRequest,
    from_date: date,
    to_date: date,
) -> list[date]:
    """Return occurrence dates for a schedule request within a range."""
    if schedule_request.Requested_Date is None:
        return []
    return expand_recurrence(
        anchor=schedule_request.Requested_Date,
        recurrence_type=schedule_request.Recurrence_Type or "once",
        interval=max(schedule_request.Recurrence_Interval or 1, 1),
        from_date=from_date,
        to_date=to_date,
        until=schedule_request.Recurrence_End_Date,
        excluded_dates=schedule_request.Excluded_Dates or [],
    )


def expand_recurrence(
    *,
    anchor: date,
    recurrence_type: str,
    interval: int,
    from_date: date,
    to_date: date,
    until: date | None = None,
    excluded_dates: list[str] | None = None,
) -> list[date]:
    """Return occurrence dates for a recurrence configuration within a range."""
    if from_date > to_date:
        return []

    excluded = {
        excluded_date
        for excluded_date in (excluded_dates or [])
        if isinstance(excluded_date, str)
    }

    if until and until < from_date:
        return []

    upper_bound = min(to_date, until) if until else to_date
    occurrences: list[date] = []

    if recurrence_type == "once":
        if from_date <= anchor <= upper_bound and anchor.isoformat() not in excluded:
            return [anchor]
        return []

    if recurrence_type == "date_range":
        current = max(anchor, from_date)
        while current <= upper_bound:
            if current.isoformat() not in excluded:
                occurrences.append(current)
            current += timedelta(days=1)
        return occurrences

    if recurrence_type == "weekly":
        current = anchor
        while current < from_date:
            current += timedelta(weeks=interval)
        while current <= upper_bound:
            if current.isoformat() not in excluded:
                occurrences.append(current)
            current += timedelta(weeks=interval)
        return occurrences

    if recurrence_type == "monthly_date":
        index = 0
        while True:
            current = _monthly_date_occurrence(anchor, interval, index)
            if current is None or current > upper_bound:
                break
            if current >= from_date and current.isoformat() not in excluded:
                occurrences.append(current)
            index += 1
        return occurrences

    if recurrence_type == "monthly_nth_weekday":
        index = 0
        while True:
            current = _monthly_nth_weekday_occurrence(anchor, interval, index)
            if current is None or current > upper_bound:
                break
            if current >= from_date and current.isoformat() not in excluded:
                occurrences.append(current)
            index += 1
        return occurrences

    return []


def _add_months(year: int, month: int, months_to_add: int) -> tuple[int, int]:
    month_index = (year * 12) + (month - 1) + months_to_add
    return month_index // 12, (month_index % 12) + 1


def _monthly_date_occurrence(anchor: date, interval: int, index: int) -> date | None:
    year, month = _add_months(anchor.year, anchor.month, interval * index)
    try:
        return date(year, month, anchor.day)
    except ValueError:
        return None


def _monthly_nth_weekday_occurrence(anchor: date, interval: int, index: int) -> date | None:
    year, month = _add_months(anchor.year, anchor.month, interval * index)
    first_of_month = date(year, month, 1)
    weekday_offset = (anchor.weekday() - first_of_month.weekday()) % 7
    nth = ((anchor.day - 1) // 7) + 1
    day_number = 1 + weekday_offset + ((nth - 1) * 7)

    try:
        candidate = date(year, month, day_number)
    except ValueError:
        return None

    if candidate.month != month:
        return None
    return candidate

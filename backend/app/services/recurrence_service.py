"""Helpers for expanding recurring schedules into concrete issue dates.

A repeating schedule (weekly or monthly) must say when it stops: either a
Recurrence_End_Date or, for UCM staff, an explicit Repeats_Indefinitely flag
(#538). Requests saved before that rule may have neither; those run only on
their requested date(s) instead of repeating into every future edition (#477).
Staff see a note on the submission and can give it an end date or tick
"Repeat indefinitely".

Indefinite schedules have no built-in horizon here: expansion runs to whatever
range the caller asks for. The practical limits sit with the callers. The
Builder asks for one publish date at a time; the Edit page previews 365 days;
the dashboard list previews 180 days (first three dates); and every date must
also fall inside a configured publication schedule.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.models.submission import SubmissionScheduleRequest

REPEATING_RECURRENCE_TYPES = frozenset({"weekly", "monthly_date", "monthly_nth_weekday"})


def effective_recurrence_type(schedule_request: SubmissionScheduleRequest) -> str:
    """Return the recurrence type to expand.

    A repeating schedule with no end date runs once unless staff marked it
    Repeats_Indefinitely. If a row somehow has both, the end date still
    applies because it is passed to ``expand_recurrence`` as ``until``.
    """
    recurrence_type = schedule_request.Recurrence_Type or "once"
    if (
        recurrence_type in REPEATING_RECURRENCE_TYPES
        and schedule_request.Recurrence_End_Date is None
        and not getattr(schedule_request, "Repeats_Indefinitely", False)
    ):
        return "once"
    return recurrence_type


def expand_schedule_request(
    schedule_request: SubmissionScheduleRequest,
    from_date: date,
    to_date: date,
) -> list[date]:
    """Return occurrence dates for a schedule request within a range."""
    second_date = getattr(schedule_request, "Second_Requested_Date", None)
    recurrence_anchor = schedule_request.Requested_Date or second_date
    if recurrence_anchor is None:
        return []

    occurrences = expand_recurrence(
        anchor=recurrence_anchor,
        recurrence_type=effective_recurrence_type(schedule_request),
        interval=max(schedule_request.Recurrence_Interval or 1, 1),
        from_date=from_date,
        to_date=to_date,
        until=schedule_request.Recurrence_End_Date,
        excluded_dates=schedule_request.Excluded_Dates or [],
    )
    if (
        schedule_request.Requested_Date is not None
        and second_date is not None
        and from_date <= second_date <= to_date
        and second_date.isoformat() not in (schedule_request.Excluded_Dates or [])
        and second_date not in occurrences
    ):
        occurrences.append(second_date)
        occurrences.sort()
    return occurrences


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
    """Return occurrence dates for a recurrence configuration within a range.

    A zero, negative or missing interval is treated as 1 so a bad stored
    value (e.g. a recurring message's Recurrence_Interval) can't loop forever.
    """
    interval = max(interval or 1, 1)
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

    monthly_occurrence = {
        "monthly_date": _monthly_date_occurrence,
        "monthly_nth_weekday": _monthly_nth_weekday_occurrence,
    }.get(recurrence_type)
    if monthly_occurrence is not None:
        # A month without the anchor day (the 31st, or a 5th Friday) is
        # skipped; the series carries on in the next month that has it (#488).
        index = 0
        while True:
            year, month = _add_months(anchor.year, anchor.month, interval * index)
            if date(year, month, 1) > upper_bound:
                break
            current = monthly_occurrence(anchor, interval, index)
            if (
                current is not None
                and from_date <= current <= upper_bound
                and current.isoformat() not in excluded
            ):
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

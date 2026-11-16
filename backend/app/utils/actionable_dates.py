"""Earliest actionable date of a newsletter item, for default Builder order (#388).

An item's actionable date is the earliest event date or deadline it names
that has not passed by the edition's publish date: "Register by Nov. 20 for
the Dec. 3 workshop" is actionable on Nov. 20. Dates come from the copy as
month-and-day mentions ("Nov. 20", "December 3, 2026") plus any structured
deadline the submission carries. Weekday-only and relative mentions
("Tuesday", "next week") are not read.

A range ("Nov. 18-20, 2027", "Nov. 30–Dec. 2") is read as a unit: a
trailing year applies to both ends, and a range already under way on the
publish date is actionable on the publish date itself.

A date written without a year uses the publish year, or the next year when
that would put it more than 60 days in the past, matching the newsletter's
year-boundary handling elsewhere. Dates before the publish date have passed
and are ignored.
"""

import re
from collections.abc import Iterable
from datetime import date, timedelta

from app.utils.style_checks.text import _MONTH_DAY, _MONTH_NAME, _MONTH_NUMBERS, strip_html

_YEAR_ROLLOVER_DAYS = 60

# "Nov. 18-20, 2027", "Nov. 18 – 20", "Nov. 30–Dec. 2, 2026", "Nov. 30 to Dec. 2"
_DATE_RANGE = re.compile(
    rf"\b(?P<month>{_MONTH_NAME})\.?\s+(?P<day>\d{{1,2}})"
    rf"\s*(?:[-–—]|\bto\b|\bthrough\b|\bthru\b)\s*"
    rf"(?:(?P<end_month>{_MONTH_NAME})\.?\s+)?(?P<end_day>\d{{1,2}})\b"
    rf"(?:,\s*(?P<year>\d{{4}}))?",
    re.IGNORECASE,
)


def _month_number(name: str | None) -> int | None:
    return _MONTH_NUMBERS.get(name.lower().rstrip(".")) if name else None


def _resolve(month: int, day: int, explicit_year: str | None, publish_date: date) -> date | None:
    year = int(explicit_year) if explicit_year else publish_date.year
    try:
        resolved = date(year, month, day)
        if not explicit_year and resolved < publish_date - timedelta(days=_YEAR_ROLLOVER_DAYS):
            resolved = date(year + 1, month, day)
    except ValueError:
        return None
    return resolved


def _range_dates(match: re.Match, publish_date: date) -> list[date]:
    """Both ends of a range, plus the publish date when the range is under way."""
    start_month = _month_number(match.group("month"))
    end_month = _month_number(match.group("end_month")) or start_month
    if start_month is None or end_month is None:
        return []
    start_day, end_day = int(match.group("day")), int(match.group("end_day"))
    explicit_year = match.group("year")
    if explicit_year:
        end_year = int(explicit_year)
        start_year = end_year - 1 if end_month < start_month else end_year
        try:
            start, end = date(start_year, start_month, start_day), date(end_year, end_month, end_day)
        except ValueError:
            return []
    else:
        # Anchor on the end, so a range spanning New Year that is under way
        # ("Dec. 30 to Jan. 2" read on Jan. 1) starts in the previous year.
        end = _resolve(end_month, end_day, None, publish_date)
        if end is None:
            return []
        start_year = end.year - 1 if end_month < start_month else end.year
        try:
            start = date(start_year, start_month, start_day)
        except ValueError:
            return []
    if end < start:
        return []
    dates = [start, end]
    if start < publish_date <= end:
        dates.append(publish_date)
    return dates


def dates_in_text(text: str, publish_date: date) -> list[date]:
    """Calendar dates named in ``text``, resolved against ``publish_date``."""
    plain = strip_html(text or "")
    found: list[date] = []
    range_spans: list[tuple[int, int]] = []
    for match in _DATE_RANGE.finditer(plain):
        found.extend(_range_dates(match, publish_date))
        range_spans.append(match.span())
    for match in _MONTH_DAY.finditer(plain):
        if any(lo <= match.start() < hi for lo, hi in range_spans):
            continue
        month = _month_number(match.group("month"))
        if month is None:
            continue
        resolved = _resolve(month, int(match.group("day")), match.group("year"), publish_date)
        if resolved is not None:
            found.append(resolved)
    return found


def earliest_actionable_date(
    texts: Iterable[str],
    publish_date: date,
    known_dates: Iterable[date | None] = (),
) -> date | None:
    """Earliest date on or after ``publish_date`` in the texts or known dates.

    Returns None when the item names no upcoming date.
    """
    candidates = [d for d in known_dates if d is not None]
    for text in texts:
        candidates.extend(dates_in_text(text, publish_date))
    upcoming = [d for d in candidates if d >= publish_date]
    return min(upcoming) if upcoming else None

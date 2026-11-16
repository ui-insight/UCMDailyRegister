"""Earliest actionable date of a newsletter item, for default Builder order (#388).

An item's actionable date is the earliest event date or deadline it names
that has not passed by the edition's publish date: "Register by Nov. 20 for
the Dec. 3 workshop" is actionable on Nov. 20. Dates come from the copy as
month-and-day mentions ("Nov. 20", "December 3, 2026") plus any structured
deadline the submission carries. Weekday-only and relative mentions
("Tuesday", "next week") are not read.

A date written without a year uses the publish year, or the next year when
that would put it more than 60 days in the past, matching the newsletter's
year-boundary handling elsewhere. Dates before the publish date have passed
and are ignored.
"""

from collections.abc import Iterable
from datetime import date, timedelta

from app.utils.style_checks.text import _MONTH_DAY, _MONTH_NUMBERS, strip_html

_YEAR_ROLLOVER_DAYS = 60


def dates_in_text(text: str, publish_date: date) -> list[date]:
    """Calendar dates named in ``text``, resolved against ``publish_date``."""
    found: list[date] = []
    for match in _MONTH_DAY.finditer(strip_html(text or "")):
        month = _MONTH_NUMBERS.get(match.group("month").lower().rstrip("."))
        if month is None:
            continue
        day = int(match.group("day"))
        explicit_year = match.group("year")
        year = int(explicit_year) if explicit_year else publish_date.year
        try:
            resolved = date(year, month, day)
            if not explicit_year and resolved < publish_date - timedelta(
                days=_YEAR_ROLLOVER_DAYS
            ):
                resolved = date(year + 1, month, day)
        except ValueError:
            continue
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

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

Within a day, items sort by start time (#531). A time belongs to a date when
the two sit next to each other in the same sentence ("3-4 p.m. Wednesday,
Nov. 18" or "Nov. 18 at 3 p.m."). A dated item with no time sorts ahead of
timed items that day; noon is 12 p.m. and midnight is the end of the day.
"""

import re
from collections.abc import Iterable
from datetime import date, timedelta

from app.utils.style_checks.text import _MONTH_DAY, _MONTH_NAME, _MONTH_NUMBERS, strip_html

_YEAR_ROLLOVER_DAYS = 60

# Sort position within a day for a date with no time, and for midnight.
UNTIMED = -1
_MIDNIGHT = 24 * 60

# A time and a date pair up when separated by at most this much text with no
# sentence break between them.
_MAX_TIME_GAP = 40
_SENTENCE_BREAK = re.compile(r"[.!?;\n]")

_PERIOD = r"[ap]\.?\s?m\b\.?"
# "3 p.m.", "10:30 a.m.", "3-4 p.m.", "11 a.m.-1 p.m.", "9 a.m. to noon", "noon"
_TIME = re.compile(
    rf"\b(?:(?P<hour>\d{{1,2}})(?::(?P<minute>\d{{2}}))?\s*(?P<period>{_PERIOD})?"
    rf"|(?P<word>noon|midnight))"
    rf"(?:\s*(?:[-–—]|\bto\b|\buntil\b)\s*"
    rf"(?:(?P<end_hour>\d{{1,2}})(?::(?P<end_minute>\d{{2}}))?\s*(?P<end_period>{_PERIOD})"
    rf"|(?P<end_word>noon|midnight)))?",
    re.IGNORECASE,
)


def _clock_minutes(hour: int, minute: int, period: str) -> int | None:
    """Minutes after midnight for a 12-hour time; midnight is the end of the day."""
    if not 1 <= hour <= 12 or minute > 59:
        return None
    is_pm = period.lower().startswith("p")
    if hour == 12:
        return 12 * 60 + minute if is_pm else _MIDNIGHT + minute
    return (hour + 12 if is_pm else hour) * 60 + minute


def _word_minutes(word: str) -> int:
    return 12 * 60 if word.lower() == "noon" else _MIDNIGHT


def _start_minutes(match: re.Match) -> int | None:
    """Start time of a time or time range, or None for a bare number."""
    if match.group("word"):
        return _word_minutes(match.group("word"))
    hour, minute = int(match.group("hour")), int(match.group("minute") or 0)
    if match.group("period"):
        return _clock_minutes(hour, minute, match.group("period"))
    # "3-4 p.m.": the start takes the end's period, unless that would put it
    # after the end ("11-1 p.m." starts at 11 a.m.).
    if match.group("end_word"):
        end = _word_minutes(match.group("end_word"))
        end_period = "p.m." if match.group("end_word").lower() == "noon" else "a.m."
    elif match.group("end_period"):
        end_period = match.group("end_period")
        end = _clock_minutes(int(match.group("end_hour")), int(match.group("end_minute") or 0), end_period)
    else:
        return None
    start = _clock_minutes(hour, minute, end_period)
    if start is None or end is None:
        return None
    if start > end and start >= 12 * 60:
        start -= 12 * 60
    return start


def _times_in_text(plain: str) -> list[tuple[int, int, int]]:
    """(start offset, end offset, start minutes) for each time in ``plain``."""
    found = []
    for match in _TIME.finditer(plain):
        minutes = _start_minutes(match)
        if minutes is not None:
            found.append((match.start(), match.end(), minutes))
    return found


def _joined(gap: str) -> bool:
    return len(gap) <= _MAX_TIME_GAP and not _SENTENCE_BREAK.search(gap)


def _time_for(
    span: tuple[int, int],
    times: list[tuple[int, int, int]],
    date_starts: list[int],
    plain: str,
) -> int:
    """Start time written next to the date at ``span``, preferring one before it.

    A time written just before a date belongs to that date, so it can't also
    be read as following an earlier one ("by Nov. 18 for the 2 p.m. Nov. 18
    session" leaves the first Nov. 18 untimed).
    """
    start, end = span
    before = [t for t in times if t[1] <= start and _joined(plain[t[1]:start])]
    if before:
        return max(before)[2]
    after = [
        t
        for t in times
        if t[0] >= end
        and _joined(plain[end:t[0]])
        and not any(d >= t[1] and _joined(plain[t[1]:d]) for d in date_starts)
    ]
    if after:
        return min(after)[2]
    return UNTIMED

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


def moments_in_text(text: str, publish_date: date) -> list[tuple[date, int]]:
    """(date, start minutes) for each calendar date named in ``text``.

    Minutes are ``UNTIMED`` when no time is written next to the date. A
    range's time applies to every date read from it.
    """
    plain = strip_html(text or "")
    times = _times_in_text(plain)
    date_starts = [m.start() for m in _MONTH_DAY.finditer(plain)]
    found: list[tuple[date, int]] = []
    range_spans: list[tuple[int, int]] = []
    for match in _DATE_RANGE.finditer(plain):
        minutes = _time_for(match.span(), times, date_starts, plain)
        found.extend((d, minutes) for d in _range_dates(match, publish_date))
        range_spans.append(match.span())
    for match in _MONTH_DAY.finditer(plain):
        if any(lo <= match.start() < hi for lo, hi in range_spans):
            continue
        month = _month_number(match.group("month"))
        if month is None:
            continue
        resolved = _resolve(month, int(match.group("day")), match.group("year"), publish_date)
        if resolved is not None:
            found.append((resolved, _time_for(match.span(), times, date_starts, plain)))
    return found


def dates_in_text(text: str, publish_date: date) -> list[date]:
    """Calendar dates named in ``text``, resolved against ``publish_date``."""
    return [d for d, _ in moments_in_text(text, publish_date)]


def earliest_actionable_moment(
    texts: Iterable[str],
    publish_date: date,
    known_dates: Iterable[date | None] = (),
) -> tuple[date, int] | None:
    """Earliest (date, start minutes) on or after ``publish_date``.

    Known dates (structured deadlines) carry no time. Returns None when the
    item names no upcoming date.
    """
    candidates = [(d, UNTIMED) for d in known_dates if d is not None]
    for text in texts:
        candidates.extend(moments_in_text(text, publish_date))
    upcoming = [m for m in candidates if m[0] >= publish_date]
    return min(upcoming) if upcoming else None


def earliest_actionable_date(
    texts: Iterable[str],
    publish_date: date,
    known_dates: Iterable[date | None] = (),
) -> date | None:
    """Earliest date on or after ``publish_date`` in the texts or known dates.

    Returns None when the item names no upcoming date.
    """
    moment = earliest_actionable_moment(texts, publish_date, known_dates)
    return moment[0] if moment else None

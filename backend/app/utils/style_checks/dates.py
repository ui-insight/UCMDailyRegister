"""Dates and times: AP month and time style, weekday/date conflicts and relative dates (#384, #410)."""

import re
from datetime import date, timedelta

from app.utils.style_checks.text import (
    _MONTH_ABBREV,
    _MONTH_DAY,
    _MONTH_NAME,
    _MONTH_NUMBERS,
    _WEEKDAY_NAME,
    strip_html,
)

# Months AP abbreviates when paired with a specific date.
_ABBREVIATABLE_FULL = "January|February|August|September|October|November|December"

_FULL_MONTH_WITH_DATE = re.compile(rf"\b(?:{_ABBREVIATABLE_FULL})\s+\d{{1,2}}(?!\d)")
_ABBREV_WITHOUT_DATE = re.compile(rf"\b(?:{_MONTH_ABBREV})\.(?!\s*\d)")

_BAD_MERIDIEM = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:AM|PM|A\.M\.|P\.M\.|am\b|pm\b)")
_TWELVE_MERIDIEM = re.compile(r"\b12(?::00)?\s*(?:a\.m\.|p\.m\.)", re.IGNORECASE)
_CROSS_PERIOD_HYPHEN_RANGE = re.compile(
    r"\b(?P<start>\d{1,2}(?::\d{2})?\s*(?P<start_period>a\.m\.|p\.m\.))"
    r"\s*[-–—]\s*"
    r"(?P<end>\d{1,2}(?::\d{2})?\s*(?P<end_period>a\.m\.|p\.m\.))",
    re.IGNORECASE,
)
_WEEKDAY_DATE = re.compile(
    rf"\b(?P<weekday>{_WEEKDAY_NAME})"
    rf",?\s+(?P<month>{_MONTH_NAME})"
    rf"\.?\s+(?P<day>\d{{1,2}})(?:,\s*(?P<year>\d{{4}}))?\b",
    re.IGNORECASE,
)
# "Added Thursday to the Oct. 28 date", "Changed Tuesday to Thursday for Oct. 28"
_WEEKDAY_ASSIGNED_TO_DATE = re.compile(
    rf"\b(?P<weekday>{_WEEKDAY_NAME})\s+(?:to|for)\s+(?:the\s+)?"
    rf"(?P<month>{_MONTH_NAME})\.?\s+(?P<day>\d{{1,2}})\b",
    re.IGNORECASE,
)
_RELATIVE_DATE_REFERENCE = re.compile(
    r"\b(?:today|tomorrow|this\s+(?:week|month)|next\s+(?:week|month))\b",
    re.IGNORECASE,
)
_WEEKDAY_PREFIX = re.compile(
    rf"\b(?:{_WEEKDAY_NAME}),?\s*$",
    re.IGNORECASE,
)


def detect_unabbreviated_month_dates(text: str) -> list[str]:
    """Find spelled-out abbreviatable months used with a specific date."""
    return _FULL_MONTH_WITH_DATE.findall(text)


def detect_abbreviated_months_without_date(text: str) -> list[str]:
    """Find abbreviated months that are not followed by a specific date."""
    return _ABBREV_WITHOUT_DATE.findall(text)


def detect_nonstandard_meridiems(text: str) -> list[str]:
    """Find times whose a.m./p.m. marker is not lowercase with periods."""
    return _BAD_MERIDIEM.findall(text)


def detect_twelve_oclock_meridiems(text: str) -> list[str]:
    """Find '12 p.m.'/'12 a.m.', which AP replaces with noon and midnight."""
    return _TWELVE_MERIDIEM.findall(text)


def detect_cross_period_hyphen_ranges(text: str) -> list[str]:
    """Find hyphenated time ranges whose endpoints use different periods."""
    findings: list[str] = []
    for match in _CROSS_PERIOD_HYPHEN_RANGE.finditer(strip_html(text)):
        if match.group("start_period").casefold() == match.group("end_period").casefold():
            continue
        findings.append(match.group())
    return findings


def detect_missing_relative_date_components(
    source_text: str,
    edited_text: str,
) -> list[str]:
    """Find source relative-date + calendar-date pairs not retained together."""
    edited = strip_html(edited_text)
    edited_relative = {
        match.group().casefold()
        for match in _RELATIVE_DATE_REFERENCE.finditer(edited)
    }
    edited_dates = {
        (_MONTH_NUMBERS[match.group("month").lower().rstrip(".")], int(match.group("day")))
        for match in _MONTH_DAY.finditer(edited)
        if match.group("month").lower().rstrip(".") in _MONTH_NUMBERS
    }
    findings: list[str] = []

    for sentence in re.split(
        r"\n+|(?<=[!?])\s+|(?<=\.)\s+(?=[A-Z])",
        strip_html(source_text),
    ):
        relatives = list(_RELATIVE_DATE_REFERENCE.finditer(sentence))
        dates = list(_MONTH_DAY.finditer(sentence))
        if not relatives or not dates:
            continue
        for relative in relatives:
            for date_match in dates:
                month = _MONTH_NUMBERS.get(date_match.group("month").lower().rstrip("."))
                if month is None:
                    continue
                date_key = (month, int(date_match.group("day")))
                if (
                    relative.group().casefold() not in edited_relative
                    or date_key not in edited_dates
                ):
                    finding = f"{relative.group()}, {date_match.group().rstrip('.')}"
                    if finding not in findings:
                        findings.append(finding)

    return findings


def _resolve_calendar_date(
    match: re.Match,
    reference: date,
) -> date | None:
    """Resolve a matched month/day to a date, or None for an impossible date.

    Dates without a year use the reference year unless that date is more than
    60 days in the past, in which case the next calendar year is assumed. This
    mirrors the newsletter's upcoming-event and year-boundary behavior.
    """
    month = _MONTH_NUMBERS[match.group("month").lower().rstrip(".")]
    day = int(match.group("day"))
    explicit_year = match.group("year")
    year = int(explicit_year) if explicit_year else reference.year
    try:
        resolved = date(year, month, day)
        if not explicit_year and resolved < reference - timedelta(days=60):
            resolved = date(year + 1, month, day)
    except ValueError:
        return None
    return resolved


def _weekday_date_matches(text: str):
    """Yield weekday/date matches whose month name is recognized."""
    for match in _WEEKDAY_DATE.finditer(strip_html(text)):
        if match.group("month").lower().rstrip(".") in _MONTH_NUMBERS:
            yield match


def _weekday_date_key(match: re.Match) -> tuple[str, int, int]:
    return (
        match.group("weekday").lower(),
        _MONTH_NUMBERS[match.group("month").lower().rstrip(".")],
        int(match.group("day")),
    )


def detect_weekday_date_mismatches(
    text: str,
    *,
    reference_date: date | None = None,
) -> list[str]:
    """Find weekday/month/day combinations that disagree with the calendar."""
    reference = reference_date or date.today()
    findings: list[str] = []
    for match in _weekday_date_matches(text):
        resolved = _resolve_calendar_date(match, reference)
        if resolved is None or (
            resolved.strftime("%A").lower() != match.group("weekday").lower()
        ):
            findings.append(match.group().rstrip("."))
    return findings


def detect_inserted_weekday_mismatches(
    source_text: str,
    edited_text: str,
    *,
    reference_date: date | None = None,
) -> dict[str, str | None]:
    """Find wrong weekday/date pairs the edit introduced, with the right weekday.

    A pair counts as introduced when the source never pairs that weekday with
    that month and day, so a weekday added to a bare source date, or changed
    from the source weekday, is checked here. Conflicts already present in the
    source are left to the general mismatch check. The value is the calendar
    weekday, or None when the month and day do not exist.
    """
    reference = reference_date or date.today()
    source_pairs = {_weekday_date_key(match) for match in _weekday_date_matches(source_text)}
    findings: dict[str, str | None] = {}
    for match in _weekday_date_matches(edited_text):
        if _weekday_date_key(match) in source_pairs:
            continue
        resolved = _resolve_calendar_date(match, reference)
        weekday = resolved.strftime("%A") if resolved else None
        if weekday is None or weekday.lower() != match.group("weekday").lower():
            findings[match.group().rstrip(".")] = weekday
    return findings


def date_conflict_note(match: re.Match, reference: date) -> str:
    """Describe a weekday/date conflict in UCM's flag wording (#384).

    Example: ``DATE CONFLICT: MARCH 3, 2027, IS A WEDNESDAY, NOT A TUESDAY``.
    """
    month = _MONTH_NUMBERS[match.group("month").lower().rstrip(".")]
    day = int(match.group("day"))
    weekday = match.group("weekday").upper()
    resolved = _resolve_calendar_date(match, reference)
    if resolved is None:
        month_name = date(2000, month, 1).strftime("%B").upper()
        return f"DATE CONFLICT: {month_name} {day} DOES NOT EXIST"
    return (
        f"DATE CONFLICT: {resolved.strftime('%B').upper()} {day}, {resolved.year}, "
        f"IS A {resolved.strftime('%A').upper()}, NOT A {weekday}"
    )


def detect_weekday_date_conflicts(
    text: str,
    *,
    reference_date: date | None = None,
) -> dict[str, str]:
    """Map each mismatched weekday/date pair to its conflict note."""
    reference = reference_date or date.today()
    return {
        match.group().rstrip("."): date_conflict_note(match, reference)
        for match in _weekday_date_matches(text)
        if (resolved := _resolve_calendar_date(match, reference)) is None
        or resolved.strftime("%A").lower() != match.group("weekday").lower()
    }


def detect_changed_source_date_conflicts(
    source_text: str,
    edited_text: str,
    *,
    reference_date: date | None = None,
) -> dict[str, str]:
    """Find source weekday/date conflicts the edit no longer keeps as written.

    UCM keeps both the supplied weekday and the supplied date and flags the
    conflict instead of choosing a correction (#384). A conflicting source
    pair missing from the edit means the AI changed or dropped one of them.
    """
    reference = reference_date or date.today()
    edited_pairs = {_weekday_date_key(match) for match in _weekday_date_matches(edited_text)}
    return {
        match.group().rstrip("."): date_conflict_note(match, reference)
        for match in _weekday_date_matches(source_text)
        if _weekday_date_key(match) not in edited_pairs
        and (
            (resolved := _resolve_calendar_date(match, reference)) is None
            or resolved.strftime("%A").lower() != match.group("weekday").lower()
        )
    }


def detect_headline_date_conflicts(headline: str, body: str) -> list[str]:
    """Find headline dates the body never gives (#384).

    When the headline and body disagree, the body date is kept and the
    headline date is flagged. Only month/day dates are compared, and a body
    without any date is not judged.
    """
    def month_days(text: str) -> dict[tuple[int, int], str]:
        found: dict[tuple[int, int], str] = {}
        for match in _MONTH_DAY.finditer(strip_html(text)):
            month = _MONTH_NUMBERS.get(match.group("month").lower().rstrip("."))
            if month is not None:
                found.setdefault((month, int(match.group("day"))), match.group())
        return found

    body_dates = month_days(body)
    if not body_dates:
        return []
    return [
        written
        for key, written in month_days(headline).items()
        if key not in body_dates
    ]


def change_contradicts_final_dates(change: str, final_text: str) -> bool:
    """Whether a change-log entry gives a date a weekday the final text does not.

    Only weekdays the entry ties to a date are judged: written with it
    ("Thursday, Oct. 28") or assigned to it ("Added Thursday to Oct. 28").
    The entry contradicts the final edit when, for a month and day the final
    text pairs with a weekday, none of the weekdays it ties to that date is
    the final one. A weekday mentioned on its own, such as the one replaced,
    is not judged.
    """
    change_text = strip_html(change)
    claimed_weekdays: dict[tuple[int, int], set[str]] = {}
    for match in _weekday_date_matches(change_text):
        weekday, month, day = _weekday_date_key(match)
        claimed_weekdays.setdefault((month, day), set()).add(weekday)
    for match in _WEEKDAY_ASSIGNED_TO_DATE.finditer(change_text):
        month = _MONTH_NUMBERS.get(match.group("month").lower().rstrip("."))
        if month is not None:
            claimed_weekdays.setdefault((month, int(match.group("day"))), set()).add(
                match.group("weekday").lower()
            )

    final_weekdays: dict[tuple[int, int], set[str]] = {}
    for match in _weekday_date_matches(final_text):
        weekday, month, day = _weekday_date_key(match)
        final_weekdays.setdefault((month, day), set()).add(weekday)

    return any(
        final_weekdays.get(month_day) and not final_weekdays[month_day] & claimed
        for month_day, claimed in claimed_weekdays.items()
    )


def detect_missing_near_term_weekdays(
    text: str,
    *,
    reference_date: date | None = None,
) -> list[str]:
    """Find dates in the next 30 days that are not paired with a weekday.

    The check is intentionally context-agnostic: deadlines, enrollment dates,
    drawings and promotional dates follow the same near-term rule as events.
    Dates without a year use the same year-boundary resolution as the weekday
    consistency check.
    """
    reference = reference_date or date.today()
    findings: list[str] = []
    plain_text = strip_html(text)

    for match in _MONTH_DAY.finditer(plain_text):
        if _WEEKDAY_PREFIX.search(plain_text[:match.start()]):
            continue

        month_key = match.group("month").lower().rstrip(".")
        month = _MONTH_NUMBERS.get(month_key)
        if month is None:
            continue
        day = int(match.group("day"))
        explicit_year = match.group("year")
        year = int(explicit_year) if explicit_year else reference.year
        try:
            candidate_date = date(year, month, day)
        except ValueError:
            continue
        if not explicit_year and candidate_date < reference - timedelta(days=60):
            try:
                candidate_date = date(year + 1, month, day)
            except ValueError:
                continue

        days_ahead = (candidate_date - reference).days
        if 0 <= days_ahead <= 30:
            findings.append(match.group().rstrip("."))

    return findings

"""Deterministic post-edit style checks for AI-edited copy.

The AI editing pipeline injects the active style rules into the system prompt,
but prompt text alone cannot guarantee compliance: Joy's Aug. 10 production
feedback (issues #299 and #300) showed the model violating rules that were
active in the prompt at the time. The detectors here cover the subset of those
rules that can be verified mechanically — AP month abbreviation, a.m./p.m.
formatting, platform names, undefined acronyms, repeated calls to action and
the Jobs single-line contract — so a violation surfaces as a flag on the AI
version regardless of whether the model honored the prompt.

Each detector is a pure function over edited text and returns the offending
fragments. Mapping findings to flags (and gating on whether the corresponding
rule is active) happens in the AIEditor, keeping these functions independent
of the database. Detectors marked heuristic can produce false positives and
should be surfaced as warnings, never errors.
"""

import re
from datetime import date, timedelta

_HTML_TAG = re.compile(r"<[^>]*>")

# Months AP abbreviates when paired with a specific date.
_ABBREVIATABLE_FULL = "January|February|August|September|October|November|December"
_MONTH_ABBREV = "Jan|Feb|Aug|Sept|Oct|Nov|Dec"

_FULL_MONTH_WITH_DATE = re.compile(rf"\b(?:{_ABBREVIATABLE_FULL})\s+\d{{1,2}}(?!\d)")
_ABBREV_WITHOUT_DATE = re.compile(rf"\b(?:{_MONTH_ABBREV})\.(?!\s*\d)")

_BAD_MERIDIEM = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:AM|PM|A\.M\.|P\.M\.|am\b|pm\b)")
_TWELVE_MERIDIEM = re.compile(r"\b12(?::00)?\s*(?:a\.m\.|p\.m\.)", re.IGNORECASE)

_PLATFORM_NAMES = re.compile(r"\b(?:Zoom|Webex|Microsoft Teams|Google Meet|Skype)\b")

_ACRONYM_TOKEN = re.compile(r"\b[A-Z]{2,6}\b")
_ROMAN_NUMERAL = re.compile(r"^[IVXLCDM]+$")
# Acronyms AP or campus usage treats as standing on their own.
_KNOWN_ACRONYMS = {
    "AP", "US", "USA", "TDR", "RSVP", "GPA", "ID", "PDF", "FAQ", "HR", "IT",
    "TV", "AV", "GED", "ADA", "FYI", "AM", "PM",
}

_CTA_PHRASES = ("register", "sign up", "rsvp", "apply", "learn more")

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s])\d{3}[-.\s]\d{4}(?!\d)"
)
_CONTACT_NAME = re.compile(
    r"\b(?i:contact|email|call|reach)\s+(?:the\s+)?"
    r"([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})\b",
)
_ORGANIZATION_SUFFIXES = {
    "Center", "Centre", "Clinic", "College", "Department", "Division", "Ensemble",
    "Entertainment", "Foundation", "Institute", "Office", "Program",
    "School", "Services", "Team", "Unit", "University",
}
_OFFICIAL_NAME = re.compile(
    r"\b[A-Z][A-Za-z'’.-]*"
    r"(?:\s+(?:(?:and|of|for|the)\s+|&\s+)?[A-Z][A-Za-z'’.-]*){1,6}\b"
)
_BRANDED_TOKEN = re.compile(r"\b[A-Z][a-z]+[A-Z][A-Za-z]*\b")
_WEEKDAY_DATE = re.compile(
    r"\b(?P<weekday>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
    r",?\s+(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?\s+(?P<day>\d{1,2})(?:,\s*(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)
_MONTH_DAY = re.compile(
    r"\b(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?\s+(?P<day>\d{1,2})(?:,\s*(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)
_WEEKDAY_PREFIX = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*$",
    re.IGNORECASE,
)
_MONTH_NUMBERS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def strip_html(text: str) -> str:
    """Replace HTML tags with spaces so detectors never match inside markup."""
    return _HTML_TAG.sub(" ", text)


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


def detect_platform_names(text: str) -> list[str]:
    """Heuristic: find virtual-meeting platform names that may need 'online'."""
    return _PLATFORM_NAMES.findall(text)


def detect_undefined_acronyms(body: str) -> list[str]:
    """Heuristic: find acronyms the body never defines as Full Name (ACRONYM).

    Roman numerals (job classifications such as III) and widely recognized
    acronyms are skipped. A token counts as defined when it appears in
    parentheses anywhere in the body, the shape the acronym rule requires.
    """
    tokens = set(_ACRONYM_TOKEN.findall(body))
    return sorted(
        token
        for token in tokens
        if token not in _KNOWN_ACRONYMS
        and not _ROMAN_NUMERAL.fullmatch(token)
        and f"({token})" not in body
    )


def detect_repeated_cta_phrases(text: str) -> list[str]:
    """Heuristic: find call-to-action phrases that appear more than once.

    'Register' is also the newsletter's name, so occurrences inside 'Daily
    Register' are not counted.
    """
    lowered = re.sub(r"daily\s+register", "", text.lower())
    return [
        phrase
        for phrase in _CTA_PHRASES
        if len(re.findall(rf"\b{phrase}\b", lowered)) >= 2
    ]


def _contact_channels(text: str) -> dict[str, str]:
    """Return normalized contact channels while preserving report-friendly text."""
    channels = {match.group().lower(): match.group() for match in _EMAIL.finditer(text)}
    for match in _PHONE.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        channels[digits[-10:]] = match.group()
    return channels


def detect_missing_source_contacts(source_text: str, edited_text: str) -> list[str]:
    """Find source emails or phone numbers removed from the edited copy.

    Raw HTML is intentionally retained so an address preserved only in a
    ``mailto:`` destination still counts as present.
    """
    source = _contact_channels(source_text)
    edited = _contact_channels(edited_text)
    return [display for key, display in source.items() if key not in edited]


def detect_new_contact_channels(source_text: str, edited_text: str) -> list[str]:
    """Find emails or phone numbers introduced by the edited copy."""
    source = _contact_channels(source_text)
    edited = _contact_channels(edited_text)
    return [display for key, display in edited.items() if key not in source]


def detect_new_contact_names(source_text: str, edited_text: str) -> list[str]:
    """Find likely person names introduced by contact instructions.

    This is deliberately narrow: it only examines two-or-more-word title-case
    spans after contact verbs and ignores common organization suffixes. The
    narrow seam catches the production regression without treating ordinary
    rewritten prose as a new identity.
    """
    source_lower = strip_html(source_text).lower()
    findings: list[str] = []
    for match in _CONTACT_NAME.finditer(strip_html(edited_text)):
        candidate = match.group(1).strip()
        if candidate.lower() in source_lower:
            continue
        if any(word in _ORGANIZATION_SUFFIXES for word in candidate.split()):
            continue
        if candidate not in findings:
            findings.append(candidate)
    return findings


def _official_name_candidates(source_text: str) -> list[str]:
    text = strip_html(source_text)
    candidates: list[tuple[int, str]] = []

    for match in _OFFICIAL_NAME.finditer(text):
        candidate = match.group().strip()
        candidate = re.sub(
            r"^(?:Attend|Join|Register|Apply|Audition|Email|Contact|Learn|Visit)"
            r"\s+(?:(?:for|at|with|the)\s+)?",
            "",
            candidate,
        )
        words = candidate.split()
        if words and words[0] == "The":
            candidate = " ".join(words[1:])
            words = words[1:]
        if candidate.startswith("University of Idaho"):
            # The managed U of I abbreviation rule intentionally rewrites this phrase.
            continue
        has_branded_token = any(_BRANDED_TOKEN.fullmatch(word) for word in words)
        has_org_marker = any(word.strip(".,") in _ORGANIZATION_SUFFIXES for word in words)
        has_vandal_brand = any(word.startswith("Vandal") for word in words)
        if has_branded_token or has_org_marker or has_vandal_brand:
            marker_positions = [
                index
                for index, word in enumerate(words)
                if word.strip(".,") in _ORGANIZATION_SUFFIXES
            ]
            if marker_positions:
                candidate = " ".join(words[: marker_positions[-1] + 1])
            elif has_branded_token or has_vandal_brand:
                candidate = " ".join(words[:2])
            candidates.append((match.start(), candidate))

    for match in _BRANDED_TOKEN.finditer(text):
        if not any(match.group() in candidate for _, candidate in candidates):
            candidates.append((match.start(), match.group()))

    ordered: list[str] = []
    for _, candidate in sorted(candidates):
        if candidate not in ordered:
            ordered.append(candidate)
    return ordered


def detect_changed_official_names(source_text: str, edited_text: str) -> list[str]:
    """Find protected official/branded source spans no longer present exactly."""
    edited = strip_html(edited_text)
    return [
        candidate
        for candidate in _official_name_candidates(source_text)
        if candidate not in edited
    ]


def detect_weekday_date_mismatches(
    text: str,
    *,
    reference_date: date | None = None,
) -> list[str]:
    """Find weekday/month/day combinations that disagree with the calendar.

    Dates without a year use the reference year unless that date is more than
    60 days in the past, in which case the next calendar year is assumed. This
    mirrors the newsletter's upcoming-event and year-boundary behavior.
    """
    reference = reference_date or date.today()
    findings: list[str] = []
    for match in _WEEKDAY_DATE.finditer(strip_html(text)):
        month_key = match.group("month").lower().rstrip(".")
        month = _MONTH_NUMBERS.get(month_key)
        if month is None:
            continue
        day = int(match.group("day"))
        explicit_year = match.group("year")
        year = int(explicit_year) if explicit_year else reference.year
        try:
            event_date = date(year, month, day)
        except ValueError:
            findings.append(match.group().rstrip("."))
            continue
        if not explicit_year and event_date < reference - timedelta(days=60):
            try:
                event_date = date(year + 1, month, day)
            except ValueError:
                findings.append(match.group().rstrip("."))
                continue
        if event_date.strftime("%A").lower() != match.group("weekday").lower():
            findings.append(match.group().rstrip("."))
    return findings


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

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

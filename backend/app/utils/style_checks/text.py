"""Shared text helpers: markup stripping, sentences and month/weekday patterns."""

import re

_HTML_TAG = re.compile(r"<[^>]*>")
_MONTH_ABBREV = "Jan|Feb|Aug|Sept|Oct|Nov|Dec"

# Shared alternations for any month or weekday name, full or abbreviated.
_MONTH_NAME = (
    "Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    "June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|"
    "Dec(?:ember)?"
)
_WEEKDAY_NAME = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
_MONTH_DAY = re.compile(
    rf"\b(?P<month>{_MONTH_NAME})"
    rf"\.?\s+(?P<day>\d{{1,2}})(?:,\s*(?P<year>\d{{4}}))?\b",
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


def _first_sentence(text: str) -> str:
    """Return the first visible sentence from edited copy."""
    visible = re.sub(r"\s+", " ", strip_html(text)).strip()
    return re.split(r"(?<=[.!?])\s+", visible, maxsplit=1)[0]


def _leading_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9\u2019']+", text.casefold().replace("\u2018", "'"))


def _normalized_visible_text(text: str) -> str:
    """Collapse visible text for case-insensitive source-fidelity comparisons."""
    return re.sub(r"\s+", " ", strip_html(text)).strip().casefold()

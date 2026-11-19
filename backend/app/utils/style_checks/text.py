"""Shared text helpers: markup stripping, quote marks, sentences and month/weekday patterns."""

import html
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


# Typographic quote marks and apostrophes, each mapped to its straight form.
_STRAIGHT_QUOTES = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u02bc": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
}
_QUOTE_TRANSLATION = str.maketrans(_STRAIGHT_QUOTES)
_ENTITY = re.compile(r"&(?:#\d+|#[xX][0-9a-fA-F]+|[A-Za-z]+);")


def straight_quotes(text: str) -> str:
    """Write every quote mark and apostrophe in its straight form (#512).

    The editor curls quotes in the model's draft (#409) but the source keeps
    whatever the submitter typed, so checks that compare the two as strings
    run both through this first. Entities for quote marks (``&#39;``,
    ``&rsquo;`` and the like) count as the mark they display. Other entities
    and markup are left alone.
    """
    def _quote_entity(match: re.Match[str]) -> str:
        shown = html.unescape(match.group())
        return shown if shown in _STRAIGHT_QUOTES or shown in ("'", '"') else match.group()

    return _ENTITY.sub(_quote_entity, text).translate(_QUOTE_TRANSLATION)


def _first_sentence(text: str) -> str:
    """Return the first visible sentence from edited copy."""
    visible = re.sub(r"\s+", " ", strip_html(text)).strip()
    return re.split(r"(?<=[.!?])\s+", visible, maxsplit=1)[0]


def _leading_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9\u2019']+", text.casefold().replace("\u2018", "'"))


def _normalized_visible_text(text: str) -> str:
    """Collapse visible text for case-insensitive source-fidelity comparisons."""
    return re.sub(r"\s+", " ", strip_html(text)).strip().casefold()


def comparable_words(text: str) -> str:
    """Reduce text to its words for checks that ask whether content was kept.

    Markup, case, punctuation and spacing are dropped and ``&`` reads as
    ``and``, so ``All are welcome.`` and ``all are welcome`` compare equal.
    """
    visible = strip_html(text).replace("&", " and ").casefold()
    return " ".join(re.findall(r"[^\W_]+", visible))


def contains_words(text: str, phrase: str) -> bool:
    """Whether ``phrase`` appears in ``text`` as whole words (see ``comparable_words``)."""
    wanted = comparable_words(phrase)
    return bool(wanted) and f" {wanted} " in f" {comparable_words(text)} "

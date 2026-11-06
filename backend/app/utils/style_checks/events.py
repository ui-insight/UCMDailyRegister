"""Event structure: time, day, date and place order, and event calls to action (#373)."""

import re

from app.utils.style_checks.text import (
    _MONTH_ABBREV,
    _MONTH_DAY,
    _MONTH_NAME,
    _WEEKDAY_NAME,
    strip_html,
)

_TIME_WITH_PERIOD = re.compile(
    r"\b\d{1,2}(?::\d{2})?\s*(?P<period>a\.m\.|p\.m\.)",
    re.IGNORECASE,
)
_PROTECTED_SENTENCE_PERIOD = re.compile(
    rf"\b(?:a\.m|p\.m|{_MONTH_ABBREV})\.",
    re.IGNORECASE,
)
_STANDALONE_EVENT_DETAIL_START = re.compile(
    rf"^(?:"
    rf"\d{{1,2}}(?::\d{{2}})?(?:\s*[-–—]\s*\d{{1,2}}(?::\d{{2}})?)?"
    rf"\s*(?:a\.m\.|p\.m\.)"
    rf"|noon\b|midnight\b"
    rf"|(?:{_WEEKDAY_NAME})\b"
    rf"|(?:{_MONTH_NAME})"
    rf"\.?\s+\d{{1,2}}\b"
    rf")",
    re.IGNORECASE,
)
_COMPLETE_EVENT_DETAIL_VERB = re.compile(
    r"\b(?:is|are|was|were|begins?|starts?|ends?|marks?|offers?|hosts?|"
    r"includes?|takes?|features?|opens?|closes?|will|can|must)\b",
    re.IGNORECASE,
)
_LIVE_READING_EVENT = re.compile(
    r"\b(?:reads?\s+from|reading\s+(?:from|by|with)|"
    r"(?:poetry|book|author|writer)\s+reading)\b",
    re.IGNORECASE,
)
_MISDIRECTED_READING_ACTION = re.compile(
    r"^\s*(?:read|purchase|buy|learn\s+about)\b",
    re.IGNORECASE,
)


def detect_event_detail_order_violations(text: str) -> list[str]:
    """Find event sentences that place a calendar date before the first time."""
    findings: list[str] = []
    for sentence in re.split(r"(?<=[!?])\s+|(?<=\.)\s+(?=[A-Z])", strip_html(text)):
        sentence = sentence.strip()
        if not sentence:
            continue
        date_match = _MONTH_DAY.search(sentence)
        time_match = _TIME_WITH_PERIOD.search(sentence)
        if date_match and time_match and date_match.start() < time_match.start():
            findings.append(sentence)
    return findings


def detect_standalone_event_detail_fragments(text: str) -> list[str]:
    """Find time/date fragments detached from the event's complete sentence."""
    period_placeholder = "\x00"
    protected = _PROTECTED_SENTENCE_PERIOD.sub(
        lambda match: match.group().replace(".", period_placeholder),
        strip_html(text),
    )
    findings: list[str] = []
    for protected_sentence in re.split(r"(?<=[.!?])\s+|\n+", protected):
        sentence = protected_sentence.replace(period_placeholder, ".").strip()
        if not _STANDALONE_EVENT_DETAIL_START.match(sentence):
            continue
        if _COMPLETE_EVENT_DETAIL_VERB.search(sentence):
            continue
        findings.append(sentence)
    return findings


def detect_changed_event_call_to_action(source_body: str, headline: str) -> list[str]:
    """Catch a live author reading rewritten as reading or purchasing the book."""
    if not _LIVE_READING_EVENT.search(strip_html(source_body)):
        return []
    visible_headline = strip_html(headline).strip()
    if not _MISDIRECTED_READING_ACTION.match(visible_headline):
        return []
    return [visible_headline]

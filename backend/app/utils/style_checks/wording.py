"""Wording: headlines, calls to action, platform names, ampersands and review notes (#376)."""

import re

from app.utils.style_checks.text import _first_sentence, _leading_words, strip_html

_PLATFORM_NAMES = re.compile(r"\b(?:Zoom|Webex|Microsoft Teams|Google Meet|Skype)\b")

_CTA_PHRASES = ("register", "sign up", "enroll", "rsvp", "apply", "learn more")

_ANCHOR_ELEMENT = re.compile(r"<a\b[^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)
_GENERIC_DESTINATION_REFERENCE = re.compile(
    r"\b(?:landing\s+page|this\s+page|web\s*page)\b",
    re.IGNORECASE,
)
_INDIRECT_CONTACT_LANGUAGE = re.compile(
    r"\b(?:interested\s+)?(?:participants?|individuals?|people|applicants?)\s+"
    r"should\s+contact\b",
    re.IGNORECASE,
)
_REDUNDANT_PROMOTIONAL_LEAD = re.compile(
    r"^\s*The\s+last\s+week\s+to\b[^.!?]*\bis\s+this\s+week\b",
    re.IGNORECASE,
)


def detect_disallowed_ampersands(text: str) -> list[str]:
    """Find literal ampersands outside the sole editorial exception, Q&A."""
    visible = strip_html(text)
    visible = re.sub(r"\bQ\s*&\s*A\b", "", visible, flags=re.IGNORECASE)
    visible = re.sub(r"&(?:#\d+|#x[0-9a-f]+|[a-z][a-z0-9]+);", "", visible, flags=re.IGNORECASE)
    return [match.group() for match in re.finditer(r"&", visible)]


def detect_platform_names(text: str) -> list[str]:
    """Heuristic: find virtual-meeting platform names that may need 'online'."""
    return _PLATFORM_NAMES.findall(text)


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


# Staff review notes use these openings (#396, #384, #410); ordinary
# bracketed copy such as "[NASA]" is not a note.
_REVIEW_NOTE = re.compile(
    r"\[(?:CONFIRM|DATE CONFLICT|DATE HAS PASSED|DAY OF WEEK NOT VERIFIED|"
    r"NAME VARIES|VERIFY|CHECK|STAFF REVIEW|EDITOR NOTE|TBD)\b[^\]]*\]"
)


def detect_review_notes_in_copy(text: str) -> list[str]:
    """Bracketed staff notes such as [CONFIRM VENUE NAME] left in the copy."""
    return _REVIEW_NOTE.findall(text)


def detect_headline_echoes_lead(headline: str, body: str, words: int = 4) -> bool:
    """True when the headline opens with the same words as the body (#376).

    Compares up to the first four words; a headline of two or three words
    echoes the body when all of them open it.
    """
    head = _leading_words(strip_html(headline).replace("\u2019", "'"))[:words]
    lead = _leading_words(_first_sentence(strip_html(body)).replace("\u2019", "'"))
    return len(head) >= 2 and head == lead[: len(head)]


def detect_redundant_promotional_leads(text: str) -> list[str]:
    """Find narrow, high-confidence passive or circular promotional leads."""
    first_sentence = _first_sentence(text)
    if _REDUNDANT_PROMOTIONAL_LEAD.search(first_sentence):
        return [first_sentence]
    return []


def detect_generic_destination_references(text: str) -> list[str]:
    """Find generic page references that are not themselves descriptive links."""
    without_links = _ANCHOR_ELEMENT.sub(" ", text)
    return [match.group() for match in _GENERIC_DESTINATION_REFERENCE.finditer(without_links)]


def detect_indirect_contact_language(text: str) -> list[str]:
    """Find wordy audience-prefixed contact constructions."""
    return [match.group() for match in _INDIRECT_CONTACT_LANGUAGE.finditer(strip_html(text))]

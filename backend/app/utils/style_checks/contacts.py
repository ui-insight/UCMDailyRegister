"""Contacts and required details: contacts, titles, information options and requirements kept, none invented (#385)."""

import re

from app.utils.style_checks.names import _ORGANIZATION_SUFFIXES
from app.utils.style_checks.text import strip_html

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s])\d{3}[-.\s]\d{4}(?!\d)"
)
_CONTACT_NAME = re.compile(
    r"\b(?i:contact|email|call|reach)\s+(?:the\s+)?"
    r"([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})\b",
)
_PARENTHETICAL_CONTACT_TITLE = re.compile(
    r"\b(?P<name>[A-Z][A-Za-z'’.-]+"
    r"(?:\s+[A-Z][A-Za-z'’.-]+){1,3})\s*"
    r"\((?P<title>[A-Za-z][A-Za-z'’&/.-]*"
    r"(?:\s+[A-Za-z'’&/.-]+){0,8})\)"
)
_COMMA_CONTACT_TITLE = re.compile(
    r"\b(?P<name>[A-Z][A-Za-z'’.-]+"
    r"(?:\s+[A-Z][A-Za-z'’.-]+){1,3})\s*,\s*"
    r"(?P<title>[A-Z][A-Za-z'’/-]*"
    r"(?:\s+(?:&|[A-Z][A-Za-z'’&/-]*)){1,10})"
)
_INFORMATION_OPTION = re.compile(
    r"\b(?:learn\s+more|more\s+information|additional\s+information|"
    r"(?:get|request|find)\s+(?:more|additional)\s+information|"
    r"(?:get|view|see|find)\s+(?:the\s+)?details?|questions?)\b",
    re.IGNORECASE,
)
_REQUIREMENT_MARKER = re.compile(
    r"\b(?:must|required(?:\s+to)?|requires?|eligible|eligibility|certified|"
    r"certification|licensed|may\s+only|cannot|prohibited)\b",
    re.IGNORECASE,
)
_REQUIREMENT_ANCHOR = re.compile(r"\b[A-Z]{2,}\b|\b\d+(?:\.\d+)?\+?")


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


def detect_missing_contact_titles(source_text: str, edited_text: str) -> list[str]:
    """Find parenthetical or comma-style source contact titles missing in edits."""
    source = strip_html(source_text)
    edited = re.sub(r"\s+", " ", strip_html(edited_text)).strip()
    findings: list[str] = []

    matches = [
        *_PARENTHETICAL_CONTACT_TITLE.finditer(source),
        *_COMMA_CONTACT_TITLE.finditer(source),
    ]
    for match in matches:
        nearby_before = source[max(0, match.start() - 80):match.start()]
        nearby_after = source[match.end():match.end() + 160]
        name_with_cue = match.group("name")
        is_contact_context = bool(
            re.search(r"\b(?:contact|email|call|reach)\b", nearby_before, re.IGNORECASE)
            or re.match(r"(?:Contact|Email|Call|Reach)\b", name_with_cue)
            or _EMAIL.search(nearby_after)
            or _PHONE.search(nearby_after)
        )
        if not is_contact_context:
            continue
        name = re.sub(
            r"^(?:Contact|Email|Call|Reach)\s+",
            "",
            name_with_cue,
        ).strip()
        title = match.group("title").strip()
        if title.isupper() and len(title) <= 10:
            # Parenthetical acronyms are definitions, not contact titles.
            continue
        name_pattern = r"\s+".join(re.escape(word) for word in name.split())
        title_pattern = r"\s+".join(re.escape(word) for word in title.split())
        if re.search(
            rf"\b{name_pattern}\b[^.!?]{{0,120}}\b{title_pattern}\b",
            edited,
            re.IGNORECASE,
        ):
            continue
        display = f"{name}, {title.lower()}"
        if display not in findings:
            findings.append(display)

    return findings


def detect_missing_information_options(source_text: str, edited_text: str) -> list[str]:
    """Find an explicit information-seeking option removed from edited copy."""
    source_matches = [
        re.sub(r"\s+", " ", match.group()).strip()
        for match in _INFORMATION_OPTION.finditer(strip_html(source_text))
    ]
    if not source_matches or _INFORMATION_OPTION.search(strip_html(edited_text)):
        return []
    return list(dict.fromkeys(source_matches))


def detect_missing_anchored_requirements(
    source_text: str,
    edited_text: str,
) -> list[str]:
    """Find mandatory source clauses whose objective anchors disappeared.

    Only clauses with stable anchors such as an age, GPA or certification
    acronym are checked. Requirements without those anchors remain prompt-only
    protections instead of relying on a noisy semantic guess.
    """
    edited = strip_html(edited_text)
    edited_anchors = {
        anchor.rstrip("+").casefold()
        for anchor in _REQUIREMENT_ANCHOR.findall(edited)
    }
    edited_has_requirement = bool(_REQUIREMENT_MARKER.search(edited))
    findings: list[str] = []

    for sentence in re.split(r"(?<=[.!?])\s+|\n+", strip_html(source_text)):
        sentence = sentence.strip()
        if not sentence or not _REQUIREMENT_MARKER.search(sentence):
            continue
        anchors = {
            anchor.rstrip("+").casefold()
            for anchor in _REQUIREMENT_ANCHOR.findall(sentence)
        }
        if not anchors:
            continue
        if not edited_has_requirement or not anchors.issubset(edited_anchors):
            findings.append(sentence)

    return findings

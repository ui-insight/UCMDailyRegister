"""Audience: specific and broad audiences kept, and none invented (#377, #379)."""

import re

from app.utils.style_checks.text import _first_sentence, strip_html

_RECRUITMENT_CONTEXT = re.compile(
    r"\b(?:seeking|recruiting|recruit|inviting|invites?|looking\s+for|open\s+to|"
    r"eligible|opportunity\s+for|needed|wanted)\b",
    re.IGNORECASE,
)
_SPECIFIC_AUDIENCE_GROUPS = (
    (
        "breastfeeding/lactating women",
        re.compile(r"\b(?:breastfeeding|lactating)\s+women\b", re.IGNORECASE),
    ),
    ("donors", re.compile(r"\bdonors?\b", re.IGNORECASE)),
    ("volunteers", re.compile(r"\bvolunteers?\b", re.IGNORECASE)),
    ("faculty members", re.compile(r"\bfaculty\s+members?\b", re.IGNORECASE)),
    (
        "first-year students",
        re.compile(r"\bfirst[\s-]+year\s+students?\b", re.IGNORECASE),
    ),
    ("alumni", re.compile(r"\balumni\b", re.IGNORECASE)),
)
_AGE_RANGE_PATTERNS = (
    re.compile(
        r"\bbetween\s+(?:the\s+)?ages?\s+of\s+(\d{1,3})\s+and\s+(\d{1,3})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bages?\s+(\d{1,3})\s*(?:-|–|—|to)\s*(\d{1,3})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d{1,3})\s*(?:-|–|—|to)\s*(\d{1,3})\s+years?\s+old\b",
        re.IGNORECASE,
    ),
)
_BROAD_AUDIENCE_PHRASES = (
    ("all are welcome", re.compile(r"\ball\s+are\s+welcome\b", re.IGNORECASE)),
    (
        "everyone is invited",
        re.compile(r"\beveryone\s+is\s+invited\b", re.IGNORECASE),
    ),
    (
        "the public is welcome",
        re.compile(r"\bthe\s+public\s+is\s+welcome\b", re.IGNORECASE),
    ),
)
_AUDIENCE_GROUPS = (
    ("employees", re.compile(r"\bemployees?\b", re.IGNORECASE)),
    ("faculty", re.compile(r"\bfaculty\b", re.IGNORECASE)),
    ("staff", re.compile(r"\bstaff\b", re.IGNORECASE)),
    ("students", re.compile(r"\bstudents?\b", re.IGNORECASE)),
    (
        "campus community",
        re.compile(r"\bcampus\s+community\b", re.IGNORECASE),
    ),
    ("public", re.compile(r"\b(?:the\s+)?public\b", re.IGNORECASE)),
)
_DIRECT_INVITATION_LEAD = re.compile(
    r"^(?:Attend|Join|Visit|Watch|Come|Participate|Register|Explore|Learn)\b",
    re.IGNORECASE,
)


def detect_missing_specific_audience_lead(
    source_body: str,
    edited_body: str,
) -> list[str]:
    """Find source-specific recruitment audience details missing from the lead.

    A group is protected only when it appears in a source sentence with a
    recruitment or eligibility cue. This prevents incidental references to
    volunteers or alumni later in an announcement from being misclassified as
    the target audience.
    """
    source = strip_html(source_body)
    source_sentences = re.split(r"(?<=[.!?])\s+|\n+", source)
    edited_lead = _first_sentence(edited_body)
    protected_groups: list[tuple[str, re.Pattern[str]]] = []

    for display, pattern in _SPECIFIC_AUDIENCE_GROUPS:
        if any(
            pattern.search(sentence) and _RECRUITMENT_CONTEXT.search(sentence)
            for sentence in source_sentences
        ):
            protected_groups.append((display, pattern))

    findings = [
        display
        for display, pattern in protected_groups
        if not pattern.search(edited_lead)
    ]

    if protected_groups:
        for pattern in _AGE_RANGE_PATTERNS:
            match = pattern.search(source)
            if match is None:
                continue
            lower_age, upper_age = match.groups()
            if not (
                re.search(rf"\b{re.escape(lower_age)}\b", edited_lead)
                and re.search(rf"\b{re.escape(upper_age)}\b", edited_lead)
            ):
                findings.append(f"ages {lower_age}-{upper_age}")
            break

    return findings


def detect_missing_broad_audience(source_body: str, edited_body: str) -> list[str]:
    """Find a broad invitation narrowed or removed from the edited lead.

    A direct imperative such as ``Attend the reception`` preserves open access
    without repeating ``all are welcome``. Audience-prefixed rewrites such as
    ``Employees are invited`` do not.
    """
    source = strip_html(source_body)
    edited_lead = _first_sentence(edited_body)
    findings: list[str] = []

    for display, pattern in _BROAD_AUDIENCE_PHRASES:
        if not pattern.search(source):
            continue
        if pattern.search(edited_lead) or _DIRECT_INVITATION_LEAD.search(edited_lead):
            continue
        findings.append(display)

    return findings


def detect_introduced_audience_groups(
    source_body: str,
    edited_body: str,
) -> list[str]:
    """Find explicit audience groups introduced only by the edited copy."""
    source = strip_html(source_body)
    edited = strip_html(edited_body)
    return [
        display
        for display, pattern in _AUDIENCE_GROUPS
        if pattern.search(edited) and not pattern.search(source)
    ]

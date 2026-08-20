"""Deterministic post-edit style checks for AI-edited copy.

The AI editing pipeline injects the active style rules into the system prompt,
but prompt text alone cannot guarantee compliance: Joy's Aug. 10 production
feedback (issues #299 and #300) showed the model violating rules that were
active in the prompt at the time. The detectors here cover the subset of those
rules that can be verified mechanically — AP month abbreviation, a.m./p.m.
formatting, platform names, undefined acronyms, repeated calls to action and
the Jobs single-line contract, plus high-confidence source contacts,
organizations, titles, audience qualifiers, composition titles, canonical
locations, information paths, promotional leads and anchored requirements —
so a violation surfaces as a flag on the AI version regardless of whether the
model honored the prompt.

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
_TIME_WITH_PERIOD = re.compile(
    r"\b\d{1,2}(?::\d{2})?\s*(?P<period>a\.m\.|p\.m\.)",
    re.IGNORECASE,
)
_CROSS_PERIOD_HYPHEN_RANGE = re.compile(
    r"\b(?P<start>\d{1,2}(?::\d{2})?\s*(?P<start_period>a\.m\.|p\.m\.))"
    r"\s*[-–—]\s*"
    r"(?P<end>\d{1,2}(?::\d{2})?\s*(?P<end_period>a\.m\.|p\.m\.))",
    re.IGNORECASE,
)

_PLATFORM_NAMES = re.compile(r"\b(?:Zoom|Webex|Microsoft Teams|Google Meet|Skype)\b")

_ACRONYM_TOKEN = re.compile(r"\b[A-Z]{2,6}\b")
_ROMAN_NUMERAL = re.compile(r"^[IVXLCDM]+$")
# Acronyms AP or campus usage treats as standing on their own.
_KNOWN_ACRONYMS = {
    "AP", "US", "USA", "TDR", "RSVP", "GPA", "ID", "PDF", "FAQ", "HR", "IT",
    "TV", "AV", "GED", "ADA", "FYI", "AM", "PM", "ISUB", "IRIC",
}

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

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s])\d{3}[-.\s]\d{4}(?!\d)"
)
_CONTACT_NAME = re.compile(
    r"\b(?i:contact|email|call|reach)\s+(?:the\s+)?"
    r"([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})\b",
)
_PROTECTED_ORGANIZATION_NAME = (
    r"[A-Z][A-Za-z0-9&'’.-]*"
    r"(?:\s+(?:(?:and|of|for|the|in)\s+)?[A-Z][A-Za-z0-9&'’.-]*){1,12}"
)
_SPONSORING_ORGANIZATION = re.compile(
    rf"\b(?P<name>{_PROTECTED_ORGANIZATION_NAME})(?:['’]s)?\s+"
    r"(?:offers?|provides?|administers?|sponsors?|presents?|hosts?|manages?|oversees?)\b"
)
_DESIGNATION_ORGANIZATION = re.compile(
    rf"\b(?:an?|the)\s+(?P<name>{_PROTECTED_ORGANIZATION_NAME})\s+"
    r"(?=(?:STARS\b|[^.!?]{0,30}\b(?:award|ranking|rating|certification|"
    r"accreditation|recognition|designation)\b))"
)
_RECOGNITION_FROM_ORGANIZATION = re.compile(
    r"\b(?:award|ranking|rating|certification|accreditation|recognition|designation)\b"
    rf"[^.!?]{{0,80}}\b(?:from|by|through)\s+(?P<name>{_PROTECTED_ORGANIZATION_NAME})"
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
_COMPOSITION_CUE = re.compile(
    r"\b(?:book|exhibit|exhibition|film|horror|lecture|movie|opera|play|poem|"
    r"reading|screening|song|speech|work\s+of\s+art)\b",
    re.IGNORECASE,
)
_QUOTED_TEXT = re.compile(r"[\"“](?P<title>[^\"”]{2,100})[\"”]")
_TITLE_CASE_SPAN = re.compile(
    r"\b[A-Z][A-Za-z0-9'’.-]*(?:\s+(?:in|of|the|and|&)?\s*"
    r"[A-Z][A-Za-z0-9'’.-]*){0,5}\b"
)
_CANONICAL_CAMPUS_LOCATIONS = (
    "ISUB Reflections Gallery",
    "Bruce M. Pitman Center International Ballroom",
    "IRIC 352",
)
_APPROVED_VENUE_ADDRESSES = {
    "Kenworthy Performing Arts Centre": "508 S. Main St.",
    "1912 Center": "412 E. Third St.",
    "One World Cafe": "840 W. Seventh St.",
    "Hunga Dunga Brewing Co.": "333 N. Jackson St.",
    "Moscow Public Library": "110 S. Jefferson St.",
    "Palouse-Clearwater Environmental Institute": "1040 Rodeo Drive",
    "Best Western Plus University Inn": "1516 W. Pullman Road",
    "East City Park": "900 E. Third St.",
}
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
_RELATIVE_DATE_REFERENCE = re.compile(
    r"\b(?:today|tomorrow|this\s+(?:week|month)|next\s+(?:week|month))\b",
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


def detect_cross_period_hyphen_ranges(text: str) -> list[str]:
    """Find hyphenated time ranges whose endpoints use different periods."""
    findings: list[str] = []
    for match in _CROSS_PERIOD_HYPHEN_RANGE.finditer(strip_html(text)):
        if match.group("start_period").casefold() == match.group("end_period").casefold():
            continue
        findings.append(match.group())
    return findings


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


def detect_disallowed_ampersands(text: str) -> list[str]:
    """Find literal ampersands outside the sole editorial exception, Q&A."""
    visible = strip_html(text)
    visible = re.sub(r"\bQ\s*&\s*A\b", "", visible, flags=re.IGNORECASE)
    visible = re.sub(r"&(?:#\d+|#x[0-9a-f]+|[a-z][a-z0-9]+);", "", visible, flags=re.IGNORECASE)
    return [match.group() for match in re.finditer(r"&", visible)]


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


def _first_sentence(text: str) -> str:
    """Return the first visible sentence from edited copy."""
    visible = re.sub(r"\s+", " ", strip_html(text)).strip()
    return re.split(r"(?<=[.!?])\s+", visible, maxsplit=1)[0]


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


def _composition_titles(source_text: str) -> list[str]:
    """Extract high-confidence composition titles from source copy."""
    source = strip_html(source_text)
    titles: list[str] = []

    for match in _QUOTED_TEXT.finditer(source):
        context = source[max(0, match.start() - 100):match.end() + 100]
        if not _COMPOSITION_CUE.search(context):
            continue
        title = match.group("title").strip().rstrip(",.;:!?")
        if title and title not in titles:
            titles.append(title)

    for match in _TITLE_CASE_SPAN.finditer(source):
        title = match.group().strip()
        if title in titles or len(title) < 3:
            continue
        context = source[max(0, match.start() - 45):match.start()]
        if not _COMPOSITION_CUE.search(context):
            continue
        if len(re.findall(rf"\b{re.escape(title)}\b", source)) < 2:
            continue
        titles.append(title)

    return titles


def detect_unformatted_composition_titles(
    source_text: str,
    edited_headline: str,
    edited_body: str,
) -> list[str]:
    """Find source composition titles lacking AP quotation treatment."""
    findings: list[str] = []
    for title in _composition_titles(source_text):
        escaped = re.escape(title)
        headline_quoted = re.search(
            rf"(?:'{escaped}'|‘{escaped}’)",
            edited_headline,
            re.IGNORECASE,
        )
        body_quoted = re.search(
            rf'(?:"{escaped}"|“{escaped}”)',
            strip_html(edited_body),
            re.IGNORECASE,
        )
        if not headline_quoted or not body_quoted:
            findings.append(title)
    return findings


def detect_noncanonical_campus_locations(edited_text: str) -> list[str]:
    """Find known campus locations whose building/room order is not canonical."""
    visible = re.sub(r"[^a-z0-9]+", " ", strip_html(edited_text).casefold()).strip()
    findings: list[str] = []
    for canonical in _CANONICAL_CAMPUS_LOCATIONS:
        normalized = re.sub(r"[^a-z0-9]+", " ", canonical.casefold()).strip()
        tokens = normalized.split()
        if all(re.search(rf"\b{re.escape(token)}\b", visible) for token in tokens):
            if normalized not in visible:
                findings.append(canonical)
    return findings


def detect_missing_approved_venue_addresses(
    source_text: str,
    edited_text: str,
) -> list[str]:
    """Find approved venues whose canonical address is absent from the edit."""
    source = strip_html(source_text)
    edited = strip_html(edited_text)
    findings: list[str] = []
    for venue, address in _APPROVED_VENUE_ADDRESSES.items():
        if venue not in source and venue not in edited:
            continue
        canonical = f"{venue}, {address}"
        if canonical not in edited:
            findings.append(canonical)
    return findings


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


def _normalized_visible_text(text: str) -> str:
    """Collapse visible text for case-insensitive source-fidelity comparisons."""
    return re.sub(r"\s+", " ", strip_html(text)).strip().casefold()


def detect_missing_protected_organizations(
    source_text: str,
    edited_body: str,
) -> list[str]:
    """Find source sponsors or awarding bodies omitted from the edited body.

    Each candidate must be tied to an organizational role verb or to
    award/designation context. This keeps the detector narrower than a generic
    proper-name comparison while covering the sponsor and accreditor losses
    reported in issue #312.
    """
    source = strip_html(source_text)
    edited = _normalized_visible_text(edited_body)
    candidates: list[str] = []

    for pattern in (
        _SPONSORING_ORGANIZATION,
        _DESIGNATION_ORGANIZATION,
        _RECOGNITION_FROM_ORGANIZATION,
    ):
        for match in pattern.finditer(source):
            candidate = re.sub(r"\s+", " ", match.group("name")).strip(" ,.;:")
            if candidate.casefold().startswith("university of idaho"):
                # The managed campus-name rule intentionally permits "U of I."
                continue
            if candidate not in candidates:
                candidates.append(candidate)

    return [candidate for candidate in candidates if candidate.casefold() not in edited]


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


def _official_name_candidates(source_text: str) -> list[str]:
    # Source components are newline-delimited. Treat those boundaries as
    # sentence breaks so a headline-ending phrase cannot merge with a
    # body-opening phrase into a fabricated official name.
    text = re.sub(r"[\r\n]+", " | ", strip_html(source_text))
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
    findings: list[str] = []
    for candidate in _official_name_candidates(source_text):
        allowed_variants = {candidate}
        if "&" in candidate:
            allowed_variants.add(re.sub(r"\s*&\s*", " and ", candidate))
        if not any(variant in edited for variant in allowed_variants):
            findings.append(candidate)
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

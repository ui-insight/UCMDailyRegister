"""Names, titles and places: official names, organizations, composition titles, campus locations and venues (#396)."""

import re

from app.utils.style_checks.text import _normalized_visible_text, strip_html

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

"""Fetch and normalize external University of Idaho job postings."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape, unescape
import re
from typing import Iterable
from urllib.parse import urljoin

import httpx

from app.config import settings

_JOB_BLOCK_RE = re.compile(
    r"<div class='job-item job-item-posting'(?P<body>.*?)(?=<div class='job-item job-item-posting'|"
    r"<div role=\"navigation\" aria-label=\"Pagination\" class=\"pagination\">|$)",
    re.DOTALL,
)
_TITLE_RE = re.compile(
    r"<h3>\s*<a href=\"(?P<href>[^\"]+)\">(?P<title>.*?)</a>\s*</h3>",
    re.DOTALL,
)
_META_RE = re.compile(
    r"<div class='col-md-2 col-xs-12 job-title job-title-text-wrap col-md-push-2'>"
    r"(?P<value>.*?)</div>",
    re.DOTALL,
)
_DESCRIPTION_RE = re.compile(
    r"<span class='job-description'>(?P<value>.*?)</span>",
    re.DOTALL,
)
_PAGE_RE = re.compile(r"/postings/search\?page=(?P<page>\d+)")
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_ROMAN_NUMERAL_RE = re.compile(r"^[IVXLCDM]+$")
_OFF_CAMPUS_PREFIX_RE = re.compile(
    r"^Off Campus Location\s*-\s*",
    re.IGNORECASE,
)
_JOB_TITLE_PROPER_WORDS = {
    "boise": "Boise",
    "idaho": "Idaho",
    "moscow": "Moscow",
    "uidaho": "UIdaho",
}
_OFFICIAL_UNIT_EXPANSIONS = {
    "IMCI": "Institute for Modeling Collaboration and Innovation",
}


@dataclass(slots=True)
class JobPosting:
    source_id: str
    source_type: str
    url: str
    title: str
    department: str | None
    posting_number: str | None
    location: str | None
    closing_date: str | None
    summary: str


async def fetch_job_postings(selected_source_ids: Iterable[str] = ()) -> list[dict]:
    """Fetch open job postings from the public University of Idaho portal."""
    source_url = settings.job_postings_source_url
    timeout = settings.job_postings_request_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        first_response = await client.get(source_url)
        first_response.raise_for_status()

        pages = _get_page_count(first_response.text)
        pages = max(1, min(pages, settings.job_postings_max_pages))
        responses = [first_response]
        for page in range(2, pages + 1):
            response = await client.get(source_url, params={"page": page})
            response.raise_for_status()
            responses.append(response)

    selected = set(selected_source_ids)
    postings: list[JobPosting] = []
    seen: set[str] = set()
    for response in responses:
        for posting in parse_peopleadmin_search_results(response.text, source_url):
            if posting.source_id in seen:
                continue
            seen.add(posting.source_id)
            postings.append(posting)

    return [
        {
            "Source_Id": posting.source_id,
            "Source_Type": posting.source_type,
            "Url": posting.url,
            "Title": posting.title,
            "Department": posting.department,
            "Posting_Number": posting.posting_number,
            "Location": posting.location,
            "Closing_Date": posting.closing_date,
            "Summary": posting.summary,
            "Selected": posting.source_id in selected,
        }
        for posting in postings
    ]


def parse_peopleadmin_search_results(html_text: str, source_url: str) -> list[JobPosting]:
    """Parse the public PeopleAdmin search results page into normalized postings."""
    postings: list[JobPosting] = []
    for match in _JOB_BLOCK_RE.finditer(html_text):
        body = match.group("body")
        title_match = _TITLE_RE.search(body)
        if not title_match:
            continue

        href = title_match.group("href")
        title = _clean_html(title_match.group("title"))
        if not title:
            continue

        meta_values = [_clean_html(value) or None for value in _META_RE.findall(body)]
        department = meta_values[0] if len(meta_values) > 0 else None
        closing_date = meta_values[1] if len(meta_values) > 1 else None
        posting_number = meta_values[2] if len(meta_values) > 2 else None
        location = meta_values[3] if len(meta_values) > 3 else None

        description_match = _DESCRIPTION_RE.search(body)
        summary = (
            _clean_html(description_match.group("value"))
            if description_match
            else "Imported from the University of Idaho jobs portal."
        )
        if not summary:
            summary = "Imported from the University of Idaho jobs portal."

        url = urljoin(source_url, href)
        postings.append(
            JobPosting(
                source_id=url,
                source_type="job_posting",
                url=url,
                title=title,
                department=department,
                posting_number=posting_number,
                location=location,
                closing_date=closing_date,
                summary=summary,
            )
        )
    return postings


def build_job_headline(posting: JobPosting) -> str:
    """Jobs are deliberately body-only and do not have newsletter headlines."""
    return ""


def build_job_body(posting: JobPosting) -> str:
    """Build the complete one-line linked listing used in Builder and export."""
    listing = build_job_listing_text(posting)
    return f'<a href="{escape(posting.url, quote=True)}">{escape(listing)}</a>'


def build_job_listing_text(posting: JobPosting) -> str:
    """Return title, official unit and any non-Moscow location as one line."""
    parts = [format_job_title(posting.title)]
    if posting.department:
        department = posting.department
        for abbreviation, expansion in _OFFICIAL_UNIT_EXPANSIONS.items():
            department = re.sub(
                rf"\b{re.escape(abbreviation)}\b",
                expansion,
                department,
            )
        parts.append(department)
    location = format_job_location(posting.location)
    if location:
        parts.append(location)
    return ", ".join(part for part in parts if part)


def format_job_title(title: str) -> str:
    """Apply conservative sentence case while retaining acronyms and levels."""
    formatted_words: list[str] = []
    for word in _WHITESPACE_RE.split(title.strip()):
        core = word.strip("()[],.;:")
        prefix_length = word.find(core) if core else 0
        prefix = word[:prefix_length]
        suffix = word[prefix_length + len(core):]
        proper = _JOB_TITLE_PROPER_WORDS.get(core.casefold())
        if proper:
            formatted_core = proper
        elif _ROMAN_NUMERAL_RE.fullmatch(core) or (
            core.isupper() and 1 < len(core) <= 5
        ):
            formatted_core = core
        else:
            formatted_core = core.lower()
        formatted_words.append(f"{prefix}{formatted_core}{suffix}")

    formatted = " ".join(formatted_words)
    first_letter = re.search(r"[A-Za-z]", formatted)
    if first_letter:
        index = first_letter.start()
        formatted = formatted[:index] + formatted[index].upper() + formatted[index + 1:]
    return formatted


def format_job_location(location: str | None) -> str | None:
    """Omit Moscow and normalize PeopleAdmin's off-campus location prefix."""
    if not location:
        return None
    locations: list[str] = []
    for part in location.split(","):
        normalized = _OFF_CAMPUS_PREFIX_RE.sub("", part.strip()).strip()
        if not normalized or normalized.casefold() == "moscow":
            continue
        if normalized not in locations:
            locations.append(normalized)
    return ", ".join(locations) or None


def _get_page_count(html_text: str) -> int:
    pages = [int(match.group("page")) for match in _PAGE_RE.finditer(html_text)]
    return max(pages, default=1)


def _clean_html(value: str) -> str:
    text = _TAG_RE.sub(" ", value)
    text = unescape(text)
    return _WHITESPACE_RE.sub(" ", text).strip()

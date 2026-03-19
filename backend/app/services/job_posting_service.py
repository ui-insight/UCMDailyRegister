"""Fetch and normalize external University of Idaho job postings."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
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
    """Build the one-line headline used in the builder and export."""
    parts = [posting.title]
    if posting.department:
        parts.append(posting.department)
    if posting.location:
        parts.append(posting.location)
    return ", ".join(part for part in parts if part)


def build_job_body(posting: JobPosting) -> str:
    """Build the body text for an imported job posting."""
    details = []
    if posting.posting_number:
        details.append(f"Posting number: {posting.posting_number}.")
    if posting.closing_date:
        details.append(f"Closing date: {posting.closing_date}.")

    parts = [posting.summary.strip()]
    if details:
        parts.append(" ".join(details))
    parts.append(f'<a href="{posting.url}">View job posting</a>.')
    return " ".join(part for part in parts if part).strip()


def _get_page_count(html_text: str) -> int:
    pages = [int(match.group("page")) for match in _PAGE_RE.finditer(html_text)]
    return max(pages, default=1)


def _clean_html(value: str) -> str:
    text = _TAG_RE.sub(" ", value)
    text = unescape(text)
    return _WHITESPACE_RE.sub(" ", text).strip()

"""Fetch and normalize University of Idaho job postings from the careers site.

The University moved from PeopleAdmin to PageUp in fall 2026. Open jobs now
live at careers.uidaho.edu. Its search page sits behind a bot check, so this
service reads the public sitemap for job URLs and then each job's own page,
which carries a schema.org JobPosting block. The "Appointment Information"
lines in that block give the working title, department and location UCM
uses for the one-line Jobs listing.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape, unescape
import json
import logging
import re
import time
from typing import Iterable
from urllib.parse import urlsplit
from xml.etree import ElementTree

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
_JOB_PATH_RE = re.compile(r"^https://[^/]+/(?:[a-z]{2}-[A-Z]{2}/)?jobs/(?!search$)[^/?#]+$")
_LD_JSON_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(?P<body>.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)
_LINE_BREAK_RE = re.compile(r"<br\s*/?>|</(?:p|div|li|h[1-6])>", re.IGNORECASE)
_FIELD_RE = re.compile(
    r"^(?P<label>Working Title|Department|Division/College|Location|Position Overview)"
    r"\s*:\s*(?P<value>.*)$",
    re.IGNORECASE,
)
# PageUp prefixes units with a finance code, e.g. "749-PROV Provost Office".
_UNIT_CODE_RE = re.compile(r"^\s*\d+-[A-Z0-9]+\s+")
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
_DEFAULT_SUMMARY = "Imported from the University of Idaho careers site."
_SUMMARY_MAX_LENGTH = 300
_CACHE_TTL_SECONDS = 6 * 60 * 60

# Job pages rarely change, and the careers site throttles bursts, so parsed
# pages are kept per URL until the sitemap's lastmod changes or the TTL ends.
_page_cache: dict[str, tuple[str | None, float, JobPosting]] = {}


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
    date_posted: str | None = None


class CareersSiteBusyError(RuntimeError):
    """The careers site answered with its empty throttling response."""


@dataclass(slots=True)
class JobPostingFetchResult:
    postings: list[dict]
    is_complete: bool


async def fetch_job_postings(selected_source_ids: Iterable[str] = ()) -> JobPostingFetchResult:
    """Fetch open job postings from the University of Idaho careers site.

    The careers site throttles bursts with an empty HTTP 202. Once that
    happens, no further pages are requested in this run; postings already
    read (or cached from earlier runs) are returned and the result is marked
    incomplete so staff can retry later or add a job by its link.
    """
    timeout = settings.job_postings_request_timeout_seconds
    throttled = False
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        sitemap = await client.get(settings.job_postings_source_url)
        sitemap.raise_for_status()
        entries = parse_careers_sitemap(sitemap.text)[: settings.job_postings_max_listings]

        semaphore = asyncio.Semaphore(settings.job_postings_fetch_concurrency)

        async def load(url: str, lastmod: str | None) -> JobPosting | None:
            nonlocal throttled
            cached = _page_cache.get(url)
            if cached and cached[0] in (lastmod, None) and time.monotonic() - cached[1] < _CACHE_TTL_SECONDS:
                return cached[2]
            async with semaphore:
                if throttled:
                    return None
                try:
                    posting = await _fetch_job_page(client, url)
                except CareersSiteBusyError:
                    throttled = True
                    return None
                except httpx.HTTPError as exc:
                    logger.warning("Job page %s could not be read: %s", url, exc)
                    return None
            if posting is not None:
                _page_cache[url] = (lastmod, time.monotonic(), posting)
            return posting

        results = await asyncio.gather(*(load(url, lastmod) for url, lastmod in entries))

    postings = [posting for posting in results if posting is not None]
    if throttled:
        logger.warning(
            "Careers site throttled job page reads; %s of %s listings available",
            len(postings),
            len(entries),
        )
    if entries and not postings:
        raise CareersSiteBusyError("No job pages could be read from the careers site")
    # Newest at top, matching the Jobs section rule.
    postings.sort(key=lambda posting: posting.date_posted or "", reverse=True)

    selected = set(selected_source_ids)
    return JobPostingFetchResult(
        postings=[posting_to_candidate(posting, posting.source_id in selected) for posting in postings],
        is_complete=not throttled,
    )


async def lookup_job_posting(url: str) -> JobPosting | None:
    """Read one job page that staff pasted into the Builder."""
    if not is_careers_job_url(url):
        raise ValueError("Use a job link from the University careers site.")
    timeout = settings.job_postings_request_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        posting = await _fetch_job_page(client, url)
    if posting is not None:
        _page_cache[url] = (None, time.monotonic(), posting)
    return posting


def is_careers_job_url(url: str) -> bool:
    """Accept only job pages on the configured careers host."""
    careers_host = urlsplit(settings.job_postings_source_url).netloc
    parts = urlsplit(url.strip())
    return (
        parts.scheme == "https"
        and parts.netloc == careers_host
        and bool(_JOB_PATH_RE.match(f"https://{parts.netloc}{parts.path}"))
    )


def posting_to_candidate(posting: JobPosting, selected: bool = False) -> dict:
    return {
        "Source_Id": posting.source_id,
        "Source_Type": posting.source_type,
        "Url": posting.url,
        "Title": posting.title,
        "Department": posting.department,
        "Posting_Number": posting.posting_number,
        "Location": posting.location,
        "Closing_Date": posting.closing_date,
        "Summary": posting.summary,
        "Selected": selected,
    }


async def _fetch_job_page(client: httpx.AsyncClient, url: str) -> JobPosting | None:
    response = await client.get(url)
    # The careers site answers a throttled request with an empty 202.
    if response.status_code == 202 or (response.status_code == 200 and not response.text):
        raise CareersSiteBusyError(url)
    response.raise_for_status()
    posting = parse_careers_job_page(response.text, url)
    if posting is None:
        logger.warning("Job page %s had no open JobPosting data", url)
    return posting


def parse_careers_sitemap(xml_text: str) -> list[tuple[str, str | None]]:
    """Return (job URL, lastmod) pairs for job pages listed in the sitemap."""
    root = ElementTree.fromstring(xml_text)
    entries: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for url_node in root.iter(f"{_SITEMAP_NS}url"):
        loc = (url_node.findtext(f"{_SITEMAP_NS}loc") or "").strip()
        if not _JOB_PATH_RE.match(loc) or loc in seen:
            continue
        seen.add(loc)
        lastmod = (url_node.findtext(f"{_SITEMAP_NS}lastmod") or "").strip() or None
        entries.append((loc, lastmod))
    return entries


def parse_careers_job_page(html_text: str, url: str) -> JobPosting | None:
    """Parse one careers-site job page into a normalized posting."""
    data = _find_job_posting_ld(html_text)
    if data is None:
        return None

    fields = _appointment_fields(str(data.get("description") or ""))
    title = fields.get("working title") or _clean_html(str(data.get("title") or ""))
    if not title:
        return None

    department = clean_unit_name(fields.get("department"))
    location = fields.get("location") or _ld_locality(data)
    overview = fields.get("position overview") or ""
    summary = _truncate(overview) or _DEFAULT_SUMMARY

    if _is_expired(data.get("validThrough")):
        return None

    return JobPosting(
        source_id=url,
        source_type="job_posting",
        url=url,
        title=title,
        department=department,
        posting_number=None,
        location=location,
        closing_date=None,
        summary=summary,
        date_posted=str(data.get("datePosted") or "") or None,
    )


def clean_unit_name(value: str | None) -> str | None:
    """Drop PageUp's leading finance code, e.g. "749-PROV Provost Office"."""
    if not value:
        return None
    return _UNIT_CODE_RE.sub("", value).strip() or None


def _find_job_posting_ld(html_text: str) -> dict | None:
    for match in _LD_JSON_RE.finditer(html_text):
        try:
            data = json.loads(match.group("body"))
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("@type") == "JobPosting":
                return candidate
    return None


def _appointment_fields(description_html: str) -> dict[str, str]:
    """Read "Label: value" lines from the posting's description."""
    text = _LINE_BREAK_RE.sub("\n", description_html)
    text = unescape(_TAG_RE.sub("", text))
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]

    fields: dict[str, str] = {}
    for index, line in enumerate(lines):
        match = _FIELD_RE.match(line)
        if not match:
            continue
        label = match.group("label").casefold()
        value = match.group("value").strip()
        # "Position Overview:" is a heading; its text follows on the next line.
        if not value and label == "position overview" and index + 1 < len(lines):
            value = lines[index + 1]
        if value and label not in fields:
            fields[label] = value
    return fields


def _ld_locality(data: dict) -> str | None:
    places = data.get("jobLocation") or []
    if isinstance(places, dict):
        places = [places]
    localities = []
    for place in places:
        address = place.get("address") if isinstance(place, dict) else None
        locality = address.get("addressLocality") if isinstance(address, dict) else None
        if locality and locality not in localities:
            localities.append(locality)
    return ", ".join(localities) or None


def _is_expired(valid_through: object) -> bool:
    if not isinstance(valid_through, str) or not valid_through:
        return False
    try:
        expires = datetime.fromisoformat(valid_through.replace("Z", "+00:00"))
    except ValueError:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires < datetime.now(timezone.utc)


def _truncate(text: str) -> str:
    if len(text) <= _SUMMARY_MAX_LENGTH:
        return text
    cut = text[:_SUMMARY_MAX_LENGTH].rsplit(" ", 1)[0]
    return f"{cut}…"


def build_job_headline(posting: JobPosting) -> str:
    """Jobs are deliberately body-only and do not have newsletter headlines."""
    return ""


def build_job_body(posting: JobPosting) -> str:
    """Build the complete one-line linked listing used in Builder and export."""
    listing = build_job_listing_text(posting)
    return f'<a href="{escape(posting.url, quote=True)}">{escape(listing)}</a>'


def build_job_listing_text(posting: JobPosting) -> str:
    """Return title, official unit and any non-Moscow location as one line."""
    title = posting.title.strip()
    department = clean_unit_name(posting.department)
    # Some working titles already name the unit ("..., UI Foundation"). Use
    # the unit once, with its official capitalization rather than title case.
    unit_index = title.casefold().find(department.casefold()) if department else -1
    if department and unit_index > 0:
        title = title[:unit_index].rstrip(" ,-–—")
    parts = [format_job_title(title)]
    if department:
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
    """Omit Moscow and normalize an "Off Campus Location -" prefix."""
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


def _clean_html(value: str) -> str:
    text = _TAG_RE.sub(" ", value)
    text = unescape(text)
    return _WHITESPACE_RE.sub(" ", text).strip()

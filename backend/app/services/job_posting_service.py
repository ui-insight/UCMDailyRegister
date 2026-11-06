"""Read and normalize a University of Idaho job posting from its careers link.

The University moved from PeopleAdmin to PageUp in fall 2026. Open jobs now
live at careers.uidaho.edu. UCM runs only jobs people submit, so the tool
never lists the careers site's jobs; staff can paste a submitted job's link
in the Builder, and this service reads that one page, which carries a
schema.org JobPosting block. The "Appointment Information"
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
from urllib.parse import urljoin, urlsplit

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

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
# After the careers site throttles a request, every caller waits this long
# before asking it for job pages again.
_THROTTLE_BACKOFF_SECONDS = 120
_MAX_REDIRECTS = 3
_SOURCE_ID_MAX_LENGTH = 255
_LOCALE_PREFIX_RE = re.compile(r"^/[a-z]{2}-[A-Z]{2}(?=/jobs/)")


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


@dataclass(slots=True)
class _CachedPage:
    lastmod: str | None
    fetched_at: float
    fetched_on: str  # UTC date, comparable with sitemap lastmod dates
    posting: JobPosting | None


# Job pages rarely change, and the careers site throttles bursts, so parsed
# pages (and confirmed closed ones, as None) are shared across callers until
# the sitemap's lastmod changes or the TTL ends.
_page_cache: dict[str, _CachedPage] = {}
_in_flight: dict[str, asyncio.Task] = {}
_throttled_until = 0.0
_fetch_limit: tuple[asyncio.AbstractEventLoop, asyncio.Semaphore] | None = None


class CareersSiteError(RuntimeError):
    """The careers site could not be read."""


class CareersSiteBusyError(CareersSiteError):
    """The careers site answered with its empty throttling response."""


async def lookup_job_posting(url: str) -> JobPosting | None:
    """Read one job page that staff pasted into the Builder."""
    canonical = canonical_job_url(url)
    if canonical is None:
        raise ValueError("Use a job link from the University careers site.")
    timeout = settings.job_postings_request_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        read, posting = await _load_job_page(client, canonical, None, force=True)
    if not read:
        if time.monotonic() < _throttled_until:
            raise CareersSiteBusyError(canonical)
        raise CareersSiteError(f"Job page {canonical} could not be read")
    return posting


def canonical_job_url(url: str) -> str | None:
    """Return the one stable URL for a careers job page, or None if it isn't one.

    Query strings, fragments, a locale prefix (/en-US/) and a trailing slash
    don't change which posting a link names, so they are dropped. The result
    is also the posting's Source_Id, which is limited to 255 characters.
    """
    careers_host = urlsplit(settings.job_postings_source_url).netloc
    parts = urlsplit(url.strip())
    if parts.scheme != "https" or parts.netloc != careers_host:
        return None
    path = _LOCALE_PREFIX_RE.sub("", parts.path).rstrip("/")
    canonical = f"https://{parts.netloc}{path}"
    if not _JOB_PATH_RE.match(canonical) or len(canonical) > _SOURCE_ID_MAX_LENGTH:
        return None
    return canonical


def is_careers_job_url(url: str) -> bool:
    """Accept only job pages on the configured careers host."""
    return canonical_job_url(url) is not None


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


def _cache_is_fresh(cached: _CachedPage, lastmod: str | None) -> bool:
    if time.monotonic() - cached.fetched_at >= _CACHE_TTL_SECONDS:
        return False
    if lastmod is None or cached.lastmod == lastmod:
        return True
    # A page cached by a link lookup has no sitemap revision: reuse it only
    # if it was read after the sitemap's last change.
    return cached.lastmod is None and cached.fetched_on > lastmod


def _shared_fetch_limit() -> asyncio.Semaphore:
    """One request limit for every caller on this event loop."""
    global _fetch_limit
    loop = asyncio.get_running_loop()
    if _fetch_limit is None or _fetch_limit[0] is not loop:
        _fetch_limit = (loop, asyncio.Semaphore(settings.job_postings_fetch_concurrency))
    return _fetch_limit[1]


async def _load_job_page(
    client: httpx.AsyncClient,
    url: str,
    lastmod: str | None,
    *,
    force: bool = False,
) -> tuple[bool, JobPosting | None]:
    """Return (read, posting). read is False when the page couldn't be read.

    A posting of None with read True means the page is closed or has no
    job data. Concurrent callers asking for the same page share one request.
    """
    cached = _page_cache.get(url)
    if cached and not force and _cache_is_fresh(cached, lastmod):
        return True, cached.posting

    task = _in_flight.get(url)
    if task is None:
        task = asyncio.ensure_future(_fetch_and_cache(client, url, lastmod))
        _in_flight[url] = task
        task.add_done_callback(lambda _task, key=url: _in_flight.pop(key, None))
    return await asyncio.shield(task)


async def _fetch_and_cache(
    client: httpx.AsyncClient,
    url: str,
    lastmod: str | None,
) -> tuple[bool, JobPosting | None]:
    global _throttled_until
    async with _shared_fetch_limit():
        if time.monotonic() < _throttled_until:
            return False, None
        try:
            response = await _get_careers_page(client, url)
        except CareersSiteBusyError:
            _throttled_until = time.monotonic() + _THROTTLE_BACKOFF_SECONDS
            return False, None
        except (CareersSiteError, httpx.HTTPError) as exc:
            logger.warning("Job page %s could not be read: %s", url, exc)
            return False, None
    posting = parse_careers_job_page(response.text, url)
    if posting is None:
        logger.info("Job page %s has no open JobPosting data", url)
    _page_cache[url] = _CachedPage(
        lastmod=lastmod,
        fetched_at=time.monotonic(),
        fetched_on=datetime.now(timezone.utc).date().isoformat(),
        posting=posting,
    )
    return True, posting


async def _get_careers_page(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """GET a careers-site page, following redirects only within that site."""
    careers_host = urlsplit(settings.job_postings_source_url).netloc
    for _ in range(_MAX_REDIRECTS + 1):
        response = await client.get(url)
        if response.is_redirect:
            target = urljoin(url, response.headers.get("location", ""))
            parts = urlsplit(target)
            if parts.scheme != "https" or parts.netloc != careers_host:
                raise CareersSiteError(f"Refused redirect off the careers site: {target}")
            url = target
            continue
        # The careers site answers a throttled request with an empty 202.
        if response.status_code == 202 or (response.status_code == 200 and not response.text):
            raise CareersSiteBusyError(url)
        response.raise_for_status()
        return response
    raise CareersSiteError(f"Too many redirects reading {url}")


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
    # Some working titles already end with the unit ("..., UI Foundation").
    # Only a delimited unit at the very end is dropped, so a unit named
    # mid-title ("Director of Financial Aid and Scholarships") stays whole.
    if department:
        suffix = re.search(
            rf"\s*(?:,|\s[-\u2013\u2014])\s*{re.escape(department)}\s*$",
            title,
            re.IGNORECASE,
        )
        if suffix and suffix.start() > 0:
            title = title[: suffix.start()]
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

"""Fetch and normalize external calendar events for newsletter selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from html import unescape
import re
from typing import Iterable
from urllib.parse import urljoin

import httpx

from app.config import settings

_EVENT_BLOCK_RE = re.compile(
    r"<h2[^>]*>(?P<title>.*?)</h2>(?P<body>.*?)(?=<h2[^>]*>|$)",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_LINK_RE = re.compile(r'<a[^>]+href="(?P<href>[^"]+)"[^>]*>', re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")
_DATE_RE = re.compile(
    r"(?P<start>(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    r"[A-Z][a-z]+ \d{1,2}, \d{4}(?:, \d{1,2}:\d{2} [AP]M)?)"
    r"(?:\s*[–-]\s*(?P<end>(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    r"[A-Z][a-z]+ \d{1,2}, \d{4}(?:, \d{1,2}:\d{2} [AP]M)?|\d{1,2}:\d{2} [AP]M))?",
)


@dataclass(slots=True)
class CalendarEvent:
    source_id: str
    source_type: str
    url: str | None
    title: str
    description: str
    location: str | None
    event_start: datetime | None
    event_end: datetime | None


async def fetch_calendar_events(
    publish_date: date,
    newsletter_type: str,
    selected_source_ids: Iterable[str] = (),
) -> list[dict]:
    """Fetch upcoming events for a given newsletter date."""
    source_url = settings.calendar_source_url
    timeout = settings.calendar_request_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(source_url)
        response.raise_for_status()

    selected = set(selected_source_ids)
    events = parse_trumba_hcalendar(response.text, source_url)
    end_date = publish_date + timedelta(days=7)
    filtered = [
        {
            "Source_Id": event.source_id,
            "Source_Type": event.source_type,
            "Url": event.url,
            "Title": event.title,
            "Description": event.description,
            "Location": event.location,
            "Event_Start": event.event_start,
            "Event_End": event.event_end,
            "Selected": event.source_id in selected,
        }
        for event in events
        if _include_event(event, publish_date, end_date, newsletter_type)
    ]
    filtered.sort(
        key=lambda event: (
            event["Event_Start"] or datetime.combine(publish_date, time.min),
            event["Title"].lower(),
        )
    )
    return filtered


def parse_trumba_hcalendar(html_text: str, source_url: str) -> list[CalendarEvent]:
    """Parse the Trumba hCalendar page into normalized events."""
    events: list[CalendarEvent] = []
    for match in _EVENT_BLOCK_RE.finditer(html_text):
        title = _clean_html(match.group("title"))
        if not title:
            continue
        if title.lower() == "contact us":
            break

        block_html = match.group("body")
        block_text = _clean_html(block_html)
        if not _DATE_RE.search(block_text):
            continue

        start, end = _extract_datetimes(block_text)
        description = _extract_description(block_text)
        location = _extract_location(block_text)
        url = _extract_event_url(match.group("title"), block_html, source_url)
        source_id = _build_source_id(url, title, start)
        events.append(
            CalendarEvent(
                source_id=source_id,
                source_type="calendar_event",
                url=url,
                title=title,
                description=description,
                location=location,
                event_start=start,
                event_end=end,
            )
        )
    return events


def build_event_body(event: CalendarEvent) -> str:
    """Build the builder/export body text for an imported calendar event."""
    parts = [event.description.strip()]
    details = []
    if event.event_start:
        if event.event_end and event.event_end.date() == event.event_start.date():
            details.append(
                f"{event.event_start.strftime('%A, %B %-d, %Y, %-I:%M %p')} - "
                f"{event.event_end.strftime('%-I:%M %p')}"
            )
        else:
            details.append(event.event_start.strftime("%A, %B %-d, %Y, %-I:%M %p"))
    if event.location:
        details.append(event.location)
    if details:
        parts.append(". ".join(details) + ".")
    if event.url:
        parts.append(f'<a href="{event.url}">Event details</a>.')
    return " ".join(part for part in parts if part).strip()


def _include_event(
    event: CalendarEvent,
    publish_date: date,
    end_date: date,
    newsletter_type: str,
) -> bool:
    if event.event_start is None:
        return False
    event_date = event.event_start.date()
    if newsletter_type == "tdr":
        return publish_date <= event_date <= end_date
    return publish_date <= event_date <= end_date


def _extract_datetimes(text: str) -> tuple[datetime | None, datetime | None]:
    matches = list(_DATE_RE.finditer(text))
    if not matches:
        return None, None
    match = matches[-1]
    start_text = match.group("start")
    end_text = match.group("end")
    start = _parse_datetime(start_text)
    end = _parse_end_datetime(end_text, start) if end_text else None
    return start, end


def _extract_description(text: str) -> str:
    match = _DATE_RE.search(text)
    if not match:
        return text.strip()
    description = text[:match.start()].strip(" .")
    if "For more info visit" in description:
        description = description.split("For more info visit", 1)[0].strip(" .")
    return description or "Imported from the University of Idaho events calendar."


def _extract_location(text: str) -> str | None:
    prefix = text
    match = _DATE_RE.search(text)
    if match:
        prefix = text[:match.start()]

    for label in ("University Location:", "Location:", "Participate Online:"):
        if label in prefix:
            value = prefix.rsplit(label, 1)[-1].strip(" .")
            if value:
                return value

    sentences = [segment.strip(" .") for segment in prefix.split(".") if segment.strip()]
    if len(sentences) >= 2:
        candidate = sentences[-1]
        if len(candidate) <= 255:
            return candidate
    return None


def _extract_event_url(title_html: str, block_html: str, source_url: str) -> str | None:
    for html_fragment in (block_html, title_html):
        match = _LINK_RE.search(html_fragment)
        if match:
            return urljoin(source_url, unescape(match.group("href")))
    return None


def _build_source_id(url: str | None, title: str, start: datetime | None) -> str:
    if url:
        return url
    parts = [title.strip().lower()]
    if start:
        parts.append(start.isoformat())
    return "::".join(parts)


def _clean_html(value: str) -> str:
    text = _TAG_RE.sub(" ", value)
    text = unescape(text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _parse_datetime(value: str) -> datetime | None:
    for fmt in ("%A, %B %d, %Y, %I:%M %p", "%A, %B %d, %Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_end_datetime(value: str, start: datetime | None) -> datetime | None:
    if start is None:
        return _parse_datetime(value)
    for fmt in ("%I:%M %p",):
        try:
            parsed = datetime.strptime(value, fmt)
            return datetime.combine(start.date(), parsed.time())
        except ValueError:
            continue
    return _parse_datetime(value)

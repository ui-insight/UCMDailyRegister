"""Fetch and normalize external calendar events for newsletter selection.

Events are pulled from the University of Idaho's Trumba calendar RSS feed at
uidaho.edu/events. The RSS feed provides structured event data including titles,
dates, descriptions, and links.

Day-of-week import logic determines which dates to include:
  - Monday through Thursday: events for today and the following day
  - Friday: events for Friday, Saturday, Sunday, and Monday
  - Holiday/summer weekly editions: entire week plus the following Monday

Editors can override this to include additional days via the `extra_days`
parameter.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from html import unescape
from typing import Iterable

import httpx

from app.config import settings

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_TIME_RE = re.compile(
    r"(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))"
    r"(?:\s*[-–]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)))?",
    re.IGNORECASE,
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


def _get_import_date_range(
    publish_date: date,
    is_weekly: bool = False,
    extra_days: int = 0,
) -> tuple[date, date]:
    """Compute the event date range to import based on day-of-week rules.

    Args:
        publish_date: The newsletter's publication date.
        is_weekly: True for summer/holiday weekly editions.
        extra_days: Extra days to extend the range (editor override).
    """
    dow = publish_date.weekday()  # 0=Mon, 4=Fri

    if is_weekly:
        # Weekly editions: entire week (Mon-Sun) plus the following Monday
        start = publish_date
        end = publish_date + timedelta(days=7)
    elif dow == 4:  # Friday
        # Fri + Sat + Sun + Mon
        start = publish_date
        end = publish_date + timedelta(days=3)
    else:
        # Mon-Thu: today + tomorrow
        start = publish_date
        end = publish_date + timedelta(days=1)

    end = end + timedelta(days=extra_days)
    return start, end


async def fetch_calendar_events(
    publish_date: date,
    newsletter_type: str,
    selected_source_ids: Iterable[str] = (),
    is_weekly: bool = False,
    extra_days: int = 0,
) -> list[dict]:
    """Fetch upcoming events for a given newsletter date.

    Args:
        publish_date: The newsletter's publication date.
        newsletter_type: "tdr" or "myui".
        selected_source_ids: Source IDs already added to the newsletter.
        is_weekly: Whether this is a weekly edition (summer/holiday).
        extra_days: Additional days to include (editor override).
    """
    source_url = settings.calendar_source_url
    timeout = settings.calendar_request_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(source_url)
        response.raise_for_status()

    selected = set(selected_source_ids)
    events = parse_trumba_rss(response.text)

    start_date, end_date = _get_import_date_range(publish_date, is_weekly, extra_days)

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
        if _include_event(event, start_date, end_date)
    ]
    filtered.sort(
        key=lambda event: (
            event["Event_Start"] or datetime.combine(publish_date, time.min),
            event["Title"].lower(),
        )
    )
    return filtered


def parse_trumba_rss(xml_text: str) -> list[CalendarEvent]:
    """Parse the Trumba RSS feed into normalized CalendarEvent objects."""
    events: list[CalendarEvent] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return events

    for item in root.iter("item"):
        title_elem = item.find("title")
        if title_elem is None or not title_elem.text:
            continue

        title = title_elem.text.strip()
        link_elem = item.find("link")
        url = link_elem.text.strip() if link_elem is not None and link_elem.text else None

        guid_elem = item.find("guid")
        source_id = (
            guid_elem.text.strip()
            if guid_elem is not None and guid_elem.text
            else _build_source_id(url, title)
        )

        # Parse description (HTML content)
        desc_elem = item.find("description")
        raw_desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
        description, location, event_start, event_end = _parse_description(raw_desc)

        # Parse date from category field (format: "YYYY/MM/DD (Day)")
        if event_start is None:
            cat_elem = item.find("category")
            if cat_elem is not None and cat_elem.text:
                event_start = _parse_category_date(cat_elem.text.strip())

        events.append(
            CalendarEvent(
                source_id=source_id,
                source_type="calendar_event",
                url=url,
                title=title,
                description=description or "Imported from the U of I events calendar.",
                location=location,
                event_start=event_start,
                event_end=event_end,
            )
        )

    return events


# Keep the HTML parser for backwards compatibility
def parse_trumba_hcalendar(html_text: str, source_url: str) -> list[CalendarEvent]:
    """Parse the Trumba hCalendar HTML page into normalized events (legacy)."""
    return parse_trumba_rss(html_text) if html_text.strip().startswith("<?xml") else []


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
    start_date: date,
    end_date: date,
) -> bool:
    """Check if an event falls within the import date range."""
    if event.event_start is None:
        return False
    event_date = event.event_start.date()
    return start_date <= event_date <= end_date


def _parse_description(raw_html: str) -> tuple[str, str | None, datetime | None, datetime | None]:
    """Extract description, location, and datetimes from RSS description HTML."""
    text = _clean_html(raw_html)
    description = text
    location = None
    event_start = None
    event_end = None

    # Try to extract location from common patterns
    for label in ("University Location:", "Location:"):
        if label in text:
            loc_part = text.split(label, 1)[1].strip()
            # Location is typically before the next label or end
            for terminator in ("\n", "Participate", "For more", "http"):
                if terminator in loc_part:
                    loc_part = loc_part.split(terminator, 1)[0]
            location = loc_part.strip(" .")
            if location and len(location) > 255:
                location = location[:255]

    # Try to extract date/time from the text
    # Trumba descriptions often start with the date line
    lines = text.split("\n") if "\n" in text else text.split("  ")
    for line in lines:
        line = line.strip()
        # Look for date-like patterns: "Tuesday, March 24, 2026" or "March 24, 2026"
        date_match = re.search(
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
            r"(January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+(\d{1,2}),?\s+(\d{4})",
            line,
        )
        if date_match:
            month_str = date_match.group(1)
            day_num = int(date_match.group(2))
            year_num = int(date_match.group(3))
            try:
                month_num = [
                    "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December",
                ].index(month_str) + 1
                event_date = date(year_num, month_num, day_num)

                # Try to get times
                time_match = _TIME_RE.search(line)
                if time_match:
                    start_time = _parse_time_str(time_match.group(1))
                    if start_time:
                        event_start = datetime.combine(event_date, start_time)
                    end_time_str = time_match.group(2)
                    if end_time_str and event_start:
                        end_time = _parse_time_str(end_time_str)
                        if end_time:
                            event_end = datetime.combine(event_date, end_time)
                else:
                    event_start = datetime.combine(event_date, time.min)
            except (ValueError, IndexError):
                pass
            break

    # Clean up description: remove the date line if it's at the start
    if event_start and lines:
        clean_parts = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip lines that are purely date/time info
            if re.match(
                r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
                line,
            ) and event_start:
                continue
            clean_parts.append(line)
        if clean_parts:
            description = " ".join(clean_parts)

    return description.strip() or "Imported from the U of I events calendar.", location, event_start, event_end


def _parse_time_str(time_str: str) -> time | None:
    """Parse a time string like '9am', '3:30 p.m.' into a time object."""
    cleaned = time_str.strip().lower().replace(".", "").replace(" ", "")
    for fmt in ("%I:%M%p", "%I%p"):
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue
    return None


def _parse_category_date(cat_text: str) -> datetime | None:
    """Parse the category field format: 'YYYY/MM/DD (Day)'."""
    match = re.match(r"(\d{4})/(\d{2})/(\d{2})", cat_text)
    if match:
        try:
            return datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
        except ValueError:
            return None
    return None


def _build_source_id(url: str | None, title: str) -> str:
    """Build a stable source ID from URL or title."""
    if url:
        return url
    return hashlib.md5(title.encode()).hexdigest()


def _clean_html(value: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = _TAG_RE.sub(" ", value)
    text = unescape(text)
    return _WHITESPACE_RE.sub(" ", text).strip()

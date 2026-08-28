"""Harvest University of Idaho Trumba calendar events for SLC triage.

Pulls the university's Trumba calendar JSON feed and upserts each event
occurrence into the harvested_events table. The JSON feed is richer than the
RSS feed used by calendar_event_service: every entry carries a stable eventID,
real start/end datetimes, a categoryCalendar hierarchy (pipe-delimited, e.g.
"Student Affairs|Campus Recreation|Intramurals"), and a canceled flag. One
feed covers all of the university's public calendar views — uidaho.edu/events
and the department pages are filtered spuds of the same Trumba account.

The feed returns roughly three weeks of upcoming occurrences and caps at 200
rows, which comfortably covers the weekly SLC triage cadence. Repeating events
appear once per occurrence, each with its own eventID and a shared seriesID.

Upserts are keyed by (Source_Type, Source_Id) so harvesting is idempotent:
re-running never duplicates rows. A SHA-256 Content_Hash over the harvested
fields detects upstream edits; changed events are updated in place while the
coordinator's SLC_Review_Status is always preserved. Every event seen in the
feed gets its Last_Seen_At bumped.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, time

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.harvested_event import HarvestedEvent
from app.services.calendar_event_service import _clean_html

TRUMBA_SOURCE_TYPE = "trumba"

_MAX_LOCATION_LENGTH = 255
_MAX_CATEGORY_LENGTH = 255


@dataclass(slots=True)
class TrumbaFeedEvent:
    source_id: str
    series_id: str | None
    url: str | None
    title: str
    description: str
    location: str | None
    event_start: datetime
    event_end: datetime | None
    all_day: bool
    category_path: str | None
    canceled: bool


@dataclass(slots=True)
class HarvestSummary:
    fetched: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0


async def fetch_trumba_feed() -> list[dict]:
    """Fetch the raw Trumba JSON feed configured in settings."""
    timeout = settings.slc_trumba_request_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(settings.slc_trumba_feed_url)
        response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Trumba feed did not return a JSON array of events.")
    return payload


def parse_trumba_feed(payload: list[dict]) -> tuple[list[TrumbaFeedEvent], int]:
    """Normalize raw feed entries, returning (events, skipped_count).

    Entries missing an eventID, title, or parseable startDateTime are skipped
    rather than guessed at. Duplicate eventIDs within one payload collapse to
    the last occurrence seen.
    """
    events: dict[str, TrumbaFeedEvent] = {}
    skipped = 0
    for entry in payload:
        if not isinstance(entry, dict):
            skipped += 1
            continue
        event_id = entry.get("eventID")
        # Titles arrive HTML-escaped (e.g. "&#39;") and with stray whitespace.
        title = _clean_html(entry.get("title") or "")
        event_start = _parse_feed_datetime(entry.get("startDateTime"))
        if not event_id or not title or event_start is None:
            skipped += 1
            continue

        series_id = entry.get("seriesID")
        # Trumba locations occasionally carry embedded anchor markup.
        location = _clean_html(entry.get("location") or "") or None
        if location and len(location) > _MAX_LOCATION_LENGTH:
            location = location[:_MAX_LOCATION_LENGTH]
        category_path = (entry.get("categoryCalendar") or "").strip() or None
        if category_path and len(category_path) > _MAX_CATEGORY_LENGTH:
            category_path = category_path[:_MAX_CATEGORY_LENGTH]
        url = (entry.get("permaLinkUrl") or "").strip() or (
            (entry.get("webLink") or "").strip() or None
        )

        events[str(event_id)] = TrumbaFeedEvent(
            source_id=str(event_id),
            series_id=str(series_id) if series_id else None,
            url=url,
            title=title,
            description=_clean_html(entry.get("description") or ""),
            location=location,
            event_start=event_start,
            event_end=_parse_feed_datetime(entry.get("endDateTime")),
            all_day=bool(entry.get("allDay")),
            category_path=category_path,
            canceled=bool(entry.get("canceled")),
        )
    return list(events.values()), skipped


def compute_content_hash(event: TrumbaFeedEvent) -> str:
    """Hash the harvested fields so upstream edits are detectable."""
    parts = [
        event.title,
        event.description,
        event.location or "",
        event.event_start.isoformat(),
        event.event_end.isoformat() if event.event_end else "",
        "all_day" if event.all_day else "",
        event.category_path or "",
        event.url or "",
        "canceled" if event.canceled else "",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


async def harvest_trumba_events(db: AsyncSession) -> HarvestSummary:
    """Fetch the Trumba feed and upsert its events. Idempotent."""
    payload = await fetch_trumba_feed()
    events, skipped = parse_trumba_feed(payload)
    summary = await upsert_harvested_events(db, events)
    summary.fetched = len(payload)
    summary.skipped += skipped
    return summary


async def upsert_harvested_events(
    db: AsyncSession, events: list[TrumbaFeedEvent]
) -> HarvestSummary:
    """Insert new events and update changed ones, keyed by Source_Id.

    SLC_Review_Status is never touched here — triage decisions survive
    re-harvests. Events absent from the feed are left alone.
    """
    summary = HarvestSummary()
    if not events:
        return summary

    result = await db.execute(
        sa.select(HarvestedEvent).where(
            HarvestedEvent.Source_Type == TRUMBA_SOURCE_TYPE,
            HarvestedEvent.Source_Id.in_([event.source_id for event in events]),
        )
    )
    existing_by_source_id = {row.Source_Id: row for row in result.scalars()}

    for event in events:
        content_hash = compute_content_hash(event)
        existing = existing_by_source_id.get(event.source_id)
        if existing is None:
            db.add(
                HarvestedEvent(
                    Source_Type=TRUMBA_SOURCE_TYPE,
                    Source_Id=event.source_id,
                    Series_Id=event.series_id,
                    Source_Url=event.url,
                    Title=event.title,
                    Description=event.description,
                    Location=event.location,
                    Event_Start=event.event_start,
                    Event_End=event.event_end,
                    All_Day=event.all_day,
                    Category_Path=event.category_path,
                    Is_Canceled=event.canceled,
                    Content_Hash=content_hash,
                )
            )
            summary.created += 1
            continue

        if existing.Content_Hash == content_hash:
            summary.unchanged += 1
        else:
            existing.Series_Id = event.series_id
            existing.Source_Url = event.url
            existing.Title = event.title
            existing.Description = event.description
            existing.Location = event.location
            existing.Event_Start = event.event_start
            existing.Event_End = event.event_end
            existing.All_Day = event.all_day
            existing.Category_Path = event.category_path
            existing.Is_Canceled = event.canceled
            existing.Content_Hash = content_hash
            summary.updated += 1
        existing.Last_Seen_At = sa.func.now()

    await db.commit()
    return summary


async def list_harvested_events(
    db: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    review_status: str | None = None,
    offset: int = 0,
    limit: int = 200,
) -> tuple[list[HarvestedEvent], int]:
    """List harvested events ordered by start time.

    The category filter matches a Category_Path branch: "Student Affairs"
    matches both "Student Affairs" and "Student Affairs|Campus Recreation".
    """
    query = sa.select(HarvestedEvent)
    if date_from:
        query = query.where(
            HarvestedEvent.Event_Start >= datetime.combine(date_from, time.min)
        )
    if date_to:
        query = query.where(
            HarvestedEvent.Event_Start <= datetime.combine(date_to, time.max)
        )
    if category:
        query = query.where(
            sa.or_(
                HarvestedEvent.Category_Path == category,
                HarvestedEvent.Category_Path.like(f"{category}|%"),
            )
        )
    if review_status:
        query = query.where(HarvestedEvent.SLC_Review_Status == review_status)

    total = (
        await db.execute(
            sa.select(sa.func.count()).select_from(query.subquery())
        )
    ).scalar_one()

    query = query.order_by(
        HarvestedEvent.Event_Start, HarvestedEvent.Title
    ).offset(offset).limit(limit)
    items = list((await db.execute(query)).scalars().all())
    return items, total


def _parse_feed_datetime(value: object) -> datetime | None:
    """Parse a Trumba local-time string like '2026-08-28T10:00:00'."""
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    # Feed datetimes are wall-clock Pacific time; offsets, when present,
    # arrive in the separate *TimeZoneOffset fields. Store naive local time.
    return parsed.replace(tzinfo=None)

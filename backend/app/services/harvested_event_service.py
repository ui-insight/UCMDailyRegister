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

For flagged events, a harvest additionally guards against emailing stale
information. An upstream edit or cancellation stamps Upstream_Changed_At,
which the triage page surfaces as an acknowledgeable badge. A flagged future
event that disappears from the feed while still inside the feed's coverage
window (bounded by the last fetched occurrence, since the feed is a rolling
~3-week window capped at 200 rows) is treated as canceled upstream. And every
harvest re-syncs each flagged event's promoted submission — headline, body,
and schedule dates — with the current harvested data, which doubles as an
automatic backfill whenever the promoted body format changes. The harvested
feed is the source of truth for promoted events: manual edits to a promoted
submission are overwritten by design.

Triage transitions live here too. Flagging promotes the event onto the SLC
calendar by creating an SLC-only Submission (same shape as the workbook
importer: Category "slc_event", Target_Newsletter "none", schedule rows for
the event dates) and linking it via Promoted_Submission_Id. Withdrawing a
flag deletes that promoted submission: it is a machine-created copy fully
derivable from the harvested event, so deletion loses nothing and keeps
un-flagged events off the SLC calendar entirely.
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
from app.models.submission import Submission, SubmissionScheduleRequest
from app.services.calendar_event_service import _clean_html

TRUMBA_SOURCE_TYPE = "trumba"
TRIAGE_NAME = "SLC event triage"
TRIAGE_EMAIL = "slc-triage@uidaho.edu"
REVIEW_STATUSES = ("new", "flagged", "dismissed")

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
    # Existing events newly canceled this harvest (feed-marked or disappeared);
    # a subset of `updated`, broken out so cancellations stand out in logs.
    canceled: int = 0


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
    disappeared = await _cancel_disappeared_flagged_events(db, events)
    summary.updated += disappeared
    summary.canceled += disappeared
    summary.fetched = len(payload)
    summary.skipped += skipped
    return summary


async def plan_trumba_harvest(db: AsyncSession) -> HarvestSummary:
    """Fetch the feed and report what a harvest would change, without writing.

    The CLI's dry-run mode. Mirrors the decision rules of
    upsert_harvested_events and _cancel_disappeared_flagged_events.
    """
    payload = await fetch_trumba_feed()
    events, skipped = parse_trumba_feed(payload)
    summary = HarvestSummary(fetched=len(payload), skipped=skipped)
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
        existing = existing_by_source_id.get(event.source_id)
        if existing is None:
            summary.created += 1
        elif (
            existing.Content_Hash != compute_content_hash(event)
            or existing.Is_Canceled != event.canceled
        ):
            summary.updated += 1
            if event.canceled and not existing.Is_Canceled:
                summary.canceled += 1
        else:
            summary.unchanged += 1

    disappeared = len(await _select_disappeared_flagged_events(db, events))
    summary.updated += disappeared
    summary.canceled += disappeared
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

        was_canceled = existing.Is_Canceled
        if existing.Content_Hash == content_hash:
            if existing.Is_Canceled != event.canceled:
                # Only the disappearance handling below desyncs Is_Canceled
                # from the hash; a reappearing event is restored here.
                existing.Is_Canceled = event.canceled
                _mark_upstream_change(existing)
                summary.updated += 1
            else:
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
            _mark_upstream_change(existing)
            summary.updated += 1
        if event.canceled and not was_canceled:
            summary.canceled += 1
        _sync_promoted_submission(existing)
        existing.Last_Seen_At = sa.func.now()

    await db.commit()
    return summary


def _mark_upstream_change(event: HarvestedEvent) -> None:
    """Stamp each lens's change marker on the events it is watching.

    The SLC lens watches flagged events (their promoted submissions could go
    stale); the ops lens watches reviewed events (their confirmed needs
    represent Event Services planning). The two markers are acknowledged
    independently, so both are stamped here and never read together.
    """
    if event.SLC_Review_Status == "flagged":
        event.Upstream_Changed_At = sa.func.now()
    if event.Ops_Review_Status == "reviewed":
        event.Ops_Upstream_Changed_At = sa.func.now()


async def _select_disappeared_flagged_events(
    db: AsyncSession, events: list[TrumbaFeedEvent]
) -> list[HarvestedEvent]:
    """Watched, un-canceled future events inside feed coverage but absent.

    Trumba drops deleted events from the feed without a tombstone. The feed
    only covers a rolling window (~3 weeks, capped at 200 rows), so absence is
    only meaningful for events starting on or before the last fetched
    occurrence; events beyond that boundary simply are not covered yet. Limited
    to watched events — SLC-flagged (their promoted submissions would
    otherwise be emailed stale) or ops-reviewed (Event Services would
    otherwise staff a vanished event).
    """
    if not events:
        return []
    coverage_end = max(event.event_start for event in events)
    seen_ids = {event.source_id for event in events}
    result = await db.execute(
        sa.select(HarvestedEvent).where(
            HarvestedEvent.Source_Type == TRUMBA_SOURCE_TYPE,
            sa.or_(
                HarvestedEvent.SLC_Review_Status == "flagged",
                HarvestedEvent.Ops_Review_Status == "reviewed",
            ),
            HarvestedEvent.Is_Canceled.is_(False),
            HarvestedEvent.Event_Start > datetime.now(),
            HarvestedEvent.Event_Start <= coverage_end,
            HarvestedEvent.Source_Id.not_in(seen_ids),
        )
    )
    return list(result.scalars().all())


async def _cancel_disappeared_flagged_events(
    db: AsyncSession, events: list[TrumbaFeedEvent]
) -> int:
    """Mark watched future events missing from the feed as canceled upstream."""
    rows = await _select_disappeared_flagged_events(db, events)
    for event in rows:
        event.Is_Canceled = True
        _mark_upstream_change(event)
        _sync_promoted_submission(event)
    if rows:
        await db.commit()
    return len(rows)


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
    Without an explicit review_status, dismissed events are excluded so the
    default triage view only shows events still worth looking at.
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
    else:
        query = query.where(HarvestedEvent.SLC_Review_Status != "dismissed")

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


async def set_review_status(
    db: AsyncSession,
    harvested_event_id: str,
    *,
    status: str,
    classification: str | None = None,
) -> HarvestedEvent | None:
    """Apply a triage decision to a harvested event. Idempotent.

    Flagging creates (or, on re-flag, updates the classification of) the
    promoted SLC submission; any other status withdraws the promotion by
    deleting that submission. Returns None when the event does not exist.
    """
    event = await db.get(HarvestedEvent, harvested_event_id)
    if event is None:
        return None

    if status == "flagged":
        await _promote_event(db, event, classification)
    else:
        await _withdraw_promotion(db, event)
        # The badge only makes sense while the promotion exists.
        event.Upstream_Changed_At = None
    event.SLC_Review_Status = status

    await db.commit()
    await db.refresh(event)
    return event


async def acknowledge_upstream_change(
    db: AsyncSession, harvested_event_id: str
) -> HarvestedEvent | None:
    """Clear the upstream-change marker once the coordinator has reviewed it.

    Returns None when the event does not exist.
    """
    event = await db.get(HarvestedEvent, harvested_event_id)
    if event is None:
        return None
    event.Upstream_Changed_At = None
    await db.commit()
    await db.refresh(event)
    return event


async def _promote_event(
    db: AsyncSession, event: HarvestedEvent, classification: str | None
) -> None:
    """Create the SLC calendar submission for a flagged event, once."""
    if event.Promoted_Submission_Id:
        existing = await db.get(Submission, event.Promoted_Submission_Id)
        if existing is not None:
            existing.Event_Classification = classification
            _sync_promoted_submission(event)
            return
        # Staff deleted the promoted submission out from under the link;
        # fall through and promote again.

    submission = Submission(
        Category="slc_event",
        Target_Newsletter="none",
        Original_Headline=event.Title,
        Original_Body=_build_promoted_body(event),
        Submitter_Name=TRIAGE_NAME,
        Submitter_Email=TRIAGE_EMAIL,
        Submitter_Notes=(
            f"Promoted from harvested event {event.Id} "
            f"({event.Source_Type} event {event.Source_Id})."
        ),
        Show_In_SLC_Calendar=True,
        Event_Classification=classification,
        Status="approved",
    )
    db.add(submission)
    await db.flush()

    start_date = event.Event_Start.date()
    end_date = event.Event_End.date() if event.Event_End else start_date
    is_range = end_date > start_date
    db.add(
        SubmissionScheduleRequest(
            Submission_Id=submission.Id,
            Requested_Date=start_date,
            Repeat_Count=1,
            Recurrence_Type="date_range" if is_range else "once",
            Recurrence_Interval=1,
            Recurrence_End_Date=end_date if is_range else None,
            Excluded_Dates=[],
        )
    )
    event.Promoted_Submission_Id = submission.Id


def _sync_promoted_submission(event: HarvestedEvent) -> None:
    """Re-derive the promoted submission from the current harvested data.

    Keeps headline, body, and schedule dates in step with upstream edits, and
    doubles as a backfill when the promoted body format changes: the body is
    rebuilt on every harvest and updated whenever the rendered form differs.
    No-op for events without a live promotion.
    """
    submission = event.Promoted_Submission_Rel
    if submission is None:
        return
    if submission.Original_Headline != event.Title:
        submission.Original_Headline = event.Title
    new_body = _build_promoted_body(event)
    if submission.Original_Body != new_body:
        submission.Original_Body = new_body

    request = submission.Schedule_Requests[0] if submission.Schedule_Requests else None
    if request is None:
        return
    start_date = event.Event_Start.date()
    end_date = event.Event_End.date() if event.Event_End else start_date
    is_range = end_date > start_date
    request.Requested_Date = start_date
    request.Recurrence_Type = "date_range" if is_range else "once"
    request.Recurrence_End_Date = end_date if is_range else None


async def _withdraw_promotion(db: AsyncSession, event: HarvestedEvent) -> None:
    """Delete the promoted submission, if one still exists."""
    if not event.Promoted_Submission_Id:
        return
    submission = await db.get(Submission, event.Promoted_Submission_Id)
    if submission is not None:
        await db.delete(submission)
    event.Promoted_Submission_Id = None


def _build_promoted_body(event: HarvestedEvent) -> str:
    """Render the label/value body the SLC calendar day panel expects."""
    start_date = event.Event_Start.date()
    end_date = event.Event_End.date() if event.Event_End else start_date
    source_date = start_date.strftime("%-m/%-d/%Y")
    if end_date > start_date:
        source_date = f"{source_date} - {end_date.strftime('%-m/%-d/%Y')}"

    parts = []
    if event.Is_Canceled:
        # Parsed by the digest view, which strikes canceled events in the
        # preview and keeps them out of the copied email.
        parts.append("Canceled: yes")
    parts.append(f"Source date: {source_date}")
    if event.All_Day:
        parts.append("Start time: All day")
    else:
        parts.append(f"Start time: {event.Event_Start.strftime('%-I:%M %p')}")
    if event.Location:
        parts.append(f"Location: {event.Location}")
    if event.Category_Path:
        parts.append(f"Category: {event.Category_Path}")
    description = _flatten_description(event.Description)
    if description:
        parts.append(f"Description: {description}")
    if event.Source_Url:
        parts.append(f"Event page: {event.Source_Url}")
    parts.append("Source: U of I events calendar (Trumba)")
    return "\n".join(parts)


DESCRIPTION_MAX_CHARS = 600


def _flatten_description(description: str) -> str:
    """Collapse a feed description to one capped line for the label/value body.

    The body format is line-oriented ("Label: value"), so embedded newlines
    would be parsed as separate fields by the digest and calendar views.
    """
    flat = " ".join(description.split())
    if len(flat) <= DESCRIPTION_MAX_CHARS:
        return flat
    return flat[:DESCRIPTION_MAX_CHARS].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


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

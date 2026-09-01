"""Event Services (ops) triage over harvested external calendar events.

The ops lens answers a different question than the SLC lens: not "does this
event belong on a leadership calendar?" but "will this event create demands
on Event Services staff?" — catering, alcohol service, room setup, tabling,
outdoor space. People publish public events on the university calendar and
forget to tell Event Services what they expect; this lens surfaces those
events before the demands surface themselves.

Both lenses read the same HarvestedEvent rows; this module only ever touches
Ops_Review_Status and never reads or writes SLC review state, promotion, or
upstream-change bookkeeping.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.allowed_value import AllowedValue
from app.models.harvested_event import HarvestedEvent
from app.models.ops_need_assessment import OpsNeedAssessment
from app.services.ai.ops_needs_classifier import (
    assess_event,
    build_ops_classifier_provider,
)
from app.services.ai.provider import LLMProvider

logger = logging.getLogger(__name__)


async def list_ops_events(
    db: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    review_status: str | None = None,
    need: str | None = None,
    offset: int = 0,
    limit: int = 200,
) -> tuple[list[HarvestedEvent], int]:
    """List harvested events for the ops lens, ordered by start time.

    The category filter matches a Category_Path branch: "Student Affairs"
    matches both "Student Affairs" and "Student Affairs|Campus Recreation".
    The need filter keeps events with a suspected or confirmed assessment
    for that need (rejected doesn't count). Without an explicit
    review_status, ops-dismissed events are excluded so the default queue
    only shows events still worth looking at.
    """
    query = sa.select(HarvestedEvent)
    if need:
        query = query.where(
            sa.select(OpsNeedAssessment.Id)
            .where(
                OpsNeedAssessment.Harvested_Event_Id == HarvestedEvent.Id,
                OpsNeedAssessment.Need == need,
                OpsNeedAssessment.Verdict != "rejected",
            )
            .exists()
        )
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
        query = query.where(HarvestedEvent.Ops_Review_Status == review_status)
    else:
        query = query.where(HarvestedEvent.Ops_Review_Status != "dismissed")

    total = (
        await db.execute(sa.select(sa.func.count()).select_from(query.subquery()))
    ).scalar_one()

    query = query.order_by(
        HarvestedEvent.Event_Start, HarvestedEvent.Title
    ).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all()), total


@dataclass
class ClassificationSummary:
    """Outcome counts for one classify-pending run."""

    assessed: int = 0
    failed: int = 0
    pending: int = 0  # events still owed an assessment after this run


def _pending_filter():
    return sa.or_(
        HarvestedEvent.Ops_Assessed_Content_Hash.is_(None),
        HarvestedEvent.Ops_Assessed_Content_Hash != HarvestedEvent.Content_Hash,
    )


async def _need_codes(db: AsyncSession) -> list[str]:
    result = await db.execute(
        sa.select(AllowedValue.Code)
        .where(
            AllowedValue.Value_Group == "Ops_Need_Type",
            AllowedValue.Is_Active == True,  # noqa: E712
        )
        .order_by(AllowedValue.Display_Order)
    )
    return list(result.scalars().all())


async def _count_pending(db: AsyncSession) -> int:
    return (
        await db.execute(
            sa.select(sa.func.count())
            .select_from(HarvestedEvent)
            .where(_pending_filter())
        )
    ).scalar_one()


async def classify_pending_ops_events(
    db: AsyncSession,
    *,
    provider: LLMProvider | None = None,
    limit: int = 200,
) -> ClassificationSummary:
    """Assess events that are new or whose content changed since assessment.

    Each event is classified at most once per content version
    (Ops_Assessed_Content_Hash records what the assessment saw), and each
    success commits individually so progress survives interruption. A
    connectivity failure aborts the run — the platform is down, so there is
    no point burning the rest of the batch — while a malformed response
    skips just that event. Either way nothing is marked, so unassessed
    events are picked up on the next run. Never raises for classifier
    trouble; the harvest that invoked it must not fail.
    """
    summary = ClassificationSummary()
    need_codes = await _need_codes(db)
    if not need_codes:
        logger.warning("Ops_Need_Type vocabulary is empty; skipping classification")
        summary.pending = await _count_pending(db)
        return summary

    if provider is None:
        provider = build_ops_classifier_provider(settings)

    result = await db.execute(
        sa.select(HarvestedEvent)
        .where(_pending_filter())
        .order_by(HarvestedEvent.Event_Start)
        .limit(limit)
    )
    events = list(result.scalars().all())

    for event in events:
        try:
            suggestions = await assess_event(
                provider,
                title=event.Title,
                description=event.Description,
                location=event.Location,
                category_path=event.Category_Path,
                need_codes=need_codes,
            )
        except httpx.HTTPError as exc:
            logger.error("Ops classifier unreachable; aborting run: %s", exc)
            break
        except ValueError as exc:
            logger.warning(
                "Ops classifier returned malformed output for event %s: %s",
                event.Id,
                exc,
            )
            summary.failed += 1
            continue

        # Staff judgment survives re-assessment: any row that was confirmed,
        # rejected, or staff-added stays, and the classifier never resurrects
        # a need the reviewer already judged. Still-suggested rows update in
        # place (never delete-and-reinsert the same (event, need) key — the
        # unique constraint would trip inside one flush) or drop away when no
        # longer suggested.
        judged = {
            row.Need
            for row in event.Ops_Needs_Rel
            if row.Verdict != "suggested" or row.Source == "staff"
        }
        fresh = {
            suggestion.need: suggestion
            for suggestion in suggestions
            if suggestion.need not in judged
        }
        for row in list(event.Ops_Needs_Rel):
            if row.Need in judged:
                continue
            suggestion = fresh.pop(row.Need, None)
            if suggestion is None:
                event.Ops_Needs_Rel.remove(row)
            else:
                row.Confidence = suggestion.confidence
                row.Rationale = suggestion.rationale
        event.Ops_Needs_Rel.extend(
            OpsNeedAssessment(
                Need=suggestion.need,
                Confidence=suggestion.confidence,
                Rationale=suggestion.rationale,
            )
            for suggestion in fresh.values()
        )
        event.Ops_Assessed_Content_Hash = event.Content_Hash
        await db.commit()
        summary.assessed += 1

    summary.pending = await _count_pending(db)
    return summary


async def set_ops_review_status(
    db: AsyncSession,
    harvested_event_id: str,
    *,
    status: str,
) -> HarvestedEvent | None:
    """Apply an ops triage decision to a harvested event. Idempotent.

    Unlike the SLC lens's set_review_status, no transition has side effects:
    the ops lens promotes nothing and keeps no per-lens bookkeeping yet, so
    this only moves Ops_Review_Status. Returns None when the event does not
    exist.
    """
    event = await db.get(HarvestedEvent, harvested_event_id)
    if event is None:
        return None
    event.Ops_Review_Status = status
    await db.commit()
    await db.refresh(event)
    return event


async def set_need_verdict(
    db: AsyncSession,
    harvested_event_id: str,
    need: str,
    *,
    verdict: str,
) -> HarvestedEvent | None:
    """Record Event Services' judgment on one assessed need. Idempotent.

    Returns None when the event or the need's assessment row does not exist.
    """
    event = await db.get(HarvestedEvent, harvested_event_id)
    if event is None:
        return None
    row = next((r for r in event.Ops_Needs_Rel if r.Need == need), None)
    if row is None:
        return None
    row.Verdict = verdict
    await db.commit()
    await db.refresh(event)
    return event


async def add_staff_need(
    db: AsyncSession,
    harvested_event_id: str,
    need: str,
) -> HarvestedEvent | None:
    """Add a need the AI missed, entering as confirmed with staff provenance.

    Adding a need that already has an assessment row (suggested or rejected)
    confirms that row instead of duplicating it. Raises ValueError for a
    need outside the Ops_Need_Type vocabulary; returns None when the event
    does not exist.
    """
    if need not in await _need_codes(db):
        raise ValueError(f"Unknown ops need type: {need}")
    event = await db.get(HarvestedEvent, harvested_event_id)
    if event is None:
        return None
    row = next((r for r in event.Ops_Needs_Rel if r.Need == need), None)
    if row is not None:
        row.Verdict = "confirmed"
    else:
        event.Ops_Needs_Rel.append(
            OpsNeedAssessment(
                Need=need,
                Confidence=None,
                Rationale="",
                Verdict="confirmed",
                Source="staff",
            )
        )
    await db.commit()
    await db.refresh(event)
    return event


async def remove_staff_need(
    db: AsyncSession,
    harvested_event_id: str,
    need: str,
) -> tuple[HarvestedEvent | None, str]:
    """Remove a staff-added need row. AI suggestions are rejected, not removed.

    Returns (event, outcome) where outcome is "removed", "not_staff", or
    "not_found".
    """
    event = await db.get(HarvestedEvent, harvested_event_id)
    if event is None:
        return None, "not_found"
    row = next((r for r in event.Ops_Needs_Rel if r.Need == need), None)
    if row is None:
        return None, "not_found"
    if row.Source != "staff":
        return event, "not_staff"
    event.Ops_Needs_Rel.remove(row)
    await db.commit()
    await db.refresh(event)
    return event, "removed"

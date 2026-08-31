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

from datetime import date, datetime, time

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.harvested_event import HarvestedEvent


async def list_ops_events(
    db: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    review_status: str | None = None,
    offset: int = 0,
    limit: int = 200,
) -> tuple[list[HarvestedEvent], int]:
    """List harvested events for the ops lens, ordered by start time.

    The category filter matches a Category_Path branch: "Student Affairs"
    matches both "Student Affairs" and "Student Affairs|Campus Recreation".
    Without an explicit review_status, ops-dismissed events are excluded so
    the default queue only shows events still worth looking at.
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

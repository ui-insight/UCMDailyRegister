"""Event Services (ops) triage endpoints for harvested calendar events.

Limited to the trusted staff and ops roles: the ops lens exists so Event
Services can spot operational demands (catering, alcohol service, room
setup, tabling, outdoor space) hiding in publicly scheduled events, and is
not part of the public submission surface.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SubmitterRole, get_db, require_staff_or_ops
from app.schemas.harvested_event import OpsEventListResponse, OpsEventResponse
from app.services import ops_event_service

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/harvested-events", response_model=OpsEventListResponse)
async def list_ops_events(
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    review_status: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    submitter_role: SubmitterRole = Depends(require_staff_or_ops),
):
    """List harvested events through the ops lens, ordered by start time."""
    items, total = await ops_event_service.list_ops_events(
        db,
        date_from=date_from,
        date_to=date_to,
        category=category,
        review_status=review_status,
        offset=offset,
        limit=limit,
    )
    return OpsEventListResponse(
        Items=[OpsEventResponse.model_validate(item) for item in items],
        Total=total,
    )

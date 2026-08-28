"""SLC triage endpoints for harvested external calendar events.

Both endpoints are limited to the trusted staff and slc roles: harvested
events feed the Senior Leadership Council triage workflow and are not part
of the public submission surface.
"""

from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SubmitterRole, get_db, require_staff_or_slc
from app.schemas.harvested_event import (
    HarvestedEventListResponse,
    HarvestedEventResponse,
    HarvestSummaryResponse,
)
from app.services import harvested_event_service

router = APIRouter(prefix="/slc", tags=["slc"])


@router.post("/harvest", response_model=HarvestSummaryResponse)
async def harvest_events(
    db: AsyncSession = Depends(get_db),
    submitter_role: SubmitterRole = Depends(require_staff_or_slc),
):
    """Fetch the Trumba feed and upsert its events. Safe to re-run."""
    try:
        summary = await harvested_event_service.harvest_trumba_events(db)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not fetch the university events feed. Try again shortly.",
        ) from exc
    return HarvestSummaryResponse(
        Fetched=summary.fetched,
        Created=summary.created,
        Updated=summary.updated,
        Unchanged=summary.unchanged,
        Skipped=summary.skipped,
    )


@router.get("/harvested-events", response_model=HarvestedEventListResponse)
async def list_harvested_events(
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    review_status: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    submitter_role: SubmitterRole = Depends(require_staff_or_slc),
):
    """List harvested events, ordered by start time."""
    items, total = await harvested_event_service.list_harvested_events(
        db,
        date_from=date_from,
        date_to=date_to,
        category=category,
        review_status=review_status,
        offset=offset,
        limit=limit,
    )
    return HarvestedEventListResponse(
        Items=[HarvestedEventResponse.model_validate(item) for item in items],
        Total=total,
    )

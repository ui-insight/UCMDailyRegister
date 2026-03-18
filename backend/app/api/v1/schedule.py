"""Schedule config and publication calendar API endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services import schedule_service
from app.schemas.newsletter import (
    BlackoutDateCreate,
    BlackoutDateResponse,
    ScheduleConfigResponse,
    ValidDatesResponse,
    ValidPublicationDate,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/configs", response_model=list[ScheduleConfigResponse])
async def list_configs(
    newsletter_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all schedule configurations."""
    return await schedule_service.list_configs(db, newsletter_type)


@router.get("/active")
async def get_active_config(
    newsletter_type: str,
    for_date: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get the currently active schedule config for a newsletter type."""
    config = await schedule_service.get_active_config(db, newsletter_type, for_date)
    if not config:
        raise HTTPException(status_code=404, detail="No active schedule config found")

    publish_date = schedule_service.get_next_publish_date(config, for_date or date.today())
    deadline = schedule_service.get_submission_deadline(config, publish_date)

    return {
        "config": ScheduleConfigResponse.model_validate(config),
        "next_publish_date": publish_date.isoformat(),
        "submission_deadline": deadline.isoformat(),
    }


@router.get("/valid-dates", response_model=ValidDatesResponse)
async def get_valid_dates(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    newsletter_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return valid publication dates in a range, respecting schedule config and blackouts."""
    if (to_date - from_date).days > 366:
        raise HTTPException(status_code=400, detail="Date range cannot exceed one year")

    valid = await schedule_service.get_valid_publication_dates(
        db, from_date, to_date, newsletter_type
    )
    blackouts = await schedule_service.list_blackout_dates(
        db, newsletter_type=newsletter_type, from_date=from_date, to_date=to_date
    )
    return ValidDatesResponse(
        dates=[ValidPublicationDate(**d) for d in valid],
        blackout_dates=[BlackoutDateResponse.model_validate(b) for b in blackouts],
    )


@router.get("/blackout-dates", response_model=list[BlackoutDateResponse])
async def list_blackout_dates(
    newsletter_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all active blackout dates."""
    return await schedule_service.list_blackout_dates(db, newsletter_type=newsletter_type)


@router.post("/blackout-dates", response_model=BlackoutDateResponse, status_code=201)
async def create_blackout_date(
    data: BlackoutDateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new blackout date."""
    return await schedule_service.create_blackout_date(db, data)


@router.delete("/blackout-dates/{blackout_id}", status_code=204)
async def delete_blackout_date(
    blackout_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a blackout date."""
    deleted = await schedule_service.delete_blackout_date(db, blackout_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Blackout date not found")

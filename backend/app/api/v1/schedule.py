"""Schedule config and publication calendar API endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services import schedule_service
from app.schemas.newsletter import (
    BlackoutDateCreate,
    BlackoutDateResponse,
    CustomPublishDateCreate,
    CustomPublishDateResponse,
    ScheduleConfigResponse,
    ScheduleModeOverrideCreate,
    ScheduleModeOverrideResponse,
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

    # Include override info if active
    override = await schedule_service.get_active_override(db, newsletter_type, for_date)

    return {
        "config": ScheduleConfigResponse.model_validate(config),
        "next_publish_date": publish_date.isoformat(),
        "submission_deadline": deadline.isoformat(),
        "active_override": (
            ScheduleModeOverrideResponse.model_validate(override)
            if override
            else None
        ),
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


# ---------------------------------------------------------------------------
# Blackout dates
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Mode overrides
# ---------------------------------------------------------------------------


@router.get("/mode-overrides", response_model=list[ScheduleModeOverrideResponse])
async def list_mode_overrides(
    newsletter_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all schedule mode overrides."""
    return await schedule_service.list_mode_overrides(db, newsletter_type)


@router.post("/mode-overrides", response_model=ScheduleModeOverrideResponse, status_code=201)
async def create_mode_override(
    data: ScheduleModeOverrideCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a schedule mode override (e.g., activate winter break for a date range)."""
    if data.End_Date < data.Start_Date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    return await schedule_service.create_mode_override(
        db,
        newsletter_type=data.Newsletter_Type,
        override_mode=data.Override_Mode,
        start_date=data.Start_Date,
        end_date=data.End_Date,
        description=data.Description,
    )


@router.delete("/mode-overrides/{override_id}", status_code=204)
async def delete_mode_override(
    override_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a schedule mode override."""
    deleted = await schedule_service.delete_mode_override(db, override_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mode override not found")


# ---------------------------------------------------------------------------
# Custom publish dates
# ---------------------------------------------------------------------------


@router.get("/custom-dates", response_model=list[CustomPublishDateResponse])
async def list_custom_dates(
    newsletter_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all custom publish dates (used during winter break)."""
    return await schedule_service.list_custom_publish_dates(db, newsletter_type)


@router.post("/custom-dates", response_model=CustomPublishDateResponse, status_code=201)
async def create_custom_date(
    data: CustomPublishDateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a custom publish date (e.g., for winter break editions)."""
    return await schedule_service.create_custom_publish_date(
        db,
        newsletter_type=data.Newsletter_Type,
        publish_date=data.Publish_Date,
        description=data.Description,
    )


@router.delete("/custom-dates/{custom_date_id}", status_code=204)
async def delete_custom_date(
    custom_date_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom publish date."""
    deleted = await schedule_service.delete_custom_publish_date(db, custom_date_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Custom publish date not found")

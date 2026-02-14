"""Schedule config API endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services import schedule_service
from app.schemas.newsletter import ScheduleConfigResponse

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

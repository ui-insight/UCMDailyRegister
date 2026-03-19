"""Read-only API endpoint for the AllowedValue controlled vocabulary."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SubmitterRole, get_db, get_submitter_role
from app.schemas.allowed_value import AllowedValueResponse
from app.services import allowed_value_service

router = APIRouter(prefix="/allowed-values", tags=["allowed-values"])


@router.get("", response_model=list[AllowedValueResponse])
async def list_allowed_values(
    group: str | None = Query(None, description="Filter by Value_Group"),
    active_only: bool = Query(True, description="Only return active values"),
    db: AsyncSession = Depends(get_db),
    submission_role: SubmitterRole = Depends(get_submitter_role),
):
    """List allowed values, optionally filtered by group."""
    return await allowed_value_service.list_allowed_values(
        db,
        group=group,
        active_only=active_only,
        submission_role=submission_role,
    )

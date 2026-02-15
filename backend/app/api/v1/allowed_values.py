"""Read-only API endpoint for the AllowedValue controlled vocabulary."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.allowed_value import AllowedValue
from app.schemas.allowed_value import AllowedValueResponse

router = APIRouter(prefix="/allowed-values", tags=["allowed-values"])


@router.get("", response_model=list[AllowedValueResponse])
async def list_allowed_values(
    group: str | None = Query(None, description="Filter by Value_Group"),
    active_only: bool = Query(True, description="Only return active values"),
    db: AsyncSession = Depends(get_db),
):
    """List allowed values, optionally filtered by group."""
    query = sa.select(AllowedValue).order_by(
        AllowedValue.Value_Group, AllowedValue.Display_Order
    )
    if group:
        query = query.where(AllowedValue.Value_Group == group)
    if active_only:
        query = query.where(AllowedValue.Is_Active == True)  # noqa: E712
    result = await db.execute(query)
    return result.scalars().all()

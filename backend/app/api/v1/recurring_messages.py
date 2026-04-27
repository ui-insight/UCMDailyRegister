"""Recurring message CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_staff
from app.schemas.recurring_message import (
    RecurringMessageCreate,
    RecurringMessageResponse,
    RecurringMessageUpdate,
)
from app.services import recurring_message_service

router = APIRouter(prefix="/recurring-messages", tags=["recurring-messages"])


@router.get("", response_model=list[RecurringMessageResponse])
async def list_recurring_messages(
    newsletter_type: str | None = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """List recurring messages."""
    return await recurring_message_service.list_recurring_messages(
        db,
        newsletter_type=newsletter_type,
        active_only=active_only,
    )


@router.post("", response_model=RecurringMessageResponse, status_code=201)
async def create_recurring_message(
    data: RecurringMessageCreate,
    db: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """Create a recurring message."""
    try:
        return await recurring_message_service.create_recurring_message(
            db,
            newsletter_type=data.Newsletter_Type,
            section_id=data.Section_Id,
            headline=data.Headline,
            body=data.Body,
            start_date=data.Start_Date,
            recurrence_type=data.Recurrence_Type,
            recurrence_interval=data.Recurrence_Interval,
            end_date=data.End_Date,
            excluded_dates=data.Excluded_Dates,
            is_active=data.Is_Active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{recurring_message_id}", response_model=RecurringMessageResponse)
async def get_recurring_message(
    recurring_message_id: str,
    db: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """Get a recurring message."""
    message = await recurring_message_service.get_recurring_message(db, recurring_message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Recurring message not found")
    return message


@router.patch("/{recurring_message_id}", response_model=RecurringMessageResponse)
async def update_recurring_message(
    recurring_message_id: str,
    data: RecurringMessageUpdate,
    db: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """Update a recurring message."""
    try:
        message = await recurring_message_service.update_recurring_message(
            db,
            recurring_message_id,
            **data.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not message:
        raise HTTPException(status_code=404, detail="Recurring message not found")
    return message


@router.delete("/{recurring_message_id}", status_code=204)
async def delete_recurring_message(
    recurring_message_id: str,
    db: AsyncSession = Depends(get_db),
    _staff: None = Depends(require_staff),
):
    """Delete a recurring message."""
    if not await recurring_message_service.delete_recurring_message(db, recurring_message_id):
        raise HTTPException(status_code=404, detail="Recurring message not found")

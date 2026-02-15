"""Style rules CRUD API endpoints."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.style_rule import StyleRule
from app.schemas.ai_edit import StyleRuleCreate, StyleRuleUpdate, StyleRuleResponse

router = APIRouter(prefix="/style-rules", tags=["style-rules"])


@router.get("", response_model=list[StyleRuleResponse])
async def list_style_rules(
    rule_set: str | None = None,
    category: str | None = None,
    active_only: bool = False,
    session: AsyncSession = Depends(get_db),
):
    """List style rules, optionally filtered by rule_set, category, or active status."""
    query = sa.select(StyleRule).order_by(StyleRule.Rule_Set, StyleRule.Category, StyleRule.Rule_Key)
    if rule_set:
        query = query.where(StyleRule.Rule_Set == rule_set)
    if category:
        query = query.where(StyleRule.Category == category)
    if active_only:
        query = query.where(StyleRule.Is_Active == True)  # noqa: E712
    result = await session.execute(query)
    return result.scalars().all()


@router.post("", response_model=StyleRuleResponse, status_code=201)
async def create_style_rule(
    data: StyleRuleCreate,
    session: AsyncSession = Depends(get_db),
):
    """Create a new style rule."""
    rule = StyleRule(
        Rule_Set=data.Rule_Set,
        Category=data.Category,
        Rule_Key=data.Rule_Key,
        Rule_Text=data.Rule_Text,
        Severity=data.Severity,
        Is_Active=True,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=StyleRuleResponse)
async def get_style_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get a single style rule."""
    result = await session.execute(
        sa.select(StyleRule).where(StyleRule.Id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Style rule not found")
    return rule


@router.patch("/{rule_id}", response_model=StyleRuleResponse)
async def update_style_rule(
    rule_id: str,
    data: StyleRuleUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Update a style rule."""
    result = await session.execute(
        sa.select(StyleRule).where(StyleRule.Id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Style rule not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    await session.commit()
    await session.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_style_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Delete a style rule."""
    result = await session.execute(
        sa.select(StyleRule).where(StyleRule.Id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Style rule not found")
    await session.delete(rule)
    await session.commit()

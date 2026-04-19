"""Helpers for controlled-vocabulary lookups and visibility checks."""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SubmitterRole
from app.models.allowed_value import AllowedValue


def _submission_category_visibility_filter(submission_role: SubmitterRole):
    if submission_role == "staff":
        return sa.true()
    return sa.or_(
        AllowedValue.Value_Group != "Submission_Category",
        AllowedValue.Visibility_Role == "public",
        AllowedValue.Visibility_Role == submission_role,
    )


async def list_allowed_values(
    db: AsyncSession,
    group: str | None = None,
    active_only: bool = True,
    submission_role: SubmitterRole = "public",
) -> list[AllowedValue]:
    query = sa.select(AllowedValue).order_by(
        AllowedValue.Value_Group, AllowedValue.Display_Order
    )
    if group:
        query = query.where(AllowedValue.Value_Group == group)
    if active_only:
        query = query.where(AllowedValue.Is_Active == True)  # noqa: E712
    query = query.where(_submission_category_visibility_filter(submission_role))
    result = await db.execute(query)
    return list(result.scalars().all())


async def is_submission_category_allowed(
    db: AsyncSession,
    category_code: str,
    submission_role: SubmitterRole = "public",
) -> bool:
    query = sa.select(AllowedValue.Id).where(
        AllowedValue.Value_Group == "Submission_Category",
        AllowedValue.Code == category_code,
        AllowedValue.Is_Active == True,  # noqa: E712
    )
    if submission_role != "staff":
        query = query.where(
            sa.or_(
                AllowedValue.Visibility_Role == "public",
                AllowedValue.Visibility_Role == submission_role,
            )
        )
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None

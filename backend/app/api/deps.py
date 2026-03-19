from collections.abc import AsyncGenerator
from typing import Literal, cast

from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import async_session_factory

SubmitterRole = Literal["public", "staff"]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_submitter_role(
    x_user_role: str | None = Header(None, alias="X-User-Role"),
) -> SubmitterRole:
    if x_user_role and x_user_role.lower() == "staff":
        return cast(SubmitterRole, "staff")
    return cast(SubmitterRole, "public")

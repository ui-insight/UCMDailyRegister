from collections.abc import AsyncGenerator
from typing import Literal, cast

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.engine import async_session_factory

SubmitterRole = Literal["public", "staff", "slc"]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_submitter_role(
    x_user_role: str | None = Header(None, alias="X-User-Role"),
    x_trusted_user_role: str | None = Header(None, alias="X-Trusted-User-Role"),
    x_trusted_auth_secret: str | None = Header(None, alias="X-Trusted-Auth-Secret"),
) -> SubmitterRole:
    if x_user_role:
        raise HTTPException(
            status_code=400,
            detail="X-User-Role is not accepted; user role must come from the trusted auth boundary.",
        )

    if x_trusted_user_role:
        if not settings.trusted_role_header_secret:
            raise HTTPException(status_code=403, detail="Trusted role headers are not configured.")
        if x_trusted_auth_secret != settings.trusted_role_header_secret:
            raise HTTPException(status_code=403, detail="Trusted role header verification failed.")

        normalized = x_trusted_user_role.lower()
        if normalized in ("staff", "slc"):
            return cast(SubmitterRole, normalized)

    return cast(SubmitterRole, "public")


async def require_staff(
    submitter_role: SubmitterRole = Depends(get_submitter_role),
) -> SubmitterRole:
    if submitter_role != "staff":
        raise HTTPException(
            status_code=403,
            detail="This action is available to staff editors only.",
        )
    return submitter_role

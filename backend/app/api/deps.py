from collections.abc import AsyncGenerator
from typing import Literal, cast

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.identity import TokenIdentity
from app.auth.session_tokens import decode_session_token
from app.config import settings
from app.db.engine import async_session_factory

SubmitterRole = Literal["public", "staff", "slc", "ops"]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip() or None


async def get_current_identity(
    authorization: str | None = Header(None),
) -> TokenIdentity | None:
    """Resolve the bearer session token, if one was sent.

    `None` means no token at all. A token that is present but invalid or
    expired is a 401, never a fall-through to "public": an expired staff
    session must surface as "sign in again", not as a silent downgrade that
    turns the next save into a 403.
    """
    token = _bearer_token(authorization)
    if token is None:
        return None
    return decode_session_token(token)


async def require_identity(
    identity: TokenIdentity | None = Depends(get_current_identity),
) -> TokenIdentity:
    if identity is None:
        raise HTTPException(
            status_code=401,
            detail="Sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return identity


async def get_submitter_role(
    identity: TokenIdentity | None = Depends(get_current_identity),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
    x_trusted_user_role: str | None = Header(None, alias="X-Trusted-User-Role"),
    x_trusted_auth_secret: str | None = Header(None, alias="X-Trusted-Auth-Secret"),
) -> SubmitterRole:
    """Resolve the caller's role from whichever auth path presented one.

    A session token minted by SSO wins over the proxy header, so a signed-in
    SLC member on a prototype deployment that still stamps every request as
    staff is treated as SLC. Neither path present means an anonymous
    submitter.
    """
    if x_user_role:
        raise HTTPException(
            status_code=400,
            detail="X-User-Role is not accepted; user role must come from the trusted auth boundary.",
        )

    if identity is not None:
        return cast(SubmitterRole, identity.role)

    if x_trusted_user_role:
        if not settings.trusted_role_header_secret:
            raise HTTPException(status_code=403, detail="Trusted role headers are not configured.")
        if x_trusted_auth_secret != settings.trusted_role_header_secret:
            raise HTTPException(status_code=403, detail="Trusted role header verification failed.")

        normalized = x_trusted_user_role.lower()
        if normalized in ("staff", "slc", "ops"):
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


async def require_staff_or_slc(
    submitter_role: SubmitterRole = Depends(get_submitter_role),
) -> SubmitterRole:
    if submitter_role not in ("staff", "slc"):
        raise HTTPException(
            status_code=403,
            detail="This action is only available to authorized SLC viewers and staff.",
        )
    return submitter_role


async def require_staff_or_ops(
    submitter_role: SubmitterRole = Depends(get_submitter_role),
) -> SubmitterRole:
    if submitter_role not in ("staff", "ops"):
        raise HTTPException(
            status_code=403,
            detail="This action is only available to Event Services and staff.",
        )
    return submitter_role

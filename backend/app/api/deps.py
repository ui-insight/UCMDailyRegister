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

    Tokens count only under AUTH_PROVIDER=oidc. Header mode skips the
    SECRET_KEY strength checks, so a header-mode deployment usually still
    signs with the public default key; honoring tokens there would let
    anyone mint a staff session.
    """
    if settings.auth_provider != "oidc":
        return None
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
    """Resolve the caller's role from the active AUTH_PROVIDER's credential.

    Each mode accepts only its own credential: header mode the proxy-asserted
    role, oidc mode the SSO session token. Under oidc a proxy that still
    stamps every request as staff must not grant staff to anonymous
    visitors. No credential means an anonymous submitter.
    """
    if x_user_role:
        raise HTTPException(
            status_code=400,
            detail="X-User-Role is not accepted; user role must come from the trusted auth boundary.",
        )

    if identity is not None:
        return cast(SubmitterRole, identity.role)

    if settings.auth_provider == "header" and x_trusted_user_role:
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

"""Auth endpoints that exist under every AUTH_PROVIDER.

The Entra sign-in routes themselves live in `app.api.v1.sso` and are mounted
only when `AUTH_PROVIDER=oidc`.
"""

from fastapi import APIRouter, Depends

from app.api.deps import require_identity
from app.auth.identity import TokenIdentity
from app.config import settings
from app.schemas.auth import AuthConfig, CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfig)
async def get_auth_config() -> AuthConfig:
    """Report whether this deployment signs users in through Entra.

    Deliberately unauthenticated: the landing page reads it before anyone
    has a token. Runtime rather than a build-time flag, so switching a
    deployment to SSO is a backend redeploy, not a frontend rebuild.
    """
    return AuthConfig(sso_enabled=settings.auth_provider == "oidc")


@router.get("/me", response_model=CurrentUser)
async def get_current_user(identity: TokenIdentity = Depends(require_identity)) -> CurrentUser:
    """Return the identity behind the caller's session token."""
    return CurrentUser(subject=identity.subject, name=identity.name, role=identity.role)

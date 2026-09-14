from pydantic import BaseModel

from app.auth.identity import SignedInRole


class AuthConfig(BaseModel):
    """Which sign-in this deployment offers. Read by the login screen, unauthenticated."""

    sso_enabled: bool


class CurrentUser(BaseModel):
    """The signed-in identity, as carried by the bearer session token."""

    subject: str
    name: str
    role: SignedInRole

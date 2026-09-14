"""The identity carried by a verified session token."""

from typing import Literal

from pydantic import BaseModel

# Roles a signed-in user can hold. Deliberately excludes "public": anonymous
# submitters never sign in, so a session token always names a real role.
SignedInRole = Literal["staff", "slc", "ops"]


class TokenIdentity(BaseModel):
    """Identity resolved from a verified bearer token."""

    subject: str
    role: SignedInRole
    name: str

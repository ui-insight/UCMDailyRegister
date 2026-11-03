"""The identity carried by a verified session token."""

from typing import Literal

from pydantic import BaseModel

# Roles a signed-in user can hold. Any University account that signs in
# without a UCM role is a "submitter": it may submit items and nothing more,
# so for authorization it is treated exactly like the old anonymous "public"
# role (see app.api.deps). "public" itself never appears in a token.
SignedInRole = Literal["staff", "slc", "ops", "submitter"]


class TokenIdentity(BaseModel):
    """Identity resolved from a verified bearer token."""

    subject: str
    role: SignedInRole
    name: str

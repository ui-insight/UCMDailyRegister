"""The identity carried by a verified session token."""

from typing import Literal

from pydantic import BaseModel

# Roles a signed-in user can hold. Any University account that signs in
# without a UCM role is a "submitter": it may submit items and nothing more,
# so for authorization it is treated exactly like the old anonymous "public"
# role (see app.api.deps). "public" itself never appears in a token.
SignedInRole = Literal["staff", "slc", "ops", "submitter"]


class TokenIdentity(BaseModel):
    """Identity resolved from a verified bearer token.

    `object_id` is the Microsoft Entra object ID (`oid`) of the signed-in
    account. It is the actor reference written to the audit trail
    (`app.services.audit`) in place of an email address. Tokens minted before
    the claim existed decode with `None`, and their requests audit with a
    null actor reference plus the role.
    """

    subject: str
    role: SignedInRole
    name: str
    object_id: str | None = None

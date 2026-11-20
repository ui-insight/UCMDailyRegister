"""Append-only per-user audit trail of API access, changes and sign-ins.

Staff routes authorize by role, so before this table nothing recorded which
person read, changed, deleted or exported a record. Each row answers "who did
what to which record, and was it allowed" for a security or records review
(APM 30.11 / OIT review finding). Rows are written by the HTTP audit middleware
(`app.api.audit_middleware`) after the response, and by the SSO callback for
sign-in outcomes, each in its own database session so an audit row survives a
request that rolls back.

The actor reference is the Microsoft Entra object ID (`oid`) carried in the
app's session token, never an email address, name or group list. Authorized
Entra administrators can resolve an object ID to an account when a review
needs it; the table alone does not name anyone. Header-mode and local
deployments have no identity, and sessions minted before the `oid` claim
existed carry none, so Actor_Ref is null there and only Actor_Role is known.

Rows deliberately hold no content: no request or response bodies, field
values, query strings, raw URLs, IP addresses or user agents. Route_Template
is the declared FastAPI path (`/api/v1/submissions/{submission_id}`),
Record_Ids holds only the opaque path-parameter values, and Changed_Fields
holds only the top-level JSON body keys of a write. Event_Type and
Reason_Code are code-validated discriminators (see `app.services.audit`).

There is no API to update or delete rows, and no retention job: no disposal
process is approved for this data. See `docs/audit-logging.md`.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    """One audited API request or sign-in outcome."""

    __tablename__ = "audit_events"

    Id: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Occurred_At: Mapped[datetime] = mapped_column(sa.DateTime, nullable=False, index=True)
    Actor_Ref: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, index=True)
    Actor_Role: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    Event_Type: Mapped[str] = mapped_column(sa.String(40), nullable=False, index=True)
    Reason_Code: Mapped[str | None] = mapped_column(sa.String(40), nullable=True)
    Http_Method: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    Route_Template: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    Record_Ids: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    Changed_Fields: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    Status_Code: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

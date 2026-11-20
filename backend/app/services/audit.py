"""Write append-only audit events (`app.models.audit_event.AuditEvent`).

Every write opens its own short session from `audit_session_factory`, so an
audit row commits independently of the request it describes. A failed write
is logged by exception class name only and never surfaces to the caller:
the audit trail must not take the application down with it.

Event types and reason codes are fixed here rather than in AllowedValue
because the code, not staff, decides what is audited.
"""

import logging
from datetime import UTC, datetime

from app.db.engine import async_session_factory
from app.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)

# Tests point this at their own database; read at call time, not import time.
audit_session_factory = async_session_factory

EVENT_RECORD_READ = "record_read"
EVENT_RECORD_EXPORT = "record_export"
EVENT_RECORD_CHANGE = "record_change"
EVENT_RECORD_DELETE = "record_delete"
EVENT_AUTHORIZATION_FAILURE = "authorization_failure"
EVENT_SIGN_IN_SUCCESS = "sign_in_success"
EVENT_SIGN_IN_FAILURE = "sign_in_failure"

REASON_UNAUTHENTICATED = "unauthenticated"
REASON_FORBIDDEN = "forbidden"

SIGN_IN_ROUTE = "/api/v1/auth/callback"


async def record_audit_event(
    *,
    event_type: str,
    actor_role: str,
    http_method: str,
    route_template: str,
    actor_ref: str | None = None,
    reason_code: str | None = None,
    record_ids: dict[str, str] | None = None,
    changed_fields: list[str] | None = None,
    status_code: int | None = None,
) -> None:
    """Append one audit row; swallow and minimally log any failure."""
    try:
        async with audit_session_factory() as session:
            session.add(
                AuditEvent(
                    Occurred_At=datetime.now(UTC).replace(tzinfo=None),
                    Actor_Ref=actor_ref,
                    Actor_Role=actor_role,
                    Event_Type=event_type,
                    Reason_Code=reason_code,
                    Http_Method=http_method,
                    Route_Template=route_template,
                    Record_Ids=record_ids or None,
                    Changed_Fields=changed_fields,
                    Status_Code=status_code,
                )
            )
            await session.commit()
    except Exception as exc:  # the audit write must never fail a request
        logger.error("Audit event write failed error_type=%s", type(exc).__name__)


async def record_sign_in(
    *, succeeded: bool, actor_ref: str | None, actor_role: str, reason_code: str | None = None
) -> None:
    """Record the outcome of an Entra sign-in from the SSO callback."""
    await record_audit_event(
        event_type=EVENT_SIGN_IN_SUCCESS if succeeded else EVENT_SIGN_IN_FAILURE,
        actor_ref=actor_ref,
        actor_role=actor_role,
        reason_code=reason_code,
        http_method="GET",
        route_template=SIGN_IN_ROUTE,
    )

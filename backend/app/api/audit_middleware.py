"""ASGI middleware that writes the per-user audit trail for `/api/v1/*`.

After each matched API request it records one `AuditEvent` when:

- the method changes state (anything but GET/HEAD/OPTIONS), whoever called;
- a signed-in privileged role (staff, slc, ops) read a record (GET) - the
  read and export trail;
- the response is 401 or 403, with the caller's role.

Health/readiness probes and the SSO redirects are never recorded; the SSO
callback records its own sign-in outcome. Requests that match no route are
skipped, so scanners cannot fill the table and no raw path is ever stored.

The caller is resolved the same way `app.api.deps` resolves it - the session
token under AUTH_PROVIDER=oidc, the verified trusted-role header in header
mode - but without failing: an invalid token is audited as "public". Only the
route template, path-parameter values shaped like record IDs (UUIDs or
integers) and top-level JSON body keys that the route's request schema
declares are kept. Anything else a caller typed into a path or body key is
dropped, so an email in a URL or a free-text key cannot reach the table.
Body values, query strings, headers and client addresses are not kept.

A pure ASGI middleware rather than `BaseHTTPMiddleware`, so responses stream
through untouched and the route FastAPI matched is visible in the scope.
"""

import hmac
import json
import re
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from app.auth.session_tokens import decode_session_token
from app.config import settings
from app.services import audit

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

API_PREFIX = "/api/v1/"
READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
PRIVILEGED_ROLES = frozenset({"staff", "slc", "ops"})

# Never audited: probes, and the sign-in redirects (the callback writes its
# own sign-in event; login/logout/config are anonymous by design).
EXCLUDED_ROUTES = frozenset({
    "/api/v1/health",
    "/api/v1/readyz",
    "/api/v1/auth/config",
    "/api/v1/auth/sso/login",
    "/api/v1/auth/callback",
    "/api/v1/auth/logout",
})
# A privileged user reading their own session is not a record read. Its
# 401s are still audited as authorization failures.
NON_RECORD_READS = frozenset({"/api/v1/auth/me"})

# Bodies larger than this are not inspected for keys; the event is still
# recorded, with Changed_Fields left null.
MAX_BODY_BYTES = 256 * 1024
MAX_FIELDS = 64
# Record IDs in this app are UUIDs (most tables) or integers. A path value of
# any other shape is caller-typed text - possibly an email or copy - and is
# not stored.
_RECORD_ID = re.compile(
    r"^(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[0-9]{1,18})$"
)


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", ()):
        if key == name:
            return value.decode("latin-1")
    return None


def _resolve_actor(scope: Scope) -> tuple[str | None, str]:
    """Return (actor reference, role) for the caller without raising."""
    if settings.auth_provider == "oidc":
        authorization = _header(scope, b"authorization") or ""
        if not authorization.lower().startswith("bearer "):
            return None, "public"
        token = authorization.split(" ", 1)[1].strip()
        if not token:
            return None, "public"
        try:
            identity = decode_session_token(token)
        except HTTPException:
            return None, "public"
        return identity.object_id, identity.role

    claimed = (_header(scope, b"x-trusted-user-role") or "").lower()
    secret = settings.trusted_role_header_secret
    supplied = _header(scope, b"x-trusted-auth-secret") or ""
    if (
        claimed in PRIVILEGED_ROLES
        and secret
        and hmac.compare_digest(supplied.encode(), secret.encode())
    ):
        return None, claimed
    return None, "public"


def _schema_fields(route: object) -> frozenset[str]:
    """Body field names (and aliases) the route's request schema declares.

    Body keys are caller-supplied text. Only a key the route's own Pydantic
    schema names is known to be a field name rather than smuggled content.
    """
    dependant = getattr(route, "dependant", None)
    names: set[str] = set()
    for param in getattr(dependant, "body_params", None) or ():
        annotation = getattr(getattr(param, "field_info", None), "annotation", None)
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            for name, field in annotation.model_fields.items():
                names.add(name)
                if field.alias:
                    names.add(field.alias)
        else:
            names.add(param.name)
    return frozenset(names)


def _changed_fields(body: bytes | None, allowed: frozenset[str]) -> list[str] | None:
    if not body or not allowed:
        return None
    try:
        parsed = json.loads(body)
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    return [key for key in parsed if key in allowed][:MAX_FIELDS]


def _record_ids(scope: Scope) -> dict[str, str] | None:
    params = scope.get("path_params") or {}
    ids = {
        str(name): str(value)
        for name, value in params.items()
        if _RECORD_ID.match(str(value))
    }
    return ids or None


def _event_type(method: str, status: int, role: str, template: str) -> str | None:
    if status in (401, 403):
        return audit.EVENT_AUTHORIZATION_FAILURE
    if method == "DELETE":
        return audit.EVENT_RECORD_DELETE
    if method not in READ_METHODS:
        return audit.EVENT_RECORD_CHANGE
    if method == "GET" and role in PRIVILEGED_ROLES and template not in NON_RECORD_READS:
        if any(segment.endswith("export") for segment in template.split("/")):
            return audit.EVENT_RECORD_EXPORT
        return audit.EVENT_RECORD_READ
    return None


def _is_json(scope: Scope) -> bool:
    content_type = (_header(scope, b"content-type") or "").lower()
    return content_type.startswith("application/json")


class AuditTrailMiddleware:
    """Record audit events for API requests after the response is sent."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(API_PREFIX):
            await self.app(scope, receive, send)
            return

        method = scope["method"].upper()
        status: dict[str, int] = {}
        capture = method not in READ_METHODS and _is_json(scope)
        chunks: list[bytes] = []
        size = 0

        async def receive_wrapper() -> Message:
            nonlocal size, capture
            message = await receive()
            if capture and message["type"] == "http.request":
                body = message.get("body", b"")
                size += len(body)
                if size > MAX_BODY_BYTES:
                    capture = False
                    chunks.clear()
                else:
                    chunks.append(body)
            return message

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except Exception:
            status.setdefault("code", 500)
            await self._record(scope, method, status["code"], chunks if capture else None)
            raise
        await self._record(scope, method, status.get("code", 500), chunks if capture else None)

    async def _record(
        self, scope: Scope, method: str, status: int, chunks: list[bytes] | None
    ) -> None:
        route = scope.get("route")
        template = getattr(route, "path", None)
        if not isinstance(template, str) or template in EXCLUDED_ROUTES:
            return
        actor_ref, role = _resolve_actor(scope)
        event_type = _event_type(method, status, role, template)
        if event_type is None:
            return
        reason = None
        if status == 401:
            reason = audit.REASON_UNAUTHENTICATED
        elif status == 403:
            reason = audit.REASON_FORBIDDEN
        await audit.record_audit_event(
            event_type=event_type,
            actor_ref=actor_ref,
            actor_role=role,
            reason_code=reason,
            http_method=method,
            route_template=template,
            record_ids=_record_ids(scope),
            changed_fields=(
                _changed_fields(b"".join(chunks), _schema_fields(route))
                if chunks is not None
                else None
            ),
            status_code=status,
        )

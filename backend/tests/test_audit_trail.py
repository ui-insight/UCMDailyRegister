"""Per-user audit trail: middleware events, sign-in events, minimization.

All identities and content here are synthetic.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import jwt
import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps as auth_deps
from app.auth import session_tokens
from app.auth.session_tokens import create_session_token, decode_session_token
from app.models.audit_event import AuditEvent
from app.services import audit as audit_service
from tests.conftest import make_newsletter_data, make_submission_data
from tests.test_auth_sso import OIDC_ENV, _fragment

STAFF_OID = "11111111-2222-4333-8444-555555555555"
SUBMITTER_OID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
BODY_MARKER = "SYNTHETIC-SENSITIVE-MARKER-41c7"
EMAIL_MARKER = "synthetic-audit-marker@example.test"


def _bearer(role: str, oid: str | None) -> dict[str, str]:
    token = create_session_token(
        subject=EMAIL_MARKER, role=role, name="Synthetic Person", object_id=oid  # type: ignore[arg-type]
    )
    return {"Authorization": f"Bearer {token}"}


async def _events(db: AsyncSession) -> list[AuditEvent]:
    db.expire_all()
    result = await db.execute(sa.select(AuditEvent).order_by(AuditEvent.Occurred_At))
    return list(result.scalars().all())


def _row_text(event: AuditEvent) -> str:
    return json.dumps(
        {column.name: getattr(event, column.name) for column in AuditEvent.__table__.columns},
        default=str,
    )


@pytest.fixture
def oidc_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(auth_deps.settings, "auth_provider", "oidc")


@pytest.mark.asyncio
@pytest.mark.usefixtures("oidc_mode")
class TestRequestAuditUnderSso:
    async def test_staff_read_is_recorded_with_object_id(
        self, client: AsyncClient, db: AsyncSession
    ):
        created = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
            headers=_bearer("submitter", SUBMITTER_OID),
        )
        submission_id = created.json()["Id"]

        resp = await client.get(
            f"/api/v1/submissions/{submission_id}", headers=_bearer("staff", STAFF_OID)
        )
        assert resp.status_code == 200

        reads = [e for e in await _events(db) if e.Event_Type == "record_read"]
        assert len(reads) == 1
        read = reads[0]
        assert read.Actor_Ref == STAFF_OID
        assert read.Actor_Role == "staff"
        assert read.Http_Method == "GET"
        assert read.Route_Template == "/api/v1/submissions/{submission_id}"
        assert read.Record_Ids == {"submission_id": submission_id}
        assert read.Changed_Fields is None
        assert read.Status_Code == 200

    async def test_staff_export_is_its_own_event_type(
        self, client: AsyncClient, db: AsyncSession
    ):
        staff = _bearer("staff", STAFF_OID)
        created = await client.post(
            "/api/v1/newsletters", json=make_newsletter_data(), headers=staff
        )
        resp = await client.get(f"/api/v1/newsletters/{created.json()['Id']}/export", headers=staff)
        assert resp.status_code == 200
        exports = [e for e in await _events(db) if e.Event_Type == "record_export"]
        assert [e.Route_Template for e in exports] == ["/api/v1/newsletters/{newsletter_id}/export"]
        assert exports[0].Actor_Ref == STAFF_OID

    async def test_submitter_write_records_field_names_never_values(
        self, client: AsyncClient, db: AsyncSession
    ):
        resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Body=f"Body with {BODY_MARKER} inside.",
                Submitter_Email=EMAIL_MARKER,
            ),
            headers=_bearer("submitter", SUBMITTER_OID),
        )
        assert resp.status_code == 201

        events = await _events(db)
        assert len(events) == 1
        event = events[0]
        assert event.Event_Type == "record_change"
        assert event.Actor_Ref == SUBMITTER_OID
        assert event.Actor_Role == "submitter"
        assert event.Http_Method == "POST"
        assert event.Route_Template == "/api/v1/submissions/"
        assert event.Status_Code == 201
        assert "Original_Body" in event.Changed_Fields
        assert "Submitter_Email" in event.Changed_Fields
        row = _row_text(event)
        assert BODY_MARKER not in row
        assert EMAIL_MARKER not in row
        assert "Synthetic Person" not in row

    async def test_query_string_is_not_stored(self, client: AsyncClient, db: AsyncSession):
        resp = await client.get(
            f"/api/v1/submissions/?search={BODY_MARKER}", headers=_bearer("staff", STAFF_OID)
        )
        assert resp.status_code == 200
        events = await _events(db)
        assert len(events) == 1
        assert events[0].Route_Template == "/api/v1/submissions/"
        assert BODY_MARKER not in _row_text(events[0])

    async def test_crafted_body_keys_are_dropped(self, client: AsyncClient, db: AsyncSession):
        await client.post(
            "/api/v1/feedback",
            json={"Summary": "x", f"{BODY_MARKER} free text key": "y"},
            headers=_bearer("submitter", SUBMITTER_OID),
        )
        events = await _events(db)
        assert len(events) == 1
        assert events[0].Changed_Fields == ["Summary"]
        assert BODY_MARKER not in _row_text(events[0])

    async def test_forbidden_is_recorded_with_role(self, client: AsyncClient, db: AsyncSession):
        resp = await client.get(
            "/api/v1/submissions/", headers=_bearer("submitter", SUBMITTER_OID)
        )
        assert resp.status_code == 403
        events = await _events(db)
        assert len(events) == 1
        event = events[0]
        assert event.Event_Type == "authorization_failure"
        assert event.Reason_Code == "forbidden"
        assert event.Actor_Role == "submitter"
        assert event.Actor_Ref == SUBMITTER_OID
        assert event.Status_Code == 403

    async def test_invalid_token_is_recorded_as_unauthenticated(
        self, client: AsyncClient, db: AsyncSession
    ):
        resp = await client.get(
            "/api/v1/submissions/", headers={"Authorization": "Bearer not-a-token"}
        )
        assert resp.status_code == 401
        events = await _events(db)
        assert [(e.Event_Type, e.Reason_Code, e.Actor_Role, e.Actor_Ref) for e in events] == [
            ("authorization_failure", "unauthenticated", "public", None)
        ]

    async def test_token_without_oid_audits_role_only(
        self, client: AsyncClient, db: AsyncSession
    ):
        now = datetime.now(UTC)
        legacy = jwt.encode(
            {"sub": EMAIL_MARKER, "role": "staff", "name": "x", "iat": now,
             "exp": now + timedelta(hours=1)},
            session_tokens.settings.secret_key,
            algorithm="HS256",
        )
        resp = await client.get(
            "/api/v1/submissions/", headers={"Authorization": f"Bearer {legacy}"}
        )
        assert resp.status_code == 200
        events = await _events(db)
        assert [(e.Event_Type, e.Actor_Role, e.Actor_Ref) for e in events] == [
            ("record_read", "staff", None)
        ]
        assert EMAIL_MARKER not in _row_text(events[0])

    async def test_probes_and_auth_config_are_not_recorded(
        self, client: AsyncClient, db: AsyncSession
    ):
        staff = _bearer("staff", STAFF_OID)
        assert (await client.get("/api/v1/health", headers=staff)).status_code == 200
        await client.get("/api/v1/readyz", headers=staff)
        await client.get("/api/v1/auth/config", headers=staff)
        await client.get("/api/v1/auth/me", headers=staff)
        assert await _events(db) == []

    async def test_public_reads_are_not_recorded(self, client: AsyncClient, db: AsyncSession):
        resp = await client.get("/api/v1/sections", headers=_bearer("submitter", SUBMITTER_OID))
        assert resp.status_code == 200
        assert await _events(db) == []

    async def test_unmatched_routes_are_not_recorded(
        self, client: AsyncClient, db: AsyncSession
    ):
        resp = await client.post(f"/api/v1/{BODY_MARKER}", json={"a": 1})
        assert resp.status_code == 404
        assert await _events(db) == []

    async def test_audit_write_failure_does_not_break_the_request(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch, caplog
    ):
        class BrokenSession:
            async def __aenter__(self):
                raise RuntimeError(f"connection refused {BODY_MARKER}")

            async def __aexit__(self, *exc):
                return False

        monkeypatch.setattr(audit_service, "audit_session_factory", BrokenSession)
        with caplog.at_level(logging.ERROR, logger="app.services.audit"):
            resp = await client.post(
                "/api/v1/submissions/",
                json=make_submission_data(),
                headers=_bearer("submitter", SUBMITTER_OID),
            )
        assert resp.status_code == 201
        records = [r for r in caplog.records if r.name == "app.services.audit"]
        assert [r.getMessage() for r in records] == [
            "Audit event write failed error_type=RuntimeError"
        ]
        assert all(r.exc_info is None for r in records)


@pytest.mark.asyncio
class TestRequestAuditInHeaderMode:
    async def test_staff_read_has_role_but_no_actor(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
    ):
        assert (await client.get("/api/v1/submissions/", headers=staff_headers)).status_code == 200
        events = await _events(db)
        assert [(e.Event_Type, e.Actor_Role, e.Actor_Ref) for e in events] == [
            ("record_read", "staff", None)
        ]

    async def test_wrong_header_secret_is_public(self, client: AsyncClient, db: AsyncSession):
        headers = {"X-Trusted-User-Role": "staff", "X-Trusted-Auth-Secret": "wrong"}
        assert (await client.get("/api/v1/submissions/", headers=headers)).status_code == 403
        events = await _events(db)
        assert [(e.Event_Type, e.Actor_Role) for e in events] == [
            ("authorization_failure", "public")
        ]

    async def test_anonymous_write_is_recorded(self, client: AsyncClient, db: AsyncSession):
        resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        assert resp.status_code == 201
        events = await _events(db)
        assert [(e.Event_Type, e.Actor_Role, e.Actor_Ref) for e in events] == [
            ("record_change", "public", None)
        ]


class TestSessionTokenObjectId:
    def test_oid_round_trips(self):
        token = create_session_token(
            subject="x@example.test", role="staff", name="x", object_id=STAFF_OID
        )
        assert jwt.decode(token, options={"verify_signature": False})["oid"] == STAFF_OID
        assert decode_session_token(token).object_id == STAFF_OID

    def test_missing_oid_is_omitted(self):
        token = create_session_token(subject="x@example.test", role="staff", name="x")
        assert "oid" not in jwt.decode(token, options={"verify_signature": False})
        assert decode_session_token(token).object_id is None


@pytest.fixture
def sso_app(monkeypatch: pytest.MonkeyPatch):
    """Only the SSO router, authlib stubbed out (as in test_auth_sso)."""
    from starlette.middleware.sessions import SessionMiddleware

    from app.api.v1 import sso

    for key, value in OIDC_ENV.items():
        monkeypatch.setattr(sso.settings, key, value)
    monkeypatch.setattr(sso.settings, "oidc_group_source", "claim")
    monkeypatch.setattr(sso.settings, "oidc_role_claim", "roles")
    app = FastAPI()
    app.include_router(sso.router, prefix="/api/v1")
    app.add_middleware(SessionMiddleware, secret_key="test-session-secret")
    return app, sso


@pytest.mark.asyncio
class TestSignInAudit:
    async def _callback(self, sso_app, token: dict | Exception) -> str:
        app, sso = sso_app
        if isinstance(token, Exception):
            sso.oauth.entra.authorize_access_token = AsyncMock(side_effect=token)
        else:
            sso.oauth.entra.authorize_access_token = AsyncMock(return_value=token)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/auth/callback?code=x&state=y")
        assert resp.status_code == 302
        return resp.headers["location"]

    async def test_callback_puts_oid_in_token_and_records_success(
        self, sso_app, db: AsyncSession
    ):
        location = await self._callback(
            sso_app,
            {"userinfo": {"email": EMAIL_MARKER, "oid": STAFF_OID.upper(), "roles": ["UCM-Staff"]}},
        )
        identity = decode_session_token(_fragment(location)["access_token"])
        assert identity.object_id == STAFF_OID
        assert identity.role == "staff"

        events = await _events(db)
        assert [(e.Event_Type, e.Actor_Ref, e.Actor_Role, e.Reason_Code) for e in events] == [
            ("sign_in_success", STAFF_OID, "staff", None)
        ]
        assert EMAIL_MARKER not in _row_text(events[0])

    async def test_malformed_oid_is_dropped(self, sso_app, db: AsyncSession):
        location = await self._callback(
            sso_app, {"userinfo": {"email": EMAIL_MARKER, "oid": BODY_MARKER, "roles": []}}
        )
        assert decode_session_token(_fragment(location)["access_token"]).object_id is None
        events = await _events(db)
        assert [(e.Event_Type, e.Actor_Ref, e.Actor_Role) for e in events] == [
            ("sign_in_success", None, "submitter")
        ]

    async def test_failed_exchange_records_reason(self, sso_app, db: AsyncSession):
        await self._callback(sso_app, RuntimeError("bad"))
        events = await _events(db)
        assert [(e.Event_Type, e.Reason_Code, e.Actor_Role, e.Actor_Ref) for e in events] == [
            ("sign_in_failure", "sign_in_failed", "public", None)
        ]

    async def test_no_account_failure_keeps_oid(self, sso_app, db: AsyncSession):
        await self._callback(sso_app, {"userinfo": {"oid": STAFF_OID, "roles": ["UCM-Staff"]}})
        events = await _events(db)
        assert [(e.Event_Type, e.Reason_Code, e.Actor_Ref) for e in events] == [
            ("sign_in_failure", "no_account", STAFF_OID)
        ]

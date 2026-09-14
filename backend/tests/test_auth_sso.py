"""Tests for session tokens, Entra role mapping, and the SSO endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import jwt
import pytest
from authlib.integrations.base_client import OAuthError
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import deps as auth_deps
from app.auth import entra_roles, session_tokens
from app.auth.entra_roles import map_groups_to_role
from app.auth.session_tokens import create_session_token, decode_session_token
from app.config import Settings
from app.services.graph_groups import GraphGroupLookupError, GraphPermissionError
from tests.conftest import make_newsletter_data


def _token(role: str = "staff", **overrides: Any) -> str:
    return create_session_token(
        subject=overrides.get("subject", "jdoe@uidaho.edu"),
        role=role,  # type: ignore[arg-type]
        name=overrides.get("name", "J Doe"),
    )


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- session tokens -------------------------------------------------------


class TestSessionTokens:
    def test_round_trip(self):
        identity = decode_session_token(_token("slc"))
        assert identity.subject == "jdoe@uidaho.edu"
        assert identity.role == "slc"
        assert identity.name == "J Doe"

    def test_expired_token_is_401(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(session_tokens.settings, "access_token_expire_minutes", -1)
        token = _token()
        with pytest.raises(Exception) as exc_info:
            decode_session_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[attr-defined]

    def test_tampered_signature_is_401(self):
        token = _token()
        forged = jwt.encode(
            jwt.decode(token, options={"verify_signature": False}),
            "someone-elses-key-that-is-long-enough-for-hs256",
            algorithm="HS256",
        )
        with pytest.raises(Exception) as exc_info:
            decode_session_token(forged)
        assert exc_info.value.status_code == 401  # type: ignore[attr-defined]

    def test_public_is_not_a_valid_token_role(self):
        now = datetime.now(UTC)
        token = jwt.encode(
            {"sub": "x", "role": "public", "name": "x", "iat": now, "exp": now + timedelta(hours=1)},
            session_tokens.settings.secret_key,
            algorithm="HS256",
        )
        with pytest.raises(Exception) as exc_info:
            decode_session_token(token)
        assert exc_info.value.status_code == 401  # type: ignore[attr-defined]


# --- bearer token in get_submitter_role -----------------------------------


@pytest.mark.asyncio
class TestBearerTokenAuthorization:
    async def test_staff_token_passes_staff_gate(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/newsletters", json=make_newsletter_data(), headers=_bearer(_token("staff"))
        )
        assert resp.status_code == 201

    async def test_slc_token_is_refused_at_staff_gate(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/newsletters", json=make_newsletter_data(), headers=_bearer(_token("slc"))
        )
        assert resp.status_code == 403

    async def test_slc_token_passes_slc_gate(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/submissions/?slc_calendar_only=true", headers=_bearer(_token("slc"))
        )
        assert resp.status_code == 200

    async def test_ops_token_passes_ops_gate(self, client: AsyncClient):
        resp = await client.get("/api/v1/ops/harvested-events", headers=_bearer(_token("ops")))
        assert resp.status_code == 200

    async def test_invalid_token_is_401_not_public(self, client: AsyncClient):
        """A bad token must not fall through to anonymous access."""
        resp = await client.get("/api/v1/submissions/", headers=_bearer("not-a-token"))
        assert resp.status_code == 401
        assert resp.headers.get("www-authenticate") == "Bearer"

    async def test_token_wins_over_trusted_header(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        """A signed-in SLC member on a proxy that stamps 'staff' is still SLC."""
        resp = await client.post(
            "/api/v1/newsletters",
            json=make_newsletter_data(),
            headers={**staff_headers, **_bearer(_token("slc"))},
        )
        assert resp.status_code == 403

    async def test_no_token_and_no_header_is_public(self, client: AsyncClient):
        resp = await client.get("/api/v1/submissions/")
        assert resp.status_code == 403


# --- /auth endpoints -------------------------------------------------------


@pytest.mark.asyncio
class TestAuthEndpoints:
    async def test_config_reports_header_mode(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/config")
        assert resp.status_code == 200
        assert resp.json() == {"sso_enabled": False}

    async def test_config_reports_oidc_mode(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        from app.api.v1 import auth as auth_module

        monkeypatch.setattr(auth_module.settings, "auth_provider", "oidc")
        resp = await client.get("/api/v1/auth/config")
        assert resp.json() == {"sso_enabled": True}

    async def test_me_requires_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_ignores_trusted_header(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        """The proxy header names a role, not a person; /me is for signed-in users."""
        resp = await client.get("/api/v1/auth/me", headers=staff_headers)
        assert resp.status_code == 401

    async def test_me_returns_identity(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me", headers=_bearer(_token("ops")))
        assert resp.status_code == 200
        assert resp.json() == {"subject": "jdoe@uidaho.edu", "name": "J Doe", "role": "ops"}


# --- Entra role mapping ----------------------------------------------------


class TestEntraRoleMapping:
    @pytest.fixture(autouse=True)
    def _configure(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(entra_roles.settings, "entra_group_staff", "UCM-Staff, ucm-editors")
        monkeypatch.setattr(entra_roles.settings, "entra_group_slc", "SLC-Members")
        monkeypatch.setattr(entra_roles.settings, "entra_group_ops", "Event-Services")

    def test_no_match_is_none(self):
        assert map_groups_to_role(["Some-Other-Group"]) is None
        assert map_groups_to_role([]) is None

    def test_matches_case_insensitively(self):
        assert map_groups_to_role(["ucm-staff"]) == "staff"
        assert map_groups_to_role(["slc-members"]) == "slc"
        assert map_groups_to_role(["EVENT-SERVICES"]) == "ops"

    def test_comma_separated_config(self):
        assert map_groups_to_role(["ucm-editors"]) == "staff"

    def test_highest_privilege_wins(self):
        assert map_groups_to_role(["Event-Services", "SLC-Members", "UCM-Staff"]) == "staff"
        assert map_groups_to_role(["Event-Services", "SLC-Members"]) == "slc"

    def test_empty_config_matches_nothing(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(entra_roles.settings, "entra_group_ops", "")
        assert map_groups_to_role([""]) is None


# --- SSO callback ----------------------------------------------------------


OIDC_ENV = {
    "auth_provider": "oidc",
    "entra_client_id": "client",
    "entra_client_secret": "secret",
    "entra_metadata_url": "https://login.microsoftonline.com/t/v2.0/.well-known/openid-configuration",
    "entra_redirect_uri": "http://localhost:5173/api/v1/auth/callback",
    "oidc_post_login_redirect": "http://localhost:5173/sso/callback",
    "oidc_post_logout_redirect": "http://localhost:5173/",
    "entra_group_staff": "UCM-Staff",
    "entra_group_slc": "SLC-Members",
    "entra_group_ops": "Event-Services",
}


@pytest.fixture
def sso_app(monkeypatch: pytest.MonkeyPatch):
    """A minimal app with only the SSO router, authlib stubbed out."""
    from app.api.v1 import sso

    for key, value in OIDC_ENV.items():
        monkeypatch.setattr(sso.settings, key, value)
    monkeypatch.setattr(sso.settings, "oidc_group_source", "claim")
    monkeypatch.setattr(sso.settings, "oidc_role_claim", "roles")

    app = FastAPI()
    app.include_router(sso.router, prefix="/api/v1")
    return app, sso


def _fragment(location: str) -> dict[str, str]:
    from urllib.parse import parse_qs

    _, _, fragment = location.partition("#")
    return {k: v[0] for k, v in parse_qs(fragment).items()}


@pytest.mark.asyncio
class TestSsoCallback:
    async def _callback(self, sso_app, token: dict | Exception) -> str:
        app, sso = sso_app
        if isinstance(token, Exception):
            sso.oauth.entra.authorize_access_token = AsyncMock(side_effect=token)
        else:
            sso.oauth.entra.authorize_access_token = AsyncMock(return_value=token)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/auth/callback?code=x&state=y")
        assert resp.status_code == 302
        return resp.headers["location"]

    async def test_mints_token_for_mapped_role(self, sso_app):
        location = await self._callback(
            sso_app,
            {
                "userinfo": {
                    "email": "GFizzell@uidaho.edu",
                    "name": "Greg Fizzell (gfizzell@uidaho.edu)",
                    "roles": ["SLC-Members"],
                }
            },
        )
        assert location.startswith("http://localhost:5173/sso/callback#")
        identity = decode_session_token(_fragment(location)["access_token"])
        assert identity.subject == "gfizzell@uidaho.edu"
        assert identity.name == "Greg Fizzell"
        assert identity.role == "slc"

    async def test_reads_roles_from_token_when_not_on_userinfo(self, sso_app):
        location = await self._callback(
            sso_app,
            {"userinfo": {"preferred_username": "a@uidaho.edu"}, "roles": ["UCM-Staff"]},
        )
        assert decode_session_token(_fragment(location)["access_token"]).role == "staff"

    async def test_unmapped_user_is_not_authorized(self, sso_app):
        location = await self._callback(
            sso_app, {"userinfo": {"email": "x@uidaho.edu", "roles": ["Nothing"]}}
        )
        assert _fragment(location) == {"error": "not_authorized"}

    async def test_missing_email_is_no_account(self, sso_app):
        location = await self._callback(sso_app, {"userinfo": {"roles": ["UCM-Staff"]}})
        assert _fragment(location) == {"error": "no_account"}

    async def test_oauth_error_is_sign_in_failed(self, sso_app):
        location = await self._callback(sso_app, OAuthError("bad"))
        assert _fragment(location) == {"error": "sign_in_failed"}

    async def test_graph_outage_is_unavailable(self, sso_app, monkeypatch):
        app, sso = sso_app
        monkeypatch.setattr(sso.settings, "oidc_group_source", "graph")
        monkeypatch.setattr(
            sso, "fetch_group_names", AsyncMock(side_effect=GraphGroupLookupError("down"))
        )
        location = await self._callback(
            sso_app, {"userinfo": {"email": "x@uidaho.edu"}, "access_token": "at"}
        )
        assert _fragment(location) == {"error": "unavailable"}

    async def test_graph_refusal_is_misconfigured(self, sso_app, monkeypatch):
        app, sso = sso_app
        monkeypatch.setattr(sso.settings, "oidc_group_source", "graph")
        monkeypatch.setattr(
            sso, "fetch_group_names", AsyncMock(side_effect=GraphPermissionError("no"))
        )
        location = await self._callback(
            sso_app, {"userinfo": {"email": "x@uidaho.edu"}, "access_token": "at"}
        )
        assert _fragment(location) == {"error": "misconfigured"}

    async def test_graph_success_maps_role(self, sso_app, monkeypatch):
        app, sso = sso_app
        monkeypatch.setattr(sso.settings, "oidc_group_source", "graph")
        monkeypatch.setattr(sso, "fetch_group_names", AsyncMock(return_value=["Event-Services"]))
        location = await self._callback(
            sso_app, {"userinfo": {"email": "x@uidaho.edu"}, "access_token": "at"}
        )
        assert decode_session_token(_fragment(location)["access_token"]).role == "ops"


@pytest.mark.asyncio
class TestSsoLogout:
    async def test_redirects_through_entra_end_session(self, sso_app):
        app, sso = sso_app
        sso.oauth.entra.load_server_metadata = AsyncMock(
            return_value={"end_session_endpoint": "https://login.microsoftonline.com/t/logout"}
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/auth/logout")
        assert resp.status_code == 302
        assert resp.headers["location"] == (
            "https://login.microsoftonline.com/t/logout"
            "?post_logout_redirect_uri=http%3A%2F%2Flocalhost%3A5173%2F"
        )

    async def test_falls_back_to_local_signout(self, sso_app):
        app, sso = sso_app
        sso.oauth.entra.load_server_metadata = AsyncMock(return_value={})
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/auth/logout")
        assert resp.headers["location"] == "http://localhost:5173/"


# --- config validation -----------------------------------------------------


def _settings(**overrides: Any) -> Settings:
    base = {"cors_origins": "http://localhost:5173", "_env_file": None}
    return Settings(**{**base, **overrides})


class TestAuthConfigValidation:
    def test_header_mode_needs_nothing(self):
        assert _settings().auth_provider == "header"

    def test_header_mode_in_production_only_warns(self):
        # Prod runs on the trusted-header boundary today; a deploy of this
        # code must not refuse to boot.
        assert _settings(environment="production").auth_provider == "header"

    def test_oidc_requires_entra_settings(self):
        with pytest.raises(ValueError, match="ENTRA_CLIENT_ID"):
            _settings(auth_provider="oidc")

    def test_oidc_requires_at_least_one_role_mapping(self):
        with pytest.raises(ValueError, match="ENTRA_GROUP_STAFF"):
            _settings(**{**OIDC_ENV, "entra_group_staff": "", "entra_group_slc": "", "entra_group_ops": ""})

    def test_oidc_dev_accepts_localhost(self):
        assert _settings(**OIDC_ENV).auth_provider == "oidc"

    def test_oidc_production_rejects_default_secret(self):
        with pytest.raises(ValueError, match="SECRET_KEY"):
            _settings(**OIDC_ENV, environment="production")

    def test_oidc_production_rejects_localhost_redirects(self):
        with pytest.raises(ValueError, match="ENTRA_REDIRECT_URI"):
            _settings(
                **OIDC_ENV,
                environment="production",
                secret_key="x" * 40,
                session_cookie_secret="y" * 40,
            )

    def test_oidc_production_rejects_shared_cookie_secret(self):
        with pytest.raises(ValueError, match="differ"):
            _settings(
                **OIDC_ENV,
                environment="production",
                secret_key="x" * 40,
                session_cookie_secret="x" * 40,
            )

    def test_oidc_production_accepts_complete_config(self):
        s = _settings(
            **{
                **OIDC_ENV,
                "entra_redirect_uri": "https://ucmnews.insight.uidaho.edu/api/v1/auth/callback",
                "oidc_post_login_redirect": "https://ucmnews.insight.uidaho.edu/sso/callback",
                "oidc_post_logout_redirect": "https://ucmnews.insight.uidaho.edu/",
            },
            environment="production",
            secret_key="x" * 40,
            session_cookie_secret="y" * 40,
            cors_origins="https://ucmnews.insight.uidaho.edu",
        )
        assert s.auth_provider == "oidc"

    def test_graph_source_implies_graph_scope(self):
        s = _settings(**OIDC_ENV, oidc_group_source="graph")
        assert s.oidc_scopes_requested == "openid email profile GroupMember.Read.All"
        assert _settings(**OIDC_ENV).oidc_scopes_requested == "openid email profile"


def test_deps_module_exposes_identity_dependency():
    assert callable(auth_deps.get_current_identity)
    assert callable(auth_deps.require_identity)

import json
import logging
from typing import Any, Literal, Self
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)

LOCAL_DEV_CORS_ORIGINS = ["http://localhost:5173"]
PRODUCTION_ENVIRONMENTS = {"prod", "production"}
MIN_SECRET_KEY_LENGTH = 32
DEFAULT_SECRET_KEY = "change-me-in-production-min-32-bytes"
# Delegated Graph scope needed to read the signed-in user's own group
# memberships. Appended automatically when OIDC_GROUP_SOURCE=graph.
GRAPH_GROUP_SCOPE = "GroupMember.Read.All"


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./ucm_newsletter.db"

    # LLM Provider
    llm_provider: str = "claude"  # "claude", "openai", or "mindrouter"

    # Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # MindRouter (University of Idaho on-prem AI services)
    mindrouter_api_key: str = ""
    mindrouter_endpoint_url: str = "https://mindrouter.uidaho.edu/v1/chat/completions"
    mindrouter_model: str = "openai/gpt-oss-120b"

    # Ops needs classifier â€” always MindRouter, independent of LLM_PROVIDER.
    # Endpoint and key fall back to the MINDROUTER_* values when unset.
    ops_classifier_model: str = "qwen/qwen3.8-27b"
    ops_classifier_endpoint_url: str = ""
    ops_classifier_api_key: str = ""

    # App
    environment: str = "development"
    upload_dir: str = "./uploads"
    image_upload_max_bytes: int = 10 * 1024 * 1024
    image_upload_max_pixels: int = 36_000_000
    cors_origins: str | list[str] | None = None

    # Authentication. Who the caller is reaches the API one of two ways:
    #   header — the reverse proxy asserts a role via X-Trusted-User-Role +
    #            X-Trusted-Auth-Secret (the prototype boundary; the default).
    #   oidc   — Microsoft Entra ID sign-in (Web/confidential flow). The
    #            callback mints this app's own session token, which the
    #            browser then presents as a bearer token on every request.
    # Both paths resolve to the same SubmitterRole in app.api.deps, so no
    # router knows which one is active.
    auth_provider: Literal["header", "oidc"] = "header"
    trusted_role_header_secret: str = ""

    # Signs this app's session token (HS256). Must be changed and >= 32 chars
    # when AUTH_PROVIDER=oidc in production.
    secret_key: str = DEFAULT_SECRET_KEY
    access_token_expire_minutes: int = 480

    # Microsoft Entra registration (required when AUTH_PROVIDER=oidc).
    entra_client_id: str = ""
    entra_client_secret: str = ""
    # OIDC discovery document, e.g.
    # https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration
    entra_metadata_url: str = ""
    # Registered with OIT character-for-character, one per environment:
    # https://<host>/api/v1/auth/callback
    entra_redirect_uri: str = ""
    # Where the backend sends the browser after minting a token — the SPA's
    # callback page: https://<host>/sso/callback
    oidc_post_login_redirect: str = ""
    # Where Entra returns the browser after sign-out: https://<host>/
    oidc_post_logout_redirect: str = ""
    oidc_scopes: str = "openid email profile"
    # Where the user's role comes from:
    #   claim — read OIDC_ROLE_CLAIM off the token (Entra App Roles). Default.
    #   graph — call Microsoft Graph /me/memberOf for security-group names;
    #           needs the delegated GroupMember.Read.All scope (admin consent).
    oidc_group_source: Literal["claim", "graph"] = "claim"
    oidc_role_claim: str = "roles"
    # Entra App Role / group names that grant each role. Comma-separated
    # lists are accepted; matching is case-insensitive. A signed-in user
    # matching none of them is refused — there is no default role.
    entra_group_staff: str = ""
    entra_group_slc: str = ""
    entra_group_ops: str = ""
    # Signs authlib's OIDC-state cookie. Must be set, and differ from
    # SECRET_KEY, in production; falls back to SECRET_KEY otherwise.
    session_cookie_secret: str = ""
    calendar_source_url: str = (
        "https://www.qatrumba.com/events-calendar/ui/uidaho/vandals/vandal/event/events/calendar/moscow/idaho/id/university-of-idaho"
    )
    calendar_request_timeout_seconds: float = 10.0
    job_postings_source_url: str = "https://uidaho.peopleadmin.com/postings/search"
    job_postings_request_timeout_seconds: float = 10.0
    job_postings_max_pages: int = 5
    slc_trumba_feed_url: str = "https://www.trumba.com/calendars/university-of-idaho.json"
    slc_trumba_request_timeout_seconds: float = 15.0
    ai_edit_max_concurrency: int = 2
    feedback_notification_channel: Literal["disabled"] = "disabled"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str] | None:
        """Accept comma-separated or JSON-array CORS origin values."""
        if value is None:
            return None

        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                return None
            if raw_value.startswith("["):
                try:
                    value = json.loads(raw_value)
                except json.JSONDecodeError as exc:
                    raise ValueError("CORS_ORIGINS must be comma-separated or a JSON array") from exc
            else:
                value = raw_value.split(",")

        if isinstance(value, list):
            origins = [str(origin).strip() for origin in value if str(origin).strip()]
            return origins or None

        raise ValueError("CORS_ORIGINS must be comma-separated or a JSON array")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in PRODUCTION_ENVIRONMENTS

    @property
    def oidc_scopes_requested(self) -> str:
        """Scopes sent to Entra, with the Graph scope implied by the group source."""
        scopes = self.oidc_scopes.split()
        if self.oidc_group_source == "graph" and GRAPH_GROUP_SCOPE not in scopes:
            scopes.append(GRAPH_GROUP_SCOPE)
        return " ".join(scopes)

    @property
    def session_cookie_secret_key(self) -> str:
        return self.session_cookie_secret or self.secret_key

    @model_validator(mode="after")
    def validate_auth(self) -> Self:
        if self.auth_provider == "header":
            if self.is_production:
                # Deliberately a warning, not an error: production currently
                # runs on the trusted-header boundary, and a deploy of this
                # code must not take it down. Tighten once prod is on oidc.
                logger.warning(
                    "AUTH_PROVIDER=header in production: roles are asserted by the "
                    "reverse proxy, not by user sign-in. Set AUTH_PROVIDER=oidc."
                )
            return self

        required = (
            "entra_client_id",
            "entra_client_secret",
            "entra_metadata_url",
            "entra_redirect_uri",
            "oidc_post_login_redirect",
        )
        missing = [name.upper() for name in required if not getattr(self, name)]
        if missing:
            raise ValueError("AUTH_PROVIDER=oidc requires " + ", ".join(missing))

        if not (self.entra_group_staff or self.entra_group_slc or self.entra_group_ops):
            raise ValueError(
                "AUTH_PROVIDER=oidc requires at least one of ENTRA_GROUP_STAFF, "
                "ENTRA_GROUP_SLC, ENTRA_GROUP_OPS — otherwise every sign-in is refused."
            )

        if not self.is_production:
            return self

        if self.secret_key == DEFAULT_SECRET_KEY or len(self.secret_key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                "SECRET_KEY must be changed from the default and be at least "
                f"{MIN_SECRET_KEY_LENGTH} characters when AUTH_PROVIDER=oidc in production."
            )
        if not self.session_cookie_secret:
            raise ValueError(
                "SESSION_COOKIE_SECRET must be set when AUTH_PROVIDER=oidc in production."
            )
        if self.session_cookie_secret == self.secret_key:
            raise ValueError("SESSION_COOKIE_SECRET must differ from SECRET_KEY.")
        if not self.oidc_post_logout_redirect:
            raise ValueError(
                "OIDC_POST_LOGOUT_REDIRECT must be set when AUTH_PROVIDER=oidc in "
                "production; without it sign-out leaves the Entra session alive."
            )
        for name in ("entra_redirect_uri", "oidc_post_login_redirect", "oidc_post_logout_redirect"):
            parsed = urlparse(getattr(self, name))
            if parsed.scheme != "https" or parsed.hostname in ("localhost", "127.0.0.1"):
                raise ValueError(
                    f"{name.upper()} must be an https:// URL on the public hostname in "
                    "production; Entra sends the browser there."
                )
        if urlparse(self.entra_metadata_url).scheme != "https":
            raise ValueError("ENTRA_METADATA_URL must be an https:// URL in production.")
        return self

    @model_validator(mode="after")
    def validate_cors_origins(self) -> Self:
        is_production = self.is_production

        if self.cors_origins is None:
            if is_production:
                raise ValueError("CORS_ORIGINS must be set when ENVIRONMENT=production")
            self.cors_origins = LOCAL_DEV_CORS_ORIGINS.copy()
            return self

        if is_production and "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS cannot include '*' when ENVIRONMENT=production")

        return self


settings = Settings()

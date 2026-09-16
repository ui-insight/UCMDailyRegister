"""Microsoft Entra single sign-on.

Mounted only when `AUTH_PROVIDER=oidc`, so a deployment on the trusted-header
boundary never imports authlib and never needs session support.

The registration OIT issues for this app is a **Web** (confidential) client:
the authorization code is exchanged for a token server-side, using the client
secret, and the Entra token never reaches the browser. What the browser
receives is this app's own session token (`app.auth.session_tokens`), handed
over in the URL fragment - see `sso_callback`.

Mirrors campus-services-maintenance's `app/api/v1/sso.py` (ADR-004 there),
which OIT has already reviewed. This app has no user table: the role is
resolved from Entra on every sign-in and carried in the token, so nothing is
persisted here.
"""

import logging
import re
from urllib.parse import urlencode

from authlib.integrations.base_client import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Query, Request, status
from starlette.responses import RedirectResponse

from app.auth.entra_roles import map_groups_to_role
from app.auth.session_tokens import create_session_token
from app.config import settings
from app.services.graph_groups import (
    GraphGroupLookupError,
    GraphPermissionError,
    fetch_group_names,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="entra",
    client_id=settings.entra_client_id,
    client_secret=settings.entra_client_secret,
    server_metadata_url=settings.entra_metadata_url,
    # Derived, not raw: reading groups from Graph implies the scope that
    # makes it possible.
    client_kwargs={"scope": settings.oidc_scopes_requested},
)

# This tenant appends the address to display names - "Greg Fizzell
# (gfizzell@uidaho.edu)" - which would otherwise be shown on every screen.
_TRAILING_EMAIL = re.compile(r"\s*\([^)]*@[^)]*\)\s*$")

# The login page offers an optional email field whose only job is to
# pre-fill Microsoft's sign-in form. Anything that is not shaped like an
# address is dropped rather than forwarded, so the field cannot be used to
# smuggle arbitrary text into the Entra redirect.
_LOGIN_HINT = re.compile(r"^[^\s@/\\]{1,64}@[^\s@/\\]{1,255}$")
LOGIN_HINT_MAX_LENGTH = 320

# Where the SPA should land after sign-in. Kept in the session alongside
# authlib's OIDC state, and only ever an in-app path: an absolute URL here
# would turn the callback into an open redirect.
_NEXT_SESSION_KEY = "sso_next"
_SAFE_NEXT = re.compile(r"^/(?![/\\])[^\s]*$")


def _sanitize_display_name(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    return _TRAILING_EMAIL.sub("", raw).strip()


# Reason codes handed to the frontend callback page, which turns each into a
# sentence. Codes rather than messages so the wording stays in the UI.
ERROR_NOT_AUTHORIZED = "not_authorized"
ERROR_UNAVAILABLE = "unavailable"
ERROR_MISCONFIGURED = "misconfigured"
ERROR_NO_ACCOUNT = "no_account"
ERROR_SIGN_IN_FAILED = "sign_in_failed"


def _error_redirect(reason: str) -> RedirectResponse:
    """Return the browser to the callback page with a reason it can explain.

    Raising here would render FastAPI's JSON body straight into the browser
    window - no layout, no way back. The commonest reason (`not_authorized`)
    is what everyone sees until OIT assigns them a role, so it has to read
    as a next step rather than as a broken app.
    """
    return RedirectResponse(
        f"{settings.oidc_post_login_redirect}#{urlencode({'error': reason})}",
        status_code=status.HTTP_302_FOUND,
    )


def _claim_values(*sources: dict, claim: str) -> list[object]:
    """Collect a claim that Entra may emit on the ID token or on userinfo."""
    for source in sources:
        raw = source.get(claim)
        if raw is None:
            continue
        return list(raw) if isinstance(raw, list) else [raw]
    return []


async def _resolve_group_names(userinfo: dict, token: dict) -> list[object]:
    """Read the user's Entra roles/groups from whichever source is configured."""
    if settings.oidc_group_source == "claim":
        return _claim_values(userinfo, token, claim=settings.oidc_role_claim)

    access_token = token.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GraphGroupLookupError("Entra returned no access token to read group membership with")
    return list(await fetch_group_names(access_token))


def _sanitize_login_hint(raw: str | None) -> str | None:
    if not raw:
        return None
    hint = raw.strip()
    if len(hint) > LOGIN_HINT_MAX_LENGTH or not _LOGIN_HINT.match(hint):
        return None
    return hint


def _sanitize_next(raw: str | None) -> str | None:
    if not raw:
        return None
    candidate = raw.strip()
    return candidate if _SAFE_NEXT.match(candidate) else None


@router.get("/sso/login", name="sso_login")
async def sso_login(
    request: Request,
    login_hint: str | None = Query(None, max_length=LOGIN_HINT_MAX_LENGTH),
    next: str | None = Query(None, max_length=2048),
) -> RedirectResponse:
    """Begin sign-in by redirecting the browser to Microsoft Entra.

    `login_hint`, when the login page collected one, pre-fills Microsoft's
    form with that address so the user skips the account picker. Without it,
    `prompt=select_account` forces the picker every time: otherwise Entra
    silently reuses its own still-valid session cookie, and the next person
    at a shared office computer is signed in as the last one. With a hint,
    Entra prompts whenever the hinted account is not the one signed in, which
    covers the same case.

    `next` is the in-app path to land on afterwards; it rides the session so
    the callback can honour it without trusting anything from the URL.
    """
    hint = _sanitize_login_hint(login_hint)
    request.session[_NEXT_SESSION_KEY] = _sanitize_next(next)
    params: dict[str, str] = {"login_hint": hint} if hint else {"prompt": "select_account"}
    return await oauth.entra.authorize_redirect(request, settings.entra_redirect_uri, **params)


@router.get("/logout", name="sso_logout")
async def sso_logout() -> RedirectResponse:
    """End the Entra session too, not just this app's.

    The frontend has already dropped its own token before navigating here.
    Sending the browser through Entra's `end_session_endpoint` ends both
    sessions, so the next sign-in starts from nothing.
    """
    metadata = await oauth.entra.load_server_metadata()
    end_session = metadata.get("end_session_endpoint")
    target = settings.oidc_post_logout_redirect or settings.oidc_post_login_redirect

    if not end_session:
        logger.warning(
            "Entra discovery document has no end_session_endpoint; signing out locally only"
        )
        return RedirectResponse(target, status_code=status.HTTP_302_FOUND)

    query = urlencode({"post_logout_redirect_uri": target}) if target else ""
    url = f"{end_session}?{query}" if query else end_session
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get("/callback", name="sso_callback")
async def sso_callback(request: Request) -> RedirectResponse:
    """Complete sign-in: verify the Entra response, then mint a session token.

    Registered with OIT as this app's reply URL, character-for-character.
    """
    try:
        token = await oauth.entra.authorize_access_token(request)
    except OAuthError:
        # Mismatched state, a replayed or expired code, a refused client.
        logger.warning("Entra rejected the sign-in exchange", exc_info=True)
        return _error_redirect(ERROR_SIGN_IN_FAILED)
    except Exception:
        # authlib raises its own JOSE errors (bad ID-token signature, a
        # stale JWKS after key rotation) and httpx errors (discovery or token
        # endpoint unreachable) outside the OAuthError hierarchy. Every one of
        # these lands on a person mid-sign-in, and a raw 500 gives them
        # FastAPI's plain-text body with no way back.
        logger.exception("Sign-in exchange with Entra failed")
        return _error_redirect(ERROR_SIGN_IN_FAILED)

    userinfo = token.get("userinfo") or {}
    # `preferred_username` is the fallback because this tenant has been seen
    # to populate one or the other.
    subject = str(userinfo.get("email") or userinfo.get("preferred_username") or "")
    subject = subject.strip().lower()
    if not subject:
        logger.error("Entra returned neither an email nor a username claim")
        return _error_redirect(ERROR_NO_ACCOUNT)
    name = _sanitize_display_name(userinfo.get("name")) or subject

    try:
        group_names = await _resolve_group_names(userinfo, token)
    except GraphPermissionError:
        # Graph understood us and said no. Permanent, affects everyone, and
        # fixed by an administrator - so it must not borrow the outage copy
        # that tells the reader to wait.
        logger.exception(
            "Graph refused group membership for %s - check that the app registration "
            "has consent for GroupMember.Read.All",
            subject,
        )
        return _error_redirect(ERROR_MISCONFIGURED)
    except GraphGroupLookupError:
        # Deliberately *not* "not authorized": failing to read membership is
        # an outage, and telling the user they lack access would send every
        # one of them chasing their own account instead of the incident.
        logger.exception("Could not read group membership for %s", subject)
        return _error_redirect(ERROR_UNAVAILABLE)

    role = map_groups_to_role(group_names)
    if role is None:
        logger.info("Sign-in refused for %s: no configured role matched", subject)
        return _error_redirect(ERROR_NOT_AUTHORIZED)

    logger.info("Sign-in for %s as %s", subject, role)
    session_token = create_session_token(subject=subject, role=role, name=name)
    # The fragment is never sent to a server, so the token stays out of
    # access logs, browser history, and the Referer header. The frontend
    # callback page reads it client-side and clears the address bar.
    fragment_params = {"access_token": session_token}
    next_path = _sanitize_next(request.session.pop(_NEXT_SESSION_KEY, None))
    if next_path:
        fragment_params["next"] = next_path
    fragment = urlencode(fragment_params)
    return RedirectResponse(
        f"{settings.oidc_post_login_redirect}#{fragment}",
        status_code=status.HTTP_302_FOUND,
    )

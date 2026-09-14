"""This application's own signed session token.

OIT registers this app in Entra as a "Web" (confidential) client: the Entra
token is exchanged server-side and never reaches the browser, so it cannot
serve as the bearer token. The SSO callback mints this HS256 token instead,
which keeps the lifetime (`ACCESS_TOKEN_EXPIRE_MINUTES`) under this app's
control rather than Entra's.
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.auth.identity import SignedInRole, TokenIdentity
from app.config import settings

SESSION_TOKEN_ALGORITHM = "HS256"


def create_session_token(*, subject: str, role: SignedInRole, name: str) -> str:
    """Mint this app's signed session token for an authenticated identity."""
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "name": name,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=SESSION_TOKEN_ALGORITHM)


def decode_session_token(token: str) -> TokenIdentity:
    """Verify a session token and resolve it to a `TokenIdentity`, or raise 401."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[SESSION_TOKEN_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        return TokenIdentity(
            subject=payload["sub"], role=payload["role"], name=payload["name"]
        )
    except (KeyError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token is missing required claims.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

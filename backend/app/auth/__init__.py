"""Session-token identity for user sign-in.

Identity is proven once, at login, by Microsoft Entra (`app.api.v1.sso`).
The callback mints this application's own signed session token, and from then
on every request carries that token as a bearer token. `app.api.deps` resolves
it to a `SubmitterRole` exactly as it resolves the trusted proxy header, so no
router knows which login path is active.
"""

from app.auth.identity import TokenIdentity
from app.auth.session_tokens import create_session_token, decode_session_token

__all__ = ["TokenIdentity", "create_session_token", "decode_session_token"]

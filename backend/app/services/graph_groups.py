"""Read a user's Entra group memberships from Microsoft Graph.

Called during the SSO callback with the **signed-in user's own** delegated
token — never a functional/service account. That keeps this app to a single
Entra registration with no persisted MSAL cache to bootstrap or re-seed.

Why Graph at all, when Entra can put groups in the token: the `groups` claim
is only emitted when the app registration is configured for it, and
overflows to a lookup link past a few hundred groups. `OIDC_GROUP_SOURCE`
selects which mechanism this deployment uses.

Groups are matched by **object ID**, never display name. Display names are
not unique: anyone able to create a group could name one after the staff
group and be granted staff. Under `OIDC_GROUP_SOURCE=graph` the
`ENTRA_GROUP_*` settings therefore hold group object IDs, which config
validation enforces.
"""

import httpx

GRAPH_ORIGIN = "https://graph.microsoft.com/"
GRAPH_MEMBER_OF_URL = (
    # The `/microsoft.graph.group` type cast filters out directory roles and
    # administrative units server-side, so only real groups come back.
    "https://graph.microsoft.com/v1.0/me/memberOf/microsoft.graph.group"
    "?$select=id&$top=999"
)
REQUEST_TIMEOUT_SECONDS = 10.0
# A user in more pages than this is far outside anything this app expects;
# the bound stops a malformed nextLink chain from looping forever.
MAX_PAGES = 20


class GraphGroupLookupError(RuntimeError):
    """Graph could not be reached, or answered with an error.

    Distinct from "this user is in no mapped group" on purpose. An outage
    must surface as a failed sign-in, never as an authorization refusal —
    otherwise a Graph incident reads to every user as "you lost access".
    """


class GraphPermissionError(GraphGroupLookupError):
    """Graph refused us — the app lacks the scope, not the user the access.

    Separate because the two need opposite advice. An outage clears on its
    own and "try again shortly" is true; a missing or revoked permission is
    permanent, affects everyone, and needs an administrator. Telling someone
    to wait out a configuration error costs a day (GitHub #163).
    """


async def fetch_group_ids(access_token: str) -> list[str]:
    """Return the object IDs of every Entra group the user belongs to."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    group_ids: list[str] = []
    url: str | None = GRAPH_MEMBER_OF_URL

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        for _ in range(MAX_PAGES):
            if url is None:
                break
            try:
                response = await client.get(url, headers=headers)
            except httpx.HTTPError as exc:
                raise GraphGroupLookupError(
                    "Could not reach Microsoft Graph to read group membership"
                ) from exc

            if response.status_code in (
                httpx.codes.UNAUTHORIZED,
                httpx.codes.FORBIDDEN,
            ):
                # Microsoft understood us and said no: the app's registration
                # lacks GroupMember.Read.All, or consent was revoked. Waiting
                # cannot fix it, so it must not be reported as an outage.
                raise GraphPermissionError(
                    "Microsoft Graph refused the group-membership request "
                    f"(HTTP {response.status_code}) — the app registration is "
                    "missing consent for GroupMember.Read.All"
                )

            if response.status_code != httpx.codes.OK:
                raise GraphGroupLookupError(
                    "Microsoft Graph could not answer the group-membership "
                    f"request (HTTP {response.status_code})"
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise GraphGroupLookupError(
                    "Microsoft Graph returned a non-JSON response"
                ) from exc

            for item in payload.get("value") or []:
                if not isinstance(item, dict):
                    continue
                # Belt and braces: the URL already type-casts to groups, but
                # a mis-set URL should not silently promote a directory role
                # into a group ID.
                odata_type = item.get("@odata.type")
                if odata_type is not None and odata_type != "#microsoft.graph.group":
                    continue
                group_id = item.get("id")
                if isinstance(group_id, str) and group_id.strip():
                    group_ids.append(group_id)

            next_link = payload.get("@odata.nextLink")
            url = next_link if isinstance(next_link, str) else None
            if url is not None and not url.startswith(GRAPH_ORIGIN):
                # The user's delegated token rides on every page request;
                # a paging link to any other host would hand it away.
                raise GraphGroupLookupError(
                    "Microsoft Graph returned a paging link to another host"
                )

    return group_ids

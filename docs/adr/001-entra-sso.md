# ADR-001: Microsoft Entra SSO alongside the trusted-header boundary

## Status

Accepted

## Context

The application has run on a *trusted-header* boundary since the prototype:
the nginx container in front of the API stamps every request with
`X-Trusted-User-Role` and a shared secret, and FastAPI resolves that to one of
`public`, `staff`, `slc`, or `ops`. In the deployed environments
`TRUSTED_ROLE_HEADER_ROLE=staff`, so **anyone who can reach the URL is
staff** — the "Choose your view" landing page is a UI preference, not an
access decision. The SLC Leadership calendar, which the page describes as
private, is readable by every visitor.

OIT Identity & Access Management requires institutional sign-in through
Microsoft Entra ID and does not permit an application to build its own
authentication. The sibling campus-services-maintenance application already
implements this (its ADR-004) in a form OIT has reviewed.

Two things distinguish this application from that one:

1. **It has no login at all today**, and no user table. There is no
   "mint a session token at login" seam for SSO to plug into.
2. **Anonymous use is a feature.** Campus submitters send announcements
   without an account, and must keep doing so.

## Decision

Add Entra sign-in as a second way for a role to reach the API, selected by
`AUTH_PROVIDER`, without removing the header path:

- `AUTH_PROVIDER=header` (default) is exactly today's behavior.
- `AUTH_PROVIDER=oidc` mounts `GET /auth/sso/login`, `GET /auth/callback`,
  and `GET /auth/logout`, and adds Starlette's session middleware for
  authlib's OIDC state.

The application is registered in Entra as a **Web (confidential)** client. The
callback exchanges the code server-side, so the Entra token never reaches the
browser; the app mints its **own HS256 session token** carrying `sub`, `name`,
and `role`, and hands it to the SPA in the URL **fragment**, which is never
sent to a server. The SPA presents it as a bearer token thereafter.

`get_submitter_role` in `app/api/deps.py` reads the bearer token *ahead of*
the trusted header. That is the only behavioral change on the request path:
every `require_staff` / `require_staff_or_slc` / `require_staff_or_ops`
dependency and every router is untouched. A token that is present but invalid
is a **401, never a fall-through to `public`** — an expired staff session must
surface as "sign in again", not as a silent downgrade that turns the next save
into a 403.

Roles come from Entra **App Roles** on the registration by default
(`OIDC_GROUP_SOURCE=claim`), mapped highest-privilege-first: `staff` > `slc` >
`ops`. There is **no default role**: a signed-in user in no mapped group is
refused with a `not_authorized` reason. Anonymous users already have `public`
without signing in, so the refusal costs them nothing. The Graph
`/me/memberOf` path is retained as `OIDC_GROUP_SOURCE=graph` in case OIT
provisions security groups instead.

**No user table.** The role is resolved from Entra on every sign-in and
carried in the token. Nothing about a person is persisted, so there is no
migration, and rollback is a config change.

On the frontend, the landing page's four cards become the sign-in entry:
Submitter view stays open; the other three hand an anonymous visitor to
Microsoft. `getSubmitterRole()` prefers the token's role over the URL
heuristic, which is how every existing page becomes role-aware without being
edited. A `RequireRole` guard sends anonymous or under-privileged deep links
back to the landing page; it is a UX guard only, since the API decides.

### Rollout on a live deployment

Because the default is `header`, the code deploys to production as a no-op.
The production boot check therefore only **warns** under `header` mode; it
hard-fails only an *incomplete* `oidc` configuration (missing Entra settings,
default `SECRET_KEY`, `localhost` or plain-http redirect URLs, a
`SESSION_COOKIE_SECRET` equal to `SECRET_KEY`). Once production is on `oidc`,
a follow-up should turn the warning into a refusal.

## Consequences

**Good**

- The client secret stays server-side; an XSS yields only an app-scoped
  session token, never an Entra token.
- Token lifetime and role mapping are under this application's control.
  Renaming an App Role in Entra is a config change.
- The SLC calendar and editor tools are gated on a verified identity for the
  first time, while the public submission path is unchanged.
- Matching the sibling application's OIT-reviewed design should shorten this
  application's own review.

**Costs and risks**

- A role revoked in Entra survives in an outstanding token until it expires
  (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 480). Accepted for an internal tool
  with a small user base; revisit if OIT asks for per-request revocation, which
  would need a user table.
- OIT issues a **24-month client secret**; sign-in stops the day it lapses. The
  rotation date belongs in `docs/deployment.md`.
- Sign-out has to end two sessions. Clearing the app token alone leaves Entra's
  cookie, so the next person at a shared office computer would be signed in as
  the last one. `prompt=select_account` on every sign-in and a sign-out that
  goes through Entra's `end_session_endpoint` address both halves.
- While both paths coexist, a deployment could run `oidc` with
  `TRUSTED_ROLE_HEADER_ROLE=staff` still set. The bearer token wins when
  present, but an anonymous visitor would still get staff from the header. The
  deployment doc says to blank it; the follow-up hardening should refuse it.

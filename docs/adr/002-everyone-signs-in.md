# ADR-002: Everyone signs in, and the role picks the view

## Status

Accepted. Under `AUTH_PROVIDER=oidc` this supersedes every part of
[ADR-001](001-entra-sso.md) that relies on anonymous submission:

- context point 2, "Anonymous use is a feature";
- the "no default role" paragraph and its `not_authorized` refusal;
- the landing-page paragraph, where the Submitter view "stays open" and only
  the other views hand visitors to Microsoft;
- the consequence that "the public submission path is unchanged".

The rest of ADR-001 stands: token handling, the per-mode credential rule, and
header mode, which still allows anonymous submission.

## Context

Under ADR-001, only people holding a UCM App Role could sign in. Campus
submitters used the submission form anonymously, so the landing page had to
offer two paths: "Submit an item" without signing in, and a separate staff
sign-in. The project owner wants one simple landing page with a single
University sign-in, with each person sent to the view their role allows.

## Decision

Under `AUTH_PROVIDER=oidc`, every University account can sign in. An account
with no mapped App Role receives the `submitter` role instead of being refused
with `not_authorized`.

- `submitter` grants exactly what anonymous `public` callers had:
  `get_submitter_role` resolves it to `public`, so every existing check,
  allowed-value scope and redaction rule is unchanged.
- `POST /api/v1/submissions/` and `POST /api/v1/feedback` require a signed-in
  identity under `oidc` (`require_signed_in_under_sso`). Anonymous calls get
  `401`. Read-only public metadata (schedule, sections, allowed values) stays
  open, because the landing page and form read it.
- After sign-in, `staff` lands on the dashboard and `submitter` on the
  submission form, which is pre-filled with the person's name and University
  email. There is no view picker.
- `AUTH_PROVIDER=header` deployments, including local development, have no
  sign-in and keep anonymous submission.

The Entra registration is single-tenant (`ENTRA_METADATA_URL` names the
University tenant), so only University accounts and the tenant's guests can
sign in.

## Consequences

- Submitters without a University account can no longer submit. UCM staff can
  still enter those items themselves.
- Entra must let every tenant user sign in to the app. If the enterprise
  application has "Assignment required" turned on, unassigned users are stopped
  by Microsoft before reaching the app; an administrator must turn it off or
  assign a default group.
- Submitter name and email are pre-filled but stay editable, so they remain
  self-reported. Recording the signed-in subject on each submission would be a
  separate schema change.
- The `not_authorized` callback reason is no longer produced. The frontend keeps
  its message for old links.

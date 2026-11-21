# Risk assessment

Prepared 2026-11-20 for the OIT security review. Reviewed against `main` at
`52d156d`. Two related pull requests were open when this was written and are
marked "pending merge" where they change a control: #550 (record the signed-in
account on each submission) and #551 (opt-in off-host backup copy).

This register states risks and controls at the level a reviewer needs. It does
not describe how to exploit an open weakness. Report suspected vulnerabilities
privately as described in `SECURITY.md`.

## Scope and system summary

UCM Daily Register is the University Communications and Marketing (UCM) tool
for producing two newsletters: The Daily Register (faculty and staff) and My UI
(students). University users sign in with Microsoft Entra SSO and submit
announcements. UCM staff review AI-suggested edits, schedule items, build
editions and export them to Word.

| Item | Value |
| --- | --- |
| Tier | Enterprise (Entra SSO, staff and student users) |
| Hosting | IIDS-hosted on `openera.insight.uidaho.edu`, by agreement with OIT (Trevor). OIT cluster delivery tooling does not apply. |
| Components | nginx frontend (only host port: 9280 prod, 9290 dev), FastAPI backend on an internal Docker network, PostgreSQL in the shared `insight-db` container, a Docker volume for uploaded images |
| AI processing | MindRouter, the University-run AI service, only. Off-campus providers were removed on 2026-11-20. |
| Inbound data | University Trumba calendar feed; single job pages on the University careers site (PageUp), fetched only when staff paste a link |
| In scope | Production and dev deployments, backups on openera, the GitHub repository and CI |
| Out of scope | Campus network and ingress, Entra itself, MindRouter itself, the `insight-db` host beyond this app's databases |

Architecture and data flows: [Architecture](../architecture.md) and the data
flow diagrams in this folder.

## Method

Each risk is scored for **likelihood** and **impact** on a 1–3 scale.

| Score | Likelihood | Impact |
| --- | --- | --- |
| 1 | Unlikely in a year | Minor: little or no personal data, short disruption |
| 2 | Possible in a year | Moderate: limited personal data or a missed edition |
| 3 | Likely in a year | Major: broad disclosure or loss of Moderate-tier data, or extended outage |

**Rating = likelihood × impact.** 1–2 is Low, 3–4 is Medium, 6–9 is High.
Scores describe the residual risk with the listed controls in place.

## Data summary

The canonical inventory is the governance catalog,
`frontend/src/data/governance-catalog.json`, published as the
[Data Dictionary](../governance/data-dictionary.md). Under APM 30.11 the
application is proposed as **Moderate**: 194 columns are Low and 30 are
Moderate (counts before #550, which adds one Moderate column). Moderate data is
mainly submitter contact details, free-text submission copy and notes that can
contain incidental personal information, and the audit trail's account
references. Classifications are provisional until the Data Owner reviews them
([Decisions](../governance/decisions.md)).

## Risk register

| ID | Risk | L | I | Rating | Existing controls | Residual risk and plan | Owner |
| --- | --- | :-: | :-: | --- | --- | --- | --- |
| R1 | Someone gets staff access they should not have, through a wrong Entra group assignment or a role mapping error | 1 | 3 | Medium (3) | Entra SSO for everyone (ADR-001, ADR-002). Roles come from Entra app roles or groups matched by object ID, never display name. A Graph lookup failure fails sign-in instead of downgrading or granting a role. Staff routes require the staff role; `deploy.sh` checks that they refuse anonymous callers. Authorization failures are recorded in the audit trail. | Group membership is managed outside the app. A role removed in Entra still works until the user's session token expires (up to 8 hours). Plan: UCM confirms who manages the staff group and reviews membership each term. | Data Owner (UCM); IIDS maintainer for mapping |
| R2 | A stolen session token is used to act as that user | 1 | 3 | Medium (3) | Tokens are signed (HS256) with a secret the app refuses to start without (minimum 32 characters, not the default). Expiry is 8 hours (`ACCESS_TOKEN_EXPIRE_MINUTES`). The CSP allows scripts only from the app's own origin. The sign-in state cookie lasts 10 minutes and is HTTPS-only in production. Sign-out ends the Entra session. | **Disclosed gap:** the token is kept in browser `localStorage`, and there is no server-side session revocation; a token stays valid until it expires. Emergency response is rotating `SECRET_KEY`, which signs everyone out ([Runbook](../runbook.md#rotate-secrets)). Plan: decide whether to shorten expiry or add revocation. | IIDS maintainer |
| R3 | Personal information in submission text is processed by the AI service | 2 | 2 | Medium (4) | Only MindRouter, the University-run service, is accepted (`LLM_PROVIDER=mindrouter`); Anthropic and OpenAI were removed on 2026-11-20. Dedicated contact fields (submitter name and email) are not put into prompts. | Free text, notes and links are sent as written; there is no automatic removal of personal information. No approval reference for MindRouter as the processor is recorded yet. Plan: record OIT/Data Owner approval of MindRouter and its retention terms in [Decisions](../governance/decisions.md). | Data Owner (UCM) with OIT |
| R4 | Instructions hidden in submission text steer the AI edit (prompt injection) | 2 | 1 | Low (2) | The AI only proposes text; the model has no tools and no access to other data. Its reply must parse as structured JSON. Every edit is shown to staff as a diff, and nothing is approved or published without a staff action. | A misleading edit could get past a rushed reviewer. Plan: none beyond staff review; keep the model tool-free. | UCM editors |
| R5 | Data is lost and cannot be recovered | 2 | 3 | High (6) | Nightly backups of prod (02:30) and dev (02:40): database dump checked with `pg_restore --list`, uploads archive, manifest with checksums. `backup.sh --check` reports staleness. A dev restore exercise passed on 2026-11-03. Pre-deploy dumps are taken before prod releases. | Backups sit on the same server as the database, so losing openera loses both. No failure alerting. Prod restore has not been rehearsed in an isolated environment. Plan: name the second IIDS server and enable the off-host copy (built in #551, pending merge); add alerting; run a prod restore exercise. | IIDS maintainer; Barrie Robison (accountable) |
| R6 | Backup files expose personal information | 1 | 3 | Medium (3) | Backup directories are mode 700 under the `devops` account. Encryption to an off-server public key is built into `backup.sh`. The off-host copy (#551) refuses unencrypted files unless that is explicitly allowed. | **Disclosed gap:** encryption is not switched on; the key decision is on hold. Anyone with `devops` access or a server snapshot can read backups. Nothing is pruned (expiry awaits Data Owner approval). | Barrie Robison (accountable) |
| R7 | Secrets leak, or are lost or expire | 2 | 2 | Medium (4) | Secrets live only in server environment files (mode 600), never in Git. CI rejects tracked environment files and runs a secret scan on every push. Docker build contexts exclude environment files. | Environment files are not backed up; losing them means reissuing secrets. The Entra client secret expires 24 months after issue and sign-in stops when it does. Plan: store the environment files in an approved vault; calendar the client-secret expiry. | IIDS maintainer |
| R8 | The audit trail is altered or not reviewed | 1 | 2 | Low (2) | An append-only `audit_events` table records reads by staff, all writes, refusals and sign-ins, with the Entra object ID and role, and no content. The app never updates or deletes rows. | The table is in the application database, so anyone with database write access could alter it. No off-host copy, alerting or scheduled review. Plan: decide on a review cadence; consider shipping events off-host. | IIDS maintainer; Data Owner (UCM) for review |
| R9 | A vulnerable dependency is deployed | 2 | 2 | Medium (4) | Dependabot watches npm, uv (Python), Docker base images and GitHub Actions. CI checks that `uv.lock` matches `pyproject.toml` and runs lint, tests and migrations on SQLite and PostgreSQL. | No vulnerability scan or SBOM is produced from each release; files in `sbom/` are dated snapshots. Plan: add a release-bound SBOM and vulnerability scan. | IIDS maintainer |
| R10 | The service is unavailable when an edition is due | 2 | 2 | Medium (4) | Containers restart automatically; the backend health check uses `/api/v1/readyz`. `deploy.sh` smoke-tests each release. AI work is queued with limits and survives restarts as failed tasks staff can retry. | One VM, one backend process, no failover. The database host is shared with other IIDS apps. Plan: accept for current use; the [Runbook](../runbook.md) covers recovery. | IIDS maintainer |
| R11 | Script injection or framing in the browser exposes a session | 1 | 3 | Medium (3) | React escapes rendered text. nginx sends a Content-Security-Policy (scripts from the app's origin only, `object-src 'none'`, `frame-ancestors 'none'`), `X-Frame-Options: DENY`, `nosniff`, a referrer policy and a permissions policy. | The campus ingress rewrites `X-Frame-Options` to allow framing from `www.uidaho.edu`. The CSP `frame-ancestors 'none'` still blocks framing in current browsers. Plan: ask OIT whether the ingress rewrite can be dropped for this host. | IIDS maintainer with OIT |
| R12 | A malicious or oversized image upload | 1 | 2 | Low (2) | Uploads are limited to staff, to five image types, to 10 MB and 36 megapixels. Files are checked as real images of the declared type, metadata (EXIF) is stripped, GIFs are re-encoded, and files get random names. nginx caps request bodies at 12 MB. | Low. | IIDS maintainer |
| R13 | Bad data arrives from an external source (calendar feed, careers site) | 1 | 1 | Low (1) | Sources are fixed University sites. Requests have timeouts. Job lookups accept only job pages on the configured careers host and do not follow redirects. Imported text goes through staff review before publication. | Low. Plan: review XML parser hardening for the calendar feed at the next dependency review. | IIDS maintainer |
| R14 | Retired features (SLC calendar, Event Services triage) are still deployed | 1 | 1 | Low (1) | Their API routes are not mounted, the pages are hidden, and the scheduled harvest has been paused since 2026-11-03. | Their code and stored data remain until the Phase 2 removal exports the data. Plan: finish removal after data export is agreed. | Barrie Robison (accountable) |
| R15 | Data is kept longer than needed, or handled under the wrong classification | 2 | 2 | Medium (4) | Retention categories and a disposal procedure are drafted ([Retention](../governance/retention.md)). Classifications and APM 30.11 tiers are recorded per column. | Classification is provisional and no automatic retention or disposal job is approved, so submissions, audit events and backups accumulate. Plan: Data Owner review of the catalog and retention periods. | Data Owner (UCM) |
| R16 | Nobody can support the app if the maintainer is unavailable | 2 | 2 | Medium (4) | Code, docs, runbook and decisions are in the repository; deploys are one script; CI covers tests and governance checks. | One primary maintainer; named on-call coverage is not recorded. Plan: name a second operator with server access and walk them through the [Runbook](../runbook.md). | Barrie Robison (accountable) |
| R17 | A submission is made in someone else's name | 2 | 1 | Low (2) | Everyone signs in before submitting. The audit trail records the account behind each submission request. | The name and email on the form are free text. #550 (pending merge) stores the signed-in account's object ID on each submission. | IIDS maintainer |
| R18 | A signed-in user floods the app with requests | 1 | 2 | Low (2) | Sign-in is required. AI edits are capped (2 running, 50 queued; extra requests get 503). Uploads are size-limited. | No general request rate limiting in the app. Plan: rely on ingress limits; revisit if abuse appears. | IIDS maintainer |

## Summary

| Rating | Risks |
| --- | --- |
| High | R5 |
| Medium | R1, R2, R3, R6, R7, R9, R10, R11, R15, R16 |
| Low | R4, R8, R12, R13, R14, R17, R18 |

The one High risk, data loss, drops to Medium once the off-host copy is running
and a prod restore has been rehearsed. Most Medium risks depend on decisions
outside the code: Data Owner review of classification and retention, recorded
approval of MindRouter, a backup encryption key, and a second operator.

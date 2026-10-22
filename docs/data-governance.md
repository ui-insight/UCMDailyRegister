# Data governance and privacy

Reviewed against repository code on **October 22, 2026**. This describes the
implemented application; it does not attest to live production configuration or
institutional approval. Accountable people and approval references are tracked in
[Governance decisions](governance/decisions.md).

## Data inventory and classification

The [data dictionary](governance/data-dictionary.md) inventories every ORM table
and column. Its machine-readable source also drives the staff governance page.
Classification is provisional until the Data Owner and institutional reviewers
approve the mapping to APM 30.11; local labels are not institutional approval.

| Local handling label | Working definition | Examples |
| --- | --- | --- |
| Public | Reviewed content approved for public release, or public reference data | Published issue copy, public calendar feed, category labels |
| Internal | Working or operational data available to authorized roles | Unpublished copy, SLC-only event details, ops verdicts, AI provenance |
| Confidential | Contact information, free text with incidental personal information, or credentials | Submitter/contact email, notes, feedback details, identity claims, session tokens |
| Restricted | Placeholder for information requiring additional institutional controls | No intentional collection; unexpected sensitive content needs incident review |

Unpublished content is not classified Public solely because it may later be
published. Treat mixed datasets and generated output according to the most
sensitive content present. Free-text fields, links, JSON flags, and images can
contain information beyond their intended purpose.

## Personal and authentication data

| Data | Location | Purpose and access | Lifecycle |
| --- | --- | --- | --- |
| Submitter name/email | `submissions` | Editorial follow-up; staff, and caller's creation response | Submission retention category |
| Submitter notes; editorial notes; assigned editor | `submissions` | Instructions and responsibility; staff; submitter notes returned to creator | Submission retention category |
| Repeat/flexibility notes | `submission_schedule_requests` | Scheduling; staff; possibly incidental personal information | Parent submission |
| Headline/body, links, images | Submissions, versions, placements, upload volume | Editorial work; may contain contact or sensitive information embedded by users | Source vs published snapshot policies differ |
| Editor instructions; findings and change summaries | `edit_versions` | AI/human revision context; staff; may repeat input text | Source history category |
| Feedback email, summary/details, route, host, browser, viewport, reported role | `product_feedback` | Product support; staff; creation response returned to caller | Feedback category; reported role is client context, not verified identity |
| Email/username subject, display name, mapped role | Entra/Graph exchange; signed app JWT; browser localStorage | Sign-in and authorization | JWT defaults to 480 minutes; browser token removed on local sign-out or next load detecting expiry |
| OIDC state and next-path context | Signed browser session cookie; transient server memory | Bind authorization flow to browser | Starlette session cookie defaults to 14 days; verify cookie policy during deployment review |
| Entra tokens/group claims | Transient backend memory during sign-in | Validate identity; optionally query Graph `/me/memberOf` | Not intentionally stored as database records or forwarded to the SPA |
| API keys, DB credentials, signing/client secrets | Runtime environment and deployment secret files | Backend/provider access | Rotate per owner-approved secrets procedure; never submit in forms |

There is no user table. This does not mean identity data is absent or that nothing
is persisted: the browser stores the app JWT, including identifiable claims.
JWT expiry ends authorization; it does not remotely erase localStorage on an
inactive browser. Signed cookies and JWTs are not encrypted storage.

The app does not intentionally request student IDs, education records, health or
financial records, passwords, or government identifiers. Free text and uploads
can still contain them. FERPA scope and directory-information treatment require
institutional privacy review; no categorical legal conclusion is asserted here.
If unexpected protected content is found, stop further sharing and follow the
incident procedure below.

## Authentication and authorization

`AUTH_PROVIDER=oidc` uses Entra's confidential-client authorization-code flow.
The backend verifies the response, maps App Roles (or Graph groups), and issues
an HS256 app JWT. Only bearer credentials count in this mode. Unmapped users
are refused; role changes take effect at next sign-in or token expiry. Browser
sign-out clears local state and goes through Entra logout. There is no
per-token revocation service.

`AUTH_PROVIDER=header` accepts `X-Trusted-User-Role` only with the configured
`X-Trusted-Auth-Secret`. Bearer tokens do not grant access in this mode.
`X-User-Role` is rejected. The frontend proxy overwrites trusted headers. If the
proxy asserts `staff` for every request, **everyone who can reach it receives
staff access**. This is a prototype boundary, not evidence of individual sign-in.
Production should use OIDC; verify actual enablement separately for each host.
See [Deployment](deployment.md) and [ADR-001](adr/001-entra-sso.md).

All paths below are under `/api/v1`. Public means no identity credential is
required; it does not imply that every column in a response is approved for
publication.

| Dataset / route family | Public | SLC | Ops | Staff |
| --- | --- | --- | --- | --- |
| `POST /submissions/` | Create with permitted public category; receives own created response | Create with permitted category | Create with permitted category | Create with permitted category |
| `/submissions/` list/detail, updates, links, schedules, images, deletes | No | No general access | No | Read/change/delete |
| `GET /submissions/?slc_calendar_only=true` | No | Read; dedicated submitter name/email/notes and editorial fields redacted | No | Read including staff fields |
| `/slc/harvest`, `/slc/harvested-events` and triage/acknowledgment | No | Read, harvest, change SLC review; flagging creates SLC-only submission | No | Same |
| `/ops/harvested-events` and needs/verdicts/acknowledgment | No | No | Read, change ops review; add/remove staff-origin needs; confirm/reject AI needs | Same |
| `/ai-edits`, `/newsletters` including imports/exports, `/recurring-messages`, `/style-rules` | No | No | No | Read/change according to endpoint |
| `POST /feedback` | Create; receives created record | Same | Same | Same |
| Feedback list/summary/update, notification retry, GitHub export preparation | No | No | No | Yes |
| Allowed values, sections, schedule GETs, `/settings/ai` | Read; category visibility filtering applies to allowed values | Read | Read | Read |
| Schedule POST/DELETE | No | No | No | Yes |
| `/health`, `/readyz`, `/auth/config` | Read | Read | Read | Read |
| `/auth/me` | No | Own valid bearer identity in OIDC mode | Same | Same |

SLC redaction removes dedicated contact fields, not names/emails embedded in event
copy or links. Staff inherit both triage capabilities; SLC and ops are separate
roles. Current settings/sections/schedule read endpoints are public; they must
contain no secrets. API responses, permission tests, and the
[API reference](api-reference.md) are the implementation evidence.

## Data flows and external processing

1. A public or authorized caller submits copy, contact fields, notes, links and
   dates through React → nginx → FastAPI → database. Staff can upload an image.
2. Staff trigger newsletter editing. Active DB style rules form the system
   prompt. The user prompt contains headline/body, category, submitter notes,
   **provided links including URLs/parameters**, and editor instructions. A
   compliance repair request can resend the original input, generated draft and
   deterministic findings. Dedicated submitter name/email, assignment, and
   editorial notes columns are not explicitly inserted, but personal data in
   content is not automatically sanitized. Returned copy, flags, change summaries,
   model/provider and editor instructions may persist in edit history.
3. Trumba calendar pages/feed and PeopleAdmin postings are fetched on demand.
   SLC harvesting upserts structured JSON-feed occurrences in `harvested_events`.
   SLC flagging promotes an event into a submission and records its provenance.
4. A harvest queues ops classification in the background. A separate MindRouter
   provider receives title, description (up to 4,000 characters), location and
   category. It uses `OPS_CLASSIFIER_*`, with endpoint/key falling back to
   `MINDROUTER_*`; it is independent of `LLM_PROVIDER`. Needs/confidence/rationale
   and staff verdicts persist. Rationale may quote source text. Staff judgments
   survive reassessment; assessment content hashes identify source versions.
5. Approved submissions and external/recurring items become issue snapshots.
   Staff download Word exports. Dedicated contact columns and internal metadata
   are not automatically exported, but contact text intentionally in copy remains.
6. Feedback stores submitted free text and lightweight browser context. Its
   notifier is disabled. Staff may prepare GitHub Markdown containing report
   details and context; **review/redact before opening or publishing a GitHub
   issue**, including the URL prefill sent to GitHub. No automatic external
   delivery is enabled. Future notifier payloads can contain summary and optional
   contact email and require destination approval.

| Processor | Configured use | Evidence required before an institutional assurance |
| --- | --- | --- |
| Anthropic / OpenAI | Selected newsletter editor; local default is Claude | Approved processor/model, endpoint and account configuration, contract retention/training/residency terms, external sharing authorization |
| MindRouter | Optional newsletter editor; dedicated ops classifier | Approved endpoint/model and operating controls; configurable URLs alone do not prove campus-only routing |
| Microsoft Entra / Graph | Sign-in and optional group lookup | Registration/consent, scopes, role assignments, secret ownership and rotation |
| Trumba / PeopleAdmin | Public source reads | Source purpose, endpoint inventory and operational limits |
| GitHub | Source control and optional staff-prepared feedback export | Approved access and export review; protected data excluded |

No external-provider residency or zero-retention claim follows from source code.
No-training terms, where agreed, do not imply zero retention. Processor approval
references remain pending in the decision register. See [AI editing](ai-editing.md).

## Uploads and minimization

JPEG, PNG, GIF and WebP uploads are UUID-named in the upload volume. Supported
still images are decoded and rewritten without metadata; processing failure
rejects the upload. GIF does not receive the same EXIF rewrite. Image content can
itself identify people. Deleting a submission through the existing endpoint does
not currently guarantee upload-file disposal; use the reviewed disposal design
rather than claiming endpoint deletion meets retention policy.

Do not put protected records or credentials in content, links, notes or feedback.
Review free text before AI processing/publication/export. Automated PII detection
and source-wide sanitization are not implemented and would not guarantee removal.

## Retention, logging and ownership

[Retention and disposal](governance/retention.md) distinguishes proposed periods
from enforced behavior, documents source/archive dependencies, and provides a
read-only inventory command. No automatic purge is enabled. The Data Owner must
resolve periods, holds and academic-year boundaries before destructive scheduling.

[Audit logging](audit-logging.md) specifies minimized diagnostics, Docker limits,
remaining access-audit work, and unverified aggregation/retention targets.
[Backup and recovery](backup-and-recovery.md) describes versioned backup and
release-specific recovery procedures; job installation and restore proof remain
operational evidence to collect.

The [decision register](governance/decisions.md) records accountable-role vacancies,
classification, processor, dev/test, tooling and approval decisions. Never treat a
blank approval reference as approval. Schema changes must update ORM, migrations,
API/types, catalog, vocabulary baseline and docs in the same review; run the
repository governance check before merging.

## Incident handling

If protected or unexpectedly sensitive content is exposed or submitted, pause
further AI/export/publication, restrict access, preserve minimized evidence and
notify the University Information Security Office through the established campus
process. Coordinate with the technical owner and UCM; do not copy the content into
GitHub, chat or email during investigation. Determine scope, containment and any
notification obligation with authorized institutional responders. Use the recovery
runbook for service restoration and record a post-incident review.

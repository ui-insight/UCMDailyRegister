# Data Flow Diagrams

Prepared for the OIT security review (see [OIT Security Review Prep](../oit-security-review-prep.md)).
Checked against the code on `main` at `52d156d` (2026-11-20). Two changes
pending merge are marked where they apply:

- **PR #550:** `submissions.Submitter_Account_Ref`, the Entra object ID of the
  account that sent each submission.
- **PR #551:** an opt-in off-host copy of backups to a second IIDS server. Not
  enabled.

Handling labels (Public / Internal / Confidential) come from
[Data Governance](../data-governance.md). APM 30.11 tiers come from the
[governance catalog](../governance/data-dictionary.md). The tiers are
**proposed** (issue #176) until the Data Owner approves them. The application
as a whole is proposed **Moderate**.

What is in scope: the newsletter app as deployed on dev and prod. The SLC
calendar harvest and the Ops needs classifier are retired. Their API routes are
not mounted (`backend/app/api/v1/router.py`) and the SLC harvest cron lines on
openera have been commented out since 2026-11-03. Their code and tables stay
until the Phase 2 removal exports the data. They are listed in
[Retired flows](#retired-flows) and are not drawn.

## 1. System context

```mermaid
flowchart LR
  subgraph USER["Trust boundary: user device"]
    B["Browser<br/>React app<br/>app JWT in localStorage"]
  end

  subgraph CAMPUS["Trust boundary: campus ingress, TLS terminates here"]
    ING["Campus reverse proxy<br/>ucmnews.insight.uidaho.edu<br/>ucmnews-dev.insight.uidaho.edu"]
  end

  subgraph OPENERA["Trust boundary: openera VM, IIDS-managed"]
    subgraph DNET["Docker network 10.x, internal only"]
      FE["frontend container<br/>nginx, host port 9280 prod / 9290 dev<br/>static build + CSP"]
      BE["backend container<br/>FastAPI uvicorn :8001<br/>no host port"]
      UP[("uploads volume<br/>submission images")]
    end
    subgraph DBNET["Docker network insight-db-net, shared"]
      DB[("PostgreSQL insight-db<br/>ucm_newsletter / ucm_newsletter_dev")]
    end
    BK[("Host backups<br/>~/backups/ucmnews-env<br/>nightly cron")]
  end

  subgraph UOFI["University-run services"]
    ENTRA["Microsoft Entra ID<br/>+ Microsoft Graph"]
    MR["MindRouter<br/>mindrouter.uidaho.edu"]
    TR["Trumba calendar feed"]
    PU["PageUp careers site<br/>careers.uidaho.edu"]
  end

  subgraph EXT["Outside the University"]
    GH["GitHub<br/>ui-insight/UCMDailyRegister"]
    GF["Google Fonts"]
  end

  B -->|"HTTPS: submissions, staff edits, feedback<br/>Confidential, Moderate"| ING
  ING -->|"HTTP to host port"| FE
  FE -->|"proxy /api/ : JSON + bearer JWT"| BE
  BE -->|"SQL, no TLS on the Docker network<br/>Confidential, Moderate"| DB
  BE -->|"image files"| UP
  B -->|"OIDC redirect sign-in"| ENTRA
  BE -->|"HTTPS: code exchange, memberOf by group ID<br/>Internal"| ENTRA
  BE -->|"HTTPS + API key: submission copy, links, notes, style rules<br/>Moderate"| MR
  BE -->|"HTTPS GET, public events<br/>Public, Low"| TR
  BE -->|"HTTPS GET, one job page per staff paste<br/>Public, Low"| PU
  B -->|"staff opens prefilled new-issue URL<br/>reviewed text only"| GH
  B -->|"font CSS and files, no app data"| GF
  DB -->|"pg_dump"| BK
  UP -->|"tar, read-only mount"| BK
```

Notes:

- Only the frontend container publishes a host port. The backend and database
  are reachable only on Docker networks (`docker-compose.yml`).
- Encryption in transit: browser to campus ingress is HTTPS. Ingress to the
  nginx host port, nginx to the backend, and the backend to PostgreSQL are
  plain HTTP/SQL inside the VM. Backend calls to Entra, Graph, MindRouter,
  Trumba and PageUp are HTTPS.
- nginx sends a Content Security Policy (`frontend/nginx.conf`) that allows
  scripts and API calls only from the app's own origin, fonts and font CSS from
  Google Fonts, and `frame-ancestors 'none'`.
- No email, SMTP, Teams or webhook path exists. The feedback notifier is a
  disabled stub (`FEEDBACK_NOTIFICATION_CHANNEL` only accepts `disabled`).

## 2. Sign-in, session tokens and audit trail

```mermaid
flowchart LR
  subgraph USER["User device"]
    B["Browser"]
    LS[("localStorage<br/>app JWT, 480 min default")]
    CK[("OIDC state cookie<br/>10 min, HttpOnly, SameSite=Lax")]
  end
  subgraph OPENERA["openera Docker networks"]
    SSO["/api/v1/auth/sso/*<br/>authlib, mounted only when AUTH_PROVIDER=oidc"]
    DEP["deps.get_current_identity<br/>verifies JWT on each request"]
    AUD["AuditTrailMiddleware"]
    AE[("audit_events<br/>Confidential, Moderate")]
  end
  ENTRA["Microsoft Entra ID"]
  GRAPH["Microsoft Graph<br/>/me/memberOf"]

  B -->|"1 start sign-in"| SSO
  SSO -->|"2 state cookie"| CK
  B -->|"3 authorize redirect"| ENTRA
  ENTRA -->|"4 code"| SSO
  SSO -->|"5 code + client secret, HTTPS"| ENTRA
  ENTRA -->|"6 ID token: email, name, oid, groups"| SSO
  SSO -->|"7 optional, user's own delegated token"| GRAPH
  GRAPH -->|"group object IDs"| SSO
  SSO -->|"8 app JWT: email, role, name, oid<br/>in URL fragment"| B
  B --> LS
  B -->|"bearer JWT"| DEP
  DEP --> AUD
  SSO -->|"sign_in_success / failure"| AE
  AUD -->|"oid, role, route template, record IDs, changed field names"| AE
```

| Item | Detail |
| --- | --- |
| Data stores | `audit_events` (append-only by convention). Browser localStorage holds the app JWT; the Entra token never reaches the browser. |
| External entities | Microsoft Entra ID, Microsoft Graph (only when `OIDC_GROUP_SOURCE=graph`). |
| Crosses boundaries | Browser ↔ Entra: OIDC redirect. Backend ↔ Entra: code exchange with client secret. Backend → Graph: group IDs for the signed-in user. Backend → browser: signed app JWT. |
| Controls | Roles mapped from Entra group **object IDs**, not display names (`graph_groups.py`). Graph pagination is restricted to `graph.microsoft.com`. JWT verified per request; an invalid or expired token is a 401, never a silent drop to the public role. Tokens are honored only under `AUTH_PROVIDER=oidc`. Audit rows store the `oid`, not email, and no content, query strings, IPs or user agents ([Audit Logging](../audit-logging.md)). |
| Gaps | No server-side session revocation: a JWT stays valid until it expires. The audit table is in the app database, not an off-host or tamper-evident store. |

## 3. Submission intake

```mermaid
flowchart LR
  B["Browser<br/>signed-in submitter or staff"]
  subgraph OPENERA["openera Docker networks"]
    API["POST /api/v1/submissions/<br/>require_signed_in_under_sso"]
    IMG["POST /submissions/id/image<br/>require_staff"]
    S[("submissions, submission_links,<br/>submission_schedule_requests<br/>Confidential, Moderate")]
    UP[("uploads volume<br/>UUID file names")]
    AE[("audit_events")]
  end

  B -->|"headline, body, contact name and email, notes,<br/>links, requested dates<br/>Confidential, Moderate"| API
  API -->|"plus Submitter_Account_Ref = oid from JWT<br/>pending PR #550"| S
  API -->|"record_change"| AE
  B -->|"staff only: image file"| IMG
  IMG -->|"verified image, EXIF and GIF metadata stripped"| UP
  IMG -->|"Image_Path"| S
```

| Item | Detail |
| --- | --- |
| Data stores | `submissions`, `submission_links`, `submission_schedule_requests`, uploads volume. |
| External entities | None. |
| Crosses boundaries | Browser → backend only. |
| Controls | Under SSO everyone signs in before submitting (ADR-002). Category, recurrence and "repeat indefinitely" options are checked against the caller's role server-side. Listing, detail, edit, delete and image read are `require_staff`. Non-staff list responses redact PII. Image upload is staff-only. Every write is an audit event. Pending PR #550: the submitting account's `oid` is stored from the token, never the request body, and is not returned by any API. |
| Gaps | Free-text fields can hold personal information the submitter typed; nothing strips it. |

## 4. AI editing pipeline

```mermaid
flowchart LR
  B["Browser, staff"]
  subgraph OPENERA["openera Docker networks"]
    API["POST /ai-edits/submission_id/edit<br/>require_staff"]
    Q[("ai_edit_tasks<br/>durable queue<br/>Confidential, Moderate")]
    W["ai_edit_service worker<br/>in the backend process"]
    SR[("style_rules<br/>Internal, Low")]
    S[("submissions + links<br/>Confidential, Moderate")]
    EV[("edit_versions<br/>Confidential, Moderate")]
  end
  MR["MindRouter<br/>mindrouter.uidaho.edu/v1/chat/completions<br/>University-run"]

  B -->|"edit request, optional editor instructions"| API
  API --> Q
  Q --> W
  SR -->|"active rules"| W
  S -->|"headline, body, notes, links"| W
  W -->|"HTTPS + bearer API key:<br/>system prompt = style rules<br/>user prompt = category, submission date, headline,<br/>body, submitter notes, link URLs and anchor text,<br/>editor instructions<br/>Moderate"| MR
  MR -->|"JSON: edited copy, flags, changes"| W
  W -->|"repair pass if checks fail:<br/>original input + draft + findings"| MR
  W -->|"draft, flags, change summary, model name"| EV
  W -->|"result or error"| Q
```

| Item | Detail |
| --- | --- |
| Data stores | `ai_edit_tasks`, `edit_versions`, `style_rules`. |
| External entities | MindRouter (the only provider; `LLM_PROVIDER` accepts only `mindrouter`). |
| Crosses boundaries | Submission copy, submitter notes, link URLs with their query parameters, and editor instructions go to MindRouter. Email-gateway wrapped links (Proofpoint, Safe Links, Mimecast, Barracuda) are unwrapped locally first; no request is made to resolve them. |
| Not sent | The `Submitter_Name`, `Submitter_Email`, `Assigned_Editor` and `Editorial_Notes` columns are not put in the prompt (`prompts.build_edit_user_prompt`). Personal information typed into the copy or notes is sent as is. |
| Controls | Staff-only trigger. HTTPS to MindRouter with an API key from the environment file. Bounded concurrency and queue size (`AI_EDIT_MAX_CONCURRENCY`, `AI_EDIT_MAX_PENDING`). Logs record model and character counts, not content. Anthropic and OpenAI were removed on 2026-11-20. |
| Gaps | No recorded approval reference for MindRouter as the AI processor, or for its retention terms. Configurable endpoint URLs alone do not prove campus-only routing. |

## 5. Newsletter builder and Word export

```mermaid
flowchart LR
  B["Browser, staff"]
  subgraph OPENERA["openera Docker networks"]
    API["/api/v1/newsletters/*<br/>require_staff on every route"]
    N[("newsletters, newsletter_items,<br/>newsletter_external_items<br/>Internal, Low")]
    EV[("edit_versions, approved revision")]
    RM[("recurring_messages")]
    EXP["utils.export<br/>export_newsletter_docx"]
  end

  B -->|"assemble, place, reorder"| API
  EV -->|"approved copy"| API
  RM -->|"due messages"| API
  API --> N
  B -->|"GET /newsletters/id/export"| API
  API --> EXP
  EXP -->|".docx streamed to the browser,<br/>not stored on the server<br/>Internal until published"| B
```

| Item | Detail |
| --- | --- |
| Data stores | `newsletters`, `newsletter_items`, `newsletter_external_items`. |
| External entities | None from the server. Staff take the .docx to the publishing process outside this app. |
| Controls | Every builder and export route is `require_staff`. Contact columns and internal notes are not exported; contact details written into the copy are. Export downloads are audit events. |
| Gaps | Downloaded .docx files on staff devices are outside the app's controls. |

## 6. Schedule and recurring messages

```mermaid
flowchart LR
  B["Browser"]
  subgraph OPENERA["openera Docker networks"]
    SCH["/api/v1/schedule/*<br/>reads open, writes require_staff"]
    REC["/api/v1/recurring-messages/*<br/>require_staff"]
    SC[("schedule_configs, blackout_dates,<br/>custom_publish_dates, schedule_mode_overrides<br/>Internal, Low to Moderate")]
    RM[("recurring_messages, issue overrides<br/>Internal, Moderate")]
  end
  B -->|"valid publish dates, read by the submission form"| SCH
  B -->|"staff: blackout and custom dates"| SCH
  SCH --> SC
  B -->|"staff: standing messages"| REC
  REC --> RM
```

| Item | Detail |
| --- | --- |
| Data stores | Schedule tables, `recurring_messages`, `recurring_message_issue_overrides`. |
| External entities | None. |
| Controls | Schedule GET routes have no auth dependency so the submission form can show valid dates; they return publication calendars, not submissions. All writes and all recurring-message routes are `require_staff`. |
| Gaps | `custom_publish_dates.Description` and `schedule_mode_overrides.Description` are free text tagged Moderate but served by the open GET routes. Confirm they never hold non-public notes, or put the read behind sign-in. |

## 7. Calendar events and jobs (inbound public reads)

```mermaid
flowchart LR
  B["Browser, staff"]
  subgraph OPENERA["openera Docker networks"]
    API["/api/v1/newsletters/* calendar and job routes<br/>require_staff"]
    CAL["calendar_event_service"]
    JOB["job_posting_service"]
    X[("newsletter_external_items, submissions<br/>Internal")]
  end
  TR["Trumba calendar feed<br/>CALENDAR_SOURCE_URL"]
  PU["PageUp careers site<br/>careers.uidaho.edu"]

  B -->|"import events for an issue"| API
  API --> CAL
  CAL -->|"HTTPS GET, no credentials"| TR
  TR -->|"public event RSS<br/>Public, Low"| CAL
  B -->|"paste a submitted job's link"| API
  API --> JOB
  JOB -->|"HTTPS GET one page, same host only"| PU
  PU -->|"public job posting<br/>Public, Low"| JOB
  CAL --> X
  JOB --> X
```

| Item | Detail |
| --- | --- |
| Data stores | `newsletter_external_items`; calendar events can also be turned into submissions. |
| External entities | Trumba, PageUp careers site. |
| Crosses boundaries | Outbound: GET requests with no credentials or user data. Inbound: public event and job text. |
| Controls | Staff-only, on demand, no scheduled fetch. Job links must be `https` on the configured careers host, and redirects off that host are refused. 10-second timeouts. The careers site's throttling response is handled with a back-off. |
| Note | The default `CALENDAR_SOURCE_URL` in `config.py` points at `www.qatrumba.com`, and as of 2026-11-20 the prod environment file does not override it, so prod reads from that host. Whether it should read from the production Trumba host is an open decision. |

## 8. Feedback

```mermaid
flowchart LR
  B["Browser, any signed-in user"]
  BS["Browser, staff"]
  subgraph OPENERA["openera Docker networks"]
    API["POST /api/v1/feedback<br/>require_signed_in_under_sso"]
    STAFF["GET, PATCH, github-export<br/>require_staff"]
    F[("product_feedback<br/>Confidential, Moderate")]
    NT["Notifier: disabled stub"]
  end
  GH["GitHub issues<br/>public repository"]

  B -->|"summary, details, optional contact email,<br/>route, browser, viewport, host"| API
  API --> F
  F -.->|"no outbound channel approved"| NT
  F --> STAFF
  STAFF -->|"staff-reviewed title and body"| BS
  BS -->|"staff opens github.com/.../issues/new<br/>with prefilled text"| GH
```

| Item | Detail |
| --- | --- |
| Data stores | `product_feedback`. Export records keep a SHA-256 of the reviewed text and the review time, not a second copy. |
| External entities | GitHub, reached by the staff member's browser, not by the server. |
| Controls | Only reviewed text is prepared for export. The server never calls GitHub. The notifier cannot send. |
| Gaps | The GitHub repository is public. Anything staff leave in the reviewed text is published, and the prefilled URL itself carries the text to GitHub. |

## 9. Backups

```mermaid
flowchart LR
  subgraph OPENERA["openera VM"]
    CRON["devops crontab<br/>02:30 prod, 02:40 dev"]
    SCRIPT["scripts/backup.sh"]
    DB[("PostgreSQL insight-db")]
    UP[("uploads volume")]
    BK[("~/backups/ucmnews-env/scheduled/stamp<br/>database.dump, uploads.tgz, MANIFEST<br/>mode 700, unencrypted today")]
  end
  OFF[("Second IIDS server<br/>not yet named<br/>pending PR #551, not enabled")]
  KEY["Owner-held private key<br/>not yet created"]

  CRON --> SCRIPT
  DB -->|"pg_dump in the db container"| SCRIPT
  UP -->|"tar, read-only mount"| SCRIPT
  SCRIPT -->|"verified with pg_restore --list,<br/>SHA-256 in manifest<br/>Confidential, Moderate"| BK
  BK -.->|"rsync over ssh, checksums compared;<br/>refuses plaintext unless allowed"| OFF
  KEY -.->|"public key would encrypt each point"| SCRIPT
```

| Item | Detail |
| --- | --- |
| Data stores | One directory per run on openera. Nothing is pruned. |
| External entities | None today. Planned: a second IIDS server (PR #551). |
| Controls | `umask 077`, directories mode 700, archive readability and schema-version check, checksums, freshness check (`--check`, 26 hours). GPG encryption support exists but is off until an owner-held key is created. |
| Gaps | Backups are on the same VM as the database and unencrypted. No failure alerting. Environment files (secrets) are not backed up. Prod restore not yet tested in an isolated environment; dev restore passed 2026-11-03. See [Backup & Recovery](../backup-and-recovery.md). |

## Retired flows

Not mounted on dev or prod; code and tables kept until Phase 2 removal.

| Flow | What it did | State |
| --- | --- | --- |
| SLC calendar harvest | Read the Trumba JSON feed into `harvested_events`; SLC users flagged events | Routes unmounted; cron lines paused since 2026-11-03 |
| Ops needs classifier | Sent event title, description (up to 4,000 characters), location and category to MindRouter; stored needs and rationale in `ops_need_assessments` | Routes unmounted; runs only as part of a harvest, which is paused |

## Gaps visible in these flows

1. Backups stay on openera, unencrypted, until an encryption key exists and the
   second IIDS host is set up (PR #551 adds the copy step; not enabled).
2. No recorded approval reference for MindRouter as the AI processor.
3. Data classification and APM 30.11 tiers are proposed until the Data Owner
   reviews them (issue #176).
4. Traffic inside the VM (ingress to nginx, nginx to backend, backend to
   PostgreSQL) is not encrypted.
5. No server-side session revocation; the audit trail is not off-host.
6. Free text from submitters goes to MindRouter without automatic removal of
   personal information.
7. Staff-prepared feedback exports go to a public GitHub repository.
8. Fonts load from Google, so browsers contact Google on every page load.

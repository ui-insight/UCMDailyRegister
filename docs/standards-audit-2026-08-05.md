# AISPEG software-development and UX standards audit

**Application:** UCM Daily Register  
**Assessment date:** 2026-08-05  
**Assessed revision:** `main` at `4c89bd5`  
**Standards source:** [AISPEG Software-development and user-experience standards](https://aispeg-dev.insight.uidaho.edu/standards) and [assessment foundation](https://aispeg-dev.insight.uidaho.edu/standards/foundation)  
**Assessor:** Codex, based on repository evidence and local automated checks

## Executive finding

The application is **nonconforming with the current measurable draft** because 24 of the 35 critical gates are Not met. One critical gate is Met, eight are Partially met, and two are institutional requirements outside the application's authority.

This is not a claim that the application violates approved University policy. The portal labels all 20 standards as working drafts, with 0 approved as of the assessment date. Binding obligations cited by the drafts, especially APM 30.11 and WCAG 2.1 AA, still apply independently.

The repository has a sound tested application foundation: FastAPI-generated OpenAPI 3.1, server-side authorization checks, PII redaction tests, bounded submission queries, database migrations, health checks, deployment smoke tests, SBOM artifacts, University brand tokens, and a growing shared component library. The principal problem is that the updated standard requires current, reviewable assurance evidence and release gates that the project does not yet have.

## Scope and method

- Local `main` was fast-forwarded to `origin/main`; both resolved to `4c89bd5` before this report was created.
- Existing untracked user files were preserved and excluded from conformance evidence.
- All 80 atomic requirements published by the portal were assessed from repository contents at the revision above.
- A missing required artifact or control is marked **N (Not met)**. **NA (Not applicable)** is used only for requirements assigned to institutional standards owners rather than an application team, or for an unsupported feature such as alternate themes.
- Live OIT approvals, GitHub branch-protection settings, production database grants, backup logs, monitoring dashboards, and user-research records were not available in the repository. Where the requirement calls for those artifacts, their absence is a finding, not an assumption that they exist elsewhere.
- Based on the foundation's seven assurance dimensions, this application is **at least Level 2 (Standard production)**: it has authenticated staff workflows, protected editorial actions, public/untrusted input and image uploads, and external integrations. This is an assessor inference, not a substitute for the required approved Application Assurance Profile.

## Result summary

| Scope | Met | Partially met | Not met | Not applicable | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Software development (I.1-I.10) | 0 | 17 | 21 | 2 | 40 |
| User experience (II.1-II.10) | 1 | 15 | 20 | 4 | 40 |
| **All requirements** | **1** | **32** | **41** | **6** | **80** |
| **Critical gates only** | **1** | **8** | **24** | **2** | **35** |

Legend: **M** = Met, **P** = Partially met, **N** = Not met, **NA** = Not applicable. A dagger (†) marks a critical gate.

## Highest-priority release-gate gaps

1. **Assurance and security profile:** no Application Assurance Profile, ASVS 5.0 control profile, threat model, or finding-disposition record (`I4-R1`).
2. **University identity:** production authorization depends on a shared trusted-header secret rather than Entra ID/OIDC and individual identity; horizontal/vertical access-control coverage is incomplete (`I4-R4`).
3. **Secrets:** environment files and variables are documented, but no OIT-approved secrets service or access/rotation evidence exists (`I4-R2`).
4. **Security pipeline:** CI does not run dependency, secret, SAST, container, or IaC scanning and does not block releases on findings (`I4-R3`).
5. **Known dependency exposure:** current audits report 58 advisories across 14 packages in the local backend environment and 5 findings in the full frontend tree (4 high, 1 moderate). The frontend production-only audit reports 3 findings (2 high, 1 moderate). The backend dependency set is not locked, so these results are not an authoritative production inventory.
6. **Data governance:** the data inventory uses Public/Internal/Confidential instead of APM 30.11 Low/Moderate/High, has no signed Data Owner/Steward approval, and has no implemented retention/disposal path (`I3-R1`, `I3-R3`).
7. **Build provenance:** production is built interactively with Docker Compose from mutable dependency ranges; there is no approved CI-built immutable artifact, digest, signature, or provenance attestation (`I5-R1`).
8. **Ownership and handoff:** no named business/technical/data owners, funded maintenance commitment, complete runbook, or decommission plan is on file (`I6-R1`, `I6-R2`).
9. **Accessibility:** no WCAG-EM report or accessibility gate exists. Static evidence includes white text on Gold 600 at 2.47:1 and white text on Gold 500 at 1.88:1, both below AA for normal text; dialogs also lack complete focus management (`II2-R2`, `II3-R1`, `II3-R3`).
10. **Forms and feedback:** failed submissions do not provide a programmatically associated error summary, `aria-invalid`/`aria-describedby`, or reliably announced success/error state (`II2-R3`, `II6-R2`).
11. **Responsive critical workflows:** the shell uses a fixed 16rem sidebar and non-responsive page padding, and forms contain fixed two-column grids without 320 CSS-pixel/reflow evidence (`II4-R4`).
12. **User validation:** no representative-user research plan, critical-task usability report, finding register, or prelaunch retest evidence exists (`II8-R1`, `II8-R3`).

## Verification performed

| Check | Result |
| --- | --- |
| Repository sync | `main == origin/main == 4c89bd5` |
| Backend tests | 159 passed |
| Backend Ruff | Passed |
| Frontend tests | 57 passed across 14 files |
| Frontend ESLint | Passed with zero warnings |
| Frontend TypeScript/Vite build | Passed |
| Generated API contract | OpenAPI 3.1.0, 52 paths; no security schemes or RFC 9457 problem schema |
| Frontend dependency audit | 5 total findings: 4 high, 1 moderate |
| Frontend production-only dependency audit | 3 total findings: 2 high, 1 moderate |
| Backend dependency audit | 58 advisory records across 14 installed packages; production applicability cannot be established without a lockfile/artifact inventory |
| MkDocs strict build | Not run: MkDocs is not installed in the project environment; documentation CI installs it ad hoc |

## Requirement-by-requirement assessment

### I.1 System Architecture & Integration Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| I1-R1† | P | `docs/architecture.md` and `docs/data-governance.md` contain version-controlled architecture/data-flow sketches, but they do not fully name trust boundaries, protocols, accountable owner, or deployed physical topology. |
| I1-R2 | P | Integrations and providers are documented, but there is no governed integration inventory covering authentication, authorization, classification, failure, retry/idempotency, and both owning teams. |
| I1-R3† | P | Frontend-to-backend access is API-first and no code-level cross-application DB access was found. Active database grants, an explicit prohibition, audit controls, and an exception register are absent. |
| I1-R4 | N | No material-change definition or required architecture impact-review/update workflow exists. |

### I.2 API & Interface Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| I2-R1† | P | FastAPI generates OpenAPI 3.1.0 for 52 paths and serves Swagger/ReDoc. The contract is not checked in or validated in CI and has no security schemes, comprehensive error contracts, or representative examples. |
| I2-R2 | P | Routes generally use appropriate methods/status codes and have automated API tests, but there is no RFC 9110 conformance suite for caching, conditional requests, or negotiation. |
| I2-R3† | N | Errors use FastAPI's `{detail: ...}` shape; there is no RFC 9457 problem-details schema, stable type URI, safe correlation ID, or redaction test suite. |
| I2-R4 | P | Submission collections use bounded `offset`/`limit` and filters. Pagination/rate-limit/deprecation policy and consumer notices are not published, and deterministic ordering is not contractually verified for every collection. |

### I.3 Data Standards & Governance

| ID | Status | Evidence and finding |
| --- | --- | --- |
| I3-R1† | N | `docs/data-governance.md` uses Public/Internal/Confidential, not APM 30.11 Low/Moderate/High, and has no signed Data Owner/Steward classification approval. |
| I3-R2 | P | Models, `AllowedValue` records, `docs/data-model.md`, and the Data Governance UI document identifiers and controlled vocabularies. System-of-record declarations and named stewards are incomplete. |
| I3-R3† | N | Collection purpose and proposed retention are documented, but there is no approved lifecycle schedule, legal-hold behavior, implemented cleanup job, verified disposal evidence, or complete lineage record. |
| I3-R4 | P | `docs/backup-and-recovery.md` defines daily backups, RPO 24h, RTO 4h, and a restore procedure. The repository contains examples rather than deployed backup configuration or a recorded restore test. |

### I.4 Security & Compliance Requirements

| ID | Status | Evidence and finding |
| --- | --- | --- |
| I4-R1† | N | No Application Assurance Profile, ASVS 5.0 applicability profile/results, or threat model exists. The available evidence indicates Level 2 is the likely minimum. |
| I4-R2† | N | Secrets are injected through environment variables/files and excluded from Git, but there is no OIT-approved secrets service, inventory, access evidence, encryption evidence for the source secret store, or tested rotation procedure. |
| I4-R3† | N | `.github/workflows/ci.yml` runs lint/tests/build only. Dependency, secret, SAST, container, and IaC scans and release-blocking dispositions are absent. Current dependency audits have findings. |
| I4-R4† | N | The backend enforces roles server-side and `backend/tests/test_authorization.py` tests important denials/PII redaction. It does not use approved University identity, identify individual users, or comprehensively test horizontal and vertical authorization. |

### I.5 DevOps, Deployment & Hosting Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| I5-R1† | N | GitHub Actions builds/tests source, but production deployment rebuilds interactively with `deploy.sh`/Docker Compose. No immutable CI artifact, digest, attestation, signing, or complete dependency lock exists. |
| I5-R2† | P | Dev/prod use separate Docker project names, subnets, environment files, and databases. Access-control evidence and an enforced prohibition on production data outside production are incomplete. |
| I5-R3 | P | Compose, Dockerfiles, nginx, entrypoint, and deploy script are version-controlled. There is no automated IaC/config validation, approved GitOps reconciliation, or drift detection. |
| I5-R4 | P | Docker readiness checks and post-deploy smoke tests exist. Release version/approver records, automated rollback/forward recovery, and a recovery rehearsal are absent. |

### I.6 Application Lifecycle & Handoff Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| I6-R1† | N | No named business owner, technical owner, data owner/steward, support contact, or funded maintenance commitment is recorded. |
| I6-R2† | P | Architecture, deployment, backup, security, data-governance, and SBOM documents provide parts of a handoff package. There is no single current runbook with monitoring ownership, access procedures, known-risk dispositions, and vendor contacts. |
| I6-R3 | P | RPO/RTO, incident steps, and contacts are documented. Service objectives, support hours, severity/escalation commitments, and maintenance windows are incomplete. |
| I6-R4 | N | No owner-approved decommission plan covers notification, export, retention/disposal, integration shutdown, access removal, and archival evidence. |

### I.7 Technical Debt & Code Quality Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| I7-R1 | P | CI enforces Ruff, pytest, ESLint, TypeScript compilation, and build. It does not run frontend tests, Pyright, secret scanning, dependency scanning, or a formatting gate; branch protection is not evidenced in-repo. |
| I7-R2† | P | The repository has 159 backend and 57 frontend tests, including authorization and data-integrity cases. Frontend tests are not a CI gate and critical recovery paths lack integration tests. |
| I7-R3 | N | Existing issue references track some standards gaps, but there is no defined, periodically reviewed technical-debt register with risk, owner, disposition, and horizon. |
| I7-R4 | P | `frontend/src/components/common/` provides shared components and services are modular. There is no component inventory or documented deviation/duplication decision process. |

### I.8 Decision-Making & Governance Model

| ID | Status | Evidence and finding |
| --- | --- | --- |
| I8-R1† | NA | Publishing the institutional standards decision-rights matrix belongs to the University standards owner, not this application repository. The application still needs named local owners under I6-R1. |
| I8-R2 | N | No ADR/decision register records material decisions, options, rationale, approver, affected standards, and review triggers. |
| I8-R3† | N | Known deviations from the draft paved road exist (identity, secrets, CI/CD, GitOps, observability), but no approved, expiring exception records with compensating controls were found. |
| I8-R4 | NA | Versioning and publishing the institutional standards catalog belongs to its standards owner. |

### I.9 Upgrade & Change Management Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| I9-R1† | N | Package manifests, an npm lockfile, Dependabot for npm, and SBOM snapshots exist. There is no complete component owner/EOL register, backend lockfile, or monitored support-lifecycle dashboard. |
| I9-R2† | N | `SECURITY.md` states remediation targets, but CI does not scan/enforce them and current audits report unresolved findings. There is no release-blocking risk-acceptance workflow. |
| I9-R3 | N | APIs are namespaced `/api/v1`, but no compatibility/deprecation policy, consumer inventory, notice period, or migration/removal template exists. |
| I9-R4 | P | Regression tests, builds, Alembic checks, health checks, and smoke tests cover portions of upgrades. Security, rollback/forward-recovery, and observability verification are not integrated. |

### I.10 Observability & Operational Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| I10-R1 | N | `docs/audit-logging.md` is a plan. No implemented structured logs, OpenTelemetry collector/instrumentation, metrics, or traces were found. |
| I10-R2† | N | The plan says not to log PII, but there is no telemetry inventory, redaction test, classified retention/access configuration, or verified disposal. |
| I10-R3 | N | No production SLI/SLO definitions or dashboards for availability, latency, errors, and critical business transactions exist. |
| I10-R4 | N | No alert catalog with owner, severity, runbook, route, response expectation, test record, or post-incident feedback loop exists. |

### II.1 Design System & Visual Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| II1-R1† | M | The app uses an approved U of I logo asset, University brand color scales, Public Sans, and documented voice/brand guidance in `docs/branding.md` and `PRODUCT.md`. Accessibility of individual uses remains assessed separately. |
| II1-R2 | P | `frontend/src/index.css` defines version-controlled color, typography, and status tokens. Spacing, elevation, borders, breakpoints, focus, and motion tokens/guidance are incomplete. |
| II1-R3 | N | Tokens/components are local copies rather than an approved versioned institutional design-system dependency or documented synchronization/provenance process. |
| II1-R4 | NA | The application exposes no alternate or dark theme. Any future theme must be reassessed. |

### II.2 Component & Interaction Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| II2-R1 | P | A shared component directory exists, but many pages use ad hoc controls. No inventory, unmet-need record, accessibility review, or contribution decision is required for custom components. |
| II2-R2† | N | Some controls have roles/names and focus-visible styles. Shared buttons lack a consistent visible-focus style; dialogs lack complete initial focus, focus trap, Escape, and focus-return behavior; no screen-reader/keyboard report exists. |
| II2-R3† | N | Forms generally have persistent labels, but failed submissions lack programmatic field associations, `aria-invalid`, an accessible error summary, and focused/announced context. |
| II2-R4 | P | Shared confirmation dialogs protect style-rule and recurring-message deletion, but other remove/skip operations execute directly and the confirmation component itself has incomplete focus management. |

### II.3 Accessibility

| ID | Status | Evidence and finding |
| --- | --- | --- |
| II3-R1† | N | No WCAG-EM report exists. Static contrast failures include white on Gold 600 (2.47:1) and white on Gold 500 (1.88:1), and modal/form/reflow concerns prevent a WCAG 2.1 AA claim. |
| II3-R2 | N | No axe/pa11y/Lighthouse accessibility CI or production scan exists, and no keyboard, zoom/reflow, contrast, screen-reader, or cognitive review record was found. |
| II3-R3† | N | No accessibility severity/release policy, equivalent-path process, executive risk decision, or retest evidence exists. |
| II3-R4 | P | The app provides a general in-app feedback channel, but no accessibility statement, named accessibility owner, acknowledgment commitment, or verified remediation workflow is published. |

### II.4 Usability & Workflow Design Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| II4-R1† | P | `PRODUCT.md` identifies three audiences, purposes, and design principles. It lacks research-backed barriers, context-of-use evidence, critical-task inventory, and baseline outcomes. |
| II4-R2 | N | No measurable critical-task success definitions cover completion, errors, effort, abandonment, accessibility, and confidence. |
| II4-R3 | P | Shared navigation, API clients, tokens, and components support consistency, but no cross-module pattern inventory, terminology review, or evidence-based exception process exists. |
| II4-R4† | N | No responsive/reflow matrix exists. Fixed sidebar/page spacing and fixed two-column form layouts provide contrary evidence for reliable 320 CSS-pixel and 200% zoom support. |

### II.5 Performance & Responsiveness Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| II5-R1 | N | No real-user Core Web Vitals collection, 28-day mobile/desktop report, or page/template coverage exists. |
| II5-R2 | N | No end-to-end latency/availability objectives or dependency budgets are defined or measured. |
| II5-R3 | N | Helpful network errors exist in the API client, but there is no constrained-network critical-workflow test covering loading, timeout, retry, and reconnection. |
| II5-R4 | P | Submission lists use bounded API queries, but large-result behavior is not consistently documented/tested and no keyboard/assistive-technology performance validation exists. |

### II.6 Error Handling & Feedback Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| II6-R1 | P | The frontend translates API/network failures into generally actionable language and preserves form values on failure. Messages do not consistently identify the affected item or provide a safe support reference ID. |
| II6-R2† | N | Validation is not consistently associated with fields and failed submissions do not provide an accessible summary/focus path. |
| II6-R3 | P | Toasts use `role="status"` and several operations expose loading/success/error text. Announcement, focus, meaningful progress, cancellation, and interrupted-connectivity behavior are not consistent or tested. |
| II6-R4† | N | Default FastAPI errors normally avoid production stack traces, but no RFC 9457 safe error boundary, correlation ID, protected diagnostic logging, or redaction tests exist. |

### II.7 Content & Language Standards

| ID | Status | Evidence and finding |
| --- | --- | --- |
| II7-R1 | P | `PRODUCT.md` defines audiences and a clear, helpful newsroom voice; forms use familiar language. No governed content brief/review artifact demonstrates consistent application. |
| II7-R2 | P | Most actions, fields, and headings are descriptive, but no out-of-context link/button and heading-hierarchy audit or usability evidence exists. |
| II7-R3 | N | Controlled database vocabularies exist, but there is no governed cross-system glossary with owner, prohibited ambiguity, and change process. |
| II7-R4 | P | Forms provide point-of-need helper text and do not rely solely on hover. No help-content inventory, keyboard/touch validation, or representative-user test exists. |

### II.8 User Testing & Validation Requirements

| ID | Status | Evidence and finding |
| --- | --- | --- |
| II8-R1† | N | No material-release research plan or representative-participant record, including participants likely to face the greatest barriers, was found. |
| II8-R2 | N | No predeclared usability test tasks, measures, stopping rules, accommodations, observation method, or decision thresholds exist. |
| II8-R3† | N | No user-finding register links critical findings to owners, launch dispositions, material-change retests, and verification. |
| II8-R4 | P | An in-app feedback channel and staff review UI exist. No declared cadence combines feedback with task analytics, support themes, and accessibility reports or traces decisions to that evidence. |

### II.9 Analytics & UX Telemetry

| ID | Status | Evidence and finding |
| --- | --- | --- |
| II9-R1† | P | Feedback capture documents a product purpose and a privacy-limited context payload. It lacks an approved event/attribute dictionary with owner, APM classification, basis, retention, access group, and prohibited uses. |
| II9-R2† | N | The payload intentionally excludes submission/editorial content, but free-text feedback and optional contact email can contain sensitive data and there is no redaction/block list or production payload inspection evidence. |
| II9-R3 | P | The feedback dialog tells users what context is included and excluded. A complete privacy notice and applicable consent, access, deletion, and downstream-control behavior are absent. |
| II9-R4 | N | No technically enforced retention, periodic access review, verified deletion, export/destination inventory, or downstream deletion evidence exists for feedback data. |

### II.10 Governance & Exception Handling

| ID | Status | Evidence and finding |
| --- | --- | --- |
| II10-R1† | NA | Naming University-wide owners for brand, design system, content, accessibility, research, and analytics is an institutional governance responsibility. The app should reference the published matrix once available. |
| II10-R2 | NA | Versioning and publishing institutional UX standards/shared components belongs to their authorized owners. Local components remain covered by II1-R2/R3 and II2-R1. |
| II10-R3 | NA | The institutional UX standards change process is outside this application's authority. |
| II10-R4† | N | The project has known UX/accessibility deviations but no application-level exception register with affected users, equivalent path, compensating measures, approval, and expiry. |

## Recommended remediation sequence

### 1. Establish the assurance baseline

- Complete the Application Assurance Profile and obtain the required independent review.
- Produce a Level 2 threat model and ASVS 5.0 applicability/results packet.
- Name business, technical, data, support, accessibility/design, and risk owners.
- Create an evidence index and approved, expiring exceptions for deviations that cannot be fixed before the next release.

### 2. Close security and supply-chain gates

- Replace prototype trusted-header identity with Entra ID/OIDC and per-user authorization evidence.
- Integrate the OIT-approved secrets service.
- Add dependency, secret, SAST, container, and IaC scans to pull requests, deployment pipelines, and the required schedule; implement release blocking and finding dispositions.
- Lock backend dependencies, refresh both SBOMs, remediate current audit findings, and build immutable signed/provenanced artifacts in an approved CI service.

### 3. Align data and operations

- Reclassify data using APM 30.11 and obtain Data Owner/Steward approval.
- Implement retention/disposal and record a non-production restore test.
- Finish the runbook, service objectives, escalation/alert catalog, rollback rehearsal, and decommission plan.
- Implement structured OpenTelemetry-compatible logging/metrics/traces with redaction, retention, dashboards, and named alert ownership.

### 4. Close accessibility and UX gates

- Fix known contrast, focus, dialog, error-summary, announcement, and responsive/reflow defects.
- Add automated accessibility checks plus a manual WCAG-EM evaluation and accessibility statement/feedback workflow.
- Define critical tasks and success measures, then test material releases with representative users and track/retest findings.
- Add Core Web Vitals/critical-transaction measurement and a governed feedback/analytics data plan.

### 5. Refresh governance evidence

- Replace or extend `docs/governance/enterprise-ai-framework/evidence.json`, which currently represents 15 requirements from the April 2026 draft, with mappings for the 80 current atomic requirements.
- Add CI validation for the evidence index and freshness dates.
- Reassess after the critical-gate remediation is deployed and current production evidence is available.

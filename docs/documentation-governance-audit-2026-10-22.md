# Documentation and data governance audit

Assessment date: **October 22, 2026**. Assessed repository revision:
`b7d893b1209ead93ad08dd2daae36fe7c953cff6`. Assessor: Codex.

Follow-up: [Remediation status](governance/remediation-2026-10-22.md). Findings below
describe the assessed revision, not the remediated working tree.

**Correction:** DG-05 originally described `/settings/ai` as staff-gated. It is
public metadata in the assessed code. Its lack of DB/readiness verification,
rather than an OIDC permission failure, is the reason to replace it as a health
probe. This correction does not change the recovery finding's other evidence.

## Assessment

The project has a useful documentation baseline, but its governance artifacts
are not reliable as a current inventory or as evidence that documented controls
operate. This review identifies **13 findings: five high and eight medium**.
The highest priorities are privacy inventory accuracy, authentication guidance,
retention/disposal, sensitive logging, and recovery procedures.

Strengths include domain explanations in model modules, Alembic migrations,
database-backed vocabularies, a staff-facing governance catalog, an explicit
Entra decision record, documented gaps, and a machine-readable evidence manifest
that separates compliance assertions from issue state. CI checks PostgreSQL
migration drift. These provide a practical foundation for remediation.

## Scope and limits

Reviewed README and agent conventions, MkDocs configuration and pages, security
and SBOM artifacts, governance JSON and its schema, ORM declarations, bootstrap
data, authentication and authorization, relevant data flows, Compose, and CI.
Code inspection corroborates documentation findings; this is not a full security
or application-code audit.

This is a repository assessment. Production configuration, database contents,
backup schedules and restore records, institutional approvals, live GitHub issue
states, and the neighboring portfolio governance repository were not verified.
An absent repository reference means evidence is missing here, not that an
institutional activity never occurred. External policies, vendor contracts, and
legal conclusions were not reassessed. Historical audits retain their original
dates and should not be treated as current verification.

High means incorrect or incomplete guidance could materially affect privacy,
access decisions, disposal, or recovery. Medium means inventory, traceability,
or maintenance assurance needs correction.

## Verified inventory and checks

| Check | Result |
| --- | --- |
| ORM declarations | 19 tables, 197 mapped columns, counted from Python AST |
| Staff governance catalog | 16 tables, 143 columns; all listed columns exist in ORM declarations |
| Catalog omissions | Three tables containing 49 columns, plus five columns in existing tables |
| AllowedValue bootstrap | 16 groups, 60 values; data-model docs say 10 groups, 41 values |
| Other bootstrap data | 15 sections, 99 style rules, six schedule configurations |
| Evidence manifest | All 15 requirements validate against Draft 2020-12 schema, including format checking; all repository source paths exist |
| Assertion freshness | All 15 assertions have `validated_at: 2026-05-05` |
| Assertion states | Eight `partially_aligned`, four `gap`, three `needs_decision` |
| Schema negative probes | Missing `repo_file.path` and duplicate requirement IDs are both accepted |
| Strict documentation build | Passed; five pre-existing Markdown pages are outside navigation |
| Focused backend verification | 80 tests passed across authorization, SSO, images, and feedback; one Authlib deprecation warning |

AST counts describe checked-in models, not a live database. Seed counts describe
bootstrap data, not expected production row counts. Passing documentation and
schema builds does not establish factual accuracy.

## Findings

### DG-01 — High: Privacy inventory omits current identity and feedback data

**Evidence:** `docs/data-governance.md:17` inventories only five submission
fields and line 29 says authentication tokens are not collected.
`backend/app/models/feedback.py:35` stores contact email and free-text report
details alongside browser, host, and route context. `backend/app/api/v1/sso.py:207`
uses email/username as the session subject; `backend/app/auth/session_tokens.py:23`
mints a token carrying subject, name, and role. `frontend/src/auth/tokenStore.ts:56`
reads that token from localStorage. The ADR's statement that nothing about a
person is persisted (`docs/adr/001-entra-sso.md:62`) overlooks browser storage.

**Impact:** Reviewers and users receive an incomplete account of identifiable
data and storage locations. No user table does not mean no identity persistence.

**Remediation:** Inventory feedback, identity claims, browser token storage,
OIDC state cookies, authentication logs, free text, and exports. State purpose,
classification, access, retention, and deletion behavior for each. Replace
absolute non-collection claims with the application's intended scope and actual
handling. Add the submitter-facing privacy notice already listed as open work.
Suggested accountable roles: data steward and authentication maintainer.

### DG-02 — High: Governance access matrix contradicts implemented authorization

**Evidence:** `docs/data-governance.md:81` and line 235 describe header-only
roles and no individual identity. Its matrix at line 229 omits `ops` and says
SLC cannot edit records. `backend/app/api/deps.py` supports mutually exclusive
header/OIDC modes and staff/SLC/ops guards; `backend/app/api/v1/slc_events.py`
and `backend/app/api/v1/ops_events.py` expose triage mutations. Public feedback
creation is also absent from the matrix. The API reference and deployment guide
already explain both authentication modes.

**Impact:** Staff cannot use the governance matrix to determine who can view or
change which datasets. Header mode can grant the proxy's configured role to
every reachable visitor, a limitation documented more clearly elsewhere.

**Remediation:** Publish a route/dataset permission matrix for public, staff,
SLC, and ops, including triage, needs verdicts, feedback, exports, and PII
redaction. Describe header and OIDC behavior separately. Record verified mode
per environment and evidence of role-by-role validation before asserting
production protection. Suggested owner: authentication maintainer.

### DG-03 — High: Retention policy lacks an executable, internally consistent disposal design

**Evidence:** `docs/data-governance.md:163` specifies two academic years for
submissions, indefinite newsletters, and 90 days for imported content. Line 175
would purge newsletter item references with a submission. No scheduled retention
implementation was found. `backend/app/services/submission_service.py:240`
deletes an ORM record without deleting its uploaded file.
`backend/app/models/newsletter.py:87` retains a required submission FK;
`Source_Version_Id` and `Upstream_Reviewed_Version_Id` add version dependencies.

**Impact:** The retention table is not evidence of enforcement. Deleting
publication placements could undermine the indefinite issue archive; deleting
only submission rows does not dispose of associated files. Feedback, harvested
events, ops assessments, identity data, and backup copies lack complete rules.

**Remediation:** Define the retention clock, academic-year boundary, exceptions
and holds, owners, and disposal evidence. Decide how to preserve published issue
snapshots while removing contact data and source history. Specify FK ordering,
file removal, backup expiry, restored-data handling, and all newer datasets
before implementing a dry-run-capable cleanup job. Suggested owners: data
steward and backend maintainer.

### DG-04 — High: Actual logging conflicts with the documented PII prohibition

**Evidence:** [Audit logging](audit-logging.md) says PII must never appear in
logs. `backend/app/api/v1/sso.py:230`, line 235, and line 238 log the subject,
which is an email/username. `backend/app/utils/hyperlinks.py:76` and related
branches log complete wrapped and destination URLs; their query strings can
contain identifiers or tokens. AI error paths also interpolate exception text
(`backend/app/services/ai/editor.py:507`).

**Impact:** If those log levels are enabled, identity and potentially sensitive
URL data enter a channel absent from the privacy inventory. The documented
90-day/one-year retention targets have no linked operational evidence.

**Remediation:** Define a deliberate identity-logging policy, use minimized
identifiers where appropriate, remove or redact URL query/fragment values, and
sanitize external error details. Classify remaining logs and record destination,
access, expiry, reviewer, and verification evidence. Test representative sensitive
values. Suggested owners: security reviewer and backend maintainer.

### DG-05 — High: Recovery runbook can produce misleading checks and lacks recoverable upload versions

**Evidence:** `docs/backup-and-recovery.md:55` syncs all upload backups into one
directory without dated snapshots or deletion, while claiming database-equivalent
retention. Lines 135 and 249 use `/settings/ai` metadata as a health probe.
Line 250 imports the database engine without executing a database query. Lines
166–177 rebuild the old application before describing migration downgrade.
No completed restore record is linked. The daily cron entries are examples,
not proof of installed jobs.

**Impact:** The upload example cannot provide the stated historical retention;
removed files can accumulate. The settings check does not verify database readiness, and an engine import
can pass without a working database.
Rollback ordering and an unspecified one-step downgrade are unsafe assumptions
for arbitrary releases.

**Remediation:** Use versioned upload backups paired with database recovery
points and bounded expiry. Use `/health` for liveness and `/readyz` for database
and reference-data readiness. Describe release-specific migration compatibility,
pre-rollback backup and preservation steps, and validation before restoring
traffic. Link a dated restore exercise and measured RPO/RTO. Suggested owner:
operations maintainer.

### DG-06 — Medium: AI data-flow and processor assurances are incomplete

**Evidence:** `docs/data-governance.md:88` describes newsletter editing and
notes-based PII risk, but does not enumerate provided links and their parameters
or the ops classifier. `backend/app/services/ai/prompts.py` transmits links and
editor instructions and can send original input, draft text, and findings in a
repair request. `backend/app/services/ai/ops_needs_classifier.py` separately
processes harvested title, description, location, and category through a
configurable MindRouter endpoint. The provider table at line 108 makes residency
and handling assertions without linked contract or configuration evidence.

**Impact:** Reviewers lack the complete input/output lineage and evidence needed
to approve each AI use. Excluding dedicated contact columns does not exclude
contacts embedded in content, links, instructions, or generated rationales.

**Remediation:** Document both AI workflows, repair requests, outputs, stored
provenance, and endpoint configuration. Link approved processor/model decisions,
retention and residency evidence, and external-provider exceptions. Distinguish
training restrictions from retention and location. No vendor compliance claim
is made by this audit. Suggested owner: AI service maintainer and data steward.

### DG-07 — Medium: Schema, catalog, and vocabulary documentation have measurable drift

**Evidence:** [Data model](data-model.md) and [UDM alignment](udm-alignment.md)
still describe 16 tables. `frontend/src/pages/DataGovernancePage.tsx:46` contains
16 of the 19 current tables. Missing tables are `product_feedback`,
`harvested_events`, and `ops_need_assessments` (49 columns). Missing columns in
existing catalog entries are `submissions.Approved_Version_Id` and
`newsletter_items.Manually_Placed`, `Source_Version_Id`, `Edition_Edited`, and
`Upstream_Reviewed_Version_Id`. Data-model vocabulary counts are 10/41 against
16/60 in the seed file. Six new groups cover SLC/ops review and ops needs.

**Impact:** The staff catalog omits entire operational datasets and editorial
provenance. Manual copies have already diverged. Vocabulary conventions are also
overstated: SLC event classification is still a schema regex, and the edit-history
docstring claims an AI provider vocabulary not present in the bootstrap groups.

**Remediation:** Establish one versioned machine-readable catalog with complete
column definitions, PII risk, retention, steward, sources, and vocabulary mapping;
generate or validate the UI and prose against it. Update the ERD and vocabulary
inventory and explicitly document intentionally code-governed exceptions. Check
the neighboring portfolio registry separately before repeating its asserted
current state. Suggested owner: data steward and schema maintainer.

### DG-08 — Medium: Evidence manifest is structurally valid but semantically stale

**Evidence:** All 15 assertions in
`docs/governance/enterprise-ai-framework/evidence.json` are dated May 5, 2026.
The auth summary at line 104 says no Entra implementation or group mapping
exists; both are now in code. The approved-stack matrix similarly says there
is no OIDC session implementation. All linked repository paths exist, which
does not establish that the assertions accurately describe their contents.

**Impact:** Aggregators can ingest obsolete conclusions successfully. Mutable
file paths do not identify the revision actually reviewed.

**Remediation:** Revalidate each assertion against a commit, add artifact/review
dates and responsible reviewers, and reconcile the matrix with the manifest.
Separate implemented code, environment enablement, test evidence, and formal
approval. Entra code alone is insufficient to mark production alignment.
Suggested owner: governance evidence maintainer.

### DG-09 — Medium: CI does not enforce documentation or governance freshness

**Evidence:** `.github/workflows/docs.yml` publishes on main with
`mkdocs gh-deploy --force`; it does not run a strict PR build.
`.github/workflows/ci.yml` checks application code and Alembic drift, but not
catalog completeness, seed/documentation consistency, or the evidence schema.
The evidence schema accepts both a `repo_file` with no path and duplicate
requirement IDs in negative probes.

**Impact:** The existing green checks permit both factual drift and ambiguous
evidence primary keys. Alembic drift checks address a different contract.

**Remediation:** Add PR checks for strict docs, evidence validation with formats,
type-specific evidence source fields and existence, unique requirement IDs,
catalog/ORM coverage, and governed seed mappings. Define a review freshness
policy. Preserve the distinction between issue state and compliance assertion.
Suggested owner: CI maintainer.

### DG-10 — Medium: Classification and privacy conclusions lack reviewable approval evidence

**Evidence:** `docs/data-governance.md:11` classifies unpublished original copy
as Public by intended use; the UI applies the same label to original and version
content. Line 159 makes an unconditional FERPA conclusion. The repository's own
classification evidence item records a missing APM 30.11 mapping; no signed data
owner classification decision is linked.

**Impact:** Intended publication can be confused with approved disclosure, and
free-text content can exceed the assumed scope. The documents do not establish
the authority or evidence behind the categorical privacy conclusion.

**Remediation:** Request steward/security review of working-copy and publication
classifications, incidental sensitive data, mixed datasets, and institutional
classification mapping. Record decision owner, date, scope, and approval
reference. Present FERPA scope as an assessed assumption pending the appropriate
institutional review; this audit makes no legal determination. Suggested owner:
data owner with privacy/security reviewer.

### DG-11 — Medium: Setup instructions and architecture facts contradict the current repository

**Evidence:** `README.md:33` puts `.env` in the root while its commands execute
from `backend/`; Settings reads `.env` relative to the working directory.
`docs/deployment.md:28` copies `.env.example` from inside `backend/`, where no
template exists. `docs/architecture.md:103` calls Compose a three-service stack,
but it defines frontend/backend and an external database network. README seed
counts say 14 sections, 37 rules, four schedule configs, and 10 value groups;
current counts are 15, 99, six, and 16. Agent deployment conventions also describe
a local database container and `POSTGRES_PASSWORD` that current Compose does not
use. Agent AI descriptions do not match the actual provider set.

**Impact:** A new maintainer can follow setup successfully while loading no
configured secrets, or fail at the copy step; deployment expectations diverge.

**Remediation:** Use `cp ../.env.example .env` for the shown local backend
workflow, reconcile topology and provider guidance, and derive volatile counts
from seed data. Review README, AGENTS, CLAUDE, architecture, and deployment as one
set. Suggested owner: documentation maintainer.

### DG-12 — Medium: Ownership and non-production data decisions remain unassigned

**Evidence:** The ownership, dev/test data, local AI tooling, and intake items in
the evidence manifest remain open assertions without linked final decisions.
The governance UI has team-level steward labels, but lacks retention metadata
and accountable review dates. The recovery guide instructs restoring production
backups to a test database without an accompanying data protection procedure.

**Impact:** Known gaps can persist without a person responsible for closure;
operators lack explicit rules for production data in tests, local AI tools,
feedback exports, and restoration exercises.

**Remediation:** Record named accountable business, technical, and data owners
with review cadence and escalation. Approve production-copy/scrubbing rules,
protected restore testing, local AI handling, and feedback export review. Link
institutional approvals or exceptions using non-sensitive references. Suggested
owner: project sponsor with operations and data steward.

### DG-13 — Medium: SBOM and vulnerability artifacts cannot represent the current release

**Evidence:** `sbom/README.md` and both CycloneDX metadata timestamps are dated
March 31, 2026. The backend SBOM lacks `authlib`, `itsdangerous`, and `pyjwt`, all
now declared in `backend/pyproject.toml`. Regeneration is recommended, but CI has
no SBOM freshness gate or release binding.

**Impact:** The artifacts omit current authentication dependencies and their
historical vulnerability summaries cannot substantiate current release posture.

**Remediation:** Generate SBOMs from the actual release dependency environment
and frontend lockfile; bind them to commit and image digest. Attach dated scan
outputs and finding dispositions. This audit did not run a fresh vulnerability
scan or assess current CVEs. Suggested owner: release maintainer.

## Remediation sequence and acceptance evidence

| Sequence | Work | Completion evidence |
| --- | --- | --- |
| 1 | Correct privacy and role guidance; reconcile logging policy | Reviewed inventory and permission matrix; sensitive-value logging tests; identified environment auth evidence |
| 2 | Decide classification and disposal; repair recovery guidance | Owner-approved decisions, complete retention matrix, dependency-aware disposal design, dated restore exercise |
| 3 | Refresh catalog, vocabulary, AI lineage, and evidence assertions | Complete 19-table/197-column catalog, 16-group/60-value bootstrap mapping, reviewed AI flow and processor references, commit-bound evidence |
| 4 | Close ownership/process gaps and add drift gates | Named owners, approved handling procedures, PR checks, release-bound SBOMs, reproducible setup instructions |

Suggested roles above are proposed assignments, not accepted commitments. No
policy approvals, live deployments, issue updates, or runtime changes were made
as part of this audit.

## Reproduction

Run from the repository root with the relevant dependencies installed:

```bash
python3 -m mkdocs build --strict --site-dir /tmp/ucm-documentation-audit-site
backend/.venv/bin/python -m pytest backend/tests/test_authorization.py backend/tests/test_auth_sso.py backend/tests/test_images.py backend/tests/test_feedback.py -q
git diff --check
```

The inventory comparison parsed each model class's `__tablename__` and
`mapped_column` declarations with Python AST and compared their names with
`GOVERNANCE_TABLES`/`col()` entries in the frontend source. Seed totals came
directly from JSON arrays. Manifest validation used
`Draft202012Validator(schema, format_checker=FormatChecker())`, followed by
existence checks for every `repo_file` and `repo_directory` source. Schema
negative probes operated on in-memory copies only.

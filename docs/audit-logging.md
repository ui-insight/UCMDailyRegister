# Audit logging and monitoring

Reviewed November 20, 2026. The code provides minimized operational diagnostics
and, since November 2026, a **per-user API audit trail** in the `audit_events`
table (below). Editorial versions record copy provenance. Model-call,
configuration and deployment events are still not audited.

## Per-user audit trail

Staff routes authorize by role (`app/api/deps.py`), so the role alone cannot say
which person read, changed, deleted or exported a record. The audit trail adds
that record without changing any route.

### Actor reference

The actor is identified by the **Microsoft Entra object ID** (`oid`) of the
signed-in account. The SSO callback reads `oid` from the ID token (Entra includes
it when the `profile` scope is granted, which the default `OIDC_SCOPES` requests)
and carries it in the app session token as the `oid` claim. Email addresses,
display names and group lists are never written to the audit trail.

An object ID does not name a person by itself, but authorized Entra administrators
can resolve it to an account, so it is handled as a personal identifier
(Confidential, PII in the [data dictionary](governance/data-dictionary.md)).
**The Data Owner should confirm this choice of actor reference** and who may
perform the resolution.

The actor reference is null when there is no identity to record: header-mode and
local deployments, anonymous callers, invalid tokens, and sessions minted before
the `oid` claim existed (those audit with their role only until the user signs in
again, at most `ACCESS_TOKEN_EXPIRE_MINUTES` later).

### What is recorded

`backend/app/api/audit_middleware.py` writes one row after the response for each
matched `/api/v1/*` request that is:

| Event_Type | When |
| --- | --- |
| `record_change` / `record_delete` | Any POST, PUT, PATCH or DELETE, by anyone (including anonymous submitters and failed writes) |
| `record_read` / `record_export` | Any GET by a signed-in `staff`, `slc` or `ops` role; routes with an `export` path segment are `record_export` |
| `authorization_failure` | Any 401 (`Reason_Code=unauthenticated`) or 403 (`forbidden`) response, with the caller's role |
| `sign_in_success` / `sign_in_failure` | Written by the SSO callback with the mapped role, or a fixed reason (`sign_in_failed`, `no_account`, `misconfigured`, `unavailable`) |

Each row stores `Occurred_At` (UTC), `Actor_Ref`, `Actor_Role`, `Event_Type`,
`Reason_Code`, `Http_Method`, `Route_Template` (for example
`/api/v1/submissions/{submission_id}`), `Record_Ids` (path-parameter values
shaped like record IDs, UUIDs or integers; any other path text, such as an
email typed into a URL, is dropped), `Changed_Fields` (top-level JSON body key
names of a write that the route's request schema declares; unknown keys are
dropped) and `Status_Code`. HEAD is not routed (405), so it cannot read a
record unaudited.

### What is not recorded

- Request or response bodies, field values, query strings or raw URLs.
- IP addresses, user agents, emails, names, tokens or group lists.
- Health and readiness probes, `/auth/config`, the SSO login, callback and logout
  redirects (the callback writes its own sign-in event), and a privileged user's
  own `/auth/me` read (its 401s are still recorded).
- GET requests by `public` or `submitter` callers that succeed.
- Requests that match no API route, so scanners cannot fill the table.
- Field names of non-JSON writes (the image upload) or of JSON bodies over 256 KB;
  the event is still recorded with `Changed_Fields` null.

Each event is written in its own database session after the response, so it
survives a request that rolls back. If the audit write fails, the request is
unaffected and only `Audit event write failed error_type=<ExceptionClass>` is
logged.

### Append-only and retention

There is no API to update or delete audit rows, and no staff UI to read them.
**No automatic deletion runs**: no disposal process is approved (see
[Retention](governance/retention.md), category `security_audit`, proposed one
year). Rows accumulate until the Data Owner and security owner approve one.

### How a reviewer queries it

With read access to the database (production uses PostgreSQL), for example the
last 30 days of one account's activity:

```sql
SELECT "Occurred_At", "Actor_Role", "Event_Type", "Reason_Code",
       "Http_Method", "Route_Template", "Record_Ids", "Changed_Fields", "Status_Code"
FROM audit_events
WHERE "Actor_Ref" = '<entra-object-id>'
  AND "Occurred_At" >= now() - interval '30 days'
ORDER BY "Occurred_At";
```

Who touched one record:

```sql
SELECT "Occurred_At", "Actor_Ref", "Actor_Role", "Event_Type", "Http_Method", "Status_Code"
FROM audit_events
WHERE "Record_Ids"->>'submission_id' = '<submission-uuid>'
ORDER BY "Occurred_At";
```

Recent refusals: filter `"Event_Type" = 'authorization_failure'`. Query results
contain personal identifiers; keep them in an approved restricted location.

### Remaining gaps

- The table lives in the application database. It is not shipped to an off-host,
  immutable or tamper-evident store, so anyone with database write access could
  alter it.
- No alerting or scheduled review of authorization failures or unusual access.
- Model-call, configuration-change and deployment events are not audited.
- Header-mode deployments record roles but no actor.
- No staff read endpoint; reviewers use SQL as above.

## Implemented logging controls

- Application sign-in messages record outcome and mapped role, never subject,
  name, group list, tokens or authorization-code parameters.
- Link unwrapping records only the wrapper type, never full URLs, query strings,
  paths, fragments or extracted destinations.
- AI/ops and feedback failure messages use exception **class names**, opaque
  application record IDs where useful, and fixed event text. Provider messages,
  response bodies and traceback text are excluded. Feedback delivery failures
  persist the error class rather than the transport's arbitrary message.
- Docker uvicorn uses `backend/logging.json`, JSON formatting and no request
  access log. The formatter excludes exception messages/tracebacks; call sites
  remain responsible for minimizing event arguments. HTTP client DEBUG/INFO URL
  logging is disabled by that configuration.
- Frontend nginx access logs contain timestamp, HTTP method, status, byte count
  and duration. They omit request URI/query, Referer, user agent and client IP.
  Its error threshold is `crit` because ordinary error diagnostics can contain
  the original request line. Rare critical diagnostics and **campus ingress
  logs** still require restricted access and deployment review.
- Compose limits each application container's `json-file` logs to three files
  of 10 MB. This bounds size; **it is not time-based retention or aggregation**.

For local servers use the same settings when handling anything beyond synthetic
inputs (from `backend/`):

```bash
uvicorn app.main:app --port 8001 --reload --no-access-log --log-config logging.json
```

Never enable HTTP/SDK wire-debug logging on real content. Avoid secrets, contact
values, raw copy, links, prompts, completions, browser context and untrusted input
in log arguments. Exception classes are useful diagnostics; deeper investigation
must use an approved restricted process with deliberately minimized captures.

## Audit-event contract

| Event family | Allowlisted fields | Status |
| --- | --- | --- |
| Submission access/change and deletion | Event code, opaque record ID, actor reference (Entra object ID), changed field names, time | Implemented in `audit_events` for every API route; Data Owner to confirm the actor reference |
| Publication/export | Event code, issue ID, operation, actor reference, time | Implemented (`record_export`, plus `record_read` for privileged GETs) |
| Authorization failures | Fixed reason code, route template, mapped role, time | Recorded in `audit_events`; central security event stream and alerts not implemented |
| AI edit/classification | Event code, record ID, approved provider/model identifier, duration, counts, outcome | Not implemented: the API call is audited, the model call itself is not |
| Configuration and deployment | Event code, revision/digest, field names, actor reference, outcome | Configuration API writes are audited as `record_change`; deployment events are not |

Do not log user-supplied field values or client identity headers. Do not
reintroduce email addresses as the audit identifier; hashes of emails are still
linkable identifiers and require review.

## Retention and operations evidence

Proposed general-log retention is 90 days; proposed security/error retention is
one year. Both require approved classification, access and expiry rules. No
central destination, retention execution, alerting, integrity/immutability or
reviewer is verified by repository configuration. Complete those fields in
[Governance decisions](governance/decisions.md) before claiming the targets operate.
Treat existing logs from earlier releases as potentially containing personal data
and sensitive URLs; restrict access and review expiry with the data owner.

The backend Compose healthcheck already queries `/api/v1/readyz`. Use `/health`
for liveness and `/readyz` for DB/reference-data readiness; keep staff workflow
smoke tests separate. See [Backup and recovery](backup-and-recovery.md).

Regression checks exercise successful/refused/failed sign-in, provider failures,
wrapped links and exception formatting with synthetic sensitive markers.
`backend/tests/test_audit_trail.py` checks that audit rows carry the object ID,
field names but never values or query strings, and that a failed audit write
does not fail the request. Review
logging call sites and ingress configuration whenever identity, AI, export or
transport code changes. Record a deployed log sample and retention validation
without collecting personal data as proof.

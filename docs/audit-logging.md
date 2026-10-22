# Audit logging and monitoring

Reviewed October 22, 2026. The code provides minimized operational diagnostics;
**it does not yet provide a complete per-user data-access or mutation audit trail**.
Editorial versions record copy provenance, not every access or actor action.

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

## Planned audit-event contract

| Event family | Allowlisted fields | Not implemented yet |
| --- | --- | --- |
| Submission access/change and deletion | Event code, opaque record ID, actor reference approved by privacy review, changed field names, time | Consistent event emission and actor mapping |
| AI edit/classification | Event code, record ID, approved provider/model identifier, duration, counts, outcome | Uniform success/failure and model-call audit events |
| Publication/export | Event code, issue ID, operation, actor reference, time | Export/access review trail |
| Configuration and deployment | Event code, revision/digest, field names, actor reference, outcome | Change/deploy event store and review |
| Authorization failures | Fixed reason code, route template, mapped role, time | Central security event stream and alerts |

Do not log user-supplied field values or client identity headers. A per-user audit
identifier requires a Data Owner/security decision; do not quietly reintroduce
email addresses to implement traceability. Hashes of emails are still linkable
identifiers and require review.

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
wrapped links and exception formatting with synthetic sensitive markers. Review
logging call sites and ingress configuration whenever identity, AI, export or
transport code changes. Record a deployed log sample and retention validation
without collecting personal data as proof.

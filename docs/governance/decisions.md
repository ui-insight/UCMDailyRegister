# Governance decisions and evidence register

Reviewed **October 22, 2026**. Role assignments below are proposed responsibilities,
not acceptance by a named person. **No institutional approval is inferred.**
The project sponsor should fill the accountable names and approval references
through the normal review process. Sensitive attachments belong in an approved
restricted system; record only non-sensitive references here.

## Accountability and evidence still required

| Responsibility / decision | Accountable role | Named owner | State and evidence needed |
| --- | --- | --- | --- |
| Business purpose, continued support and funding | UCM sponsor | Pending assignment | Confirm service commitment, support expectations and decommission authority |
| Technical operations and incident response | Technical owner / IIDS | Pending assignment | Confirm escalation, backup/restore responsibility and maintenance coverage |
| Classification, access and records lifecycle | Data Owner and Data Steward | Pending assignment | Approve per-dataset APM 30.11 mapping, restricted-data boundaries and reviews |
| Retention and archive design | Data Owner with records/privacy reviewer | Pending assignment | Approve clocks, periods, holds, publication-source decoupling and disposal evidence |
| Entra rollout | Technical owner with OIT IAM | Pending assignment | Registration/role assignment, secret rotation date and per-environment sign-in validation |
| AI processors, models and endpoints | Data Owner with OIT/security | Pending assignment | Approved gateway/model list; contract retention/residency/training terms and external-provider exceptions |
| Logging | Security and operations owner | Pending assignment | Central destination, access, review cadence, time-based expiry and campus ingress minimization |
| Non-production data and local AI tools | Data Owner with technical owner | Pending assignment | Confirm handling rules below and exceptions |
| OIT intake, source control, hosting and exceptions | Sponsor with OIT | Pending assignment | Link intake, EAR/VASA, namespace, gateway, hosting and platform approvals as applicable |

On assignment, record name/role, decision date, scope/environments, approver,
non-sensitive artifact reference, next review date, and superseding decision.
Review this register at least quarterly and after schema, processor, identity or
hosting changes. Review dependencies and operational checks at each release.

## Project handling rules pending institutional ratification

These rules govern repository work now; they do not grant permission to process
protected data or substitute for University policy.

- Use synthetic submissions, generated images and approved reference seeds in
  tests and local demonstrations. Do not copy production DBs, uploads, notes,
  identity tokens or AI conversations into development machines, fixtures, CI,
  public issues, or general-purpose AI tools.
- A restoration exercise using real backups is a restricted production-data
  operation: use an isolated approved environment, least-privilege access, no
  outbound AI/feedback transports, no public ingress, encrypted storage and a
  documented teardown. Do not run CI against that restored dataset. A redacted
  test copy requires a documented scrub process and owner review before release.
- AI coding assistants may work on source, synthetic fixtures and minimized
  diagnostics. Never provide secrets, raw production content, personal data,
  tokens, environment files or database dumps. Inspect generated artifacts and
  diffs before committing. Apply the same restriction to CI agent prompts.
- Feedback export is staff-controlled. Review summary, details, routes and browser
  context for personal/sensitive information **before opening the prefilled
  GitHub URL**; URL parameters already send the content to GitHub. Remove
  sensitive data before preparing the export. Review future notification adapters
  and destinations before enabling them; the current notifier is disabled.
- Exports and backups are copies of governed data, not exceptions to classification
  or retention. Store them in an approved location with the source dataset's
  access controls and owner-approved expiry.

## Environment evidence template

Complete one record per environment after deployment; repository implementation
and a local test pass do not establish deployed enablement.

| Field | Value |
| --- | --- |
| Environment / URL | Pending verification |
| Release commit / image digests | Pending verification |
| Verified by / date | Pending verification |
| AUTH_PROVIDER and role-by-role checks | Pending verification |
| Secrets owner / next rotation | Pending verification; never record values |
| AI endpoint/model and approval reference | Pending verification |
| Backup job, expiry, encryption and latest paired restore | Pending verification |
| Log destination, access and time-based retention | Pending verification |
| Outstanding exception / expiry / approving authority | Pending verification |

See the [remediation status](remediation-2026-10-22.md) for what repository changes
addressed and what remains dependent on these decisions.

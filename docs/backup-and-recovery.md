# Backup, recovery and incident response

Reviewed October 22, 2026. **This is an operating procedure, not proof that jobs
are installed or that a recovery target was achieved.** Record installation,
access/encryption controls, latest successful backup and measured restore results
in [Governance decisions](governance/decisions.md). Proposed RPO: 24 hours;
proposed RTO: four hours. Both require a restore exercise.

## Topology and protected copies

Compose contains frontend nginx and backend uvicorn. PostgreSQL is external on
`insight-db-net`; application uploads are in the `uploads` volume. Identify the
actual volume with `docker volume inspect`/Compose configuration rather than
assuming its name. Environment files contain secrets and require separately
controlled encrypted backups. Source recovery comes from the repository plus
release/image metadata.

Treat all DB/upload backups as containing personal information. Keep encrypted,
access-controlled off-host copies and separate keys. Never copy real backups into
ordinary development, CI or an unapproved test environment.

## Paired, versioned backup procedure

Run this procedure from an approved backup agent with credentials supplied outside
command history. Configure service files or a managed credential mechanism for
PostgreSQL; do not put passwords in a command line. Confirm source DB identity
and the upload source mount before every installation.

1. Pause application writes (stop backend or enable an upstream maintenance page)
   while taking the pair. Merely starting a DB dump and rsync at different times
   does not guarantee consistency between referenced uploads and database rows.
2. Create a new restricted timestamped directory, e.g.
   `/backups/ucmnews/prod/2026-10-22T020000Z/`, using `umask 077` and a directory
   name that is never reused. Keep prod and dev separate.
3. Run `pg_dump --format=custom --file=<new-directory>/database.dump <service-db>`.
   Copy the upload volume into `<new-directory>/uploads/` with `rsync -a`.
   Neither command should overwrite the previous recovery point.
4. Record the backup timestamp, database identity, application commit/image
   digests, Alembic revision, upload volume identity, file count and checksums in
   a restricted manifest. Do not include secrets. Confirm both operations
   succeeded before declaring a recovery point complete and resuming writes.
5. Encrypt/replicate the pair to the approved off-host store, verify checksums,
   and record success/failure and alert destination. Encrypt environment-file
   backups separately; protect encryption keys away from the backup data.

The earlier single-directory rsync example is retired: it neither preserved
historical upload snapshots nor expired deleted files. For larger datasets use a
reviewed snapshot/consistent online backup design rather than extending downtime
without agreement.

Proposed tiers are daily 30 days, weekly 90 days and monthly one year. Until the
Data Owner approves them they are planning values. Implement tier labels and
expiry on complete recovery-point directories/pairs, not ad hoc removal of files
inside them. A retained weekly/monthly pair can outlive the daily tier. Holds and
backup retention extensions require recorded owner authorization. Monitor failed
backups, missing pairs, off-host replication and expiry failures.

## Restore exercise and data loss

Use an isolated, approved recovery environment for a monthly exercise and before
significant schema/storage changes. Disable public ingress and outbound AI or
feedback work; never expose the restored DB through the normal dev host. Protect
real restore data with production controls and teardown after verification.

1. Preserve current database/uploads and failure evidence before any replacement.
   Do not start with `dropdb` against the affected production database.
2. Select a complete, verified DB/upload pair and its matching release. Restore
   the dump to a **new** isolated database. `pg_restore --list` only checks archive
   readability; it does not demonstrate a usable restore.
3. Restore uploads into a **new** volume/directory. Verify checksums and DB image
   references. Set correct ownership; do not copy over a live volume blindly.
4. Start the matching application release with migrations reviewed for that exact
   source/target revision. Prevent the normal entrypoint from automatically
   migrating to a different revision before compatibility has been checked.
5. Verify schema revision, record counts, issue snapshots and provenance,
   reference data, uploaded-image readability, role isolation, and a synthetic
   create/edit/export cycle. Use approved credentials for staff tests. Verify
   disposed/held data handling before reconnecting restored data to users.
6. Record measured data loss and recovery duration, backup/release revisions,
   tests, reviewer, deviations and corrective work. Cut traffic over only after
   owner acceptance. Securely remove test copies and temporary credentials.

A restore record must include the actual date/operator, pair identifier, checksum
results, expected/actual RPO and RTO, checks passed/failed, decision and teardown.
No completed exercise is claimed by this repository update.

## Container recovery and release rollback

For a stateless container failure, inspect `docker compose -p ucmnews-prod ps`
and minimized logs, then restart the failed service. Rebuilding is a release
operation, because the backend entrypoint runs Alembic and seeds data.

For a bad deployment:

1. Pause writes/traffic as needed; capture the deployed commit/image digests and
   current Alembic revision, then create a fresh paired recovery point.
2. Compare the current and target migration chains **before starting the older
   release**. Check whether the previous code can run on the current schema.
3. If compatible, deploy the known-good immutable image/revision and verify.
   If incompatible, prefer a forward fix or restore a paired backup into a new
   DB/volume. A downgrade is permitted only after reviewing and testing that
   exact migration path, data-loss implications and rollback plan on an isolated
   copy. Never assume `alembic downgrade -1` reverses an entire release.
4. Recheck health, readiness, role-specific workflows and source/archive
   integrity before reopening traffic. Record the result and any data loss.

## Health checks

Run against the relevant host (prod shown):

```bash
curl --fail --silent --show-error https://ucmnews.insight.uidaho.edu/api/v1/health
curl --fail --silent --show-error https://ucmnews.insight.uidaho.edu/api/v1/readyz
```

`/health` checks process liveness only. `/readyz` executes database queries and
checks load-bearing reference tables; it does not prove every workflow is healthy.
Importing the engine does not test connectivity. `/settings/ai` is currently
public metadata, not a database health probe. Inspect backup success daily;
check disk/capacity and log rotation weekly; perform and record restore exercises
monthly. The backend Compose healthcheck already uses `/readyz`.

## Incident response

| Severity | Working response target | Examples |
| --- | --- | --- |
| Critical | Immediate, within one hour | Suspected data breach, data loss, complete outage |
| High | Within four hours | Editorial pipeline/export unavailable |
| Medium | Within one business day | Degraded import or performance |
| Low | Within one week | Minor display or documentation problem |

These are proposed support targets pending named owner acceptance. Contact the
technical/operations owner and UCM sponsor through the established escalation
process; security incidents also go to the University's Information Security
Office. See repository `SECURITY.md` for the reporting
process; do not include raw personal data in ordinary issue reports.

Detect → triage → contain → notify authorized responders → preserve minimized
evidence → repair/restore → verify → review. For High/Critical incidents record a
restricted timeline, impact, affected systems, containment, root cause, measured
recovery, decision owner and prevention work. Named on-call coverage and verified
contact references remain in the governance decision register.

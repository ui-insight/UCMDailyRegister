# Operations runbook

For whoever is looking after UCM Daily Register in production. It covers what
runs where, how to deploy and roll back, how to check health, and what to do in
common incidents. Longer procedures live in the linked pages; this page does not
repeat them.

## System at a glance

| | Prod | Dev |
| --- | --- | --- |
| URL | `https://ucmnews.insight.uidaho.edu` | `https://ucmnews-dev.insight.uidaho.edu` |
| Host port (nginx) | 9280 | 9290 |
| Compose project | `ucmnews-prod` | `ucmnews-dev` |
| Containers | `ucmnews-prod-frontend-1`, `ucmnews-prod-backend-1` | `ucmnews-dev-frontend-1`, `ucmnews-dev-backend-1` |
| Environment file | `.env.prod` | `.env` |
| Database | `ucm_newsletter` on `insight-db` | `ucm_newsletter_dev` on `insight-db` |
| Uploads volume | `ucmnews-prod_uploads` | `ucmnews-dev_uploads` |
| Docker subnet | 10.20.9.0/24 | 10.20.10.0/24 |

- Server: `openera.insight.uidaho.edu`, account `devops`, repository checkout at
  `/home/devops/UCMDailyRegister`.
- Only the nginx frontend has a host port. The backend listens on 8001 inside
  the Docker network. PostgreSQL runs in the shared `insight-db` container, which
  other IIDS apps also use, reached over the external `insight-db-net` network.
- Sign-in: Microsoft Entra SSO (`AUTH_PROVIDER=oidc`). `deploy.sh` refuses to
  deploy prod with any other setting.
- AI editing: MindRouter (`mindrouter.uidaho.edu`) only.
- Diagrams: [Architecture](architecture.md) and the data flow diagrams in
  `docs/security/`.

## Access

- Server access is SSH as `devops@openera.insight.uidaho.edu` with a personal SSH
  key. People with access today: _record names here_ (IIDS).
- Entra app registration and group membership: _record the Entra administrator
  contact here_ (OIT). UCM decides who is in the staff group.
- MindRouter API key holder: _record here_.
- GitHub repository: `ui-insight/UCMDailyRegister`; merging to `main` does not
  deploy. Deploys are manual on the server.

## Deploy

```bash
ssh devops@openera.insight.uidaho.edu
cd /home/devops/UCMDailyRegister
git pull origin main
./deploy.sh dev          # always dev first
./deploy.sh prod
```

`deploy.sh` rebuilds both containers. On start the backend runs
`alembic upgrade head` and seeds reference data (`backend/docker-entrypoint.sh`),
so **every prod deploy is a schema change if new migrations arrived**. The script
then smoke-tests the site, `/api/v1/health`, `/api/v1/readyz`, that staff routes
refuse anonymous callers, and that SSO login redirects to Microsoft. It exits
non-zero if any check fails.

Before a prod deploy that includes migrations, take a dump outside the nightly
series and note the current revision:

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DIR=~/backups/ucmnews-prod/pre-deploy-$STAMP
mkdir -p "$DIR" && chmod 700 "$DIR"
docker exec insight-db pg_dump -U postgres -Fc ucm_newsletter > "$DIR/database.dump"
docker exec insight-db psql -U postgres -d ucm_newsletter -tAc 'select version_num from alembic_version' > "$DIR/alembic_revision.txt"
git rev-parse --short HEAD > "$DIR/checkout.txt"
```

After deploying, sign in on the public URL as a staff user and open one
submission. Record the deploy (commit, revision, date) in the PR or issue that
asked for it.

## Roll back

Follow [Container recovery and release rollback](backup-and-recovery.md#container-recovery-and-release-rollback).
The short version:

1. If no migration ran, check out the last good commit and run
   `./deploy.sh prod`.
2. If a migration ran, check whether the old code works on the new schema
   before starting it. Prefer a forward fix. Do not assume
   `alembic downgrade -1` undoes a release: some migrations change data, and
   downgrades are not tested for every revision. Only downgrade after testing
   that exact path on a copy.
3. Restoring the pre-deploy dump is the last resort and loses everything written
   since it was taken. Restore into a new database first, as in the restore
   exercise in [Backup and recovery](backup-and-recovery.md).

Header mode is not a rollback for sign-in problems; production refuses it.

## Health checks

```bash
# On the server, from /home/devops/UCMDailyRegister (bypasses campus ingress)
curl -fsS http://127.0.0.1:9280/api/v1/health    # process is up
curl -fsS http://127.0.0.1:9280/api/v1/readyz    # database reachable, reference tables seeded
# Through the public URL
curl -fsS https://ucmnews.insight.uidaho.edu/api/v1/readyz
docker compose --env-file .env.prod -p ucmnews-prod ps                 # backend should be "healthy"
```

`/readyz` returns 503 with the empty tables listed when seeding failed. Neither
check proves sign-in or AI editing work; a staff sign-in does.

Backups:

```bash
/home/devops/UCMDailyRegister/scripts/backup.sh prod --check   # exit 1 if older than 26 hours
```

## Logs

| What | Where |
| --- | --- |
| Backend | `docker logs ucmnews-prod-backend-1 --tail 200` (JSON, rotated at 3 × 10 MB) |
| nginx | `docker logs ucmnews-prod-frontend-1 --tail 200`. Access lines carry time, method, status, size and duration only: no URL, IP or user agent. |
| Backups | `~/backups/ucmnews-<env>/backup.log`, `last-success`, `last-failure` |
| Who did what | `audit_events` table; see [How a reviewer queries it](audit-logging.md#how-a-reviewer-queries-it) |

Docker log rotation means backend logs cover days, not weeks. Copy what you need
during an incident.

## Scheduled jobs

`crontab -l` as `devops` on openera:

| Time | Job |
| --- | --- |
| 02:30 daily | `scripts/backup.sh prod` |
| 02:40 daily | `scripts/backup.sh dev` |
| (paused) | SLC calendar harvest for prod and dev, commented out since 2026-11-03 |

The same crontab runs RFD Companion backups at 02:10 and 02:20; leave those alone.

## Incidents

Severity targets and the general response sequence are in
[Incident response](backup-and-recovery.md#incident-response). Security
incidents go to the University Information Security Office as well as the
people below.

### Site down

1. `curl -fsS http://127.0.0.1:9280/api/v1/health` from the server. If it works
   there but not on the public URL, the problem is the campus ingress or DNS:
   contact OIT.
2. `docker compose --env-file .env.prod -p ucmnews-prod ps`. If a container is stopped or unhealthy,
   read its logs, then `docker compose --env-file .env.prod -p ucmnews-prod restart backend` (or
   `frontend`). Restarting does not run migrations; rebuilding (`deploy.sh`) does.
3. If the backend logs show database connection errors, check `insight-db`:
   `docker ps --filter name=insight-db`. It is shared, so tell the other IIDS app
   owners before restarting it.
4. If the backend exits at start with a configuration error (for example
   `SECRET_KEY must be changed` or a missing `ENTRA_*` value), fix `.env.prod`
   and run `./deploy.sh prod`.

### Sign-in failing

1. Repeat the SSO checks from `deploy.sh` by hand:
   `curl -s http://127.0.0.1:9280/api/v1/auth/config` should show
   `"sso_enabled":true`, and
   `curl -s -o /dev/null -w '%{redirect_url}\n' http://127.0.0.1:9280/api/v1/auth/sso/login`
   should start with `https://login.microsoftonline.com/`.
2. Backend logs show the sign-in failure reason. The audit trail records it too
   (`sign_in_failure` with `Reason_Code` `sign_in_failed`, `no_account`,
   `misconfigured` or `unavailable`).
3. Everyone failing at once usually means: the Entra client secret expired
   (it lasts 24 months), the redirect URL in Entra no longer matches
   `ENTRA_REDIRECT_URI`, or Microsoft Graph refused the group lookup (log says
   to check consent for `GroupMember.Read.All`). Contact the Entra administrator.
4. Token validation errors that mention issued-at or expiry times point to
   clock drift: check `timedatectl` on openera. As of 2026-11-20 it reports the
   clock is not synchronized and the NTP service is inactive; IIDS should enable it.
5. One person signed in but sees the wrong role: their Entra group membership is
   wrong, or changed less than 8 hours ago and they have not signed in again.

### AI editing failing or slow

AI edits run as background tasks. When MindRouter is down or times out
(120 seconds per call), the task is marked failed with "AI editing failed. Retry
this edit." and staff retry it from the Editor. Nothing else in the app depends
on MindRouter, so staff can keep editing by hand.

1. Backend logs show the HTTP error from MindRouter.
2. If many requests are queued, staff see "busy" (503) until the queue drains
   (2 running, 50 queued by default).
3. A key error (401/403 from MindRouter) means `MINDROUTER_API_KEY` needs
   replacing; see [Rotate secrets](#rotate-secrets).
4. A restart marks running tasks failed; staff retry them.

### Backup failure

1. `cat ~/backups/ucmnews-prod/last-failure` and the end of `backup.log`.
2. Common causes: `insight-db` not running, disk full, the uploads volume
   missing, or (once encryption is enabled) the public key missing from the
   `devops` keyring.
3. Fix the cause, run `scripts/backup.sh prod` by hand, and confirm
   `--check` passes.
4. Nobody is alerted automatically, so check `--check` output after any server
   maintenance.

### Disk full

```bash
df -h / /var
du -sh ~/backups/* | sort -h
docker system df
```

Backups are not pruned automatically (expiry awaits Data Owner approval). Do not
delete recovery points to make room without the accountable owner's agreement.
`docker builder prune` and removing unused images are safe. Unused volumes
`ucmnews-dev_pgdata` and `ucmnews-prod_pgdata` are leftovers; ask before removing
them.

### Suspected account compromise or data exposure

1. Contain: remove the account from the Entra staff group. Because existing
   tokens stay valid for up to 8 hours, also rotate `SECRET_KEY` (signs everyone
   out) if the account had staff access.
2. Preserve evidence: export the relevant `audit_events` rows to a restricted
   location before anything else changes. Queries are in
   [Audit logging](audit-logging.md#how-a-reviewer-queries-it); start with the
   account's `Actor_Ref` over the last 30 days, then who touched each affected
   record. Keep backend logs (`docker logs ... > file`) before rotation drops them.
3. Notify: the University Information Security Office, the Data Owner (UCM) and
   the accountable owner, as in `SECURITY.md`. Do not put personal data in
   GitHub issues.
4. Review: which records were read or exported, whether exports (`record_export`)
   left the system, and whether any change needs reverting from the edit history.

## Rotate secrets

All secrets are in the environment file (`.env.prod` or `.env`, mode 600) on
openera. After editing it, run `./deploy.sh <env>` so the containers pick up the
change, then sign in to confirm.

| Secret | Effect of rotating | Notes |
| --- | --- | --- |
| `SECRET_KEY` | Every session token becomes invalid; everyone signs in again. | At least 32 characters; must differ from `SESSION_COOKIE_SECRET`. Use `openssl rand -base64 48`. |
| `SESSION_COOKIE_SECRET` | Sign-ins in progress at that moment fail and must be retried. | Must differ from `SECRET_KEY`. |
| `ENTRA_CLIENT_SECRET` | None if updated before the old one is removed in Entra. | Issued by the Entra administrator; expires 24 months after issue. Record the expiry date in [Deployment](deployment.md). |
| `MINDROUTER_API_KEY` | AI edits fail until the new key is in place. | From the MindRouter key holder. `OPS_CLASSIFIER_API_KEY` falls back to it. |
| Database password (in `DATABASE_URL`) | Backend cannot connect until both sides match. | Change the role's password in `insight-db` (`ALTER ROLE ... PASSWORD ...`), update `DATABASE_URL`, redeploy straight away. |

Environment files are not in the nightly backup. Keep a copy in an approved
vault whenever one changes.

## Restore

Use the procedure in [Backup and recovery](backup-and-recovery.md): restore into
a new database and volume, verify checksums and schema revision, and only then
switch the app over. Never restore over the live database as a first step.

## Contacts and escalation

| Role | Who | When |
| --- | --- | --- |
| Accountable owner | Barrie Robison | Prod deploys, data loss, security incidents, any decision to delete data |
| Technical operator (IIDS) | _record name_ | Day-to-day operation, deploys, backups |
| Second operator | _not yet named_ | Cover when the technical operator is away |
| Data Owner (UCM) | _record name_ | Data exposure, retention, who may be staff |
| Entra administrator (OIT) | _record contact_ | Sign-in outages, client secret, group consent |
| MindRouter support | _record contact_ | AI service outages and keys |
| University Information Security Office | _record contact_ | Any suspected breach |
| Vulnerability reports | `iids-security@uidaho.edu` | See `SECURITY.md` |

# Backup, Disaster Recovery & Incident Response

## Infrastructure Overview

| Component | Location | Data at Risk |
|-----------|----------|-------------|
| PostgreSQL database | External instance on `insight-db-net` Docker network | All submissions, newsletters, edit history, configuration |
| File uploads | Docker volume (`uploads`) on openera server | Submitted images |
| Application containers | Docker Compose on openera server | Stateless (rebuilt from source) |
| Environment secrets | `.env` / `.env.prod` files on server | API keys, database credentials |

---

## Backup Strategy

### PostgreSQL Database

**Tool:** `pg_dump` (logical backups)

**Schedule:** Daily automated backups via cron on the database host.

```bash
# Example cron entry (run as postgres user or with appropriate credentials)
0 2 * * * pg_dump -Fc -f /backups/ucm_newsletter_$(date +\%Y\%m\%d).dump ucm_newsletter
0 2 * * * pg_dump -Fc -f /backups/ucm_newsletter_dev_$(date +\%Y\%m\%d).dump ucm_newsletter_dev
```

**Retention:**

| Backup Type | Frequency | Retention |
|-------------|-----------|-----------|
| Daily | Every night at 02:00 | 30 days |
| Weekly | Sunday 02:00 | 90 days |
| Monthly | 1st of month | 1 year |

**Verification:** Restore a backup to a test database monthly to confirm integrity.

```bash
# Verify backup integrity
pg_restore --list /backups/ucm_newsletter_YYYYMMDD.dump

# Test restore to temporary database
createdb ucm_newsletter_restore_test
pg_restore -d ucm_newsletter_restore_test /backups/ucm_newsletter_YYYYMMDD.dump
# Run smoke tests against restored database, then drop it
dropdb ucm_newsletter_restore_test
```

### File Uploads (Images)

**Strategy:** Sync the Docker volume to a backup location.

```bash
# Rsync upload volume to backup directory
0 3 * * * rsync -a /var/lib/docker/volumes/ucmnews-prod_uploads/_data/ /backups/uploads/
```

**Retention:** Same schedule as database backups.

### Environment Files

**Strategy:** Encrypted backup of `.env.prod` and `.env` files.

```bash
# Encrypt and store environment files
gpg --symmetric --cipher-algo AES256 -o /backups/env_prod_$(date +%Y%m%d).gpg .env.prod
```

**Storage:** Keep encrypted copies in a separate location from the application server.

### Application Source

**Strategy:** The application is stateless and rebuilt from the Git repository. No application-level backup is needed beyond the GitHub repository itself.

---

## Recovery Objectives

| Metric | Target | Rationale |
|--------|--------|-----------|
| **RTO** (Recovery Time Objective) | 4 hours | Newsletter is daily; a same-day recovery is acceptable |
| **RPO** (Recovery Point Objective) | 24 hours | Daily backups; at most one day of submissions could be lost |

---

## Disaster Recovery Procedures

### Scenario 1: Application Container Failure

**Symptoms:** Frontend or backend container stops responding.

**Recovery:**

```bash
ssh devops@openera.insight.uidaho.edu
cd /path/to/UCMDailyRegister-App

# Check container status
docker compose -p ucmnews-prod ps

# Restart failed containers
docker compose -p ucmnews-prod restart

# If restart fails, rebuild
./deploy.sh prod
```

**Time estimate:** 5-15 minutes.

### Scenario 2: Database Corruption or Data Loss

**Symptoms:** Application errors referencing database, missing data.

**Recovery:**

```bash
# 1. Stop the application to prevent further writes
docker compose -p ucmnews-prod stop backend

# 2. Identify the most recent good backup
ls -lt /backups/ucm_newsletter_*.dump | head -5

# 3. Restore from backup
dropdb ucm_newsletter  # CAUTION: destroys current database
createdb ucm_newsletter
pg_restore -d ucm_newsletter /backups/ucm_newsletter_YYYYMMDD.dump

# 4. Run any pending Alembic migrations
docker compose -p ucmnews-prod run --rm backend alembic upgrade head

# 5. Restart the application
docker compose -p ucmnews-prod start backend

# 6. Verify with smoke tests
curl -f http://127.0.0.1:9280/api/v1/settings/ai
```

**Time estimate:** 30-60 minutes.

### Scenario 3: Server Failure (Full Rebuild)

**Symptoms:** openera server is unreachable or requires OS reinstall.

**Recovery:**

1. Provision new server or restore from infrastructure backup
2. Install Docker and Docker Compose
3. Clone the repository: `git clone https://github.com/ui-insight/UCMDailyRegister`
4. Restore `.env.prod` from encrypted backup
5. Restore database from backup (see Scenario 2)
6. Restore uploads from backup: `rsync /backups/uploads/ /path/to/uploads/`
7. Deploy: `./deploy.sh prod`
8. Verify: run full smoke test suite

**Time estimate:** 2-4 hours (depends on infrastructure provisioning).

### Scenario 4: Deployment Rollback

**Symptoms:** New deployment introduces a regression.

**Recovery:**

```bash
ssh devops@openera.insight.uidaho.edu
cd /path/to/UCMDailyRegister-App

# 1. Check the previous working commit
git log --oneline -10

# 2. Roll back to the previous version
git checkout <previous-commit-hash>

# 3. Rebuild and deploy
./deploy.sh prod

# 4. If database migrations need reverting
docker compose -p ucmnews-prod run --rm backend alembic downgrade -1
```

**Time estimate:** 15-30 minutes.

---

## Incident Response Procedure

### Severity Classification

| Severity | Definition | Response Time | Examples |
|----------|-----------|---------------|---------|
| **Critical** | System down, data breach, or data loss | Immediate (within 1 hour) | Database compromise, PII exposure, complete outage |
| **High** | Major functionality broken | Within 4 hours | AI editing pipeline down, newsletter export broken |
| **Medium** | Degraded functionality | Within 1 business day | Slow performance, calendar import failing |
| **Low** | Minor issue | Within 1 week | UI cosmetic bug, non-critical feature request |

### Escalation Contacts

| Role | Contact | Responsibility |
|------|---------|---------------|
| Primary on-call | IIDS development team | First response, initial triage |
| System administrator | devops@openera | Server/infrastructure issues |
| Security officer | iids-security@uidaho.edu | Data breach or security incidents |
| UCM stakeholders | UCM editorial team | Communication about service impact |

### Incident Response Steps

1. **Detect:** Alert from monitoring, user report, or smoke test failure
2. **Triage:** Classify severity, identify affected components
3. **Contain:** Isolate the issue (stop affected containers, revoke compromised credentials)
4. **Communicate:** Notify stakeholders based on severity
5. **Resolve:** Apply fix, restore from backup, or roll back deployment
6. **Verify:** Run smoke tests, confirm functionality restored
7. **Post-mortem:** Document root cause, timeline, and preventive measures (for High/Critical)

### Post-Incident Review Template

```markdown
## Incident Report: [Title]
- **Date:** YYYY-MM-DD
- **Severity:** Critical / High / Medium
- **Duration:** Start time → Resolution time
- **Impact:** What was affected and for how long

### Timeline
- HH:MM — Issue detected
- HH:MM — Triage and containment
- HH:MM — Resolution applied
- HH:MM — Service restored

### Root Cause
[Description]

### Resolution
[What was done to fix it]

### Prevention
[What changes will prevent recurrence]
```

---

## Monitoring Checklist

Until full observability is implemented, use these manual checks:

| Check | Command | Frequency |
|-------|---------|-----------|
| Containers running | `docker compose -p ucmnews-prod ps` | Daily |
| Frontend responds | `curl -f https://ucmnews.insight.uidaho.edu/` | Daily |
| API health | `curl -f https://ucmnews.insight.uidaho.edu/api/v1/settings/ai` | Daily |
| Database connectivity | `docker compose -p ucmnews-prod exec backend python -c "from app.db.engine import engine"` | Weekly |
| Disk usage | `df -h` on server | Weekly |
| Backup exists | `ls -lt /backups/ucm_newsletter_*.dump | head -1` | Daily |

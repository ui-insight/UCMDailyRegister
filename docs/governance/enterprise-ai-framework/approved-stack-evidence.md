# Approved Stack Evidence Matrix

Repository review: 2026-10-22
Reviewer: Codex; live environment and institutional approvals unverified
Source standard: OIT Enterprise AI Development Framework discussion draft,
April 2026

This matrix maps UCM Daily Register against the approved technology stack in
the OIT draft. It is evidence-first: each row identifies the current assertion,
the repo evidence, and the follow-up issue or exception path for anything that
is not fully aligned.

## Status Legend

| Status | Meaning |
| --- | --- |
| `aligned` | UCM Daily Register meets the draft requirement and has repo evidence available |
| `partially_aligned` | UCM Daily Register meets part of the requirement, but more implementation or evidence is needed |
| `gap` | UCM Daily Register does not currently meet the requirement |
| `not_applicable` | The requirement does not currently apply to UCM Daily Register |
| `needs_decision` | Compliance depends on an OIT, security, or ownership decision |

## Matrix

| OIT layer | Draft standard | Current assertion | Evidence | Follow-up / exception path |
| --- | --- | --- | --- | --- |
| Backend API | FastAPI + Uvicorn (Python) | `aligned` | `backend/pyproject.toml` lists `fastapi` and `uvicorn[standard]`; `backend/Dockerfile` runs `uvicorn app.main:app` on port 8001; `docs/architecture.md` documents the FastAPI REST API layer. | None |
| Frontend | React + Vite + TypeScript | `aligned` | `frontend/package.json` lists React, TypeScript, Vite, and `@vitejs/plugin-react`; `frontend/Dockerfile` runs `npm run build`; `docs/architecture.md` documents the React SPA layer. | None |
| Database | PostgreSQL + pgvector, pgaudit, pgsodium, containerized per application | `partially_aligned` | `docs/deployment.md` documents PostgreSQL for deployed environments on `insight-db-net`; `docker-compose.yml` requires `DATABASE_URL` and joins `insight-db-net`; `.github/workflows/ci.yml` runs a PostgreSQL 16 smoke job. SQLite remains the local default and no pgvector/pgaudit/pgsodium evidence is present. | PostgreSQL topology and extension review tracked in [#180](https://github.com/ui-insight/UCMDailyRegister/issues/180). |
| ORM / migrations | SQLAlchemy + Alembic | `aligned` | `backend/pyproject.toml` lists `sqlalchemy[asyncio]` and `alembic`; `backend/alembic/` contains checked-in migrations; `.github/workflows/ci.yml` runs `alembic upgrade head` and `alembic check` in the PostgreSQL smoke job. | None |
| Python dependency management | uv + pyproject.toml | `partially_aligned` | `backend/pyproject.toml` is the Python manifest; Docker and CI currently use `pip install -e`, not `uv`. | Tooling delta tracked in [#171](https://github.com/ui-insight/UCMDailyRegister/issues/171). |
| Python lint/format/type checks | Ruff + Pyright | `partially_aligned` | `backend/pyproject.toml` configures Ruff; `.github/workflows/ci.yml` runs `ruff check .`. No Ruff format gate or Pyright configuration is present. | Ruff format and Pyright adoption or exception tracked in [#171](https://github.com/ui-insight/UCMDailyRegister/issues/171). |
| JS/TS lint/format checks | Biome | `gap` | `frontend/package.json` uses `eslint .`; `.github/workflows/ci.yml` runs `npm run lint -- --max-warnings=0`. No Biome config is present. | Biome migration or exception tracked in [#171](https://github.com/ui-insight/UCMDailyRegister/issues/171). |
| Python testing | pytest | `aligned` | `backend/pyproject.toml` includes `pytest`, `pytest-asyncio`, and `pytest-cov`; `.github/workflows/ci.yml` runs `pytest`; `backend/tests/` contains async API and service tests. | None |
| JS/TS testing | Vitest + Testing Library | `aligned` | `frontend/package.json` includes `vitest`, jsdom, and Testing Library packages; the `test` script runs `vitest run`; frontend test files are under `frontend/src/`; the build workflow compiles TypeScript and Vite. | None |
| CI/CD | Azure Pipelines; GitHub Actions under review | `needs_decision` | `.github/workflows/ci.yml` runs backend, PostgreSQL smoke, frontend lint/build; `.github/workflows/docs.yml` deploys MkDocs to GitHub Pages. No Azure Pipelines evidence is present. | OIT deployment path tracked in [#173](https://github.com/ui-insight/UCMDailyRegister/issues/173); source-control and GitHub Actions approval tracked in [#181](https://github.com/ui-insight/UCMDailyRegister/issues/181). |
| GitOps deployment | ArgoCD + Kustomize | `gap` | Current deployment evidence is Docker Compose plus `deploy.sh`; no ArgoCD application or Kustomize overlays are present. | GitOps path tracked in [#173](https://github.com/ui-insight/UCMDailyRegister/issues/173). |
| Source control | ADO; GitHub Enterprise under review | `needs_decision` | The repo is hosted at `ui-insight/UCMDailyRegister`; `docs/contributing.md` documents GitHub branch and PR workflow; `.github/` contains workflows and Dependabot config. | Source-control approval or exception tracked in [#181](https://github.com/ui-insight/UCMDailyRegister/issues/181). |
| Authentication | Microsoft Entra ID/OIDC | `partially_aligned` | Entra confidential-client flow, App Role/Graph mapping and app session JWTs are implemented with SSO tests. Header mode remains the default; deployed enablement, IAM registration and approvals need separate evidence. | Production evidence in [#172](https://github.com/ui-insight/UCMDailyRegister/issues/172). |
| Email integration | Microsoft Graph API | `not_applicable` | No production email-sending integration is documented as an active runtime dependency. The app stores submitter email for editorial contact and exports newsletter copy to `.docx`; it does not send email. | If email sending is added, use Microsoft Graph or record an exception in [#171](https://github.com/ui-insight/UCMDailyRegister/issues/171). |
| Session storage | PostgreSQL | `partially_aligned` | OIDC uses a signed state cookie and app JWT persisted in browser localStorage. No database session store or per-token revocation exists; header prototype mode remains available. | Confirm approved session posture in [#172](https://github.com/ui-insight/UCMDailyRegister/issues/172). |
| Secrets management | 1Password Connect | `partially_aligned` | `.env.example`, `backend/app/config.py`, `docker-compose.yml`, and `SECURITY.md` show runtime environment variable injection and no committed secret values. No 1Password Connect evidence is present. | Runtime vault integration tracked in [#174](https://github.com/ui-insight/UCMDailyRegister/issues/174). |
| Observability | OpenTelemetry, Prometheus, Jaeger, Splunk | `partially_aligned` | Content-minimized JSON diagnostics and bounded Compose stdout logs are configured; `docs/audit-logging.md` separates implemented controls from pending audit/retention services; `docker-compose.yml` has backend health checks; `deploy.sh` runs smoke checks. No OTel/Prometheus/Jaeger/Splunk implementation evidence is present. | Observability implementation and evidence tracked in [#175](https://github.com/ui-insight/UCMDailyRegister/issues/175). |
| AI model gateway | Under evaluation | `needs_decision` | `docs/ai-editing.md` and `backend/app/services/ai/` document provider abstraction for Claude, OpenAI, and MindRouter; production deployment examples prefer MindRouter, but gateway requirements are not formally decided. | Gateway and provider exception decisions tracked in [#178](https://github.com/ui-insight/UCMDailyRegister/issues/178). |
| Approved AI models | MindRouter operated by U of I; others TBD | `needs_decision` | `backend/app/config.py` defaults MindRouter to `moonshotai/kimi-k3`; `docs/ai-editing.md` documents Claude, OpenAI, and MindRouter options. No approved-model registry mapping exists yet. | Approved-model mapping tracked in [#178](https://github.com/ui-insight/UCMDailyRegister/issues/178). |

## Validation Evidence

Repository validation commands (results are recorded in the remediation status):

```bash
python scripts/check_governance.py
python -m mkdocs build --strict --site-dir /tmp/ucm-documentation-site
git diff --check
```

Review basis: base revision `b7d893b1209ead93ad08dd2daae36fe7c953cff6` plus this
uncommitted remediation; bind evidence to the merged commit and release digest.
The April discussion draft is the existing baseline, not a revalidated current
institutional standard. GitHub issue states below are references, not live checks.

## Open Follow-Ups

The matrix opens the first evidence trail for [#171](https://github.com/ui-insight/UCMDailyRegister/issues/171), but these rows remain open until implementation, OIT approval, or an explicit exception is recorded:

- [#172](https://github.com/ui-insight/UCMDailyRegister/issues/172): Microsoft Entra ID/OIDC authentication
- [#173](https://github.com/ui-insight/UCMDailyRegister/issues/173): Azure Pipelines, ArgoCD, and Kustomize deployment path
- [#174](https://github.com/ui-insight/UCMDailyRegister/issues/174): 1Password Connect runtime secrets
- [#175](https://github.com/ui-insight/UCMDailyRegister/issues/175): OTel, Prometheus, Jaeger, and Splunk observability
- [#176](https://github.com/ui-insight/UCMDailyRegister/issues/176): APM 30.11 data classification
- [#178](https://github.com/ui-insight/UCMDailyRegister/issues/178): AI model gateway and approved-model registry
- [#180](https://github.com/ui-insight/UCMDailyRegister/issues/180): PostgreSQL hosting and extensions posture
- [#181](https://github.com/ui-insight/UCMDailyRegister/issues/181): Source-control and GitHub Actions approval

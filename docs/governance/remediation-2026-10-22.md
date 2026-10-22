# Documentation and governance remediation

Date: **October 22, 2026**. Responds to the
[documentation/governance audit](../documentation-governance-audit-2026-10-22.md).
Changes are repository implementation and local verification, not production
rollout or institutional sign-off. Historical findings remain available.

| Finding | Repository response | Remaining acceptance evidence |
| --- | --- | --- |
| DG-01 High: privacy inventory | Added identity/JWT/browser/cookie, feedback, free-text and export inventory; corrected ADR; inline submission/SLC/feedback notices | Owner/privacy review and verification of live handling |
| DG-02 High: access guidance | Replaced matrix with actual public/staff/SLC/ops dataset and operation boundaries; both auth modes explicit | Per-environment OIDC configuration/role checks and IAM approval |
| DG-03 High: retention | Category/clock/hold and publication-preserving disposal design; count-only read-only preview tool; no automatic purge or unapproved period interpretation | Owner-approved schedule and archive migration choice; disposal implementation, failure ledger and restore acceptance |
| DG-04 High: sensitive logs | Removed identity, URLs and external exception text at identified call sites; content-minimized JSON/server logging and bounded Docker stdout; regression tests | Campus ingress review, deployed log sample, central time-based expiry/access review and full access-audit trail |
| DG-05 High: recovery | Paired timestamped DB/upload backups, encryption/access/expiry procedure, isolated restore evidence, correct readiness checks and migration-compatible rollback | Installed jobs, off-host/expiry proof, named operator and measured paired restore |
| DG-06 Medium: AI flow | Both AI workflows, repair inputs, links/instructions, outputs and processor decisions documented | Approved processor/model/endpoint/contract references; model/prompt provenance for ops assessments |
| DG-07 Medium: catalog drift | Shared 19-table/197-column JSON catalog drives UI/generated dictionary; complete seed inventory and exception list | Owner classification approval and separately reviewed portfolio registry sync |
| DG-08 Medium: stale assertions | Re-reviewed repository assertions and matrix; dates, scope and implemented-vs-deployed distinction updated | Release commit/digest binding, live issue state and institutional approval references |
| DG-09 Medium: validation | PR/deploy strict docs and governance gate; type-specific evidence validation, unique IDs, file kinds, 180-day freshness, ORM/catalog and generated-doc checks | Confirm required checks in hosted branch protection; no live settings change made |
| DG-10 Medium: classification | Provisional handling, unpublished-content treatment, PII risk and mixed-data rules; removed categorical FERPA conclusion | Signed institutional classification/privacy assessment |
| DG-11 Medium: setup drift | Corrected env paths, topology/provider/seed guidance and agent conventions | Fresh operator setup/deployment validation |
| DG-12 Medium: ownership and data use | Decision/evidence templates, quarterly review and concrete synthetic-data, restore, AI-tool and export rules | Named owner acceptance, institutional ratification and formal intake references |
| DG-13 Medium: historical SBOM | Explicit historical/non-attestation labeling and release-binding procedure | Generate current release SBOMs/scans from actual runtime/images and retain digests/dispositions |

## Verification

Run from the repository root:

```bash
python scripts/check_governance.py
python -m mkdocs build --strict --site-dir /tmp/ucm-documentation-site
backend/.venv/bin/python -m pytest backend/tests -q
cd frontend
npm run lint -- --max-warnings=0
npm test
npm run build
```

Local verification completed:

| Check | Result |
| --- | --- |
| Governance contract and generated artifacts | Passed: 19 tables, 197 columns |
| Strict MkDocs build | Passed; five existing historical/agent pages remain outside nav |
| Backend Ruff, including governance checker | Passed |
| Full backend suite | 575 passed; one Authlib deprecation warning |
| Frontend ESLint | Passed with zero warnings |
| Full frontend suite | 228 passed across 25 files |
| TypeScript/Vite build | Passed; large main-chunk advisory remains |

Compose configuration validation and a synthetic JSON logging smoke check passed.
Nginx container validation could not run because the local Docker socket was
unavailable to this session. PostgreSQL and deployed container/ingress behavior
were not exercised locally.
Installed backup/expiry jobs, restore timing, institutional approvals and current
release vulnerability scans remain outstanding evidence. No production data was
read or deleted, no remote configuration was changed, and no approvals were
invented. Use [Governance decisions](decisions.md) to collect the outstanding
external decisions and operating evidence.

# Software Bill of Materials (SBOM)

Generated: 2026-03-31
Format: CycloneDX JSON (v1.6)

## Files

| File | Scope | Components | Tool |
|------|-------|-----------|------|
| `backend-sbom.cdx.json` | Python backend (pip environment) | 94 | cyclonedx-py 7.3.0 |
| `frontend-sbom.cdx.json` | Node.js frontend (npm lockfile) | 187 | @cyclonedx/cyclonedx-npm 4.2.1 |

**Total components:** 281

## License Summary

All dependencies use OSI-approved or permissive licenses compatible with internal university use.

### Backend Licenses
- MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, PSF-2.0, Python-2.0, LGPLv2+, MIT-CMU

### Frontend Licenses
- MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, CC-BY-4.0, Python-2.0

### License Compatibility Notes
- **LGPLv2+** (backend, via `Pillow`): Permits use in proprietary software without code disclosure, provided Pillow is dynamically linked (standard pip install satisfies this).
- **MPL-2.0**: File-level copyleft only; no impact on proprietary application code.
- **CC-BY-4.0** (frontend): Applies to documentation/data assets, not code. Attribution required if redistributed.

## Vulnerability Report

### Backend (pip-audit, 2026-03-31)

| Package | Version | CVE | Severity | Fix Version | Status |
|---------|---------|-----|----------|-------------|--------|
| pip | 25.1.1 | CVE-2025-8869 | — | 25.3 | Dev-only; not shipped in container |
| pip | 25.1.1 | CVE-2026-1703 | — | 26.0 | Dev-only; not shipped in container |
| pygments | 2.19.2 | CVE-2026-4539 | — | 2.20.0 | Dev dependency (ruff); update recommended |

**Note:** `pip` and `pygments` are build/dev tools, not runtime dependencies in the production Docker image. Risk is minimal but updates are recommended.

### Frontend (npm audit, 2026-03-31)

| Package | Severity | Advisory | Fix |
|---------|----------|----------|-----|
| ajv | moderate | GHSA-2g4f-4pwh-qvx6 (ReDoS) | `npm audit fix` |
| brace-expansion | moderate | GHSA-f886-m6hf-6m8v (DoS) | `npm audit fix` |
| flatted | high | GHSA-25h7-pfq9-p65f (DoS), GHSA-rf6f-7fwh-wjgh (Prototype Pollution) | `npm audit fix` |
| minimatch | high | GHSA-3ppc-4f35-3m26, GHSA-7r86-cg39-jmmj, GHSA-23c5-xmqv-rm74 (ReDoS) | `npm audit fix` |
| picomatch | high | GHSA-3v7f-55p6-f55p, GHSA-c2c7-rcm5-vvqj (Injection/ReDoS) | `npm audit fix` |
| rollup | high | GHSA-mw96-cpmx-2vgc (Path Traversal) | `npm audit fix` |

**6 vulnerabilities total (2 moderate, 4 high).** All fixable via `npm audit fix`. These are build-time dependencies (ESLint, Vite/Rollup) — they do not ship in the production nginx container, but should still be patched.

## Regeneration

```bash
# Backend SBOM
cd backend
source .venv/bin/activate
pip install cyclonedx-bom pip-audit
cyclonedx-py environment --output-format json -o ../sbom/backend-sbom.cdx.json
pip-audit

# Frontend SBOM
cd frontend
npx @cyclonedx/cyclonedx-npm --output-file ../sbom/frontend-sbom.cdx.json
npm audit
```

Recommended cadence: regenerate before each production deployment and monthly during active development.

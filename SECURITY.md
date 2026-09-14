# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| main branch (latest) | Yes |
| Older releases | No |

This application is deployed internally at the University of Idaho. Only the latest version on the `main` branch receives security updates.

## Reporting a Vulnerability

If you discover a security vulnerability in this application, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Email **iids-security@uidaho.edu** with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if available)
3. You will receive an acknowledgment within **2 business days**.
4. We aim to provide a fix or mitigation within **10 business days** for critical issues.

## Scope

The following are in scope for security reports:

- The UCM Daily Register web application (frontend and backend)
- API endpoints and data handling
- Authentication and authorization mechanisms
- Data exposure or leakage vulnerabilities
- Dependency vulnerabilities in production runtime

The following are **out of scope**:

- The University of Idaho network infrastructure
- Third-party services (Anthropic, OpenAI, Trumba, PeopleAdmin)
- Denial-of-service attacks
- Social engineering

## Security Architecture

### Authentication

The application supports two authentication modes, selected by `AUTH_PROVIDER`:

- **`oidc`** (intended for production): users sign in through Microsoft Entra ID using the Web (confidential) OIDC flow. The backend exchanges the authorization code server-side, maps the user's Entra App Roles to an application role, and mints its own signed (HS256) session token that the browser presents as a bearer token. The Entra token never reaches the browser. See `docs/adr/001-entra-sso.md`.
- **`header`** (the prototype boundary): the reverse proxy injects `X-Trusted-User-Role` together with a shared secret in `X-Trusted-Auth-Secret`; the backend accepts the role only when the secret matches. Client-supplied `X-User-Role` is rejected.

**Known limitation:** under `header` mode everyone who can reach the deployment receives the role the proxy asserts. That is appropriate only for prototype testing behind university network controls; production deployments should run `oidc`.

### Data Protection

- **PII minimization:** Only submitter name and email are collected. These are not included in AI prompts or published newsletters.
- **Secrets:** API keys and database credentials are managed via environment variables, never committed to the repository.
- **CORS:** Configurable allowed origins via `CORS_ORIGINS` environment variable.
- **Input validation:** All API inputs validated via Pydantic schemas before processing.
- **SQL injection:** Mitigated by SQLAlchemy ORM (parameterized queries throughout).
- **XSS:** React frontend provides built-in XSS protection. HTML in newsletter content is sanitized during .docx export.

### External Data Transmission

Content sent to external LLM providers (Anthropic, OpenAI) is limited to submission headlines, bodies, and notes. No PII fields (name, email) are included in prompts. See [Data Governance](docs/data-governance.md) for details.

The on-premises MindRouter provider keeps all data within University of Idaho infrastructure.

### File Uploads

- Restricted to image formats (JPEG, PNG, GIF, WebP)
- Maximum file size: 10 MB
- Files renamed to UUID on upload (original filename discarded)
- Stored on a dedicated Docker volume, not served directly by the application

## Dependency Management

### Scanning Cadence

- **Before each production deployment:** Run `pip-audit` and `npm audit`
- **Monthly during active development:** Review SBOM and audit reports
- **On security advisory notification:** Patch critical vulnerabilities within 5 business days

### SBOM

Software Bill of Materials in CycloneDX format is maintained in the `sbom/` directory. See `sbom/README.md` for regeneration instructions and the latest vulnerability report.

### Current Dependency Status

See `sbom/README.md` for the latest vulnerability audit results.

## Infrastructure Security

### Production Environment

- **Server:** Internal university infrastructure (openera.insight.uidaho.edu)
- **Network:** Custom 10.x.x.x subnet (not publicly routable)
- **TLS:** Terminated at the university reverse proxy / load balancer
- **Containers:** Only the nginx frontend container has a host port mapping; the backend is internal to the Docker network
- **Database:** External PostgreSQL on a shared Docker network (`insight-db-net`), accessible only within the server environment

### Secrets Management

| Secret | Storage | Rotation |
|--------|---------|----------|
| ANTHROPIC_API_KEY | Environment variable | On compromise or annually |
| OPENAI_API_KEY | Environment variable | On compromise or annually |
| MINDROUTER_API_KEY | Environment variable | On compromise or annually |
| DATABASE_URL | Environment variable | On credential change |

Secrets are injected at container startup via environment variables. They are never logged, committed, or exposed via API responses.

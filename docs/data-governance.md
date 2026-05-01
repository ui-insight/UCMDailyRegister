# Data Governance & Privacy

This document describes how the UCM Daily Register application collects, processes, stores, and transmits data. It serves as the foundation for FERPA compliance, data retention policy, and privacy risk assessment.

---

## Data Classification

| Classification | Definition | Examples in This System |
|---------------|-----------|------------------------|
| **Public** | Published or intended for public distribution | Newsletter content (headlines, bodies), calendar events, job postings |
| **Internal** | For University staff use only | Editorial notes, assigned editor, style rules, AI edit metadata |
| **Confidential** | PII or data requiring access controls | Submitter names, submitter emails, API keys, database credentials |

---

## PII Inventory

The application collects a minimal set of personally identifiable information:

| Field | Table | Classification | Purpose | Retention |
|-------|-------|---------------|---------|-----------|
| Submitter_Name | submissions | Confidential | Contact submitter, attribution tracking | Life of submission |
| Submitter_Email | submissions | Confidential | Contact submitter for edits/questions | Life of submission |
| Submitter_Notes | submissions | Confidential | Submitter instructions; may contain incidental PII | Life of submission |
| Assigned_Editor | submissions | Internal | Track editorial responsibility | Life of submission |
| Editorial_Notes | submissions | Internal | Staff-only editorial notes; may contain incidental PII | Life of submission |

**PII not collected:** Social Security numbers, student IDs, financial data, health information, passwords, or authentication tokens.

---

## Data Flow Diagram

```
                                  ┌─────────────────┐
                                  │  External LLM    │
                                  │  (Claude/OpenAI/ │
                                  │   MindRouter)    │
                                  └────────▲─────────┘
                                           │ Content + notes
                                           │ (incidental PII possible)
┌──────────┐    ┌──────────────┐    ┌──────┴────────┐    ┌──────────────┐
│ Submitter │───▶│  React       │───▶│  FastAPI      │───▶│  PostgreSQL  │
│ (browser) │    │  Frontend    │    │  Backend      │    │  Database    │
└──────────┘    └──────────────┘    └──────┬────────┘    └──────────────┘
                                           │
                                    ┌──────┴────────┐
                                    │  File System   │
                                    │  (uploads/)    │
                                    └───────────────┘

External Data Sources ──▶ Backend:
  • Trumba RSS (calendar events)
  • PeopleAdmin (job postings)
```

---

## Data Flows in Detail

### 1. Content Submission

**Source:** Public submitters and university staff via web form.

**Data collected:**

- Headline and body text (content)
- Submitter name and email (PII)
- Category, target newsletter, scheduling preferences (metadata)
- Optional image upload (media)
- Optional submitter notes (free text — may inadvertently contain PII)

**Access control:** Public submitters can create submissions and receive the
created submission response. Submission list/detail views, images, destructive
actions, AI edits, newsletter assembly, style rules, schedule configuration, and
recurring-message management are staff-only. Authorized SLC viewers can read the
SLC calendar feed with submitter PII redacted.

**Authentication model:** Role assignment comes from a trusted auth boundary.
The backend rejects client-controlled `X-User-Role` headers. Staff and SLC roles
must be asserted through `X-Trusted-User-Role` plus a matching
`X-Trusted-Auth-Secret`, which should be injected by nginx, a campus auth
gateway, or another server-side reverse proxy after stripping any inbound trusted
headers from the client.

### 2. AI Editing Pipeline

**What is sent to external LLM providers:**

- Original headline and body
- Submitter notes (free text)
- Style rules from database
- Category and editorial instructions

**What is NOT sent:**

- Submitter name
- Submitter email
- Assigned editor
- Editorial notes

**PII risk:** The Submitter_Notes field is free text and may contain email addresses, phone numbers, or other PII entered by the submitter. This content is sent to the LLM provider without sanitization.

**Provider data handling:**

| Provider | Location | Data Residency | Retention Policy |
|----------|----------|---------------|-----------------|
| Anthropic (Claude) | External (US) | US data centers | Per Anthropic API terms — no training on API data |
| OpenAI (GPT-4o) | External (US) | US data centers | Per OpenAI API terms — no training on API data |
| MindRouter | On-premises (U of I) | University infrastructure | University-controlled |

**Recommendation:** Use MindRouter (on-premises) as the default provider to keep content within university infrastructure. Use external providers only when MindRouter is unavailable or insufficient.

### 3. Newsletter Generation & Export

**Published content includes:** Final edited headlines and bodies, section headings, calendar events, job postings, recurring messages.

**Published content excludes:** Submitter names/emails, editorial notes, AI metadata, edit history.

**Export format:** Microsoft Word (.docx) downloaded by editorial staff.

### 4. External Data Ingestion

| Source | URL | Data Type | Frequency | PII Risk |
|--------|-----|----------|-----------|----------|
| Trumba RSS | trumba.com/calendars/university-of-idaho.rss | Calendar events | On-demand (editor-triggered) | Event descriptions may reference individuals |
| PeopleAdmin | uidaho.peopleadmin.com | Job postings | On-demand (editor-triggered) | Public data; may include hiring contact names |

### 5. File Uploads

**Types:** JPEG, PNG, GIF, WebP images only.

**Storage:** Local filesystem (`uploads/` directory), Docker volume in production.

**Naming:** Files renamed to UUID on upload (original filename discarded).

**EXIF metadata:** Stripped on upload for supported still-image formats. The upload
path fails closed: if the server cannot process and re-save an uploaded image
without metadata, the saved file is deleted and the upload is rejected. GIF files
are accepted without EXIF rewriting.

**Recommendation:** Keep EXIF-stripping tests in the release gate and document
any future supported media types before enabling them.

---

## FERPA Considerations

The Family Educational Rights and Privacy Act (FERPA) protects student education records. This system's FERPA exposure is limited:

**My UI newsletter (student-facing):**

- The application does not access, store, or process student education records.
- Submissions to My UI may come from students, but only collect name and email for editorial contact — not student IDs or academic records.
- Published newsletter content is intended for public distribution and does not contain protected student information.

**Conclusion:** This system does not process FERPA-protected education records. However, submitter name/email for student submissions should be treated as directory information and protected accordingly.

---

## Data Retention Policy

| Data Type | Retention Period | Justification |
|-----------|-----------------|---------------|
| Submissions (including PII) | 2 academic years | Reference for recurring content and editorial continuity |
| Edit history / versions | Same as parent submission | Audit trail for editorial decisions |
| Published newsletters | Indefinite | Institutional record |
| Calendar events / job postings | 90 days after publish date | Ephemeral external data |
| Uploaded images | Same as parent submission | Associated media |
| Style rules and configuration | Indefinite | Active system configuration |
| AI provider API logs | Not currently logged | Consider structured logging (see audit logging task) |

**Deletion:** When a submission exceeds its retention period, all associated records (links, schedule requests, edit versions, images, newsletter item references) should be purged. Implement a scheduled cleanup job.

---

## Data Minimization

| Current State | Recommendation |
|--------------|----------------|
| Submitter_Notes sent to LLM without sanitization | Strip email/phone patterns before LLM submission |
| Image EXIF metadata is stripped for supported formats | Keep fail-closed behavior and tests in place |
| No automated data expiry | Implement retention-based cleanup job |
| Assigned_Editor stored as name string | Consider referencing by internal ID |

---

## UDM and Portfolio Governance Alignment

UCM Daily Register follows the UI Insight portfolio's UDM-derived modeling
conventions: `PascalCase_With_Underscores` column names, async SQLAlchemy models,
database-backed controlled vocabularies, Pydantic schemas that mirror ORM field
names, and TypeScript interfaces that mirror API response shapes.

Unlike OpenERA, UCM is not a research-administration system and does not
implement canonical research UDM entities such as `Proposal`, `Award`,
`Personnel`, or `Organization`. Its tables should be documented as a
communications-domain extension of the UDM pattern language: submissions,
editorial versions, publication issues, publication sections, recurring
messages, schedule rules, and AI editorial policy.

See [UDM Alignment](udm-alignment.md) for the table-level alignment matrix,
extension rationale, and recommended governance artifacts.

The staff application also includes a Data Governance tab modeled after
OpenERA's interactive Data Dictionary page. It is a searchable, expandable
catalog of the UCM ORM surface, classifications, PII flags, and AllowedValue
relationships. This improves day-to-day visibility, but it is not yet a
database-backed `DataDictionary` table or automated drift-control process.

---

## Third-Party Data Processors

| Processor | Data Shared | Purpose | Terms |
|-----------|------------|---------|-------|
| Anthropic | Submission content and submitter notes; submitter name/email excluded | AI copyediting | API Terms of Service -- data not used for training |
| OpenAI | Submission content and submitter notes; submitter name/email excluded | AI copyediting (alternate provider) | API Terms of Service -- data not used for training |
| MindRouter (U of I) | Submission content and submitter notes; submitter name/email excluded | AI copyediting (on-prem) | University-controlled infrastructure |
| Trumba | None (read-only RSS) | Calendar event import | Public feed |
| PeopleAdmin | None (read-only scrape) | Job posting import | Public portal |

---

## Access Control Summary

| Role | Can Create | Can Read | Can Edit | Can Delete | Can Export |
|------|-----------|---------|---------|-----------|-----------|
| Public | Submissions | Created submission response and public allowed values | Limited submission fields when the submission ID is known | No staff-gated deletes | No staff-gated exports |
| SLC | SLC event submissions | Redacted SLC calendar feed | Same limited public submission fields | No staff-gated deletes | No staff-gated exports |
| Staff | All submissions, newsletters, recurring messages, style rules, and schedule records | All submissions and configuration | All editorial, newsletter, recurring-message, style-rule, and schedule workflows | Staff-gated destructive endpoints | All newsletters |

**Note:** There is no admin role. The current role model is still perimeter
trusted rather than per-user OAuth/JWT authorization: the application validates a
shared trusted-header secret, but it does not identify individual users or verify
campus identity tokens directly. Until stronger authentication is implemented,
deployment controls remain part of the access-control boundary.

---

## Incident Response for Data Breaches

If a data breach involving PII (submitter names/emails) is suspected:

1. Immediately notify the University of Idaho Information Security Office
2. Identify the scope of exposed records
3. Assess whether FERPA notification requirements apply
4. Document the incident and remediation steps
5. Review access logs (once audit logging is implemented)

---

## Open Items

- [x] Implement EXIF stripping on image upload
- [ ] Add PII sanitization to Submitter_Notes before LLM submission
- [ ] Implement data retention cleanup job
- [ ] Evaluate authentication hardening (JWT/OAuth vs. trusted perimeter roles)
- [ ] Establish audit logging for data access events
- [ ] Create submitter-facing privacy notice for the submission form
- [x] Add a staff-facing interactive data governance catalog
- [ ] Add a column-level data dictionary with classifications, PII flags, and retention categories
- [ ] Refresh the portfolio governance catalog and communications vocabulary registry
- [ ] Add governance drift checks for ORM/catalog/vocabulary documentation

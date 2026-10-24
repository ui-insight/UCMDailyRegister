# Retention and disposal design

Status: **proposed periods; automatic disposal not implemented**. Reviewed
October 22, 2026. Approval reference: **pending Data Owner and records review**.
The application must not infer approval from the earlier retention table.

## Categories and clocks

| Category | Coverage | Proposed period / clock | Enforced today |
| --- | --- | --- | --- |
| submission_source | Submission contact, original copy/notes, links, requested dates, images, edit history and durable AI task instructions/results | Two academic years after last editorial activity; owner must define year boundary and holds | No expiry job; staff deletion also removes AI task rows, but is not comprehensive disposal |
| publication_archive | Issue and published item snapshot, including public external content | Indefinite, subject to approved records schedule | No automatic expiry |
| external_working | Harvested occurrences and associated ops assessments | 90 days after event end (start if no end), subject to unresolved planning and promotion dependencies | No automatic expiry |
| feedback | Contact, report content, context and notification state | Proposed 90 days after resolution; Status transition and resolution timestamp need agreement before enforcement | No automatic expiry; current model has no dedicated resolution timestamp |
| configuration | Vocabularies, sections, rules, publication schedule and recurring library | Active life plus owner-approved change/records requirements | No automatic expiry |
| identity_session | App JWT and OIDC state cookie | JWT defaults to eight hours; cookie defaults to 14 days | JWT signature/expiry enforced; browser cleanup on sign-out or next token hydration, not remote erasure |
| diagnostics | Application/server diagnostics and ingress logs | Proposed 90 days general, one year security/error where approved | Compose stdout size rotation only; time-based central retention unverified |
| backup | DB/upload/secret backup copies | Proposed daily 30 days, weekly 90 days, monthly one year | Installation, encryption/access and expiry evidence pending |

These are reviewable proposals, not institutional records authorization. For
unpublished, rejected or abandoned submissions the same provisional source
category applies; do not keep contact data indefinitely merely because status
never became published. Holds override age-based disposal.

## Inventory before disposal

Run from `backend/` against an approved database with a read-only account when
available. Supply the **explicit cutoff** authorized for the review; the tool
does not interpret academic-year boundaries or delete anything:

```bash
python -m app.governance.retention_preview --before 2024-07-01
```

The cutoff is midnight UTC, matching the application's naive UTC timestamps.
The JSON result contains counts of old submissions, their AI task copies, placements that block source
deletion, upload references, feedback, harvested events and assessments. It contains
no names, email addresses, bodies, paths or record IDs. Age alone never proves
eligibility: holds, ongoing recurrences, staff decisions, downstream references and
backup copies require separate review. Never use the preview output as a purge list.

## Publication preservation decision

`newsletter_items.Submission_Id` is required. Approval/source-version pointers
also reference edit history. Therefore blindly cascading submission or version
deletion can break or remove an institutional issue archive.

Before implementing disposal, approve one of these migration designs:

1. Preserve a minimized source stub, clear contact/notes and source versions,
   retain published snapshots, and explicitly decide how to handle original copy
   that may contain personal data. Do not describe this as full source erasure.
2. Decouple published snapshots from source submissions with reviewed nullable
   provenance keys and migration rules; then dispose of eligible source records.

No choice is approved in this change. There is no deletion job or hidden default.
The implementation must recheck dependencies and holds within a transaction, clear
approval/version references in the documented order, and preserve approved issue
copy. Unpublished placeholders and promoted harvested events need explicit rules.

## Disposal acceptance procedure

1. Data Owner approves category, clock, hold rules, exceptions and archive design;
   records authority and privacy reviewer references are recorded in decisions.
2. Technical owner implements migration, dry run, bounded batches, idempotency and
   failure reporting. A changed record since preview is skipped and re-reviewed.
3. Upload cleanup resolves UUID paths strictly inside the configured upload root,
   verifies no surviving reference, and retries failed filesystem removals. File
   deletion and database commits need an explicit retry ledger; do not claim
   atomic deletion across database and filesystem.
4. Verify on synthetic data: unreferenced vs published sources, approval/version
   pointers, promoted events, ops child rows, recurring schedules, holds, changed
   records, missing files, permission errors and interrupted batches.
5. Capture counts/outcomes and cutoff/policy version, without content or contact
   values. Record a restricted run ID and reviewer. Enable a schedule only after
   these acceptance checks and a recovery exercise pass.
6. Expire backups by approved tier. Restores are isolated; replay approved disposal
   decisions before making restored data accessible. Keep any suppression ledger
   separately secured so restore does not silently reintroduce disposed data.

Database backups and uploads must be restored to matching recovery points.
Retention of exported Word files and manually created GitHub issues is outside
application deletion; the responsible owner must include those copies in the
records procedure. See [Backup and recovery](../backup-and-recovery.md).

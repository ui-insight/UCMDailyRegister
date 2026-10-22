# UDM alignment

Reviewed October 22, 2026. UCM Daily Register applies AI4RA-UDM-derived portfolio
modeling patterns to communications and operational support. It does not claim
newsletter entities are canonical research-administration UDM entities.

## Alignment and deliberate variations

| Pattern | Current implementation | Remaining consideration |
| --- | --- | --- |
| Column names | `PascalCase_With_Underscores` | Preserve API/type naming during migrations |
| ORM and relationships | SQLAlchemy async models, `sa` imports and selectin relationships as project conventions | Review each model change; no blanket future conformance claim |
| Table/PK naming | Lowercase plural tables and UUID `Id` keys | Legacy application variation from portfolio singular PascalCase/entity-ID patterns |
| Controlled vocabularies | `allowed_values` with `(Value_Group, Code)` uniqueness | Code-validated exceptions and runtime/seed reconciliation remain explicit |
| Schema change control | Alembic plus PostgreSQL CI drift check | No live schema attestation from a local test |
| Data dictionary | Complete file-backed catalog driving UI and generated Markdown | No DB-backed catalog table; classifications await owner approval |
| Governance drift | CI validates ORM columns, catalog metadata, seed references, evidence and generated pages | Portfolio repository and live runtime state need separate reconciliation |

`allowed_values` is a UDM-derived pattern. Submission intake, editorial versions,
publication issues/items/sections, recurring content, scheduling, harvested events
and ops assessments are communications-domain extensions. `product_feedback` is
operational support. The complete classifications, table inventory and stewardship
roles are in the [data dictionary](governance/data-dictionary.md).

The [generated reference inventory](governance/reference-data.md) contains current
bootstrap counts and values. Provider IDs, auth roles, some SLC values, recurrence,
feedback states and override actions still have code-governed contracts; do not
assert that adding a DB value alone makes every new behavior supported.

## Lineage and ownership

See [Data governance](data-governance.md) for intake → AI editing/repair → approval
→ issue snapshot → export, and Trumba harvest → independent SLC/ops review →
classification/promotion. Explicit version pointers preserve publication provenance.
Per-assessment model/prompt version persistence, formal lifecycle transitions,
retention enforcement and actor access auditing remain incomplete.

Catalog steward roles are proposed teams, not named accepted ownership. Institutional
classification mapping, processor decisions and publication-preserving disposal
need the approvals recorded in [Governance decisions](governance/decisions.md).

## Schema and vocabulary change protocol

1. Classify the change as UDM-derived pattern, communications extension or
   operational support. Explain domain meaning and any legacy variation.
2. Update ORM, migration, Pydantic schemas, frontend types and behavior together.
3. Review column classification/PII risk, source, steward, retention category,
   permissions and vocabulary mappings in the canonical catalog.
4. Update seed data where intended. Review existing runtime values separately;
   do not reset staff-edited configuration merely to match bootstrap counts.
5. Regenerate dictionary/reference pages with `python scripts/check_governance.py --write`;
   update data-model explanations, evidence assertions and relevant decisions.
6. Run governance validation, strict docs, backend tests and frontend checks.
   Obtain owner/security review for handling/access changes and record approvals.
7. Reconcile the portfolio catalog/vocabulary registry through its own reviewed
   change. Record application and portfolio revisions; verify environment migration
   and readiness during release.

## Portfolio registry reconciliation

Prior reports referred to `../data-governance` as stale. This remediation did not
inspect or modify that repository, so its present state is **unverified**. Use the
canonical application catalog and generated reference inventory to reconcile its
UCM catalog, communications vocabulary, domain ERD and application inventory.
Do not equate passing application CI with verified cross-repository synchronization.

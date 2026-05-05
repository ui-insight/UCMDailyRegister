# Enterprise AI Framework Evidence

UCM Daily Register publishes a machine-readable evidence manifest for the
University of Idaho Enterprise AI Development Framework discussion draft. The
manifest is the source this project owns; aggregation systems such as AISPEG can
ingest it without scraping GitHub issue prose or Markdown documentation.

## Files

| File | Purpose |
| --- | --- |
| [`evidence.json`](evidence.json) | UCM Daily Register compliance assertions, evidence links, GitHub issue references, and blockers |
| [`evidence.schema.json`](evidence.schema.json) | JSON Schema for validating the manifest before ingestion |
| [`approved-stack-evidence.md`](approved-stack-evidence.md) | Human-readable evidence matrix for OIT approved-stack issue #171 |

Canonical raw URL:

```text
https://raw.githubusercontent.com/ui-insight/UCMDailyRegister/main/docs/governance/enterprise-ai-framework/evidence.json
```

Schema raw URL:

```text
https://raw.githubusercontent.com/ui-insight/UCMDailyRegister/main/docs/governance/enterprise-ai-framework/evidence.schema.json
```

## Ingestion Contract

Aggregation tools should use this sequence:

1. Fetch `evidence.json` from the raw GitHub URL above.
2. Validate the payload against `evidence.schema.json`.
3. Use `project.slug + framework.id + requirements[].id` as the stable primary
   key.
4. Refresh linked GitHub issue state from each `requirements[].github_issue`
   number.
5. Treat `current_assertion.status` as the compliance claim and GitHub issue
   state as the work-tracking state.

The manifest intentionally separates those two states. A requirement can have a
closed issue because the evidence packet is complete, while the assertion status
may still be `needs_decision` if OIT has not made a policy decision yet.

## Assertion Status Values

| Status | Meaning |
| --- | --- |
| `not_started` | No compliance claim has been validated yet |
| `aligned` | UCM Daily Register appears to meet the requirement and has evidence ready for review |
| `partially_aligned` | UCM Daily Register meets part of the requirement, but needs more implementation, validation, or evidence |
| `gap` | UCM Daily Register does not currently meet the requirement |
| `not_applicable` | The requirement does not apply to UCM Daily Register, with rationale captured in evidence |
| `needs_decision` | Compliance depends on an OIT, security, product ownership, or governance decision |

## Evidence Lifecycle

Each requirement in the manifest points to a GitHub issue labeled
`standards-evidence`. The issue is where implementation notes, review comments,
manual evidence, and final validation notes accumulate.

When evidence changes:

1. Update the GitHub issue with the evidence or validation note.
2. Update `evidence.json` if the compliance assertion, evidence source list, or
   blockers changed.
3. Keep repo file links stable where possible so aggregation systems can retain
   history by requirement ID.

The parent tracking issue is
[#170](https://github.com/ui-insight/UCMDailyRegister/issues/170).

AISPEG ingestion is tracked in
[#258](https://github.com/ui-insight/AISPEG/issues/258).

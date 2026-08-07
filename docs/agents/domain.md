# Domain docs

This is a single-context repository. Engineering skills should consume its domain documentation using the following rules.

## Before exploring

- Read `CONTEXT.md` at the repository root when it exists.
- Read ADRs under `docs/adr/` that touch the area being changed.
- If either location does not exist, proceed silently. Domain-document producer workflows create them when terminology or architectural decisions are resolved.

## Use the glossary's vocabulary

When output names a domain concept in an issue title, refactor proposal, hypothesis, or test name, use the term defined in `CONTEXT.md`. Do not drift to synonyms the glossary explicitly avoids.

If a needed concept is absent, reconsider whether the work is inventing language the project does not use or note the genuine vocabulary gap for a domain-document workflow.

## Flag ADR conflicts

If proposed work contradicts an existing ADR, surface the conflict explicitly rather than silently overriding the decision.

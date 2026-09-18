# Architecture and production-readiness review — September 18, 2026

For editors and product owners, see the [plain-language findings and proposed remediation plan](reliability-plan-for-product-owners-2026-09-18.md).

## Judgment

The application has a suitable technical foundation and has made real progress, but it is not yet a demonstrated dependable production platform. Repeated feedback exposes weak ownership of editorial content, inconsistent editorial policy, and incomplete verification across the full publishing workflow. The appropriate response is a focused reliability and architecture phase within the existing React/FastAPI/PostgreSQL application.

Keep the modular monolith. Neither a rewrite nor a microservice migration is justified by this review. Traffic capacity is not the immediate problem: preserving an editor's decisions and producing a correct newsletter are.

## Scope and evidence

- Reviewed the September 15 reports filed as GitHub issues #373–389 and earlier feedback/issue history. Checked current issue states, including previously closed issues covering the same themes.
- Reviewed local checkout `d4d4712` and fetched/reviewed the difference through current `origin/main`, `7631fbc` (September 16). The newer change is the sign-in experience; it does not change the editorial/export findings below.
- Reviewed repository history beginning February 13, 2026: approximately seven months of development.
- Inspected nonsecret runtime configuration and style-rule fingerprints in development and production. Both use MindRouter with `openai/gpt-oss-120b`. Both have all 99 seed rules, active, with text matching the reviewed repository. Neither runtime implements the newer `auth_provider` setting. Production frontend reports `TRUSTED_ROLE_HEADER_ROLE=staff`.
- Reproduced hyperlink loss by generating a DOCX from synthetic linked content and inspecting its XML/relationships: anchor text remained, but no hyperlink element or destination remained.
- Reproduced selection of older final text by executing the actual version-selection function with two chronological final versions. This proves the selection defect; database row ordering itself is unspecified.
- All 196 frontend tests in the local checkout passed. Latest main GitHub CI passed. Local backend pytest collection was blocked by a missing installed `jwt` dependency; no local backend-suite pass is claimed.
- This was not a live-model quality benchmark, load test, penetration test, restore exercise, or complete infrastructure audit. Missing operational evidence below is not proof that the corresponding infrastructure is absent. No application fixes or deployment changes were made.

## Are problems recurring?

Yes. Thirteen new issues concern AI editorial behavior; four concern saved content, Jobs output, sorting, and hyperlinks. Earlier issues for most of these themes were closed during July and August. However, distinguish repeated symptoms from proven regressions: a new report can expose an old gap, a different interaction, an undeployed fix, or a changed requirement.

| Theme | Earlier issues | New issues | Interpretation |
|---|---|---|---|
| Event ordering, complete sentences, acronyms, months | #194, #228, #232, #300, #324 | #373, #381, #383 | Repeated requirements after several correction passes |
| Meaning, audience, recurrence, factual invention | #277, #300, #305, #312, #313, #322 | #375, #377–380, #382, #385 | Related failures to preserve source meaning, with additional protected fact types |
| Headline repeats lead | #276 | #376 | Direct follow-up to an implemented requirement |
| Relative dates and weekday conflicts | #306, #325 | #374, #384 | Recurrence mixed with editorial-policy changes |
| Saved editorial work disappears | #64, #193, #198 | #386 | Persistent ambiguity about which content version is authoritative |
| Jobs treated as articles | #197, #281, #299, #304 | #387 | Repeated mismatch between structured listings and article editing |
| Hyperlinks across editing and publication | #202, #227, #309, #326 | #389 | Repeated integrity failures across representations; export loss is confirmed |
| Earliest actionable date determines ordering | #274 | #388 | New ordering capability, not a demonstrated sorting regression |

The July 17 feedback digest already documented original-content loss, repeated style complaints, Jobs requirements, link editing, and scope confusion. These are foundational expectations. The March stakeholder feedback also expected the editor's final text to be the text published.

The currently matching rule databases rule out missing or stale seed text as the current explanation for these reports. They do not prove what prompt/model/configuration was used when each report was filed. Future diagnostic records need that provenance.

## Where structure is failing

### 1. Editorial authority is distributed across views and copies

The Editor chooses the latest version from a chronologically ordered API result. Builder's `_get_best_text` instead chooses the first version of the preferred type. The ORM relationship has no defined ordering. Thus the same submission can produce different content depending on which module reads it.

Existing newsletter items also contain copied headline/body text without a source revision identifier. Reassembly deliberately leaves that text alone, protecting manual Builder edits but hiding later upstream corrections. Automatically overwriting all Builder items would introduce another data-loss problem.

AI completion unconditionally sets a submission to `ai_edited` after waiting for its model call. A human approval during that wait can therefore be superseded by an older operation. Revision checks and explicit transition rules are missing.

**Deepening opportunity:** concentrate revision selection, staff edits, approval, and edition snapshots in one editorial-content module. Its implementation should own precedence and conflict detection so callers do not reimplement them. Record which revision is approved for which newsletter, and identify edition overrides and upstream changes explicitly. This improves locality and gives tests a meaningful interface: approved content survives every scheduling and publication transition.

Evidence: `backend/app/services/newsletter_service.py:361,451`; `backend/app/models/submission.py:91`; `backend/app/models/newsletter.py:73`; `frontend/src/pages/EditPage.tsx:89`; `backend/app/api/v1/ai_edits.py:147,253,330`.

### 2. Links are content, but their representations are independent

The application uses inline HTML, mutable submission-link rows, editor link arrays, and copied newsletter bodies. These can diverge across revisions. Word export extracts link text and paints it blue/underlined but discards the destination. Git blame shows that implementation dates to the initial February 13 pipeline, rather than a recent regression. Its docstring even claims URLs are appended when the implementation does not do so.

**Deepening opportunity:** make text and its attached links one versioned content module, with rendering adapters for editor, Builder and DOCX. The test interface must verify destinations and anchor associations in the final artifact, not just whether a preview displays underlining. This also protects job application links.

Evidence: `backend/app/utils/export.py:97`; `backend/app/api/v1/ai_edits.py:340`; `backend/app/services/ai/editor.py:690`; `frontend/src/pages/EditPage.tsx:95`.

### 3. Editorial policy has multiple authorities

Database rules, seed JSON, migrations, hard-coded prompts, and deterministic validators all shape the same behavior. For example, the prompt requires a complete event sentence but provides an event-detail fragment as its example. First-person rewriting can substitute an organization name, while new feedback prohibits inventing the speaker.

This is not merely a lack of prompt engineering. The system needs an explicit hierarchy: preserve source facts and editorial intent, apply approved transformations, enforce mechanically checkable formatting, and flag unresolved ambiguity.

The pipeline has already evolved usefully: it performs deterministic checks, a bounded repair attempt, and reports remaining findings. Existing production-derived fixtures test bad output, successful repair, provider failure, and a stubborn model. Those are valuable tests, but their providers return prescribed answers. They do not establish that the actual deployed model follows the full editorial policy.

**Deepening opportunity:** concentrate policy precedence and validation in an editorial-policy module; retain the real provider seam and its multiple adapters. Record rule/prompt/model versions, then maintain a reviewed evaluation set measuring factual preservation, dates, links, audience, Jobs formatting, and editing effort. Run model evaluations separately from deterministic unit tests and compare releases on the same cases.

Evidence: `backend/app/services/ai/prompts.py:62,75,94`; `backend/app/services/ai/editor.py:549`; `backend/tests/test_issue_300_production_fixtures.py:20,138`.

### 4. Content dates and publication dates need separate meanings

The prompt refers to publication date without receiving explicit publication/current-date/timezone context in its user prompt. Validators use `date.today()`. Upcoming event dates, registration deadlines, publication schedules, and recurring occurrences are different domain facts; prose alone is an unreliable basis for sorting them.

Three decisions should precede implementation:

1. #374 requests replacing relative dates; #325 requests preserving both relative wording and explicit dates. Define reference date, timezone, and source precedence.
2. #384 requests preserving contradictory source weekday/date values for staff review. Distinguish this from deriving a missing weekday from a known date under #306.
3. #387 requests visible job titles, while #299 intentionally removes a separate published headline. Editor visibility and published formatting need distinct rules.

**Deepening opportunity:** give verified content facts and publication scheduling separate ownership. Treat article copy, structured Jobs listings and imported calendar entries as distinct content types with shared publication mechanisms. Do not infer newsletter audience eligibility from the publication channel.

Evidence: `backend/app/services/ai/prompts.py:86,127`; `backend/app/services/ai/editor.py:490,557`; `backend/app/models/submission.py:61`; `backend/app/services/newsletter_service.py:319,375`.

## What has evolved correctly

- The React/FastAPI/PostgreSQL architecture fits the workload and remains understandable.
- Provider adapters provide a useful seam with multiple actual implementations.
- Original content is preserved on finalization; final text and approval status are saved together.
- Seeding no longer overwrites staff-edited rules by default, addressing the earlier #195 failure.
- Imported Jobs have deterministic structured formatting.
- Alembic migrations, migration-drift CI, PostgreSQL smoke checks, server-side role dependencies, upload validation and frontend workflow tests are substantial improvements.

The problem is incomplete consolidation around the domain rules those improvements revealed. Moving more functions into files would not by itself fix this. A deep module earns its place by keeping an important rule consistent across callers.

## Production dependability and scale

**Authentication requires a verified deployment, not just merged code.** Production currently stamps staff at the proxy and lacks the newer SSO configuration. This establishes no application-level distinction between individual visitors reaching that proxy; upstream network restrictions were not audited. Before an SSO rollout, address two code-derived hazards: bearer tokens are accepted in header mode even though signing-key validation is skipped there, and trusted-header roles remain accepted in OIDC mode. The public default signing key makes the first combination unsafe. That is a repository deployment hazard, not a claim of an active exploit against the older production runtime.

**AI work is process-local.** The job dictionary, semaphore, and FastAPI background tasks lose state on restart and do not work reliably across multiple workers. Results have no eviction. Persist job state, bound the backlog, recover interrupted work, and check the input revision before applying results. A small durable worker arrangement is sufficient; a broad distributed architecture is unnecessary.

**CI does not yet enforce the strongest available tests.** The frontend CI job lints and builds but never runs Vitest. Backend tests primarily use SQLite; PostgreSQL CI verifies migrations and performs smoke checks. Add frontend tests to CI, then a few complete submission-to-DOCX and concurrent-edit scenarios. Green CI is useful evidence within its actual scope.

**Operations need proof.** Backup and recovery documentation gives useful procedures and target RTO/RPO values, but this review did not verify a successful restore, alert delivery, or named operational coverage. Reconsider whether losing 24 hours of submissions or waiting four hours near a publication deadline is acceptable. Feedback notifications are still disabled in production.

**Builds and capacity need bounded improvements.** Backend dependencies have lower bounds without a resolved lockfile; rebuilding an old commit can change its dependencies. Record deployed commit, immutable image, schema revision and policy version. Some filtering/assembly loads broad candidate sets and eagerly fetches edit history; measure with realistic retained history and optimize those paths. No current load result justifies a claim that the system is slow, or that a new database/stack is needed.

Evidence: `backend/app/api/deps.py:26,73,76`; `backend/app/config.py:153`; `backend/app/auth/session_tokens.py:35`; `backend/app/api/v1/ai_edits.py:51,228`; `.github/workflows/ci.yml:72`; `backend/tests/conftest.py:19`; `backend/pyproject.toml:6`; `backend/app/services/submission_service.py:186`; `docs/backup-and-recovery.md`.

## Documentation and scope

Documentation is substantial but not a reliable current domain map. The architecture service inventory omits several newer systems. It still describes a Compose database container although PostgreSQL is external. README says 37 seeded rules; the actual count is 99. PRODUCT.md lists three audiences and omits Ops. There is no CONTEXT.md and only one ADR, for authentication.

The application now covers newsletter production, leadership-calendar intelligence, and event-services triage/classification. These can remain in one deployment, but should have explicit owners, vocabularies, access rules, and module interfaces. Their expansion does not establish that the core newsletter workflow is ready. The earlier feedback already questioned SLC/calendar scope.

Update documentation around source submission, AI draft, staff working revision, approval, edition snapshot, actionable date, audience versus channel, standing policy, and feedback disposition. Record the contentious decisions, rather than relying on successive issue bodies to define the product.

## Recommended sequence and release evidence

1. **Protect editorial work and access first:** fix final-version selection and real DOCX links; resolve authentication defaults and verify the deployment cutover. Preserve a manual editorial path when AI is unavailable.
2. **Consolidate content ownership:** explicit revisions, approval transitions, link snapshots, conflict checks, edition overrides and upstream-change indication. Use #386/#389 as end-to-end acceptance cases.
3. **Resolve policy and evaluate:** agree date and Jobs semantics; consolidate contradictory instructions; benchmark the deployed model against reviewed source-fidelity cases. Treat #373–385 as one policy/evaluation programme with individually traceable reports.
4. **Make release and recovery repeatable:** durable AI jobs, frontend CI, PostgreSQL workflow checks, immutable releases, actual restore/alert exercises, and deployment fingerprints.
5. **Refresh domain documentation and scope:** establish ownership of newsletter, SLC and Ops modules; stage additional expansion against evidence that the core workflow is dependable.

Before calling the application dependable production, demonstrate that two editors cannot silently overwrite each other; a restart does not lose AI job state; the selected approved revision reaches Builder and Word unchanged except for deliberate edition edits; every published link retains its destination; anonymous/SLC/Ops/staff access behaves correctly; and a real backup restores within an editorially acceptable deadline. Close the feedback loop with editor acceptance on the deployed build, recording report → issue → implementation → deployment → retest.

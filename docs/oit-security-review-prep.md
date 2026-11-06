# OIT Security Review Preparation

Planned on **November 6, 2026**. Not started yet.

After the rollout meeting with Trevor, the next step is to request a security
review of UCM Daily Register from OIT. Colin Addington is submitting the
request. This plan covers our part: moving the repository into the `ui-AI4UI`
organization and assembling a review packet that includes a data flow diagram.

## Sequence

1. **Transfer the repository to `ui-AI4UI` first.** Then every link in the
   packet points at the repository's permanent home, and OIT reviews it where it
   will live. The transfer does not affect the running application. Prod and dev
   run from their own clone on openera and do not depend on GitHub at runtime.
2. **Build the data flow diagram and review packet** while the transfer
   settles.
3. **Run our own reviews** so OIT doesn't find the easy problems.
4. **Colin submits** the request with the packet.

## Workstream A: repository transfer

Follow Phase 1 of the
[GitHub Enterprise Migration runbook](github-enterprise-migration.md). Its
inventory dates from August 6, 2026. A recheck on November 6, 2026 found:

| Item | August 6 | November 6 | Action |
| --- | --- | --- | --- |
| Open issues / PRs | 72 / 5 | 107 / 0 | Record counts again immediately before transfer |
| Destination name | Available | `ui-AI4UI/UCMDailyRegister` still available | None |
| Repository Actions secrets | None | None | None |
| External actions | GitHub-authored only | CI also uses five actions from public `ui-insight/code-health-kit` | Confirm `ui-AI4UI` Actions policy allows them (needs org admin or the `admin:org` token scope to check) |
| `ui-insight` references | Not counted | 97 lines across about 20 files | One reference-update PR after transfer |

### Transfer checklist

- [ ] Decide who needs push access. `ui-AI4UI` gives members **read** by
      default, so create a team (for example `ucm-daily-register-developers`)
      with write access before transfer.
- [ ] Confirm the `ui-AI4UI` Actions policy permits GitHub-authored actions and
      `ui-insight/code-health-kit/*`.
- [ ] Confirm public repositories and public GitHub Pages are allowed.
- [ ] Record the issue, PR, collaborator, Pages and Actions inventory.
- [ ] Transfer (organization owner: **Settings → General → Danger Zone →
      Transfer**). Never recreate `ui-insight/UCMDailyRegister`, which would
      break GitHub's redirect.
- [ ] Reference-update PR: `mkdocs.yml`, feedback issue builder and its tests,
      governance evidence JSON and schema IDs, docs, `CLAUDE.md`, agent
      instructions. Leave `code-health-kit` action references and AISPEG links
      pointing at `ui-insight`.
- [ ] Update the openera server clone remote and local clones.
- [ ] Docs URL becomes `https://ui-ai4ui.github.io/UCMDailyRegister/` with no
      redirect. Update any links already shared with Joy or OIT.
- [ ] Run the runbook's post-transfer validation.

**Visibility decision:** keeping the repository public avoids a credential
problem on the server, which currently pulls over HTTPS without credentials. If
OIT asks for a private repository, an approved machine credential is needed
first (options in the runbook).

## Workstream B: data flow diagram and review packet

### Data flow diagram

The text description in [Data Governance](data-governance.md#data-flows-and-external-processing)
and [Architecture](architecture.md#data-flow) describes the pipeline steps. OIT
will want trust boundaries. The diagram should show:

- **Hosting:** browser → nginx (only host port 9280 prod / 9290 dev exposed) →
  FastAPI on the internal 10.x Docker network → PostgreSQL on `insight-db-net`,
  and the upload volume.
- **Identity:** Microsoft Entra SSO and optional Graph group lookup. Show where
  tokens live: signed app JWT in browser localStorage and the session cookie.
- **Off-campus egress:** submission text, including links, sent to Anthropic or
  OpenAI. Content is not automatically sanitized of personal information.
  MindRouter, if used.
- **Inbound public reads:** Trumba calendar and the PageUp careers site.
- **Data at rest and copies:** nightly backups (on-host, unencrypted, no
  off-host copy), .docx exports, staff-prepared GitHub feedback issues.
- **Labels:** each arrow names the data moved and its local handling label
  (Public / Internal / Confidential) from Data Governance.

**Scope decision:** SLC harvesting and the ops classifier are hidden and paused
but still deployed. Default plan: diagram what is live in prod and list those
two as disabled and pending retirement. Alternatively, finish their removal
before the review so they are out of scope.

**Format:** Mermaid in a new `docs/security/` page (renders on GitHub and the
docs site, easy to keep current), with a PNG or PDF export for any OIT form.

### Review packet

A short cover page linking to existing docs:

- System summary, owners and users
- Data flow diagram
- Data inventory and classification ([Data Dictionary](governance/data-dictionary.md))
- AI processors and exactly what each one receives ([AI Editing](ai-editing.md))
- Authentication and roles (ADR-001, ADR-002)
- Secrets handling (environment files, CI secret scan)
- [Audit Logging](audit-logging.md) and [Backup & Recovery](backup-and-recovery.md)
- Known gaps with plans to close them

### Known gaps to state up front

- Backups are on-host only, unencrypted, with no failure alerting.
- Prod restore has not been tested in an isolated environment (dev restore
  passed November 3, 2026).
- No processor approval reference yet for Anthropic or OpenAI.
- Data classification is provisional until Data Owner review.
- Open items from the September 10, 2026 security review.

## Self-review before submission

- [ ] Run the `ai-builder-artifacts-reviewer` skill (README, architecture
      diagram, per-module data flow diagrams, risk assessment, runbook).
- [ ] Run the `ai-builder-security-review` skill (pages or endpoints that skip
      university SSO, standalone logins, committed credentials, APM 30.11 field
      labels).
- [ ] Fix findings or add them to the known-gaps list.

## Open questions for Colin and OIT

- Does OIT have its own intake form or diagram template? If so, build to it.
- Is a GitHub Enterprise migration planned after the transfer? (See the
  runbook's Phase 2 questions.)
- Does OIT need to approve the AI processors (Anthropic or OpenAI versus
  MindRouter) as part of this review?

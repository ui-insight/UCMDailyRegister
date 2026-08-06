# GitHub Organization Transfer and Enterprise Migration

This runbook describes how to move UCM Daily Register from
`ui-insight/UCMDailyRegister` to `ui-AI4UI/UCMDailyRegister` and how to prepare
for a later migration into the University of Idaho's GitHub Enterprise
environment.

The two changes must be treated separately:

1. **Repository transfer:** move the existing GitHub.com repository between the
   `ui-insight` and `ui-AI4UI` organizations.
2. **Enterprise migration:** allow OIT to attach the organization to, or import
   its repositories into, a university-managed GitHub Enterprise environment.

The first change is low risk for the running application. The risk of the second
depends on the GitHub Enterprise product and identity model selected by OIT.

## Executive assessment

Moving the repository to `ui-AI4UI` does not move or restart the production
application. Production and development run as Docker Compose projects on
`openera.insight.uidaho.edu`; their PostgreSQL databases, uploads, environment
files, DNS names, and running containers are independent of GitHub repository
ownership.

The immediate risks are instead:

- developers losing write access because the organizations have different
  membership and base-permission models;
- the GitHub Pages documentation URL changing without a redirect;
- hard-coded repository URLs continuing to reference `ui-insight`;
- GitHub Actions or Pages being restricted by destination policies; and
- the deployment server losing `git pull` access if a later enterprise migration
  makes the repository private.

## Current-state inventory

This inventory was verified on August 6, 2026. Recheck it immediately before a
transfer or migration.

| Area | Current state | Migration significance |
|---|---|---|
| Repository | Public `ui-insight/UCMDailyRegister`, default branch `main` | Eligible for a normal GitHub.com organization-to-organization transfer |
| Destination | `ui-AI4UI` exists and does not contain a repository named `UCMDailyRegister` | The destination name is available |
| Repository authority | Current maintainer has admin access to the repository and owner access in both organizations | The maintainer can perform the normal repository transfer |
| Open work | 72 open issues and 5 open pull requests | Must remain present and usable after transfer |
| CI | GitHub Actions on standard GitHub-hosted runners | Destination and enterprise Actions policies must permit the workflows |
| Actions history | 419 workflow runs | Preserved by a normal transfer, but not by GitHub Enterprise Importer |
| Actions configuration | No repository Actions secrets or variables; no custom or self-hosted runners | Reduces importer follow-up work |
| Documentation | MkDocs publishes from `gh-pages` to public GitHub Pages | Pages URL changes on repository transfer and does not redirect |
| Pages environment | One `github-pages` environment | Verify after a transfer; recreate after an importer migration if required |
| Integrations | No repository webhooks, releases, Git LFS objects, rulesets, or deploy keys | Reduces transfer and importer risk |
| Branch policy | No branch protection rule on `main` | No existing protection to preserve; destination or enterprise rules may add one |
| Deployment | Manual `git pull` followed by `./deploy.sh dev` or `./deploy.sh prod` | Running services are independent of the repository owner |
| Server clone | `/home/devops/UCMDailyRegister`, public HTTPS remote, no credential helper | Works while public; requires approved machine authentication if made private |

### Access-control difference

At the time of the inventory:

- `ui-insight` had 25 members and granted organization members base **write**
  access.
- The repository had no team-specific access grants. Most write access therefore
  came from source-organization membership.
- `ui-AI4UI` had five members and granted organization members base **read**
  access.

Inherited permissions from `ui-insight` do not become destination team grants.
Most existing contributors will therefore lose push access unless they are
invited to `ui-AI4UI` and granted explicit access.

Before transfer, create a destination team such as
`ucm-daily-register-developers`, invite the developers who still need access,
and grant the team `write` access to the repository. Do not reproduce broad
organization-wide write access unless it is an intentional governance decision.

## Enterprise models OIT must identify

"GitHub Enterprise" is not a single migration path. Ask OIT which of the
following is planned before promising dates or behavior.

| Target model | Likely process | Expected effect |
|---|---|---|
| Standard GitHub Enterprise Cloud on `github.com`, using personal GitHub accounts | OIT invites the existing `ui-AI4UI` organization into the enterprise account | Organization and repository URLs remain unchanged; enterprise billing, SSO, 2FA, Actions policies, rulesets, and other controls begin applying |
| GitHub Enterprise Cloud with Enterprise Managed Users | Import repositories or organizations into an enterprise-owned destination | Existing outside organizations cannot simply join; identity and access must be reprovisioned |
| GitHub Enterprise Cloud with data residency on `ghe.com` | GitHub Enterprise Importer into the university's `ghe.com` subdomain | Hostnames and URLs change; importer limitations and follow-up work apply |
| GitHub Enterprise Server | OIT-defined migration into a separate server installation | Separate URLs, authentication, connectivity, feature, and migration considerations apply |

GitHub documents the standard organization-attachment process and its
limitations in [Adding organizations to your enterprise][adding-orgs]. GitHub
documents importer migration paths in [About migrations between GitHub
products][migration-overview].

## Phase 1: transfer the repository to `ui-AI4UI`

### Preconditions

- [ ] Confirm the destination will remain `ui-AI4UI/UCMDailyRegister`.
- [ ] Confirm no repository or fork with that name exists in `ui-AI4UI`.
- [ ] Decide which current contributors need continued push or issue-management
      access.
- [ ] Invite those contributors to `ui-AI4UI` and create explicit team grants.
- [ ] In `ui-AI4UI` organization settings, confirm GitHub Actions is enabled.
- [ ] Confirm the Actions policy permits GitHub-authored actions including
      `actions/checkout`, `actions/setup-python`, and `actions/setup-node`.
- [ ] Confirm the documentation workflow's `GITHUB_TOKEN` can write repository
      contents so `mkdocs gh-deploy` can update `gh-pages`.
- [ ] Confirm public repositories and public GitHub Pages are allowed.
- [ ] Record the issue, pull-request, collaborator, Pages, and Actions inventory
      for post-transfer comparison.
- [ ] Avoid merges and permission changes during the transfer and validation
      window.

### Transfer procedure

1. Open `ui-insight/UCMDailyRegister` on GitHub.
2. Go to **Settings → General → Danger Zone → Transfer**.
3. Select or enter `ui-AI4UI` as the new owner.
4. Keep the repository name `UCMDailyRegister`.
5. Enter the requested confirmation text and complete the transfer.
6. Do **not** create a replacement repository at
   `ui-insight/UCMDailyRegister`. Reusing the old location permanently removes
   GitHub's redirect.

GitHub preserves Git history, issues, pull requests, wiki content, stars,
watchers, releases, repository settings, repository secrets, webhooks, and
deploy keys during a normal repository transfer. Old repository and Git URLs
redirect to the new location. See [Transferring a repository][repo-transfer].

GitHub Pages is the notable exception: the old Pages URL does not redirect.
After the transfer, the expected documentation URL is:

```text
https://ui-ai4ui.github.io/UCMDailyRegister/
```

### Update clones

Redirects provide short-term compatibility, but every maintained clone should
use the destination URL directly:

```bash
git remote set-url origin https://github.com/ui-AI4UI/UCMDailyRegister.git
git remote -v
git fetch origin
```

Update the deployment server as well:

```bash
ssh devops@openera.insight.uidaho.edu
git -C /home/devops/UCMDailyRegister remote set-url origin \
  https://github.com/ui-AI4UI/UCMDailyRegister.git
git -C /home/devops/UCMDailyRegister fetch origin
```

### Update repository references

Replace old-owner URLs where they are intended to identify this repository,
including:

- `mkdocs.yml` repository metadata;
- the frontend feedback issue builder and its tests;
- agent and contributor issue-tracker instructions;
- backup and disaster-recovery clone commands;
- governance evidence JSON, schema IDs, raw-content URLs, and Markdown links;
- issue and pull-request links in project documentation; and
- local and server Git remotes.

Links to other repositories that remain in `ui-insight`, such as AISPEG, must
not be changed mechanically.

Commit and push the reference updates after the transfer. That push should run
CI and republish the Pages branch under the new owner.

### Post-transfer validation

- [ ] Repository is public at `ui-AI4UI/UCMDailyRegister`.
- [ ] Default branch is `main`, with all expected branches and tags.
- [ ] The issue and pull-request counts match the pre-transfer inventory.
- [ ] A sample of issue comments, assignments, labels, and cross-references is
      intact.
- [ ] Required developers have their intended repository roles.
- [ ] CI completes successfully on a push or pull request.
- [ ] The documentation workflow can update `gh-pages`.
- [ ] The new GitHub Pages URL loads.
- [ ] The application feedback link opens the destination issue form.
- [ ] Dependabot remains enabled and can open pull requests.
- [ ] Local development clones can fetch and push.
- [ ] The deployment-server clone can fetch.
- [ ] A normal dev deployment succeeds when the next application change is
      ready; a repository transfer alone does not require a production restart.

## Phase 2: prepare for the OIT enterprise change

### Questions for OIT

Obtain written answers to these questions before the enterprise cutover:

1. Is the target standard GitHub Enterprise Cloud on `github.com`, Enterprise
   Managed Users, GitHub Enterprise Cloud on `ghe.com`, or GitHub Enterprise
   Server?
2. Will OIT attach the existing `ui-AI4UI` organization, or create a new
   organization and import repositories?
3. Will repository and Pages URLs remain unchanged?
4. Are public repositories and public GitHub Pages permitted?
5. Are GitHub Actions and GitHub-hosted runners permitted?
6. May Actions use a write-capable `GITHUB_TOKEN`, and must actions be pinned to
   full commit SHAs?
7. Will Azure Pipelines, ArgoCD, or another OIT service replace any current
   workflow?
8. How will current users and historical contributors be mapped or provisioned?
9. Are outside collaborators allowed?
10. What machine-authentication mechanism is approved for production servers
    that pull private source code?
11. Will OIT perform an importer trial and provide migration logs before the
    production cutover?
12. What maintenance window, change freeze, validation period, and rollback
    process will OIT use?

### Low-disruption path: attach the existing organization

If OIT uses standard GitHub Enterprise Cloud on `github.com`, an enterprise
owner can invite `ui-AI4UI` to join the enterprise. An organization owner
accepts the invitation, and the enterprise owner completes it. GitHub states
that resources remain at the same URLs.

Validate the following inherited enterprise controls immediately afterward:

- SAML SSO and authorization of personal access tokens or SSH keys;
- 2FA requirements and user license availability;
- Actions allow lists, workflow token permissions, and SHA-pinning rules;
- organization or enterprise rulesets and branch protections;
- public-repository and GitHub Pages policies;
- outside-collaborator restrictions; and
- repository creation, deletion, visibility, and administration policies.

### Importer path: managed users, `ghe.com`, or a new destination

If OIT must use GitHub Enterprise Importer, require a trial migration and a
written validation report. GitHub recommends pausing changes during the
production migration because the importer does not support delta migrations.
Changes made at the source after migration begins must be moved manually.

For GitHub.com sources, repository content such as Git history, issues, pull
requests, milestones, wikis, Actions workflow files, repository settings,
releases, and attachments is generally migrated. Important exceptions include:

- all repositories arrive private by default;
- team membership is not migrated;
- Actions secrets, variables, environments, runners, artifacts, and run history
  are not migrated;
- GitHub Apps and their installations are not migrated;
- webhook secrets are not migrated, and migrated webhooks must be re-enabled;
- Dependabot alert history and commit status checks are not migrated;
- repository discussions, comment edit history, and some cross-reference
  semantics are not migrated;
- Git LFS objects are not migrated automatically; and
- user-authored history other than Git commits may initially be assigned to
  placeholder "mannequin" identities until identities are reclaimed.

See [About migrations between GitHub products with GitHub Enterprise
Importer][importer-data] and [Overview of a migration between GitHub
products][importer-runbook] for GitHub's current support matrix and follow-up
tasks.

For this repository, the highest-priority importer follow-up tasks are:

1. Restore the intended public visibility if OIT policy permits it.
2. Recreate team membership and repository access.
3. Recreate and validate the `github-pages` environment and Pages publication.
4. Enable GitHub Actions and validate both workflow files.
5. Rebuild Dependabot configuration and confirm alerts and updates work.
6. Update all repository, raw-content, Pages, and clone URLs.
7. Configure the deployment server with an OIT-approved credential if the
   destination repository is private.
8. Reclaim contributor identities and audit issue/PR assignments.

## Deployment impact and private-repository authentication

The deployed application does not depend on GitHub at runtime. A GitHub outage,
repository transfer, or repository rename does not stop the existing containers.
It affects the ability to fetch new code for a future deployment.

While the repository is public, the deployment server can fetch over HTTPS
without credentials. If an enterprise migration makes it private, do not place
a long-lived token directly in the remote URL. Obtain OIT approval for one of:

- a GitHub App installation with narrowly scoped repository access;
- an organization-approved fine-grained personal access token stored through an
  approved secret-management mechanism; or
- an SSH/deploy-key or machine-user design allowed by enterprise policy.

The chosen credential must be tested for SSO authorization, expiration,
rotation, revocation, incident response, and noninteractive `git fetch` before
the cutover.

## Recovery and rollback

For a normal repository transfer, GitHub redirects the old repository and Git
URLs. Most failures can therefore be corrected in place by restoring access,
adjusting Actions policies, republishing Pages, or updating direct URLs.

If an essential destination policy cannot be corrected, organization owners can
transfer the repository back, provided the old repository name remains
available and policies allow the transfer. Do not create a placeholder at the
old path; doing so removes redirects and complicates rollback.

For an importer migration, follow OIT's approved rollback plan. Keep the source
repository unchanged and unavailable for writes until the destination passes
validation. Do not delete or archive the source as part of the initial cutover.

## Decision record

Record the following before each phase:

| Decision | Owner | Date | Evidence or ticket |
|---|---|---|---|
| Developers receiving destination write access |  |  |  |
| Repository visibility after transfer |  |  |  |
| OIT enterprise product and identity model |  |  |  |
| GitHub Actions approval or replacement |  |  |  |
| GitHub Pages approval or replacement |  |  |  |
| Deployment-server authentication method |  |  |  |
| Trial migration result, if applicable |  |  |  |
| Production cutover and rollback authority |  |  |  |

[adding-orgs]: https://docs.github.com/en/enterprise-cloud@latest/admin/managing-accounts-and-repositories/managing-organizations-in-your-enterprise/adding-organizations-to-your-enterprise
[migration-overview]: https://docs.github.com/en/migrations/using-github-enterprise-importer/migrating-between-github-products
[repo-transfer]: https://docs.github.com/en/enterprise-cloud@latest/repositories/creating-and-managing-repositories/transferring-a-repository
[importer-data]: https://docs.github.com/en/migrations/using-github-enterprise-importer/migrating-between-github-products/about-migrations-between-github-products
[importer-runbook]: https://docs.github.com/en/migrations/using-github-enterprise-importer/migrating-between-github-products/overview-of-a-migration-between-github-products

# Security Baseline

This document defines the minimum security configuration for the
`zurich-opendata-mcp` repository. It covers branch protection on `main`,
the access tokens used by automation, and the force-push prohibition.
These controls are deliberately simple and should be treated as a floor,
not a ceiling.

## Applying these rules in the repository settings

Branch protection is configured through the GitHub UI by a repository
**admin** — it cannot be set by merging this document, and the default
CI token cannot change it. The required status checks only appear in the
picker **after the CI workflow has run at least once** (it has, on the
PRs that introduced it).

### Classic branch protection

1. Open the repo and click **Settings** (admin access required).
2. Sidebar → **Code and automation** → **Branches**.
3. Next to **Branch protection rules**, click **Add classic branch
   protection rule**.
4. **Branch name pattern:** `main`.
5. Enable, to match the policy below:
   - **Require a pull request before merging** → **Require approvals**
     `1`; **Dismiss stale approvals when new commits are pushed**;
     **Require conversation resolution before merging**.
   - **Require status checks to pass before merging** → **Require
     branches to be up to date before merging**; then add the three
     checks: `check (3.11)`, `check (3.12)`, `check (3.13)`.
   - **Require linear history**.
   - **Do not allow bypassing the above settings** (apply to admins too).
   - Leave **Allow force pushes** unchecked (force-push prohibition).
   - Leave **Allow deletions** unchecked (block branch deletion).
6. **Create** / **Save changes**.

### Rulesets (newer UI alternative)

1. **Settings** → **Rules** → **Rulesets** → **New branch ruleset**.
2. Name it (e.g. `main-protection`); **Enforcement status** → **Active**.
3. **Target branches** → **Include default branch** (or pattern `main`).
4. Enable the same rules: require a pull request (1 approval, dismiss
   stale, require conversation resolution); require status checks (add
   the three `check (3.x)` jobs and "require branches to be up to date");
   require linear history; block force pushes; restrict deletions.
5. Leave the **Bypass list** empty so the rules cannot be bypassed.
6. **Create**.

### Verify

Open a throwaway PR (or inspect an open one): the three `check` jobs
should be listed as **Required**, and merging blocked until they pass and
one review approves.

## Required branch-protection rules on `main`

Configure the following under **Settings → Branches → Branch protection
rules** (or the equivalent ruleset) for the `main` branch:

- **Require a pull request before merging.** Direct pushes to `main` are
  not permitted; all changes land through a PR.
  - Require at least **1 approving review**.
  - **Dismiss stale approvals** when new commits are pushed.
  - Require **conversation resolution** before merging.
- **Require status checks to pass before merging**, and require branches
  to be **up to date** before merging. The required checks are the jobs
  produced by `.github/workflows/ci.yml`:
  - `check (3.11)`
  - `check (3.12)`
  - `check (3.13)`

  Each runs `uv run ruff check`, `uv run mypy`, and `uv run pytest`.
- **Require linear history** (no merge commits introduced by force).
- **Do not allow bypassing the above settings** — apply the rules to
  administrators as well. No actor should be able to merge around the
  required checks.
- **Block force pushes** (see below).
- **Block branch deletion** for `main`.

## Force-push prohibition

Force pushes to `main` are **forbidden**. Branch protection must keep
**"Allow force pushes" disabled** for `main`. Rewriting published history
on a protected branch destroys the audit trail, can silently drop
reviewed commits, and breaks every clone and open PR based on the prior
history. If history genuinely must be corrected, do it through a normal
reviewed PR — never via `git push --force`.

The same expectation applies to long-lived shared branches: rewrite only
your own short-lived feature branches, and prefer `--force-with-lease`
over `--force` even there.

## Recommended fine-grained PAT scopes for automation

Automation (CI helpers, release tooling, bots) that needs to authenticate
to this repository should use a **GitHub fine-grained personal access
token**, scoped as narrowly as possible:

- **Resource owner / repository access:** restrict to this **single
  repository** (`malkreide/zurich-opendata-mcp`). Never grant
  "All repositories".
- **Repository permissions — grant only:**
  - **Contents:** Read and write (clone, fetch, push to feature branches).
  - **Pull requests:** Read and write (open PRs, comment, manage review
    state).
- **Do NOT grant `Secrets`** (read or write). Automation has no need to
  read or manage repository/Actions secrets, and that permission would let
  a leaked token exfiltrate every stored credential.
- **Do NOT grant** other write scopes that aren't required — in
  particular avoid `Administration`, `Actions` (write), `Workflows`,
  `Environments`, and `Webhooks` unless a concrete task needs them.
- **Set a short expiration** (e.g. 90 days or less) and rotate on
  schedule. Store the token only as an encrypted GitHub Actions secret or
  in the operator's secret manager — never in the repository.

Prefer the built-in `GITHUB_TOKEN` (with least-privilege `permissions:`
blocks in each workflow, as in `ci.yml`) over a PAT wherever the workflow
runs inside this repository. Reserve fine-grained PATs for cross-cutting
automation that the default token cannot cover.

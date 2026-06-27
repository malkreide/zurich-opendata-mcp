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

> **Current state:** `main` is protected by a **ruleset** (the path
> below). Because this is a single-maintainer repository, **required
> approvals are set to `0`** — see "Solo maintainer" below. All other
> controls (PR required, status checks, linear history, no force-push, no
> deletion) are active.

### Rulesets (current setup)

1. **Settings** → **Rules** → **Rulesets** → **New branch ruleset**.
2. Name it (e.g. `main-protection`); **Enforcement status** → **Active**
   (not "Evaluate" — that only logs and does not block).
3. **Target branches** → **Include default branch** (or pattern `main`).
4. Enable, to match the policy below:
   - **Require a pull request before merging** → **Required approvals**
     (`0` for a solo repo, `1`+ once there are other reviewers); **Dismiss
     stale approvals**; **Require conversation resolution before merging**.
   - **Require status checks to pass** → add the three jobs
     `check (3.11)`, `check (3.12)`, `check (3.13)` (pick them from the
     autocomplete — a bare `check` never reports and stays stuck); enable
     **Require branches to be up to date before merging**.
   - **Require linear history**.
   - **Block force pushes**.
   - **Restrict deletions**.
5. Leave the **Bypass list** empty so the rules apply to everyone,
   including admins.
6. **Create**.

### Classic branch protection (alternative)

If you use classic rules instead of a ruleset: **Settings** → **Branches**
→ **Add classic branch protection rule**, branch pattern `main`, then
enable the same controls — *Require a pull request* (approvals `0`/`1`,
dismiss stale, require conversation resolution); *Require status checks*
(`check (3.11)`/`(3.12)`/`(3.13)` + up-to-date); *Require linear history*;
*Do not allow bypassing the above settings*; leave *Allow force pushes*
and *Allow deletions* unchecked.

### Solo maintainer

For a single-maintainer repository, keep **Required approvals at `0`**: a
PR cannot approve itself, so any non-zero value makes every PR
un-mergeable by the sole maintainer while still keeping the valuable gates
(PR required, CI must pass, linear history, no force-push). Raise it to
`1`+ as soon as there is a second person with write access.

### Verify

Open a throwaway PR (or inspect an open one): the three `check` jobs
should be listed as **Required** and merging blocked until they pass; a
direct push or force-push to `main` should be rejected.

## Required branch-protection rules on `main`

Configure the following via a **ruleset** (or classic branch protection)
for the `main` branch:

- **Require a pull request before merging.** Direct pushes to `main` are
  not permitted; all changes land through a PR.
  - **Required approvals:** `1`+ for a team; `0` for a solo repo (see
    "Solo maintainer" above). This repository currently uses `0`.
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

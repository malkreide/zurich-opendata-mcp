# Project conventions for Claude

## Changelog discipline

Every code change must include a matching entry in `CHANGELOG.md` under the
`[Unreleased]` block, in the same commit/PR as the change itself.

- Use Keep-a-Changelog sections: `### Added`, `### Changed`, `### Fixed`,
  `### Security`, `### Removed`, `### Deprecated`.
- Pure documentation tweaks, audits, and CI hardening do not need an entry.
  Anything that ships in the wheel does.
- Reference the audit finding ID (`H-1`, `M-3`, …) when fixing one, so the
  changelog tracks back to `audits/zurich-opendata-mcp-audit.md`.
- When cutting a release, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`
  and add a new empty `[Unreleased]` block at the top.

## Audit follow-ups

All known review backlogs are closed:

- Both audits (`audits/zurich-opendata-mcp-audit.md` and its rerun) shipped
  across PRs #9, #11–#15: H-1 SQL injection, H-2 CQL injection, all Mediums
  and Lows. The M-7 coverage goal is complete — the suite gates at
  `--cov-fail-under=100`.
- The July 2026 solution review (F-1 – F-13) shipped across PRs #40–#54 and
  was released as `0.5.0`: runtime resolution of year-bound UGZ resource
  IDs, shared HTTP client + retries, `zurich_` naming with deprecated STRB
  aliases, `format=json` on every data-bearing tool, SPARQL opt-in flag,
  Literal-typed UGZ filters, ILIKE wildcard escaping (rerun §2.3 — fixed,
  no longer documentation-only), defusedxml, SHA-pinned CI + pip-audit,
  metadata drift guards, and a mypy gate with zero per-module exemptions.

Invariants to preserve in new work: coverage stays at 100%, mypy has no
`ignore_errors` exemptions, doc counts are pinned by drift-guard tests
(update docs and tests together when the tool surface changes), and the
live-marked drift alarms (UGZ yearly resources, UGZ measurement network)
should be run before cutting a release.

Each substantive change should still land as its own PR with a CHANGELOG
entry, referencing the finding ID where one applies.

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

The audit (`audits/zurich-opendata-mcp-audit.md`) lists open findings.
Phase 1 (H-1, SQL injection in `tools/strb.py`) is fixed.
Remaining work — README/structure sweep, `zurich_sparql` dead code,
N+1 in `zurich_analyze_datasets`, Markdown-cell escaping, unit tests
with `respx`, Pydantic `Literal` tightening — should each land as its
own PR with a CHANGELOG entry.

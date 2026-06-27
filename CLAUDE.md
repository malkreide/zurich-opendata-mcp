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

Both audits (`audits/zurich-opendata-mcp-audit.md` and
`audits/zurich-opendata-mcp-audit-rerun.md`) are effectively closed:

- All v1 findings (H-1 SQL injection, the 8 Mediums and 11 Lows) shipped
  across PRs #9, #11–#15.
- Rerun findings are closed too: H-2 (CQL injection in `parliament.py`),
  L-A (dead layer check in `geo.py`), L-B (`--port` validation), L-C
  (logging config in `server.py:main()`).

Remaining: the M-7 *coverage* goal — keep widening `respx` test coverage
(catalog, parliament, realtime and tourism tools now have round-trip
tests) and ratchet `--cov-fail-under` upward as it grows. The ILIKE
wildcard note (rerun §2.3) is documentation-only, not a defect.

Each substantive change should still land as its own PR with a CHANGELOG
entry, referencing the finding ID where one applies.

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation
- Synced `README.md` and `README.de.md` with the post-refactor reality
  (audit findings M-2 / M-3 / L-14):
  - Tool count `20` → `24`, resource count `6` → `5` in tagline + footer.
  - New §"Stadtratsbeschlüsse / Council Resolutions" listing the three STRB
    tools with example queries.
  - "Project Structure" tree replaced with the current `app.py` /
    `clients/` / `tools/` layout (incl. `audits/`, `CLAUDE.md`).
  - "Development" section: switched from
    `python tests/test_integration.py` to `pytest tests/ -m "not live"` /
    `pytest tests/ -m live`.
  - Geo-layer table regenerated from `GEOPORTAL_LAYERS` in `config.py`
    (removed `quartiere`, `sportanlagen`, `veloparkierung`,
    `zweiradparkierung` which never existed in code; added
    `sport`, `velopruefstrecken`, `stimmlokale`, `sozialzentrum`).
  - `zurich_sparql` now flagged as "currently disabled" in the feature
    list to match the runtime behaviour.

### Security
- Fixed SQL-injection in `tools/strb.py` (audit finding H-1). The `query` and
  `departement` parameters of `search_stadtratsbeschluesse` and
  `get_beschluesse_by_departement` were f-string-interpolated into the
  `WHERE` clause sent to CKAN's `datastore_search_sql`. Quote-closing payloads
  (`x%' OR 1=1 OR '%`) bypassed the title filter. Now escaped via a small
  PostgreSQL string-literal escape (`'` → `''`, `\` → `\\`); date inputs are
  already regex-validated upstream by Pydantic and do not need escaping.
  Regression tests added in `tests/test_server.py`.

### Changed
- Refactored monolithic `server.py` (2654 lines) into a domain-organized package:
  `app.py` (FastMCP instance), `config.py`, `http_client.py`, `formatters.py`,
  `clients/{wfs,paris,tourism,sparql}.py`,
  `tools/{catalog,datastore,realtime,geo,parliament,tourism,sparql,strb,resources}.py`.
  No behavior change — `server.py` re-exports public symbols for backward compatibility.

## [0.2.0] - 2026-03-22

### Added
- Initial PyPI publication
- 20 tools for Zurich Open Data (CKAN, geodata, parliament, tourism, SPARQL, real-time)
- Dual stdio/Streamable HTTP transport
- GitHub Actions CI/CD with Trusted Publisher
- **Geoportal WFS** — 2 tools (`zurich_geo_layers`, `zurich_geo_features`) for 14 geodata layers
- **City Parliament Paris API** — 2 tools (`zurich_parliament_search`, `zurich_parliament_members`)
- **Zurich Tourism API** — `zurich_tourism` tool with 12 categories and 4 languages (de/en/fr/it)
- **SPARQL Linked Data** — `zurich_sparql` tool for statistical queries
- 2 MCP resources (`zurich://geo/{layer_id}`, `zurich://tourism/categories`)
- 6 integration tests (tests 15–20)
- Bilingual documentation (EN/DE): README, CONTRIBUTING
- CHANGELOG.md, LICENSE, .gitignore, CONTRIBUTING.md
- GitHub Actions CI workflow (lint, test, build)

### Changed
- README.md fully rewritten with all 20 tools and 6 APIs
- pyproject.toml expanded with GitHub URLs and metadata

## [0.1.0] - 2026-02-21

### Added
- **CKAN API** — 6 tools for dataset search, metadata, DataStore queries, SQL
- **Real-time environmental data** — Weather, air quality, Lake Zurich data (3 tools)
- **Real-time mobility data** — Pedestrian counts, VBZ ridership (2 tools)
- **ParkenDD** — Real-time parking occupancy
- **Analysis tools** — Dataset analysis, catalog statistics, school data search (3 tools)
- 3 MCP resources (dataset, category, parking)
- 14 integration tests
- Full README with installation guide

[Unreleased]: https://github.com/malkreide/zurich-opendata-mcp/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/malkreide/zurich-opendata-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/malkreide/zurich-opendata-mcp/releases/tag/v0.1.0

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- `server.main()` now uses `argparse` instead of hand-rolled `sys.argv`
  parsing. `--port abc`, `--port 0`, `--port 65536` and a bare `--port`
  with no value now fail with a clean usage message instead of
  `ValueError` / `IndexError`. `--help` is auto-generated. Closes audit
  rerun L-B.
- Removed unreachable runtime layer-id check in `tools/geo.py` — Pydantic
  `Literal` enforcement (#14) supersedes it; the branch was lowering
  coverage for nothing. Closes audit rerun L-A.

### Changed
- `server.main()` now calls `logging.basicConfig(stream=stderr)` so the
  `WARNING` records emitted by `formatters.handle_api_error` actually
  surface in stdio deployments (stdout is reserved for MCP framing).
  Level can be overridden via `ZURICH_OPENDATA_LOG_LEVEL`. Closes audit
  rerun L-C.

### Security
- Fixed CQL-injection in `tools/parliament.py` (audit rerun finding H-2).
  Six f-string interpolations into Paris-API CQL queries
  (`zurich_parliament_search`, `zurich_parliament_members`) were missing
  escaping. Quote-closing payloads such as `query='foo" OR Titel any "bar'`
  produced two predicates instead of one. Now neutralised by a small
  `cql_escape()` helper in `clients/paris.py` (escapes `\` then `"` for
  CQL string literals); int-typed `year_from`/`year_to` continue to bypass
  escaping because Pydantic bounds them to safe ranges. Inline CQL
  building was extracted into `_build_geschaeft_cql`,
  `_build_behoerdenmandat_cql`, and `_build_kontakt_cql` so the escaping
  is unit-testable. 8 regression tests added.

### Fixed
- Console-script entry point now targets `main()` instead of the bound
  `mcp.run` method, so `zurich-opendata-mcp --http --port 8080` actually
  takes effect when launched from the installed script. Closes audit L-1.

### Changed
- Renamed `http_client._get_client` to `http_client.get_client` and made
  it synchronous (it never awaited anything). Updated callers in
  `clients/wfs.py`, `clients/sparql.py`, `clients/paris.py` and the
  internal `ckan_request` / `http_get_json` helpers. Closes audit L-5/L-6.
- `formatters.handle_api_error` now logs a warning (with traceback) at
  the `zurich_opendata_mcp.formatters` logger before returning the
  user-facing string, so silent upstream failures leave an audit trail
  in stdio deployments. Closes audit L-7.
- `clients/wfs.py`: documented why WFS 1.1.0 is pinned (the singular
  `typename` parameter is rejected by 2.0.0; Stadt-Zürich Geoserver still
  serves 1.1.0 layers under the names in `GEOPORTAL_LAYERS`). Closes L-17.
- Tightened tool input schemas with `typing.Literal` so the JSON Schema
  exposed to MCP clients lists allowed values and Pydantic rejects typos
  at validation time (audit L-9 through L-13):
  - `SearchDatasetsInput.filter_group` and `ListGroupInput.group_id` →
    `ZurichGroup` (19 CKAN categories).
  - `GeoFeaturesInput.layer_id` → `GeoLayerId` (14 WFS layers).
  - `WaterWeatherInput.station` → `WaterStation`
    (`tiefenbrunnen` / `mythenquai`); the old fuzzy
    `if "tiefen" in station.lower()` lookup mapped typos like
    `"Tienfenbrunnen"` to Mythenquai. Now rejected with a clear error.
  - `TourismSearchInput.language` → `TourismLanguage`
    (`de` / `en` / `fr` / `it`).
  - `SearchSTRBInput.format` and `BeschluesseDepartementInput.format` →
    `OutputFormat` (`markdown` / `json`); previously any non-`json` value
    silently rendered Markdown.
  Drift tests assert each Literal still matches its runtime list/dict.
- Corrected `idempotentHint` on the five live-data tools that return
  upstream timestamps (`zurich_weather_live`, `zurich_air_quality`,
  `zurich_water_weather`, `zurich_pedestrian_traffic`,
  `zurich_vbz_passengers`) — calling them twice with the same arguments
  yields different rows, which contradicts the MCP idempotent contract.
  Flipped from `True` → `False`. Behaviour is unchanged; clients with
  caching/replay heuristics now get accurate hints.

### Fixed
- `zurich_analyze_datasets` no longer issues a redundant `package_show`
  per dataset and runs the per-dataset `datastore_search` calls
  concurrently (`asyncio.gather` with a `Semaphore(5)` cap). For
  `max_datasets=20` this drops worst-case CKAN traffic from ~41 sequential
  requests to 1 + up to 20 parallel. Closes audit M-5.
- `zurich_datastore_sql`'s SELECT-only gate now uses `sqlparse`:
  multi-statement payloads (`SELECT 1; DROP TABLE foo`) are rejected up
  front, and CTEs (`WITH … SELECT …`) — previously misclassified as
  non-SELECT — are now accepted. Closes audit M-8.

### Changed
- `sqlparse>=0.4` added as a runtime dependency for the SELECT gate.
- `USER_AGENT` is now sourced from `importlib.metadata.version()` instead of a
  hard-coded string, and points at the correct repo URL
  (`github.com/malkreide/zurich-opendata-mcp` — the previous
  `github.com/schulamt-zurich` did not exist). Closes audit M-1 / L-4.
- `tools/sparql.py`: removed ~50 lines of unreachable code after the disabled-
  endpoint return; flipped `idempotentHint` to `True` (the function now
  returns a constant) and `openWorldHint` to `False`. Behaviour for callers
  is unchanged. Closes audit M-4.
- `tools/realtime.py`: parking-lot names and pedestrian-traffic
  `location_name` / `weather_condition` cells are now escaped via the new
  `md_cell()` helper, so a `|` or newline in upstream data no longer breaks
  the rendered Markdown table. Closes audit M-6.

### Added
- `formatters.md_cell()` — small helper that escapes `|` and collapses line
  breaks for safe Markdown-table interpolation. Unit-tested in
  `tests/test_server.py`.

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

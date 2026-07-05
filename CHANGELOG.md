# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- The `--http` transport crashed on startup with a `TypeError`:
  `FastMCP.run()` accepts no `port` keyword — the port must be set via
  `mcp.settings.port`. The only test for this path monkeypatched
  `mcp.run` and asserted the (invalid) kwarg, hiding the bug. Found by
  the mypy ratchet below; verified end-to-end (server boots on the
  configured port and answers an MCP `initialize` with HTTP 200).

### Changed
- mypy now checks the entire source surface: the per-module
  `ignore_errors` exemption list in `pyproject.toml` (9 modules) is
  gone. All 33 outstanding errors fixed: tool `annotations` are passed
  as `mcp.types.ToolAnnotations` instances instead of plain dicts,
  `ckan_request` is honestly typed `Any` (CKAN returns lists for
  `group_list`/`tag_list`), and the weather/air filter dicts carry
  explicit types. (Solution-review finding F-13.)

### Fixed
- The `line` and `stop` parameters of `zurich_vbz_passengers` were
  declared but never used — only `query` ever reached the API, so
  line/stop filtering silently returned unfiltered data. `line` now
  filters on `Linienname`; `stop` is resolved via the VBZ
  Haltestellen directory (the REISENDE table only carries
  `Haltestellen_Id`) and filters on the matching ID list. Unknown stop
  names return a clear message instead of unfiltered results; resolved
  stop names are shown in the output (`haltestellen` in JSON). Found
  during the F-5 review; verified live (line 7 @ Paradeplatz).

### Changed
- Package description in `pyproject.toml` corrected from "20 tools" to
  the actual 23 (and mentions council resolutions instead of the
  opt-in SPARQL tool). Accompanying docs-only fixes: PyPI-driven
  version badge instead of the hardcoded 0.3.0 badge, tool/resource
  counts in README and SECURITY aligned with the registered surface
  (23 tools + 3 deprecated aliases, 5 resources), UGZ station count
  corrected to 4, stale "v0.2.0" removed from the `server.py`
  docstring. Two new drift-guard tests pin the registered tool and
  resource counts so future changes must update the docs in the same
  PR. (Solution-review finding F-12.)

### Security
- Paris-API XML responses are now parsed with `defusedxml` instead of
  stdlib `xml.etree`: DTDs, entity expansion (billion laughs) and
  external entity references in upstream XML are rejected and surface
  as a handled tool error. Low practical risk (fixed, trusted host over
  HTTPS), but the hardening is one dependency away. New runtime
  dependency `defusedxml>=0.7.1`. (Solution-review finding F-9.)

### Security
- STRB search terms containing the LIKE wildcards `%`/`_` no longer act
  as wildcards (audit rerun §2.3): `_sql_escape` now also escapes `%`,
  `_` and the escape character itself, and the ILIKE conditions carry
  `ESCAPE '!'`. A bare `%` used to match every resolution; it now
  matches only titles containing a literal `%`. `!` was chosen as the
  escape character because CKAN's SQL endpoint rejects a backslash
  `ESCAPE` clause with HTTP 409 (verified live). (Solution-review
  finding F-8.)

### Changed
- `station` and `parameter` on `zurich_weather_live` and
  `zurich_air_quality` are now `Literal`-typed against the actual UGZ
  measurement network (verified via `SELECT DISTINCT` on the live
  current-year resources): stations Heubeeribüel, Rosengartenstrasse,
  Schimmelstrasse, Stampfenbachstrasse; meteo parameters incl. the
  previously undocumented `StrGlo`/`WD`/`WVs`/`WVv`; air parameters
  `NO`/`NO2`/`NOx`/`O3`/`PM10`/`PM2.5`. Typos and stale values that the
  docstrings used to advertise (`Zch_Kaserne`, `SO2`, `CO` do not exist
  in the current data) are now rejected by Pydantic with the list of
  valid values instead of silently returning "Keine Daten gefunden".
  A `live`-marked drift test alarms when the measurement network
  changes. (Solution-review finding F-7.)

### Removed
- `zurich_sparql` is no longer registered by default. The Linked-Data
  endpoint is still not productive, so the tool only ever returned a
  static notice while occupying tool-list context in every MCP client
  and inviting useless calls. It can be re-enabled with
  `ZURICH_OPENDATA_ENABLE_SPARQL=1`; the implementation and the
  `server.py` re-export remain in place. (Solution-review finding F-6.)

### Added
- `format: 'markdown' | 'json'` parameter (default `markdown`) for the
  parliament, geo and tourism tools — `zurich_parliament_search`,
  `zurich_parliament_members`, `zurich_geo_layers`, `zurich_geo_features`
  and `zurich_tourism`. JSON output returns normalised records with
  `total`/`count` metadata; `zurich_geo_features` returns the raw GeoJSON
  FeatureCollection (bounded by `max_features`). Together with the STRB
  and realtime tools, every data-bearing tool of the server now offers a
  machine-readable output mode. `zurich_geo_layers` gained an optional
  input model for this; calling it without arguments behaves as before.
  Shared helpers (`json_out`, `FORMAT_FIELD_DESC`) moved to
  `formatters.py`. (Solution-review finding F-5, part 2 — completes F-5.)

### Added
- `format: 'markdown' | 'json'` parameter (default `markdown`, matching
  the existing STRB tools) for all six realtime tools —
  `zurich_parking_live`, `zurich_weather_live`, `zurich_air_quality`,
  `zurich_water_weather`, `zurich_pedestrian_traffic` and
  `zurich_vbz_passengers`. With `format='json'` the tools return a
  machine-readable payload (records with the CKAN-internal `_id`
  stripped, plus `total`/`count` metadata) instead of Markdown, so
  agents no longer have to parse Markdown tables to post-process
  measurements. `zurich_parking_live` gained an optional input model
  for this; calling it without arguments behaves as before.
  (Solution-review finding F-5, part 1 — realtime family.)

### Changed
- The three Stadtratsbeschlüsse tools now follow the `zurich_` naming
  convention of the rest of the tool surface: `zurich_strb_search`,
  `zurich_strb_by_department` and `zurich_strb_detail`. Behaviour,
  input models and output are unchanged. (Solution-review finding F-4.)

### Fixed
- `zurich_strb_detail` (formerly `get_stadtratsbeschluss_detail`) always
  failed against the live CKAN API with HTTP 409: the `filters` value
  was passed as a Python dict, which httpx urlencodes as its `repr()`
  (single quotes) instead of JSON. The filter is now serialised with
  `json.dumps`, and the regression test asserts the wire format is
  valid JSON. Found during the live verification of the F-4 rename.

### Deprecated
- The former STRB tool names `search_stadtratsbeschluesse`,
  `get_beschluesse_by_departement` and `get_stadtratsbeschluss_detail`
  remain registered as fully functional aliases, marked as deprecated in
  their descriptions/titles. They will be removed in the next major
  release.

### Changed
- Upstream calls are now retried on transient failures: connect errors
  are retried at the httpx transport layer (`retries=2`), and the new
  central `http_client.http_get()` helper retries once (1s backoff) when
  an upstream answers 502/503/504. All requests are idempotent GETs, so
  retries are safe; 4xx and plain 500 responses are never retried. All
  API clients (CKAN, ParkenDD, Paris, WFS, Tourism) route through the
  helper. (Solution-review finding F-3.)

### Changed
- All upstream HTTP calls now share one process-wide `httpx.AsyncClient`
  (pooled TCP/TLS connections) instead of creating and closing a client
  per request; the pool is closed on shutdown via a FastMCP lifespan hook
  in `app.py`. `http_client.get_client()` now returns the shared client
  and `close_client()` disposes it. The STRB tools additionally run their
  data and COUNT(*) queries concurrently via `asyncio.gather`, halving
  the round-trip latency of `search_stadtratsbeschluesse` and
  `get_beschluesse_by_departement`. (Solution-review finding F-2.)

### Fixed
- `zurich_weather_live` and `zurich_air_quality` were pinned to the 2026
  resource UUIDs of the per-year UGZ datasets (`ugz_ogd_meteo_h1_2026`,
  `ugz_ogd_air_h1_2026`) and would have silently served stale data from
  January 2027 on. The resource ID is now resolved at call time from the
  dataset's resource list (new `resolver.resolve_yearly_resource()`):
  prefer the current calendar year, else the newest year available, with
  a 24h in-process cache and the pinned IDs kept as fallback when CKAN is
  unreachable. Adds `respx` tests for the resolver and the tool wiring,
  plus a `live`-marked stale alarm that fails if the UGZ naming scheme
  changes. (Solution-review finding F-1.)

## [0.4.0] - 2026-06-27

### Added
- Structured (JSON) output for the three ID-bearing catalog tools —
  `zurich_search_datasets`, `zurich_get_dataset` and
  `zurich_analyze_datasets`. Each now returns both a Markdown `content`
  block (human-readable fallback) and a validated `structuredContent`
  payload via `Annotated[CallToolResult, Model]`, so dataset and resource
  IDs travel machine-readably into follow-up calls instead of being parsed
  out of prose. New Pydantic output models live in
  `zurich_opendata_mcp/models.py` (`SearchResult`, `GetDatasetResult`,
  `AnalysisResult` and friends); MCP clients now see an `outputSchema` for
  these tools. Added `respx`-backed tests covering the dual output, the
  empty-result case, and the schema-valid error path.
- `respx`-backed unit tests for `tools/parliament.py`, `tools/realtime.py`
  and `tools/tourism.py` (audit M-7 continuation), covering the full
  HTTP round-trip — request building, response rendering, empty results
  and error handling — without network access.

### Fixed
- `http_get_json` dropped any query string baked into the request URL: it
  passed an empty `dict` to httpx, which httpx interprets as "replace the
  query params", stripping e.g. the tourism client's `?id=<category>`. As a
  result `zurich_tourism` ignored the requested category and always hit the
  default endpoint. Now passes `params` through as `None` so the URL's own
  query is preserved. Regression test added.

### Changed
- Split the CKAN-dict → Markdown formatting in `formatters.py` into a
  model layer (`to_dataset_summary`, `to_resource_info`) and a renderer
  (`render_dataset_summary`); `format_dataset_summary` is retained as a
  thin wrapper for the remaining Markdown-only tools.

## [0.3.3] - 2026-06-07

### Changed
- Moved the MCP Registry name declaration (`io.github.malkreide/zurich-opendata-mcp`)
  from `pyproject.toml` into `README.md` to establish MCP Registry / PyPI
  ownership.

## [0.3.2] - 2026-06-07

(0.3.1 was never released — the version went straight from 0.3.0 to 0.3.2.)

### Added
- `mcp-name` metadata in `pyproject.toml` to claim MCP Registry ownership.

### Changed
- Bumped runtime and dev-dependency floors in `pyproject.toml` (#17,
  Dependabot grouped update): `mcp[cli]>=1.27.1`, `httpx>=0.28.1`,
  `pydantic>=2.13.4`, `uvicorn>=0.46.0`, `sqlparse>=0.5.5` (picks up
  CVE-2024-4340 fix), and dev tools `pytest>=9.0.3`,
  `pytest-asyncio>=1.3.0`, `pytest-cov>=7.1.0`, `respx>=0.23.1`,
  `ruff>=0.15.12`. CI green on Python 3.11 / 3.12 / 3.13.
- Bumped GitHub Actions versions (Dependabot actions group, 3 updates).
- Aligned the repository docs with the portfolio structure (English README
  primary, German README/CONTRIBUTING/SECURITY linked).

## [0.3.0] - 2026-05-11

This release closes every finding from the
[`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) audit
(`audits/zurich-opendata-mcp-audit.md`) and its rerun
(`audits/zurich-opendata-mcp-audit-rerun.md`) — 2 High, 8 Medium and
14 Low — and adds 49 unit-level tests plus a coverage gate.

### Security
- Fixed SQL-injection in `tools/strb.py` (audit finding H-1). The `query`
  and `departement` parameters of `search_stadtratsbeschluesse` and
  `get_beschluesse_by_departement` were f-string-interpolated into the
  `WHERE` clause sent to CKAN's `datastore_search_sql`. Quote-closing
  payloads (`x%' OR 1=1 OR '%`) bypassed the title filter. Now escaped
  via a PostgreSQL string-literal escape (`'` → `''`, `\` → `\\`); date
  inputs are already regex-validated upstream by Pydantic and pass
  through unchanged.
- Fixed CQL-injection in `tools/parliament.py` (audit rerun finding H-2).
  Six f-string interpolations into Paris-API CQL queries
  (`zurich_parliament_search`, `zurich_parliament_members`) were missing
  escaping. Payloads like `query='foo" OR Titel any "bar'` produced two
  CQL predicates instead of one. Now neutralised by a `cql_escape()`
  helper in `clients/paris.py` (escapes `\` then `"`); int-typed
  `year_from`/`year_to` continue to pass through because Pydantic bounds
  them. Inline CQL building extracted into `_build_geschaeft_cql`,
  `_build_behoerdenmandat_cql`, and `_build_kontakt_cql` so the escaping
  is unit-testable.

### Added
- `formatters.md_cell()` — escapes `|` and collapses line breaks for safe
  Markdown-table interpolation. Applied in `zurich_parking_live` and
  `zurich_pedestrian_traffic` so a `|` or newline in upstream data no
  longer splits table columns (audit M-6).
- `tests/test_server.py`: 49 non-live tests (up from one functional smoke
  test). New coverage: SQL/CQL escape helpers + injection regressions,
  Pydantic Literal drift, `_validate_select_only` (plain SELECT, CTE,
  stacked, DROP/INSERT/UPDATE/DELETE, empty), `md_cell` edge cases,
  `idempotentHint` invariant for live-data tools, `analyze_datasets`
  no-N+1 with monkey-patched `ckan_request`, argparse port validation,
  console-script entry-point shape, `handle_api_error` logging.
- `.github/dependabot.yml` — weekly grouped updates for GitHub Actions
  and pip (audit L-18; auto-pins by SHA on first PR).

### Changed
- Refactored monolithic `server.py` (2654 lines) into a domain-organized
  package: `app.py` (FastMCP instance), `config.py`, `http_client.py`,
  `formatters.py`, `clients/{wfs,paris,tourism,sparql}.py`,
  `tools/{catalog,datastore,realtime,geo,parliament,tourism,sparql,strb,resources}.py`.
  No behaviour change — `server.py` re-exports public symbols for
  backwards compatibility.
- `zurich_datastore_sql`'s SELECT-only gate now uses `sqlparse`:
  multi-statement payloads (`SELECT 1; DROP TABLE foo`) are rejected up
  front, and CTEs (`WITH … SELECT …`) — previously misclassified as
  non-SELECT — are now accepted (audit M-8). `sqlparse>=0.4` added as a
  runtime dependency.
- Tightened tool input schemas with `typing.Literal` so the JSON Schema
  exposed to MCP clients lists allowed values and Pydantic rejects typos
  at validation time (audit L-9 through L-13):
  - `SearchDatasetsInput.filter_group` and `ListGroupInput.group_id` →
    `ZurichGroup` (19 CKAN categories).
  - `GeoFeaturesInput.layer_id` → `GeoLayerId` (14 WFS layers).
  - `WaterWeatherInput.station` → `WaterStation`
    (`tiefenbrunnen` / `mythenquai`); the old fuzzy lookup mapped typos
    like `"Tienfenbrunnen"` to Mythenquai. Now rejected.
  - `TourismSearchInput.language` → `TourismLanguage`
    (`de` / `en` / `fr` / `it`).
  - `SearchSTRBInput.format` and `BeschluesseDepartementInput.format` →
    `OutputFormat` (`markdown` / `json`); previously any non-`json`
    string silently rendered Markdown.
  Drift tests assert each Literal still matches its runtime list/dict.
- Corrected `idempotentHint` on the five live-data tools that return
  upstream timestamps (`zurich_weather_live`, `zurich_air_quality`,
  `zurich_water_weather`, `zurich_pedestrian_traffic`,
  `zurich_vbz_passengers`): flipped `True` → `False` to match the MCP
  same-input-same-output contract.
- `USER_AGENT` is now sourced from
  `importlib.metadata.version("zurich-opendata-mcp")` instead of a
  hard-coded `0.3` string, and points at the correct repo URL
  (`github.com/malkreide/zurich-opendata-mcp` — the previous
  `github.com/schulamt-zurich` did not exist). Closes M-1 / L-4.
- `tools/sparql.py`: removed ~50 lines of unreachable code after the
  disabled-endpoint early `return`; flipped `idempotentHint` to `True`
  (the function now returns a constant) and `openWorldHint` to `False`.
  Module docstring explains the disabled state and how to restore the
  implementation from git history. Closes M-4 / L-15.
- `tools/realtime.py`: parking-lot names and pedestrian-traffic
  `location_name` / `weather_condition` cells now go through
  `md_cell()`. Closes M-6.
- Renamed `http_client._get_client` to `http_client.get_client` and made
  it synchronous (it never awaited anything). Updated callers in
  `clients/{wfs,sparql,paris}.py` and the internal `ckan_request` /
  `http_get_json` helpers. Closes L-5/L-6.
- `formatters.handle_api_error` now logs a `WARNING` (with traceback)
  at logger `zurich_opendata_mcp.formatters` before returning the
  user-facing string, so silent upstream failures leave an audit trail.
  Closes L-7.
- `clients/wfs.py`: documented why WFS 1.1.0 is pinned (singular
  `typename` parameter is rejected by 2.0.0; Stadt-Zürich Geoserver
  still serves 1.1.0 layers). Closes L-17.
- `server.main()` now calls `logging.basicConfig(stream=stderr)` so
  the `WARNING` records from `handle_api_error` surface in stdio
  deployments. Level is configurable via `ZURICH_OPENDATA_LOG_LEVEL`.
  Closes audit rerun L-C.
- CI: `cache: pip` on `setup-python` and `--cov-fail-under=30` as a
  regression gate (long-term goal: 80% once `respx`-mocked tests for
  the live-API tools land). Closes L-19.

### Fixed
- `zurich_analyze_datasets` no longer issues a redundant `package_show`
  per dataset and runs the per-dataset `datastore_search` calls
  concurrently (`asyncio.gather` with a `Semaphore(5)` cap). For
  `max_datasets=20` this drops worst-case CKAN traffic from ~41
  sequential requests to 1 + up to 20 parallel. Closes M-5.
- Console-script entry point now targets `main()` instead of the bound
  `mcp.run` method, so `zurich-opendata-mcp --http --port 8080`
  actually takes effect when launched from the installed script.
  Closes L-1.
- `server.main()` now uses `argparse` instead of hand-rolled
  `sys.argv` parsing. `--port abc`, `--port 0`, `--port 65536` and a
  bare `--port` now fail with a clean usage message instead of
  `ValueError` / `IndexError`. `--help` is auto-generated. Closes
  audit rerun L-B.
- Removed unreachable runtime layer-id check in `tools/geo.py` —
  Pydantic `Literal` enforcement now rejects unknown layers before
  the branch can run. Closes audit rerun L-A.

### Documentation
- Synced `README.md` and `README.de.md` with the post-refactor reality
  (audit findings M-2 / M-3 / L-14):
  - Tool count `20` → `24`, resource count `6` → `5` in tagline + footer.
  - New §"Stadtratsbeschlüsse / Council Resolutions" with the three STRB
    tools and example queries.
  - "Project Structure" tree replaced with the current `app.py` /
    `clients/` / `tools/` layout.
  - "Development" section: `pytest tests/ -m "not live"` /
    `pytest tests/ -m live` instead of the non-existent
    `python tests/test_integration.py`.
  - Geo-layer table regenerated from `GEOPORTAL_LAYERS` in `config.py`.
  - `zurich_sparql` flagged as "currently disabled" to match runtime.
- Added `CLAUDE.md` documenting the per-change CHANGELOG convention and
  the audit follow-up tracking.
- Added `audits/zurich-opendata-mcp-audit.md` and
  `audits/zurich-opendata-mcp-audit-rerun.md`.

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

[Unreleased]: https://github.com/malkreide/zurich-opendata-mcp/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/malkreide/zurich-opendata-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/malkreide/zurich-opendata-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/malkreide/zurich-opendata-mcp/releases/tag/v0.1.0

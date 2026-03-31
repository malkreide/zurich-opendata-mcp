# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

# Changelog

All notable changes to this project are documented in this file. /
Alle relevanten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Format based on [Keep a Changelog](https://keepachangelog.com/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [0.2.0] – 2026-02-21

### Added / Hinzugefügt
- **Geoportal WFS** – 2 new tools (`zurich_geo_layers`, `zurich_geo_features`) for 14 geodata layers
- **City Parliament Paris API** – 2 new tools (`zurich_parliament_search`, `zurich_parliament_members`)
- **Zurich Tourism API** – `zurich_tourism` tool with 12 categories and 4 languages (de/en/fr/it)
- **SPARQL Linked Data** – `zurich_sparql` tool for statistical queries
- 2 new MCP resources (`zurich://geo/{layer_id}`, `zurich://tourism/categories`)
- 6 new integration tests (tests 15–20)
- Bilingual documentation (EN/DE): README, CONTRIBUTING
- CHANGELOG.md, LICENSE, .gitignore, CONTRIBUTING.md
- GitHub Actions CI workflow (lint → test → build)

### Changed / Geändert
- README.md fully rewritten with all 20 tools and 6 APIs
- pyproject.toml expanded with GitHub URLs and metadata
- Version bump to 0.2.0

## [0.1.0] – 2026-02-21

### Added / Hinzugefügt
- **CKAN API** – 6 tools for dataset search, metadata, DataStore queries, SQL
- **Real-time environmental data** – Weather, air quality, Lake Zurich data (3 tools)
- **Real-time mobility data** – Pedestrian counts, VBZ ridership (2 tools)
- **ParkenDD** – Real-time parking occupancy
- **Analysis tools** – Dataset analysis, catalog statistics, school data search (3 tools)
- 3 MCP resources (dataset, category, parking)
- 14 integration tests
- Full README with installation guide

[0.2.0]: https://github.com/schulamt-zuerich/zurich-opendata-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/schulamt-zuerich/zurich-opendata-mcp/releases/tag/v0.1.0

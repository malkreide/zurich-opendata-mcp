> 🇨🇭 **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide)**

# 🏙️ Zurich Open Data MCP Server

[![PyPI](https://img.shields.io/pypi/v/zurich-opendata-mcp)](https://pypi.org/project/zurich-opendata-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![No Auth Required](https://img.shields.io/badge/auth-none%20required-brightgreen)](https://github.com/malkreide/zurich-opendata-mcp)
![CI](https://github.com/malkreide/zurich-opendata-mcp/actions/workflows/ci.yml/badge.svg)

🌐 **English** | **[Deutsch](README.de.md)**

An MCP (Model Context Protocol) server providing AI-powered access to **Open Data from the City of Zurich, Switzerland**.

> Enables Claude, ChatGPT, and other MCP-compatible AI assistants to directly query 900+ datasets, geodata, parliamentary proceedings, council resolutions, tourism data, linked data, and real-time environmental and mobility information from the City of Zurich. **23 Tools (+3 deprecated aliases), 5 Resources, 6 APIs.**

### Demo

![Demo: Claude using zurich_parking_live and zurich_air_quality](docs/assets/demo.svg)

## ✨ Features

### CKAN Open Data (data.stadt-zuerich.ch)
- **`zurich_search_datasets`** – Full-text search with Solr syntax across 900+ datasets
- **`zurich_get_dataset`** – Complete metadata and download URLs for a dataset
- **`zurich_datastore_query`** – Query tabular data directly (filters, sorting)
- **`zurich_datastore_sql`** – SQL queries on the DataStore
- **`zurich_list_categories`** – Browse 19 thematic categories
- **`zurich_list_tags`** – Tag-based thematic search

### Real-Time Environmental Data
- **`zurich_weather_live`** – 🌤️ Current weather (temperature, humidity, pressure, rain) from 4 UGZ stations
- **`zurich_air_quality`** – 🌬️ Live air quality (NO₂, O₃, PM10, PM2.5) with WHO thresholds
- **`zurich_water_weather`** – 🌊 Lake Zurich data (water temperature, level, wind) every 10 min

### Real-Time Mobility Data
- **`zurich_pedestrian_traffic`** – 🚶 Pedestrian counts on Bahnhofstrasse (3 locations, hourly)
- **`zurich_vbz_passengers`** – 🚊 VBZ public transit ridership (800,000+ records, all lines/stops)
- **`zurich_parking_live`** – 🅿️ Real-time occupancy of 36 parking garages (ParkenDD)

### Geoportal (WFS Geodata)
- **`zurich_geo_layers`** – 📍 List 14 available geodata layers
- **`zurich_geo_features`** – 📍 Fetch GeoJSON features (schools, districts, playgrounds, climate data, etc.)

### City Parliament (Paris API)
- **`zurich_parliament_search`** – 🏛️ Search parliamentary proceedings (interpellations, motions, postulates)
- **`zurich_parliament_members`** – 🏛️ Search council members (party, commissions, mandates)

### Zurich Tourism
- **`zurich_tourism`** – 🏨 Attractions, restaurants, hotels, events (Schema.org data, 4 languages)

### Linked Data (SPARQL)
- **`zurich_sparql`** – 📊 SPARQL queries on the statistical linked data endpoint *(endpoint not productive yet — the tool is **not registered by default**; opt in with the environment variable `ZURICH_OPENDATA_ENABLE_SPARQL=1`)*

### Stadtratsbeschlüsse (Council Resolutions)
- **`zurich_strb_search`** – 📜 Full-text search of public council resolutions (title, department, date range)
- **`zurich_strb_by_department`** – 📜 List all resolutions of a department (e.g. `SSD`, `FD`, `PRD`)
- **`zurich_strb_detail`** – 📜 Single resolution by `NNNN/YYYY` number

*(The former names `search_stadtratsbeschluesse`, `get_beschluesse_by_departement` and `get_stadtratsbeschluss_detail` remain available as deprecated aliases until the next major release.)*

### Analysis Tools
- **`zurich_analyze_datasets`** – Comprehensive analysis: relevance, recency, data structure
- **`zurich_catalog_stats`** – Catalog overview with statistics
- **`zurich_find_school_data`** – Curated search for education-related datasets

### MCP Resources
- `zurich://dataset/{name}` – Dataset metadata
- `zurich://category/{group_id}` – Category details
- `zurich://parking` – Current parking data
- `zurich://geo/{layer_id}` – GeoJSON geodata (14 layers)
- `zurich://tourism/categories` – Tourism categories

## 🚀 Installation

### Prerequisites
- Python 3.11+
- pip or uv

### Install
```bash
# Clone
git clone https://github.com/malkreide/zurich-opendata-mcp.git
cd zurich-opendata-mcp

# Install
pip install -e .

# Or with uv
uv pip install -e .
```

## ⚙️ Configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "zurich-opendata": {
      "command": "python",
      "args": ["-m", "zurich_opendata_mcp.server"],
      "env": {}
    }
  }
}
```

Alternatively, using the installed command:

```json
{
  "mcpServers": {
    "zurich-opendata": {
      "command": "zurich-opendata-mcp"
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add zurich-opendata -- python -m zurich_opendata_mcp.server
```

### Cursor / VS Code

Add to `.vscode/settings.json`:

```json
{
  "mcpServers": {
    "zurich-opendata": {
      "command": "python",
      "args": ["-m", "zurich_opendata_mcp.server"]
    }
  }
}
```

## 💬 Example Queries

Once configured, you can ask Claude:

### Open Data
- *"What datasets are available about schools in Zurich?"*
- *"Show me school holidays for public schools"*
- *"Analyze the available geodata"*

### Real-Time Data
- *"What's the current temperature in Zurich?"* → `zurich_weather_live`
- *"How is the air quality today?"* → `zurich_air_quality`
- *"What's the water temperature in Lake Zurich?"* → `zurich_water_weather`
- *"How many parking spaces are free right now?"* → `zurich_parking_live`
- *"How many people are on Bahnhofstrasse right now?"* → `zurich_pedestrian_traffic`

### Geodata
- *"Show me all school facilities in Zurich as GeoJSON"* → `zurich_geo_features`
- *"What geodata layers are available?"* → `zurich_geo_layers`
- *"Where are the playgrounds in Zurich?"*

### City Parliament
- *"What parliamentary motions about schools were filed?"* → `zurich_parliament_search`
- *"Which council members belong to the SP party?"* → `zurich_parliament_members`

### Council Resolutions (Stadtratsbeschlüsse)
- *"Find council resolutions about Volksschule from 2025"* → `zurich_strb_search`
- *"List all SSD resolutions in 2025"* → `zurich_strb_by_department`
- *"Show council resolution 1203/2025"* → `zurich_strb_detail`

### Tourism
- *"What restaurants does Zurich Tourism recommend?"* → `zurich_tourism`

## 🔗 Data Sources

| API | Endpoint | Data |
|-----|----------|------|
| **CKAN** | data.stadt-zuerich.ch/api/3/ | 900+ open datasets |
| **Geoportal WFS** | ogd.stadt-zuerich.ch/wfs/geoportal | 14 geodata layers (GeoJSON) |
| **Paris API** | gemeinderat-zuerich.ch/api | Parliamentary proceedings & members |
| **Zurich Tourism** | zuerich.com/en/api/v2/data | Attractions, restaurants, hotels |
| **SPARQL** | ld.stadt-zuerich.ch/query | Linked Open Data / statistics |
| **ParkenDD** | api.parkendd.de/Zuerich | Real-time parking occupancy |

## 📊 Available Data Categories

| Category | ID |
|----------|-----|
| Employment | `arbeit-und-erwerb` |
| Base Maps | `basiskarten` |
| Construction & Housing | `bauen-und-wohnen` |
| Population | `bevolkerung` |
| **Education** | **`bildung`** |
| Energy | `energie` |
| Finance | `finanzen` |
| Leisure | `freizeit` |
| Health | `gesundheit` |
| Crime | `kriminalitat` |
| Culture | `kultur` |
| Mobility | `mobilitat` |
| Politics | `politik` |
| Prices | `preise` |
| Social Affairs | `soziales` |
| Tourism | `tourismus` |
| Environment | `umwelt` |
| Administration | `verwaltung` |
| Economy | `volkswirtschaft` |

## 📍 Available Geo Layers

Source of truth: `GEOPORTAL_LAYERS` in [`src/zurich_opendata_mcp/config.py`](src/zurich_opendata_mcp/config.py).

| Layer ID | Description |
|----------|-------------|
| `schulanlagen` | School facilities (kindergartens, schools, after-school care) |
| `schulkreise` | School district boundaries (polygons) |
| `schulwege` | School-route crossings and hazard points |
| `stadtkreise` | City district boundaries (polygons) |
| `spielplaetze` | Public playgrounds |
| `kreisbuero` | City district offices |
| `sammelstelle` | Waste collection points |
| `sport` | Sports facilities |
| `klimadaten` | Climate data (raster, temperatures, heat islands) |
| `lehrpfade` | Educational trails |
| `stimmlokale` | Polling stations |
| `sozialzentrum` | Social centres |
| `velopruefstrecken` | Bicycle exam routes for schools |
| `familienberatung` | Family-counselling meeting points |

## 🏗️ Project Structure

```
zurich-opendata-mcp/
├── src/zurich_opendata_mcp/
│   ├── __init__.py
│   ├── app.py               # Shared FastMCP instance
│   ├── server.py            # Console entry + back-compat re-exports
│   ├── config.py            # Endpoints, layer maps, resource IDs
│   ├── http_client.py       # Shared httpx client + CKAN wrapper
│   ├── formatters.py        # CKAN→model mapping + Markdown rendering
│   ├── models.py            # Pydantic structured-output models
│   ├── clients/             # API clients: paris, sparql, tourism, wfs
│   └── tools/               # @mcp.tool implementations:
│                            #   catalog, datastore, geo, parliament,
│                            #   realtime, sparql, strb, tourism,
│                            #   resources (zurich:// URIs)
├── tests/                   # respx round-trip, unit and live-marked tests
├── audits/                  # Code-audit reports
├── .github/workflows/       # ci.yml + publish.yml (Trusted Publisher)
├── pyproject.toml
├── README.md / README.de.md
├── CONTRIBUTING.md / .de.md
├── SECURITY.md / .de.md
├── CHANGELOG.md
├── CLAUDE.md                # Project conventions for Claude
├── LICENSE
└── claude_desktop_config.json
```

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Unit + validation tests (no network)
pytest tests/ -m "not live"

# Live integration tests (against live APIs — opt-in)
pytest tests/ -m live

# Linting
ruff check src/ tests/
```

## Safety & Limits

- **Read-only:** All tools perform HTTP GET requests only — no data is written, modified, or deleted.
- **No personal data:** The APIs return open civic datasets (parking occupancy, weather readings, parliamentary proceedings). No personally identifiable information (PII) is processed or stored by this server.
- **Rate limits:** CKAN Solr search and ParkenDD are public APIs without documented rate limits; use `rows` and `limit` parameters conservatively. The server enforces a 30s timeout per request; transient upstream errors (connect failures, HTTP 502/503/504) are retried once with a short backoff.
- **Data freshness:** Real-time tools (parking, weather, air quality) reflect the upstream source at query time. Measurement data is never cached; only the lookup of the current per-year UGZ resource ID (weather/air quality) is cached in-process for 24h.
- **Terms of service:** Data is subject to the ToS of each source — [data.stadt-zuerich.ch](https://data.stadt-zuerich.ch), [ParkenDD](https://github.com/offenesdresden/ParkAPI), [gemeinderat-zuerich.ch](https://www.gemeinderat-zuerich.ch). All City of Zurich data is published under CC0 (Open by Default since 2021).
- **No guarantees:** This server is a community project, not affiliated with the City of Zurich or any of the API providers. Availability depends on upstream APIs.

---

## 🤝 Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) ([Deutsch](CONTRIBUTING.de.md)).

## 🔒 Security

Read-only, no PII, no authentication, a fixed set of public-data endpoints. See
[SECURITY.md](SECURITY.md) ([Deutsch](SECURITY.de.md)) for the full security
posture and accepted-risk decisions.

## 📜 License

MIT License — see [LICENSE](LICENSE). All data used is published under open
licenses (CC0 / Open by Default since 2021).

## 👤 Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)

---

*Powered by [Model Context Protocol](https://modelcontextprotocol.io/) • 6 APIs • 23 Tools • 5 Resources*

<!-- mcp-name: io.github.malkreide/zurich-opendata-mcp -->

<!-- BEGIN GENERATED: install -->
## Installation

Run via [`uv`](https://docs.astral.sh/uv/)'s `uvx` — no clone or manual install needed. Add to your MCP client config (`mcpServers` for Claude Desktop, Cursor and Windsurf; use a top-level `servers` key for VS Code in `.vscode/mcp.json`):

```json
{
  "mcpServers": {
    "zurich-opendata-mcp": {
      "command": "uvx",
      "args": [
        "zurich-opendata-mcp"
      ]
    }
  }
}
```
<!-- END GENERATED: install -->

# 🏙️ Zurich Open Data MCP Server

🌐 **English** | **[Deutsch](README.de.md)**

An MCP (Model Context Protocol) server providing AI-powered access to **Open Data from the City of Zurich, Switzerland**.

> Enables Claude, ChatGPT, and other MCP-compatible AI assistants to directly query 900+ datasets, geodata, parliamentary proceedings, tourism data, linked data, and real-time environmental and mobility information from the City of Zurich. **20 Tools, 6 Resources, 6 APIs.**

## ✨ Features

### CKAN Open Data (data.stadt-zuerich.ch)
- **`zurich_search_datasets`** – Full-text search with Solr syntax across 900+ datasets
- **`zurich_get_dataset`** – Complete metadata and download URLs for a dataset
- **`zurich_datastore_query`** – Query tabular data directly (filters, sorting)
- **`zurich_datastore_sql`** – SQL queries on the DataStore
- **`zurich_list_categories`** – Browse 19 thematic categories
- **`zurich_list_tags`** – Tag-based thematic search

### Real-Time Environmental Data
- **`zurich_weather_live`** – 🌤️ Current weather (temperature, humidity, pressure, rain) from 5 UGZ stations
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
- **`zurich_sparql`** – 📊 SPARQL queries on the statistical linked data endpoint

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

### Tourism & Statistics
- *"What restaurants does Zurich Tourism recommend?"* → `zurich_tourism`
- *"How has Zurich's population evolved?"* → `zurich_sparql`

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

| Layer ID | Description |
|----------|-------------|
| `schulanlagen` | School facilities (kindergartens, schools, after-school care) |
| `schulkreise` | School district boundaries |
| `schulwege` | School routes and safe paths |
| `stadtkreise` | City district boundaries |
| `quartiere` | Statistical quarters |
| `spielplaetze` | Playgrounds |
| `sportanlagen` | Sports facilities and swimming pools |
| `klimadaten` | Climate data (temperatures, heat islands) |
| `veloparkierung` | Bicycle parking facilities |
| `lehrpfade` | Educational trails |
| `familienberatung` | Family counseling meeting points |
| `kreisbuero` | City district offices |
| `sammelstelle` | Waste collection points |
| `zweiradparkierung` | Two-wheeler parking |

## 🏗️ Project Structure

```
zurich-opendata-mcp/
├── src/zurich_opendata_mcp/
│   ├── __init__.py          # Package
│   ├── server.py            # MCP Server with 20 tools & 6 resources
│   └── api_client.py        # HTTP client for 6 APIs
├── tests/
│   └── test_integration.py  # 20 integration tests
├── .github/workflows/ci.yml # GitHub Actions CI
├── pyproject.toml           # Project configuration
├── README.md / README.de.md # Documentation (EN/DE)
├── CONTRIBUTING.md / .de.md # Contribution guide (EN/DE)
├── CHANGELOG.md             # Changelog
├── LICENSE                  # MIT
└── claude_desktop_config.json
```

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Integration tests (against live APIs)
python tests/test_integration.py

# Linting
ruff check src/
```

## 📜 License

MIT License

## 🤝 Context

All data used is published under open licenses (CC0 / Open by Default since 2021).

---

*Powered by [Model Context Protocol](https://modelcontextprotocol.io/) • 6 APIs • 20 Tools • 6 Resources*

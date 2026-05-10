> 🇨🇭 **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**

# 🏙️ Zurich Open Data MCP Server

![Version](https://img.shields.io/badge/version-0.2.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![No Auth Required](https://img.shields.io/badge/auth-none%20required-brightgreen)](https://github.com/malkreide/zurich-opendata-mcp)
![CI](https://github.com/malkreide/zurich-opendata-mcp/actions/workflows/ci.yml/badge.svg)

🌐 **[English](README.md)** | **Deutsch**

MCP (Model Context Protocol) Server für den KI-gestützten Zugriff auf **Open Data der Stadt Zürich**.

> Ermöglicht Claude, ChatGPT und anderen MCP-kompatiblen KI-Assistenten den direkten Zugriff auf 900+ Datensätze, Geodaten, Parlamentsgeschäfte, Stadtratsbeschlüsse, Tourismusdaten, Linked Data und Echtzeit-Umwelt-/Mobilitätsinformationen der Stadt Zürich. **24 Tools, 5 Resources, 6 APIs.**

### Demo

![Demo: Claude nutzt zurich_parking_live und zurich_air_quality](docs/assets/demo.svg)

## ✨ Features

### CKAN Open Data (data.stadt-zuerich.ch)
- **`zurich_search_datasets`** – Volltextsuche mit Solr-Syntax über 900+ Datensätze
- **`zurich_get_dataset`** – Vollständige Metadaten und Download-URLs eines Datensatzes
- **`zurich_datastore_query`** – Tabellarische Daten direkt abfragen (Filter, Sortierung)
- **`zurich_datastore_sql`** – SQL-Abfragen auf dem DataStore
- **`zurich_list_categories`** – 19 thematische Kategorien durchsuchen
- **`zurich_list_tags`** – Tags für thematische Suche

### Echtzeit-Umweltdaten
- **`zurich_weather_live`** – 🌤️ Aktuelle Wetterdaten (Temperatur, Feuchte, Druck, Regen) von 5 UGZ-Stationen
- **`zurich_air_quality`** – 🌬️ Live-Luftqualität (NO₂, O₃, PM10, PM2.5) mit WHO-Grenzwerten
- **`zurich_water_weather`** – 🌊 Zürichsee-Daten (Wassertemperatur, Pegel, Wind) alle 10 Min.

### Echtzeit-Mobilitätsdaten
- **`zurich_pedestrian_traffic`** – 🚶 Passantenfrequenzen Bahnhofstrasse (3 Standorte, stündlich)
- **`zurich_vbz_passengers`** – 🚊 VBZ-Fahrgastzahlen (800'000+ Datensätze, alle Linien/Haltestellen)
- **`zurich_parking_live`** – 🅿️ Echtzeit-Belegung von 36 Parkhäusern (ParkenDD)

### Geoportal (WFS Geodaten)
- **`zurich_geo_layers`** – 📍 14 verfügbare Geodaten-Layer auflisten
- **`zurich_geo_features`** – 📍 GeoJSON-Features abrufen (Schulanlagen, Quartiere, Spielplätze, Klimadaten u.v.m.)

### Gemeinderat (Paris API)
- **`zurich_parliament_search`** – 🏛️ Gemeinderatsgeschäfte durchsuchen (Interpellationen, Motionen, Postulate)
- **`zurich_parliament_members`** – 🏛️ Ratsmitglieder suchen (Partei, Kommissionen, Mandate)

### Zürich Tourismus
- **`zurich_tourism`** – 🏨 Attraktionen, Restaurants, Hotels, Events (Schema.org-Daten, 4 Sprachen)

### Linked Data (SPARQL)
- **`zurich_sparql`** – 📊 SPARQL-Abfragen auf dem statistischen Linked Data Endpoint *(zurzeit deaktiviert — Endpunkt noch nicht produktiv)*

### Stadtratsbeschlüsse
- **`search_stadtratsbeschluesse`** – 📜 Volltextsuche in öffentlichen Stadtratsbeschlüssen (Titel, Departement, Datumsbereich)
- **`get_beschluesse_by_departement`** – 📜 Alle Beschlüsse eines Departements (z.B. `SSD`, `FD`, `PRD`)
- **`get_stadtratsbeschluss_detail`** – 📜 Einzelner Beschluss anhand der `NNNN/JJJJ`-Nummer

### Analyse-Tools
- **`zurich_analyze_datasets`** – Umfassende Analyse: Relevanz, Aktualität, Datenstruktur
- **`zurich_catalog_stats`** – Katalog-Übersicht mit Statistiken
- **`zurich_find_school_data`** – Kuratierte Suche nach schulrelevanten Datensätzen

### MCP Resources
- `zurich://dataset/{name}` – Datensatz-Metadaten
- `zurich://category/{group_id}` – Kategorie-Details
- `zurich://parking` – Aktuelle Parkplatzdaten
- `zurich://geo/{layer_id}` – GeoJSON-Geodaten (14 Layer)
- `zurich://tourism/categories` – Tourismus-Kategorien

## 🚀 Installation

### Voraussetzungen
- Python 3.11+
- pip oder uv

### Installation
```bash
# Klonen
git clone https://github.com/malkreide/zurich-opendata-mcp.git
cd zurich-opendata-mcp

# Installieren
pip install -e .

# Oder mit uv
uv pip install -e .
```

## ⚙️ Konfiguration

### Claude Desktop

Editiere `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

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

Alternativ mit dem installierten Kommando:

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

Füge zu `.vscode/settings.json` hinzu:

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

## 💬 Beispiel-Abfragen

Nach der Konfiguration kannst du in Claude fragen:

### Open Data
- *«Welche Datensätze gibt es zu Schulen in Zürich?»*
- *«Zeig mir die Schulferien der Volksschule»*
- *«Analysiere die verfügbaren Geodaten»*

### Echtzeit-Daten
- *«Wie warm ist es gerade in Zürich?»* → `zurich_weather_live`
- *«Wie ist die Luftqualität heute?»* → `zurich_air_quality`
- *«Was ist die aktuelle Wassertemperatur im Zürichsee?»* → `zurich_water_weather`
- *«Wie viele freie Parkplätze gibt es gerade?»* → `zurich_parking_live`
- *«Wie viele Leute sind gerade auf der Bahnhofstrasse?»* → `zurich_pedestrian_traffic`

### Geodaten
- *«Zeig mir alle Schulanlagen in Zürich als GeoJSON»* → `zurich_geo_features`
- *«Welche Geodaten-Layer gibt es?»* → `zurich_geo_layers`
- *«Wo sind die Spielplätze in Zürich?»*

### Gemeinderat
- *«Welche Vorstösse zum Thema Schule gab es im Gemeinderat?»* → `zurich_parliament_search`
- *«Welche Ratsmitglieder gehören der SP an?»* → `zurich_parliament_members`

### Stadtratsbeschlüsse
- *«Such Stadtratsbeschlüsse zur Volksschule aus 2025»* → `search_stadtratsbeschluesse`
- *«Liste alle SSD-Beschlüsse im Jahr 2025»* → `get_beschluesse_by_departement`
- *«Zeig Stadtratsbeschluss 1203/2025»* → `get_stadtratsbeschluss_detail`

### Tourismus & Statistik
- *«Welche Restaurants empfiehlt Zürich Tourismus?»* → `zurich_tourism`
- *«Wie hat sich die Bevölkerung Zürichs entwickelt?»* → `zurich_sparql`

## 🔗 Datenquellen

| API | Endpoint | Daten |
|-----|----------|-------|
| **CKAN** | data.stadt-zuerich.ch/api/3/ | 900+ Open Data Datensätze |
| **Geoportal WFS** | ogd.stadt-zuerich.ch/wfs/geoportal | 14 Geodaten-Layer (GeoJSON) |
| **Paris API** | gemeinderat-zuerich.ch/api | Parlamentsgeschäfte & Mitglieder |
| **Zürich Tourismus** | zuerich.com/en/api/v2/data | Attraktionen, Restaurants, Hotels |
| **SPARQL** | ld.stadt-zuerich.ch/query | Linked Open Data / Statistiken |
| **ParkenDD** | api.parkendd.de/Zuerich | Echtzeit-Parkplatzbelegung |

## 📊 Verfügbare Datenkategorien

| Kategorie | ID |
|-----------|-----|
| Arbeit und Erwerb | `arbeit-und-erwerb` |
| Basiskarten | `basiskarten` |
| Bauen und Wohnen | `bauen-und-wohnen` |
| Bevölkerung | `bevolkerung` |
| **Bildung** | **`bildung`** |
| Energie | `energie` |
| Finanzen | `finanzen` |
| Freizeit | `freizeit` |
| Gesundheit | `gesundheit` |
| Kriminalität | `kriminalitat` |
| Kultur | `kultur` |
| Mobilität | `mobilitat` |
| Politik | `politik` |
| Preise | `preise` |
| Soziales | `soziales` |
| Tourismus | `tourismus` |
| Umwelt | `umwelt` |
| Verwaltung | `verwaltung` |
| Volkswirtschaft | `volkswirtschaft` |

## 📍 Verfügbare Geo-Layer

Single Source of Truth: `GEOPORTAL_LAYERS` in [`src/zurich_opendata_mcp/config.py`](src/zurich_opendata_mcp/config.py).

| Layer-ID | Beschreibung |
|----------|-------------|
| `schulanlagen` | Schulstandorte (Kindergärten, Schulhäuser, Horte) |
| `schulkreise` | Schulkreis-Grenzen (Polygone) |
| `schulwege` | Schulweg-Übergänge und Gefahrenstellen |
| `stadtkreise` | Stadtkreis-Grenzen (Polygone) |
| `spielplaetze` | Öffentliche Spielplätze |
| `kreisbuero` | Kreisbüros der Stadt Zürich |
| `sammelstelle` | Abfall-Sammelstellen |
| `sport` | Sportanlagen und -einrichtungen |
| `klimadaten` | Klimadaten (Raster, Temperaturen, Hitzeinseln) |
| `lehrpfade` | Lehrpfade und Bildungswege |
| `stimmlokale` | Abstimmungs- und Wahllokale |
| `sozialzentrum` | Sozialzentren |
| `velopruefstrecken` | Veloprüfstrecken für Schulen |
| `familienberatung` | Familienberatungs-Treffpunkte |

## 🏗️ Projektstruktur

```
zurich-opendata-mcp/
├── src/zurich_opendata_mcp/
│   ├── __init__.py
│   ├── app.py               # Geteilte FastMCP-Instanz
│   ├── server.py            # Konsolen-Entrypoint + Backwards-Compat-Reexports
│   ├── config.py            # Endpunkte, Layer-Maps, Resource-IDs
│   ├── http_client.py       # Geteilter httpx-Client + CKAN-Wrapper
│   ├── formatters.py        # Markdown- + Fehlerformatierung
│   ├── clients/             # API-Clients: paris, sparql, tourism, wfs
│   └── tools/               # @mcp.tool-Implementierungen:
│                            #   catalog, datastore, geo, parliament,
│                            #   realtime, sparql, strb, tourism,
│                            #   resources (zurich:// URIs)
├── tests/
│   └── test_server.py       # Pydantic- + Integrationstests (live-markiert)
├── audits/                  # Audit-Reports
├── .github/workflows/       # ci.yml + publish.yml (Trusted Publisher)
├── pyproject.toml
├── README.md / README.de.md
├── CONTRIBUTING.md / .de.md
├── CHANGELOG.md
├── CLAUDE.md                # Projekt-Konventionen für Claude
├── LICENSE
└── claude_desktop_config.json
```

## 🧪 Entwicklung

```bash
# Dev-Dependencies installieren
pip install -e ".[dev]"

# Unit- + Validierungstests (kein Netzwerk)
pytest tests/ -m "not live"

# Live-Integrationstests (gegen Live-APIs — opt-in)
pytest tests/ -m live

# Linting
ruff check src/ tests/
```

## Sicherheit & Grenzen

- **Nur-Lesen:** Alle Tools verwenden ausschliesslich HTTP-GET-Anfragen — es werden keine Daten geschrieben, verändert oder gelöscht.
- **Keine Personendaten:** Die APIs liefern offene Stadtdatensätze (Parkplatzbelegung, Wettermessungen, Parlamentsgeschäfte). Keine personenbezogenen Daten werden durch diesen Server verarbeitet oder gespeichert.
- **Rate Limits:** CKAN-Suche und ParkenDD sind öffentliche APIs ohne dokumentierte Rate Limits; `rows`- und `limit`-Parameter konservativ einsetzen. Der Server erzwingt ein 30-Sekunden-Timeout pro Anfrage.
- **Datenaktualität:** Echtzeit-Tools (Parkplätze, Wetter, Luftqualität) spiegeln den Upstream-Stand zum Abfragezeitpunkt wider. Dieser Server nimmt kein Caching vor.
- **Nutzungsbedingungen:** Die Daten unterliegen den Nutzungsbedingungen der jeweiligen Quelle — [data.stadt-zuerich.ch](https://data.stadt-zuerich.ch), [ParkenDD](https://github.com/offenesdresden/ParkAPI), [gemeinderat-zuerich.ch](https://www.gemeinderat-zuerich.ch). Alle Stadtdaten stehen unter CC0 (Open by Default seit 2021).
- **Keine Gewähr:** Dieses Projekt ist eine Community-Initiative ohne Verbindung zur Stadt Zürich oder den API-Anbietern. Verfügbarkeit hängt von den vorgelagerten APIs ab.

---

## 📜 Lizenz

MIT License

## 🤝 Kontext

Alle genutzten Daten stehen unter offenen Lizenzen (CC0 / Open by Default seit 2021).

---

*Powered by [Model Context Protocol](https://modelcontextprotocol.io/) • 6 APIs • 24 Tools • 5 Resources*

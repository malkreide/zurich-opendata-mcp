# Contributing

🌐 **[English](CONTRIBUTING.md)** | **Deutsch**

Beiträge zu diesem Projekt sind willkommen! Dieses Dokument beschreibt den Prozess.

## Entwicklungsumgebung einrichten

```bash
git clone https://github.com/malkreide/zurich-opendata-mcp.git
cd zurich-opendata-mcp

# Virtual environment erstellen
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Pakete installieren (inkl. Dev-Dependencies)
pip install -e ".[dev]"
```

## Code-Qualität

```bash
# Linting
ruff check src/

# Formatierung
ruff format src/

# Integrationstests (gegen Live-APIs)
python tests/test_integration.py
```

## Neues Tool hinzufügen

1. **API-Client** (`api_client.py`): Falls eine neue API angebunden wird, Konstanten und HTTP-Funktionen ergänzen.
2. **Server** (`server.py`):
   - Pydantic `BaseModel` für Input-Parameter definieren
   - `@mcp.tool()`-Funktion implementieren
   - Markdown-formatierte Antwort zurückgeben
3. **Tests** (`test_integration.py`): Integrationstest gegen Live-API hinzufügen.
4. **README.md / README.de.md**: Tool-Beschreibung und Beispiel-Abfrage in beiden Sprachen ergänzen.
5. **CHANGELOG.md**: Änderung dokumentieren.

## Pull Requests

- Ein PR pro Feature/Bugfix
- Tests müssen bestehen
- `ruff check` darf keine Fehler zeigen
- Beschreibung auf Deutsch oder Englisch
- Dokumentation in beiden Sprachen aktualisieren

## Datenquellen

Alle genutzten APIs sind öffentlich zugänglich und erfordern keine Authentifizierung.
Die Daten stehen unter CC0- oder vergleichbaren offenen Lizenzen.

| API | Dokumentation |
|-----|--------------|
| CKAN | https://data.stadt-zuerich.ch/api/3/ |
| Geoportal WFS | https://www.ogd.stadt-zuerich.ch/wfs/geoportal |
| Paris (Gemeinderat) | https://www.gemeinderat-zuerich.ch/api |
| Zürich Tourismus | https://www.zuerich.com/en/api/v2/data |
| SPARQL | https://ld.stadt-zuerich.ch/query |
| ParkenDD | https://api.parkendd.de/Zuerich |

## Fragen?

Bei Fragen zur Entwicklung oder zu den genutzten APIs: Issue auf GitHub eröffnen.

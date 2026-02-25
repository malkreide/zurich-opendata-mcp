# Contributing

🌐 **English** | **[Deutsch](CONTRIBUTING.md)**

Contributions to this project are welcome! This document describes the process.

## Setting Up the Development Environment

```bash
git clone https://github.com/schulamt-zuerich/zurich-opendata-mcp.git
cd zurich-opendata-mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install packages (including dev dependencies)
pip install -e ".[dev]"
```

## Code Quality

```bash
# Linting
ruff check src/

# Formatting
ruff format src/

# Integration tests (against live APIs)
python tests/test_integration.py
```

## Adding a New Tool

1. **API Client** (`api_client.py`): If connecting a new API, add constants and HTTP functions.
2. **Server** (`server.py`):
   - Define a Pydantic `BaseModel` for input parameters
   - Implement an `@mcp.tool()` function
   - Return a Markdown-formatted response
3. **Tests** (`test_integration.py`): Add an integration test against the live API.
4. **README.md / README_EN.md**: Add tool description and example query in both languages.
5. **CHANGELOG.md**: Document the change.

## Pull Requests

- One PR per feature/bugfix
- Tests must pass
- `ruff check` must show no errors
- Documentation updated in both English and German

## Data Sources

All APIs used are publicly accessible and require no authentication.
Data is published under CC0 or comparable open licenses.

| API | Documentation |
|-----|--------------|
| CKAN | https://data.stadt-zuerich.ch/api/3/ |
| Geoportal WFS | https://www.ogd.stadt-zuerich.ch/wfs/geoportal |
| Paris (City Parliament) | https://www.gemeinderat-zuerich.ch/api |
| Zurich Tourism | https://www.zuerich.com/en/api/v2/data |
| SPARQL | https://ld.stadt-zuerich.ch/query |
| ParkenDD | https://api.parkendd.de/Zuerich |

## Questions?

For questions about development or the APIs used, open an issue on GitHub.

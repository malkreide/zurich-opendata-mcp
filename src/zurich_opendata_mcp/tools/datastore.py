"""CKAN DataStore tools: tabular query and SQL."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..formatters import handle_api_error
from ..http_client import ckan_request


class DatastoreQueryInput(BaseModel):
    """Input für Datastore-Abfragen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    resource_id: str = Field(
        ...,
        description="Resource-ID aus dem Datensatz (UUID-Format)",
        min_length=1,
    )
    filters: str | None = Field(
        default=None,
        description='JSON-Filter, z.B. {"Quartier": "Wiedikon"} oder {"Jahr": 2024}',
    )
    query: str | None = Field(
        default=None,
        description="Volltextsuche innerhalb der Ressource",
    )
    sort: str | None = Field(
        default=None,
        description="Sortierung, z.B. 'Jahr desc'",
    )
    limit: int = Field(default=20, description="Anzahl Datensätze (max. 100)", ge=1, le=100)
    offset: int = Field(default=0, description="Offset für Paginierung", ge=0)


@mcp.tool(
    name="zurich_datastore_query",
    annotations={
        "title": "Tabellarische Daten abfragen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_datastore_query(params: DatastoreQueryInput) -> str:
    """Fragt tabellarische Daten direkt aus dem CKAN DataStore ab.

    Ermöglicht gefilterte Abfragen auf Ressourcen, die im DataStore
    gespeichert sind (CSV-Daten werden automatisch indexiert).

    Returns:
        Markdown-Tabelle mit Daten und Feld-Informationen
    """
    try:
        api_params: dict = {
            "resource_id": params.resource_id,
            "limit": params.limit,
            "offset": params.offset,
        }
        if params.filters:
            try:
                json.loads(params.filters)
            except (json.JSONDecodeError, TypeError):
                return (
                    "Fehler: `filters` muss gültiges JSON sein, "
                    'z.B. `{"Quartier": "Wiedikon"}`. '
                    f"Erhalten: `{params.filters[:100]}`"
                )
            api_params["filters"] = params.filters
        if params.query:
            api_params["q"] = params.query
        if params.sort:
            api_params["sort"] = params.sort

        result = await ckan_request("datastore_search", api_params)
        total = result.get("total", 0)
        records = result.get("records", [])
        fields = result.get("fields", [])

        if not records:
            return "Keine Daten gefunden."

        # Field info
        field_info = [f"- `{f['id']}` ({f.get('type', '?')})" for f in fields if f["id"] != "_id"]

        lines = [
            f"## DataStore-Abfrage: {total} Einträge",
            f"Zeige {len(records)} (Offset: {params.offset})\n",
            "### Felder",
            "\n".join(field_info),
            "\n### Daten\n",
            "```json",
            json.dumps(records[: params.limit], indent=2, ensure_ascii=False, default=str),
            "```",
        ]

        if total > params.offset + len(records):
            lines.append(f"\n*→ Weitere mit offset={params.offset + len(records)}*")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "DataStore-Abfrage")


class DatastoreSqlInput(BaseModel):
    """Input für SQL-Abfragen auf dem DataStore."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    sql: str = Field(
        ...,
        description=(
            "SQL-Abfrage auf den DataStore. Tabellennamen in Anführungszeichen. "
            'Beispiel: SELECT * FROM "resource-uuid" WHERE "Jahr" = 2024 LIMIT 10'
        ),
        min_length=5,
    )


@mcp.tool(
    name="zurich_datastore_sql",
    annotations={
        "title": "SQL-Abfrage auf DataStore",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def zurich_datastore_sql(params: DatastoreSqlInput) -> str:
    """Führt eine SQL-Abfrage auf dem CKAN DataStore aus.

    Ermöglicht komplexe Abfragen mit JOINs, GROUP BY, Aggregationen etc.
    Nur SELECT-Abfragen sind erlaubt.

    Returns:
        JSON-Ergebnisse der SQL-Abfrage
    """
    try:
        if not params.sql.strip().upper().startswith("SELECT"):
            return (
                "Fehler: Nur SELECT-Abfragen sind erlaubt. "
                "DROP, INSERT, UPDATE, DELETE und andere Statements sind nicht gestattet."
            )

        result = await ckan_request("datastore_search_sql", {"sql": params.sql})
        records = result.get("records", [])
        fields = result.get("fields", [])

        if not records:
            return "SQL-Abfrage lieferte keine Ergebnisse."

        field_names = [f["id"] for f in fields if f["id"] != "_id"]

        lines = [
            f"## SQL-Ergebnis: {len(records)} Zeilen",
            f"**Spalten**: {', '.join(field_names)}\n",
            "```json",
            json.dumps(records, indent=2, ensure_ascii=False, default=str),
            "```",
        ]
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "SQL-Abfrage")

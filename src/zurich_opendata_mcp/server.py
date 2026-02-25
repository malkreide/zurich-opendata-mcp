"""
Zurich Open Data MCP Server
============================
MCP Server für den Zugriff auf Open Data der Stadt Zürich.
Integriert CKAN (data.stadt-zuerich.ch), ParkenDD, und weitere städtische APIs.
"""

import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from .api_client import (
    CKAN_BASE_URL,
    GEOPORTAL_LAYERS,
    PARIS_NAMESPACES,
    PARKENDD_URL,
    SPARQL_URL,
    ZT_CATEGORIES,
    ZURICH_GROUPS,
    ckan_request,
    format_dataset_summary,
    format_resource_info,
    handle_api_error,
    http_get_json,
    paris_extract_text,
    paris_get_num_hits,
    paris_search,
    sparql_query,
    wfs_get_features,
    zt_get_categories,
    zt_get_data,
)

# ─── Server Setup ─────────────────────────────────────────────────────────────

mcp = FastMCP(
    "zurich_opendata_mcp",
    instructions=(
        "MCP Server für Open Data der Stadt Zürich. "
        "Bietet Zugriff auf 900+ Datensätze via CKAN API (data.stadt-zuerich.ch), "
        "Geodaten via WFS Geoportal (Schulanlagen, Quartiere, Spielplätze etc.), "
        "Parlamentsinformationen des Gemeinderats (Paris API), "
        "Tourismusdaten (Attraktionen, Restaurants, Hotels via Zürich Tourismus), "
        "SPARQL Linked Data (Statistiken der Stadt Zürich), "
        "und Echtzeit-Parkplatzdaten (ParkenDD). "
        "Alle Datensätze unter CC0-Lizenz frei nutzbar. "
        "Kategorien: Bildung, Bevölkerung, Mobilität, Umwelt, Finanzen, u.v.m."
    ),
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "8000")),
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CKAN TOOLS – Datensatz-Suche und -Exploration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SearchDatasetsInput(BaseModel):
    """Input für die Datensatz-Suche."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Suchbegriff(e), z.B. 'Schule', 'Verkehr', 'Bevölkerung'. "
        "Unterstützt Solr-Syntax: AND, OR, NOT, Wildcards (*), Fuzzy (~).",
        min_length=1,
        max_length=500,
    )
    rows: int = Field(default=10, description="Anzahl Ergebnisse (max. 50)", ge=1, le=50)
    offset: int = Field(default=0, description="Offset für Paginierung", ge=0)
    sort: Optional[str] = Field(
        default=None,
        description="Sortierung, z.B. 'metadata_modified desc', 'title asc', 'score desc'",
    )
    filter_group: Optional[str] = Field(
        default=None,
        description=f"Nach Kategorie filtern. Verfügbar: {', '.join(ZURICH_GROUPS)}",
    )


@mcp.tool(
    name="zurich_search_datasets",
    annotations={
        "title": "Datensätze suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_search_datasets(params: SearchDatasetsInput) -> str:
    """Durchsucht den Open-Data-Katalog der Stadt Zürich nach Datensätzen.

    Nutzt die CKAN-Suchmaschine (Solr) für Volltextsuche über Titel,
    Beschreibung, Tags und Metadaten aller 900+ Datensätze.

    Returns:
        Markdown-formatierte Liste mit Datensatz-Zusammenfassungen
    """
    try:
        api_params: dict = {
            "q": params.query,
            "rows": params.rows,
            "start": params.offset,
        }
        if params.sort:
            api_params["sort"] = params.sort
        if params.filter_group:
            api_params["fq"] = f"groups:{params.filter_group}"

        result = await ckan_request("package_search", api_params)
        total = result["count"]
        datasets = result["results"]

        if not datasets:
            return f"Keine Datensätze gefunden für '{params.query}'."

        lines = [
            f"## Suchergebnis: {total} Datensätze für '{params.query}'",
            f"Zeige {len(datasets)} von {total} (Offset: {params.offset})\n",
        ]
        for ds in datasets:
            lines.append(format_dataset_summary(ds))
            lines.append("")

        if total > params.offset + len(datasets):
            lines.append(f"*→ Weitere Ergebnisse mit offset={params.offset + len(datasets)}*")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Datensatzsuche")


class GetDatasetInput(BaseModel):
    """Input für Datensatz-Details."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    dataset_id: str = Field(
        ...,
        description="ID oder Name des Datensatzes, z.B. 'geo_schulanlagen' oder 'ssd_schulferien'",
        min_length=1,
    )


@mcp.tool(
    name="zurich_get_dataset",
    annotations={
        "title": "Datensatz-Details abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_get_dataset(params: GetDatasetInput) -> str:
    """Ruft vollständige Metadaten und Ressourcen eines Datensatzes ab.

    Gibt Titel, Beschreibung, Autor, Lizenz, Aktualisierungsintervall,
    alle verfügbaren Dateiformate und Download-URLs zurück.

    Returns:
        Detaillierte Markdown-Ansicht des Datensatzes mit allen Ressourcen
    """
    try:
        result = await ckan_request("package_show", {"id": params.dataset_id})

        lines = [format_dataset_summary(result), "\n#### Ressourcen / Downloads\n"]
        for res in result.get("resources", []):
            lines.append(format_resource_info(res))

        # Extra metadata
        extras = {e["key"]: e["value"] for e in result.get("extras", [])}
        if extras:
            lines.append("\n#### Zusätzliche Metadaten")
            for k, v in extras.items():
                if not k.startswith("harvest"):
                    lines.append(f"- **{k}**: {v}")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Datensatz-Details")


class DatastoreQueryInput(BaseModel):
    """Input für Datastore-Abfragen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    resource_id: str = Field(
        ...,
        description="Resource-ID aus dem Datensatz (UUID-Format)",
        min_length=1,
    )
    filters: Optional[str] = Field(
        default=None,
        description='JSON-Filter, z.B. {"Quartier": "Wiedikon"} oder {"Jahr": 2024}',
    )
    query: Optional[str] = Field(
        default=None,
        description="Volltextsuche innerhalb der Ressource",
    )
    sort: Optional[str] = Field(
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CKAN TOOLS – Kategorien, Tags, Organisationen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ListGroupInput(BaseModel):
    """Input für Gruppen-/Kategorie-Details."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    group_id: Optional[str] = Field(
        default=None,
        description=f"Gruppen-ID für Details. Verfügbar: {', '.join(ZURICH_GROUPS)}. "
        "Wenn leer, werden alle Kategorien aufgelistet.",
    )


@mcp.tool(
    name="zurich_list_categories",
    annotations={
        "title": "Datenkategorien auflisten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_list_categories(params: ListGroupInput) -> str:
    """Listet alle Datenkategorien (Gruppen) im Katalog auf oder zeigt Details einer Kategorie.

    Die Stadt Zürich organisiert ihre Datensätze in 19 thematische Kategorien
    wie Bildung, Bevölkerung, Mobilität, Umwelt etc.

    Returns:
        Markdown-Liste der Kategorien mit Datensatz-Anzahl
    """
    try:
        if params.group_id:
            result = await ckan_request(
                "group_show",
                {
                    "id": params.group_id,
                    "include_datasets": True,
                    "include_dataset_count": True,
                },
            )
            lines = [
                f"## Kategorie: {result['title']}",
                f"**Datensätze**: {result.get('package_count', 0)}\n",
            ]
            for ds in result.get("packages", []):
                lines.append(f"- **{ds['title']}** (`{ds['name']}`)")
            return "\n".join(lines)
        else:
            result = await ckan_request("group_list", {"all_fields": True, "include_dataset_count": True})
            lines = ["## Datenkategorien der Stadt Zürich\n"]
            for group in result:
                count = group.get("package_count", 0)
                lines.append(f"- **{group['title']}** (`{group['name']}`) – {count} Datensätze")
            return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Kategorien")


class TagSearchInput(BaseModel):
    """Input für Tag-Suche."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: Optional[str] = Field(
        default=None,
        description="Suchbegriff für Tags, z.B. 'schul', 'verkehr', 'wohn'",
    )
    limit: int = Field(default=30, description="Maximale Anzahl Tags", ge=1, le=100)


@mcp.tool(
    name="zurich_list_tags",
    annotations={
        "title": "Tags durchsuchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_list_tags(params: TagSearchInput) -> str:
    """Durchsucht verfügbare Tags im Open-Data-Katalog.

    Tags helfen, thematisch verwandte Datensätze zu finden.
    Z.B. 'volksschule', 'kindergarten', 'schulweg' für Bildungsdaten.

    Returns:
        Liste passender Tags
    """
    try:
        api_params: dict = {}
        if params.query:
            api_params["query"] = params.query

        result = await ckan_request("tag_list", api_params)

        if not result:
            return f"Keine Tags gefunden für '{params.query}'."

        tags = result[: params.limit]
        lines = [f"## Tags ({len(tags)} Ergebnisse)\n"]
        for tag in tags:
            lines.append(f"- `{tag}`")

        lines.append("\n*Tipp: Nutze `zurich_search_datasets` mit `filter_group` oder Solr-Query `tags:tagname`*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Tag-Suche")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ZÜRICH-SPEZIFISCHE TOOLS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool(
    name="zurich_parking_live",
    annotations={
        "title": "Echtzeit-Parkplatzdaten Zürich",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def zurich_parking_live() -> str:
    """Ruft Echtzeit-Parkplatz-Belegungsdaten für die Stadt Zürich ab.

    Liefert aktuelle Daten von 36 Parkhäusern und Parkplätzen:
    freie Plätze, Gesamtkapazität, Standort und Status.
    Datenquelle: ParkenDD API.

    Returns:
        Markdown-Tabelle mit aktuellen Parkhaus-Belegungen
    """
    try:
        data = await http_get_json(PARKENDD_URL)
        lots = data.get("lots", [])
        last_updated = data.get("last_updated", "unbekannt")

        lines = [
            "## Parkplatzbelegung Zürich",
            f"*Stand: {last_updated}*\n",
            "| Parkhaus | Frei | Total | Belegt % | Status |",
            "|----------|------|-------|----------|--------|",
        ]

        for lot in sorted(lots, key=lambda x: x.get("name", "")):
            name = lot.get("name", "?")
            free = lot.get("free", 0)
            total = lot.get("total", 0)
            state = lot.get("state", "?")
            pct = round((1 - free / total) * 100) if total > 0 else 0
            status_icon = "🟢" if state == "open" else "🔴"
            lines.append(f"| {name} | {free} | {total} | {pct}% | {status_icon} {state} |")

        lines.append(f"\n**Gesamt**: {len(lots)} Parkhäuser")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Parkplatz-Daten")


class AnalyzeDatasetInput(BaseModel):
    """Input für Datensatz-Analyse."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Suchbegriff für die Analyse, z.B. 'Schule', 'Verkehr', 'Wohnen'",
        min_length=1,
    )
    max_datasets: int = Field(default=5, description="Maximale Anzahl zu analysierender Datensätze", ge=1, le=20)
    include_structure: bool = Field(default=True, description="Datenstruktur (Felder) einschliessen")
    include_freshness: bool = Field(default=True, description="Aktualitäts-Analyse einschliessen")


@mcp.tool(
    name="zurich_analyze_datasets",
    annotations={
        "title": "Datensätze analysieren",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_analyze_datasets(params: AnalyzeDatasetInput) -> str:
    """Analysiert Datensätze umfassend: Relevanz, Aktualität und Datenstruktur.

    Kombiniert Suche mit Analyse der Update-Frequenz und Feld-Schemas.
    Besonders nützlich um herauszufinden, welche Daten verfügbar sind
    und wie aktuell/vollständig sie sind.

    Returns:
        Umfassender Analyse-Report mit Relevanz, Aktualität und Struktur
    """
    try:
        # Search
        result = await ckan_request(
            "package_search",
            {
                "q": params.query,
                "rows": params.max_datasets,
                "sort": "score desc",
            },
        )
        datasets = result["results"]
        total = result["count"]

        if not datasets:
            return f"Keine Datensätze gefunden für '{params.query}'."

        lines = [
            f"## Analyse: '{params.query}'",
            f"**{total} Datensätze gefunden**, Top {len(datasets)} analysiert:\n",
        ]

        for i, ds in enumerate(datasets, 1):
            name = ds.get("name", "")
            title = ds.get("title", "?")
            modified = ds.get("metadata_modified", "?")[:10]
            interval = ds.get("updateInterval", ["unbekannt"])
            resources = ds.get("resources", [])
            formats = sorted(set(r.get("format", "?") for r in resources))

            lines.append(f"### {i}. {title}")
            lines.append(f"- **ID**: `{name}`")
            lines.append(f"- **Formate**: {', '.join(formats)}")
            lines.append(f"- **Ressourcen**: {len(resources)}")

            if params.include_freshness:
                lines.append(f"- **Letzte Änderung**: {modified}")
                lines.append(f"- **Aktualisierung**: {', '.join(interval)}")

            if params.include_structure:
                # Try to get field info from first datastore resource
                for res in resources:
                    if res.get("datastore_active"):
                        try:
                            ds_info = await ckan_request(
                                "datastore_search",
                                {
                                    "resource_id": res["id"],
                                    "limit": 0,
                                },
                            )
                            fields = ds_info.get("fields", [])
                            total_records = ds_info.get("total", 0)
                            field_list = [f"`{f['id']}` ({f.get('type', '?')})" for f in fields if f["id"] != "_id"]
                            lines.append(f"- **DataStore-Einträge**: {total_records:,}")
                            lines.append(f"- **Felder**: {', '.join(field_list[:15])}")
                            if len(field_list) > 15:
                                lines.append(f"  *(und {len(field_list) - 15} weitere)*")
                            break
                        except Exception:
                            pass

            lines.append(f"- **URL**: {CKAN_BASE_URL}/dataset/{name}\n")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Datensatz-Analyse")


@mcp.tool(
    name="zurich_catalog_stats",
    annotations={
        "title": "Katalog-Statistiken",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_catalog_stats() -> str:
    """Gibt einen Überblick über den gesamten Open-Data-Katalog der Stadt Zürich.

    Zeigt Gesamtzahl der Datensätze, Verteilung nach Kategorien,
    häufigste Formate und Tags.

    Returns:
        Statistik-Übersicht des Katalogs
    """
    try:
        # Get faceted stats
        result = await ckan_request(
            "package_search",
            {
                "q": "*:*",
                "rows": 0,
                "facet.field": '["groups", "res_format", "tags"]',
                "facet.limit": "15",
            },
        )
        total = result["count"]
        facets = result.get("search_facets", result.get("facets", {}))

        lines = [
            "## Open Data Katalog – Stadt Zürich",
            f"**Gesamtzahl Datensätze**: {total}\n",
            f"**Portal**: {CKAN_BASE_URL}",
            "**Lizenz**: Creative Commons CC0 (Open by Default seit 2021)\n",
        ]

        # Groups
        if "groups" in facets:
            lines.append("### Kategorien")
            groups = facets["groups"]
            if isinstance(groups, dict):
                items = groups.get("items", [])
            else:
                items = groups if isinstance(groups, list) else []
            for item in sorted(items, key=lambda x: x.get("count", 0), reverse=True):
                lines.append(f"- **{item.get('display_name', item.get('name', '?'))}**: {item.get('count', 0)}")

        # Formats
        if "res_format" in facets:
            lines.append("\n### Häufigste Formate")
            fmts = facets["res_format"]
            if isinstance(fmts, dict):
                items = fmts.get("items", [])
            else:
                items = fmts if isinstance(fmts, list) else []
            for item in sorted(items, key=lambda x: x.get("count", 0), reverse=True)[:10]:
                lines.append(f"- **{item.get('display_name', item.get('name', '?'))}**: {item.get('count', 0)}")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Katalog-Statistiken")


class FindSchoolDataInput(BaseModel):
    """Input für schulspezifische Datensuche."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    topic: Optional[str] = Field(
        default=None,
        description=(
            "Spezifisches Schulthema, z.B. 'Schulanlagen', 'Ferien', "
            "'Kreisschulbehörde', 'Musikschule', 'Schüler', 'Kindergarten'. "
            "Wenn leer, werden alle schulrelevanten Datensätze gesucht."
        ),
    )


@mcp.tool(
    name="zurich_find_school_data",
    annotations={
        "title": "Schulrelevante Daten finden",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_find_school_data(params: FindSchoolDataInput) -> str:
    """Findet Datensätze, die für das Schulamt und die Volksschule relevant sind.

    Durchsucht gezielt nach Schulanlagen, Bildungsdaten, Kreisschulbehörden,
    Schülerstatistiken, Schulwegen und verwandten Themen.
    Nutzt eine kuratierte Kombination von Suchbegriffen.

    Returns:
        Markdown-Liste schulrelevanter Datensätze
    """
    try:
        search_terms = [
            "Schule",
            "Volksschule",
            "Kindergarten",
            "Schulanlage",
            "Kreisschulbehörde",
            "Bildung",
            "Schulweg",
            "Musikschule",
            "Schulferien",
            "Sonderschule",
            "Kinderhort",
        ]

        if params.topic:
            search_terms = [params.topic] + search_terms[:4]

        # Multiple queries, merge unique results (Zurich Solr doesn't handle long OR chains well)
        seen_ids: set[str] = set()
        datasets: list[dict] = []
        for term in search_terms:
            result = await ckan_request("package_search", {"q": term, "rows": 15, "sort": "score desc"})
            for ds in result["results"]:
                if ds["name"] not in seen_ids:
                    seen_ids.add(ds["name"])
                    datasets.append(ds)

        total = len(datasets)

        lines = [
            "## Schulrelevante Datensätze",
            f"**{total} Treffer** (zeige {len(datasets)})\n",
        ]

        # Group by author relevance
        schulamt_ds = []
        other_ds = []
        for ds in datasets:
            author = ds.get("author", "")
            if "Schulamt" in author or "Schul-" in author or "Schulraumplanung" in author:
                schulamt_ds.append(ds)
            else:
                other_ds.append(ds)

        if schulamt_ds:
            lines.append("### Vom Schulamt / SSD")
            for ds in schulamt_ds:
                lines.append(format_dataset_summary(ds))
                lines.append("")

        if other_ds:
            lines.append("### Weitere relevante Datensätze")
            for ds in other_ds[:15]:
                lines.append(f"- **{ds['title']}** (`{ds['name']}`) – {ds.get('author', '?')}")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Schuldaten-Suche")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ECHTZEIT-TOOLS – Wetter, Luft, Wasser, Passanten, ÖV
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# --- Resource IDs for realtime DataStore sources ---
METEO_RESOURCE_ID = "f9aa1373-404f-443b-b623-03ff02d2d0b7"  # ugz_ogd_meteo_h1_2026
AIR_QUALITY_RESOURCE_ID = "90410203-4b4f-4a65-9015-1fca2792e04d"  # ugz_ogd_air_h1_2026
WATER_TIEFENBRUNNEN_ID = "f86b3581-6fbc-4337-ab1a-b6ead9d15daf"
WATER_MYTHENQUAI_ID = "61e26c94-c521-473f-b7bf-bb0d73f21e9f"
PEDESTRIAN_RESOURCE_ID = "ec1fc740-8e54-4116-aab7-3394575b4666"  # hystreet
VBZ_REISENDE_ID = "38b0c1e5-1f4e-444d-975c-61a462aa8ca6"
VBZ_LINIE_ID = "463f92e0-5b20-44b3-b27f-59499e331e8d"
VBZ_HALTESTELLEN_ID = "948b6347-8988-4705-9b08-45f0208a15da"


# ── Tool 1: Live Weather ─────────────────────────────────────────────────────


class WeatherLiveInput(BaseModel):
    """Input für Live-Wetterdaten."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    station: Optional[str] = Field(
        default=None,
        description=(
            "Messstation filtern (z.B. 'Zch_Stampfenbachstrasse', "
            "'Zch_Schimmelstrasse', 'Zch_Rosengartenstrasse'). "
            "Leer = alle Stationen."
        ),
    )
    parameter: Optional[str] = Field(
        default=None,
        description=(
            "Messparameter filtern: 'T' (Temperatur °C), 'Hr' (Luftfeuchte %), "
            "'p' (Luftdruck hPa), 'RainDur' (Regendauer min). Leer = alle."
        ),
    )
    limit: int = Field(default=20, description="Anzahl Messwerte (max. 100)", ge=1, le=100)


@mcp.tool(
    name="zurich_weather_live",
    annotations={
        "title": "Aktuelle Wetterdaten Zürich",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_weather_live(params: WeatherLiveInput) -> str:
    """Liefert stündlich aktualisierte Wetterdaten der UGZ-Messstationen Zürich.

    Datenquelle: Umwelt- und Gesundheitsschutz Stadt Zürich (UGZ).
    Messstationen: Stampfenbachstrasse, Schimmelstrasse, Rosengartenstrasse,
    Heubeeribüel, Kaserne.

    Returns:
        Aktuelle Temperatur, Luftfeuchte, Luftdruck, Regendauer je Station
    """
    try:
        api_params: dict = {
            "resource_id": METEO_RESOURCE_ID,
            "sort": "Datum desc",
            "limit": params.limit,
        }
        filters = {}
        if params.station:
            filters["Standort"] = params.station
        if params.parameter:
            filters["Parameter"] = params.parameter
        if filters:
            api_params["filters"] = json.dumps(filters)

        result = await ckan_request("datastore_search", api_params)
        records = result.get("records", [])

        if not records:
            return "Keine Wetterdaten gefunden. Standort/Parameter prüfen."

        lines = ["## 🌤️ Aktuelle Wetterdaten Zürich\n"]
        lines.append(f"*Quelle: UGZ Messnetz – {result.get('total', '?')} Messwerte total*\n")

        # Group by timestamp for better readability
        by_time: dict[str, list] = {}
        for r in records:
            ts = r.get("Datum", "?")
            by_time.setdefault(ts, []).append(r)

        for ts, measurements in list(by_time.items())[:5]:
            lines.append(f"### {ts}")
            for m in measurements:
                station = m.get("Standort", "?")
                param = m.get("Parameter", "?")
                value = m.get("Wert", "?")
                status = m.get("Status", "")

                # Human-readable parameter names
                param_names = {
                    "T": "🌡️ Temperatur",
                    "Hr": "💧 Luftfeuchte",
                    "p": "📊 Luftdruck",
                    "RainDur": "🌧️ Regendauer",
                }
                display = param_names.get(param, param)
                unit = {"T": "°C", "Hr": "%", "p": "hPa", "RainDur": "min"}.get(param, "")
                status_str = f" ⚠️ {status}" if status and status != "provisorisch" else ""

                lines.append(f"- **{station}** – {display}: **{value} {unit}**{status_str}")
            lines.append("")

        lines.append("---")
        lines.append("*Daten: data.stadt-zuerich.ch – stündlich aktualisiert*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Wetterdaten")


# ── Tool 2: Live Air Quality ─────────────────────────────────────────────────


class AirQualityInput(BaseModel):
    """Input für Live-Luftqualitätsdaten."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    station: Optional[str] = Field(
        default=None,
        description=(
            "Messstation: 'Zch_Stampfenbachstrasse', 'Zch_Schimmelstrasse', "
            "'Zch_Rosengartenstrasse', 'Zch_Heubeeribüel', 'Zch_Kaserne'. "
            "Leer = alle."
        ),
    )
    parameter: Optional[str] = Field(
        default=None,
        description=(
            "Schadstoff: 'NO2' (Stickstoffdioxid), 'O3' (Ozon), "
            "'PM10' (Feinstaub), 'PM2.5', 'NOx', 'SO2', 'CO'. Leer = alle."
        ),
    )
    limit: int = Field(default=30, description="Anzahl Messwerte (max. 100)", ge=1, le=100)


@mcp.tool(
    name="zurich_air_quality",
    annotations={
        "title": "Luftqualität Zürich (Echtzeit)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_air_quality(params: AirQualityInput) -> str:
    """Liefert stündlich aktualisierte Luftqualitätsmessungen aus Zürich.

    Datenquelle: Umwelt- und Gesundheitsschutz Stadt Zürich (UGZ).
    Parameter: NO2, O3, PM10, PM2.5, NOx, SO2, CO u.a.

    Returns:
        Aktuelle Schadstoffwerte je Station mit Einheiten
    """
    try:
        api_params: dict = {
            "resource_id": AIR_QUALITY_RESOURCE_ID,
            "sort": "Datum desc",
            "limit": params.limit,
        }
        filters = {}
        if params.station:
            filters["Standort"] = params.station
        if params.parameter:
            filters["Parameter"] = params.parameter
        if filters:
            api_params["filters"] = json.dumps(filters)

        result = await ckan_request("datastore_search", api_params)
        records = result.get("records", [])

        if not records:
            return "Keine Luftqualitätsdaten gefunden."

        lines = ["## 🌬️ Luftqualität Zürich\n"]
        lines.append(f"*Quelle: UGZ Messnetz – {result.get('total', '?')} Messwerte total*\n")

        # Group by timestamp
        by_time: dict[str, list] = {}
        for r in records:
            ts = r.get("Datum", "?")
            by_time.setdefault(ts, []).append(r)

        for ts, measurements in list(by_time.items())[:3]:
            lines.append(f"### {ts}")

            # Sub-group by station
            by_station: dict[str, list] = {}
            for m in measurements:
                st = m.get("Standort", "?")
                by_station.setdefault(st, []).append(m)

            for station, meas in by_station.items():
                values = []
                for m in meas:
                    param = m.get("Parameter", "?")
                    value = m.get("Wert", "?")
                    unit = m.get("Einheit", "")
                    if value is not None and value != "":
                        values.append(f"{param}={value} {unit}")
                if values:
                    lines.append(f"- **{station}**: {', '.join(values)}")
            lines.append("")

        # WHO guideline hints
        lines.append("---")
        lines.append("*WHO-Grenzwerte (24h): PM2.5 ≤15 µg/m³, PM10 ≤45 µg/m³, NO₂ ≤25 µg/m³*")
        lines.append("*Daten: data.stadt-zuerich.ch – stündlich aktualisiert*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Luftqualität")


# ── Tool 3: Water Weather Stations ───────────────────────────────────────────


class WaterWeatherInput(BaseModel):
    """Input für Wasserschutzpolizei-Wetterstationen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    station: str = Field(
        default="tiefenbrunnen",
        description="Messstation: 'tiefenbrunnen' oder 'mythenquai'",
    )
    limit: int = Field(default=6, description="Anzahl Messwerte (max. 50)", ge=1, le=50)


@mcp.tool(
    name="zurich_water_weather",
    annotations={
        "title": "See-/Wasserwetter Zürich",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_water_weather(params: WaterWeatherInput) -> str:
    """Liefert Echtzeit-Wetterdaten der Wasserschutzpolizei Zürich.

    Stationen am Zürichsee: Tiefenbrunnen und Mythenquai.
    10-Minuten-Intervall mit See- und Lufttemperatur, Wind, Wasserstand,
    Niederschlag, Luftdruck, Taupunkt, Globalstrahlung.

    Returns:
        Aktuelle See-Messwerte mit Wasser- und Lufttemperatur, Wind, Pegel
    """
    try:
        resource_id = WATER_TIEFENBRUNNEN_ID if "tiefen" in params.station.lower() else WATER_MYTHENQUAI_ID
        station_name = "Tiefenbrunnen" if "tiefen" in params.station.lower() else "Mythenquai"

        result = await ckan_request(
            "datastore_search",
            {
                "resource_id": resource_id,
                "sort": "timestamp_utc desc",
                "limit": params.limit,
            },
        )
        records = result.get("records", [])

        if not records:
            return f"Keine Daten für Station {station_name} gefunden."

        lines = [f"## 🌊 Zürichsee Wetterstation {station_name}\n"]
        lines.append("*Wasserschutzpolizei Zürich – alle 10 Min. aktualisiert*\n")

        for r in records:
            ts = r.get("timestamp_cet", r.get("timestamp_utc", "?"))
            lines.append(f"### {ts}")

            def v(key: str, unit: str = "") -> str:
                """Format value, replacing None with '–'."""
                val = r.get(key)
                return f"{val} {unit}".strip() if val is not None else "–"

            lines.append(f"- 🌊 **Wassertemperatur**: {v('water_temperature', '°C')}")
            lines.append(f"- 🌡️ **Lufttemperatur**: {v('air_temperature', '°C')}")
            lines.append(f"- 📊 **Wasserstand**: {v('water_level', 'm ü.M.')}")
            wind_speed = v("wind_speed_avg_10min", "m/s")
            wind_gust = v("wind_gust_max_10min", "m/s")
            lines.append(f"- 💨 **Wind**: {wind_speed} (Böen: {wind_gust})")
            lines.append(f"- 🧭 **Windrichtung**: {v('wind_direction', '°')}")
            lines.append(f"- 💧 **Luftfeuchte**: {v('humidity', '%')}")
            lines.append(f"- 🌧️ **Niederschlag**: {v('precipitation', 'mm')}")
            lines.append(f"- 📏 **Luftdruck**: {v('barometric_pressure_qfe', 'hPa')}")
            lines.append(f"- 🌡️ **Taupunkt**: {v('dew_point', '°C')}")
            lines.append(f"- ☀️ **Globalstrahlung**: {v('global_radiation', 'W/m²')}")
            lines.append("")

        lines.append("---")
        lines.append("*Daten: data.stadt-zuerich.ch – 10-Min.-Intervall*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Wasserwetter")


# ── Tool 4: Pedestrian Traffic ────────────────────────────────────────────────


class PedestrianInput(BaseModel):
    """Input für Passantenfrequenzen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    limit: int = Field(default=24, description="Anzahl Stundenwerte (max. 168)", ge=1, le=168)


@mcp.tool(
    name="zurich_pedestrian_traffic",
    annotations={
        "title": "Passantenfrequenzen Bahnhofstrasse",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_pedestrian_traffic(params: PedestrianInput) -> str:
    """Liefert stündliche Passantenfrequenzen an der Zürcher Bahnhofstrasse.

    Datenquelle: hystreet.com Sensoren an 3 Standorten (Nord, Mitte, Süd).
    Misst die Anzahl Fussgänger:innen pro Stunde inkl. Richtung und Wetter.

    Returns:
        Stundenwerte der Passantenfrequenz (neueste zuerst)
    """
    try:
        result = await ckan_request(
            "datastore_search",
            {
                "resource_id": PEDESTRIAN_RESOURCE_ID,
                "sort": "timestamp desc",
                "limit": params.limit,
            },
        )
        records = result.get("records", [])

        if not records:
            return "Keine Passantenfrequenz-Daten gefunden."

        lines = ["## 🚶 Passantenfrequenzen Bahnhofstrasse Zürich\n"]
        lines.append("*hystreet.com Sensoren – stündlich aktualisiert*\n")

        # Show compact table
        lines.append("| Zeitpunkt | Standort | Passanten | Temp. | Wetter |")
        lines.append("| --- | --- | ---: | ---: | --- |")
        for r in records:
            ts = str(r.get("timestamp", "?"))[:16]
            loc = str(r.get("location_name", "?"))
            count = r.get("pedestrians_count", "?")
            temp = r.get("temperature", "?")
            weather = str(r.get("weather_condition", "?"))
            lines.append(f"| {ts} | {loc} | {count} | {temp}°C | {weather} |")

        lines.append("")
        lines.append(f"*{result.get('total', '?')} Messwerte total*")
        lines.append("*Daten: data.stadt-zuerich.ch*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Passantenfrequenzen")


# ── Tool 5: VBZ Passenger Data ────────────────────────────────────────────────


class VBZPassengersInput(BaseModel):
    """Input für VBZ-Fahrgastzahlen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    line: Optional[str] = Field(
        default=None,
        description=("Liniennummer filtern, z.B. '4' (Tram 4), '33' (Bus 33). Leer = alle Linien."),
    )
    stop: Optional[str] = Field(
        default=None,
        description=(
            "Haltestelle filtern (Name oder Teilname), z.B. 'Paradeplatz', 'Central', 'Bellevue'. Leer = alle."
        ),
    )
    query: Optional[str] = Field(
        default=None,
        description="Volltextsuche über alle Felder",
    )
    limit: int = Field(default=20, description="Anzahl Ergebnisse (max. 100)", ge=1, le=100)


@mcp.tool(
    name="zurich_vbz_passengers",
    annotations={
        "title": "VBZ Fahrgastzahlen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_vbz_passengers(params: VBZPassengersInput) -> str:
    """Fragt Fahrgastzahlen der Verkehrsbetriebe Zürich (VBZ) ab.

    Jährlich aktualisierte Ein-/Aussteiger-Zahlen pro Linie und Haltestelle.
    Die Daten umfassen Tram, Bus, Trolleybus und Seilbahnen.

    Returns:
        Fahrgastzahlen mit Linien- und Haltestellendetails
    """
    try:
        api_params: dict = {
            "resource_id": VBZ_REISENDE_ID,
            "limit": params.limit,
        }
        if params.query:
            api_params["q"] = params.query

        result = await ckan_request("datastore_search", api_params)
        records = result.get("records", [])
        fields = result.get("fields", [])

        if not records:
            return "Keine VBZ-Fahrgastzahlen gefunden."

        field_names = [f["id"] for f in fields if f["id"] != "_id"]

        lines = ["## 🚊 VBZ Fahrgastzahlen\n"]
        lines.append(f"*Verkehrsbetriebe Zürich – {result.get('total', '?')} Einträge*\n")
        lines.append(f"**Felder**: {', '.join(field_names)}\n")

        # Render data
        lines.append("```json")
        lines.append(json.dumps(records, indent=2, ensure_ascii=False, default=str))
        lines.append("```")

        if result.get("total", 0) > params.limit:
            lines.append(f"\n*→ {result['total'] - params.limit} weitere Einträge verfügbar*")

        lines.append("\n---")
        lines.append(
            f"*Tipp: Für Haltestellendetails `zurich_datastore_query` mit Resource `{VBZ_HALTESTELLEN_ID}` verwenden.*"
        )
        lines.append(f"*Für Liniendetails: Resource `{VBZ_LINIE_ID}`*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "VBZ-Fahrgastzahlen")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GEOPORTAL WFS – Geodaten als GeoJSON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.tool(
    name="zurich_geo_layers",
    annotations={
        "title": "Verfügbare Geodaten-Layer",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def zurich_geo_layers() -> str:
    """Listet alle verfügbaren WFS-Layer des Geoportals der Stadt Zürich auf.

    Zeigt Layer-ID, WFS-Service-Name, Typename und Beschreibung für jeden
    verfügbaren Geodatensatz. Die IDs können mit dem Tool zurich_geo_features
    verwendet werden.

    Returns:
        Markdown-formatierte Liste aller Geodaten-Layer
    """
    lines = [
        "## Verfügbare Geoportal-Layer (WFS)",
        f"**Anzahl**: {len(GEOPORTAL_LAYERS)}\n",
        "| Layer-ID | Beschreibung | WFS-Service |",
        "|---|---|---|",
    ]
    for layer_id, (service, typename, desc) in sorted(GEOPORTAL_LAYERS.items()):
        lines.append(f"| `{layer_id}` | {desc} | {service} |")

    lines.append("\n*Nutze `zurich_geo_features` mit einer Layer-ID, um GeoJSON-Daten abzurufen.*")
    return "\n".join(lines)


class GeoFeaturesInput(BaseModel):
    """Input für Geodaten-Abfragen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    layer_id: str = Field(
        ...,
        description=f"Layer-ID. Verfügbar: {', '.join(sorted(GEOPORTAL_LAYERS.keys()))}",
        min_length=1,
    )
    max_features: int = Field(
        default=50,
        description="Maximale Anzahl Features (max. 500)",
        ge=1,
        le=500,
    )
    property_filter: Optional[str] = Field(
        default=None,
        description=(
            "CQL-Filter für Eigenschaften, z.B. \"kategorie = 'Kindergarten'\" "
            "oder \"name LIKE '%Wasser%'\". Feldnamen hängen vom Layer ab."
        ),
    )


@mcp.tool(
    name="zurich_geo_features",
    annotations={
        "title": "Geodaten abrufen (GeoJSON)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_geo_features(params: GeoFeaturesInput) -> str:
    """Ruft Geodaten aus dem WFS-Geoportal der Stadt Zürich als GeoJSON ab.

    Liefert geografische Features (Punkte, Polygone) mit Eigenschaften
    wie Name, Adresse, Kategorie etc. Nützlich für Schulanlagen,
    Stadtkreise, Spielplätze, Veloprüfstrecken und mehr.

    Returns:
        GeoJSON FeatureCollection mit Features und ihren Eigenschaften
    """
    try:
        if params.layer_id not in GEOPORTAL_LAYERS:
            available = ", ".join(sorted(GEOPORTAL_LAYERS.keys()))
            return f"Unbekannter Layer `{params.layer_id}`. Verfügbar: {available}"

        service_name, typename, description = GEOPORTAL_LAYERS[params.layer_id]

        geojson = await wfs_get_features(
            service_name=service_name,
            typename=typename,
            max_features=params.max_features,
            cql_filter=params.property_filter,
        )

        features = geojson.get("features", [])
        total = len(features)

        lines = [
            f"## Geodaten: {description}",
            f"**Layer**: `{params.layer_id}` ({typename})",
            f"**Features**: {total}\n",
        ]

        if params.property_filter:
            lines.append(f"**Filter**: `{params.property_filter}`\n")

        # Show summary of first features
        for i, feat in enumerate(features[:20], 1):
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            geom_type = geom.get("type", "?")
            coords = geom.get("coordinates", [])

            name = props.get("name") or props.get("bezeichnung") or props.get("einheit") or f"Feature {i}"
            kategorie = props.get("kategorie") or props.get("typ") or ""
            adresse = props.get("adresse") or props.get("strasse") or ""

            label = f"**{name}**"
            if kategorie:
                label += f" ({kategorie})"
            if adresse:
                label += f" – {adresse}"

            if geom_type == "Point" and coords:
                label += f" 📍 [{coords[1]:.5f}, {coords[0]:.5f}]"

            lines.append(f"{i}. {label}")

        if total > 20:
            lines.append(f"\n*… und {total - 20} weitere Features*")

        # Show property names from first feature
        if features:
            prop_keys = [k for k in features[0].get("properties", {}).keys() if k not in ("objectid", "geometrie_gdo")]
            lines.append(f"\n**Verfügbare Felder**: {', '.join(prop_keys[:20])}")

        lines.append(f"\n*Volle GeoJSON-Daten via `zurich://geo/{params.layer_id}` Resource*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Geodaten-Abfrage")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARIS API – Parlamentsinformationen Gemeinderat
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ParliamentSearchInput(BaseModel):
    """Input für die Geschäftssuche im Gemeinderat."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description=(
            "Suchbegriff für Gemeinderatsgeschäfte. Wird im Titel gesucht. "
            "Beispiele: 'Schule', 'Digitalisierung', 'Klimaschutz', 'Budget'"
        ),
        min_length=1,
        max_length=500,
    )
    year_from: Optional[int] = Field(
        default=None,
        description="Geschäfte ab diesem Jahr filtern, z.B. 2020",
        ge=1990,
        le=2030,
    )
    year_to: Optional[int] = Field(
        default=None,
        description="Geschäfte bis zu diesem Jahr filtern, z.B. 2025",
        ge=1990,
        le=2030,
    )
    department: Optional[str] = Field(
        default=None,
        description=(
            "Nach zuständigem Departement filtern. Beispiele: 'Schul- und Sportdepartement', 'Finanzdepartement'"
        ),
    )
    max_results: int = Field(default=10, description="Maximale Anzahl Ergebnisse", ge=1, le=50)


@mcp.tool(
    name="zurich_parliament_search",
    annotations={
        "title": "Gemeinderatsgeschäfte suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_parliament_search(params: ParliamentSearchInput) -> str:
    """Durchsucht die Geschäfte des Gemeinderats der Stadt Zürich (Paris API).

    Findet Interpellationen, Motionen, Postulate, Anfragen und weitere
    parlamentarische Vorstösse. Besonders nützlich für Schulthemen, da viele
    Geschäfte das SSD (Schul- und Sportdepartement) betreffen.

    Returns:
        Markdown-Liste der gefundenen Gemeinderatsgeschäfte
    """
    try:
        # Build CQL query
        cql_parts = [f'Titel any "{params.query}"']
        if params.year_from:
            cql_parts.append(f'beginn_start > "{params.year_from}-01-01 00:00:00"')
        if params.year_to:
            cql_parts.append(f'beginn_start < "{params.year_to + 1}-01-01 00:00:00"')
        if params.department:
            cql_parts.append(f'Departement any "{params.department}"')

        cql = " AND ".join(cql_parts) + " sortBy beginn_start/sort.descending"

        root = await paris_search("geschaeft", cql, max_results=params.max_results)
        num_hits = paris_get_num_hits(root)

        ns = PARIS_NAMESPACES
        hits = root.findall("sr:Hit", ns)

        if not hits:
            return f"Keine Gemeinderatsgeschäfte gefunden für '{params.query}'."

        lines = [
            f"## Gemeinderatsgeschäfte: '{params.query}'",
            f"**{num_hits} Treffer** (zeige {len(hits)})\n",
        ]

        for hit in hits:
            geschaeft = hit.find("g:Geschaeft", ns)
            if geschaeft is None:
                continue

            gr_nr = paris_extract_text(geschaeft.find("g:GRNr", ns), "?")
            titel = paris_extract_text(geschaeft.find("g:Titel", ns), "Ohne Titel")
            art = paris_extract_text(geschaeft.find("g:Geschaeftsart", ns), "?")
            status = paris_extract_text(geschaeft.find("g:Geschaeftsstatus", ns), "?")
            dept_el = geschaeft.find("g:FederfuehrendesDepartement/g:Departement/g:n", ns)
            dept = paris_extract_text(dept_el, "")

            beginn_el = geschaeft.find("g:Beginn/g:Text", ns)
            datum = paris_extract_text(beginn_el, "?")

            # Erstunterzeichner
            erst_el = geschaeft.find("g:Erstunterzeichner/g:KontaktGremium", ns)
            if erst_el is not None:
                erst_name = paris_extract_text(erst_el.find("g:n", ns), "")
                erst_partei = paris_extract_text(erst_el.find("g:Partei", ns), "")
                erstunterzeichner = f"{erst_name} ({erst_partei})" if erst_partei else erst_name
            else:
                erstunterzeichner = ""

            lines.append(f"### {gr_nr}: {titel}")
            lines.append(f"- **Art**: {art}")
            lines.append(f"- **Status**: {status}")
            lines.append(f"- **Datum**: {datum}")
            if dept:
                lines.append(f"- **Departement**: {dept}")
            if erstunterzeichner:
                lines.append(f"- **Eingereicht von**: {erstunterzeichner}")
            lines.append(f"- **Link**: https://www.gemeinderat-zuerich.ch/geschaefte/{gr_nr.replace('/', '-')}")
            lines.append("")

        if num_hits > len(hits):
            lines.append(f"*→ {num_hits - len(hits)} weitere Treffer vorhanden*")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Geschäftssuche Gemeinderat")


class ParliamentMembersInput(BaseModel):
    """Input für die Mitgliedersuche im Gemeinderat."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: Optional[str] = Field(
        default=None,
        description="Name oder Teilname des Ratsmitglieds, z.B. 'Marti' oder 'Peter'",
    )
    party: Optional[str] = Field(
        default=None,
        description="Parteiname, z.B. 'SP', 'SVP', 'Grüne', 'FDP', 'GLP', 'AL', 'Mitte'",
    )
    commission: Optional[str] = Field(
        default=None,
        description=(
            "Kommissionsname, z.B. 'GPK', 'RPK', 'Bildungsrat'. Sucht aktive Mitglieder der genannten Kommission."
        ),
    )
    active_only: bool = Field(
        default=True,
        description="Nur aktive Ratsmitglieder anzeigen",
    )
    max_results: int = Field(default=20, description="Maximale Anzahl Ergebnisse", ge=1, le=100)


@mcp.tool(
    name="zurich_parliament_members",
    annotations={
        "title": "Gemeinderatsmitglieder suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_parliament_members(params: ParliamentMembersInput) -> str:
    """Sucht Mitglieder des Gemeinderats der Stadt Zürich.

    Ermöglicht die Suche nach Name, Partei und Kommissionszugehörigkeit.
    Zeigt aktuelle Mandate und Funktionen.

    Returns:
        Markdown-Liste der gefundenen Ratsmitglieder
    """
    try:
        ns = PARIS_NAMESPACES

        if params.commission:
            # Search via Behoerdenmandat index for commission members
            cql_parts = [f'gremium any "{params.commission}"']
            if params.active_only:
                cql_parts.append('Dauer_end > "9999-12-31 00:00:00"')
            if params.name:
                cql_parts.append(f'Name any "{params.name}"')
            cql = " AND ".join(cql_parts)

            root = await paris_search("behoerdenmandat", cql, max_results=params.max_results)
            num_hits = paris_get_num_hits(root)
            hits = root.findall("sr:Hit", ns)

            if not hits:
                return f"Keine Mitglieder gefunden für Kommission '{params.commission}'."

            lines = [
                f"## Kommission: {params.commission}",
                f"**{num_hits} Mitglieder**\n",
            ]

            for hit in hits:
                bm = hit.find("b:Behordenmandat", ns)
                if bm is None:
                    continue
                name = paris_extract_text(bm.find("b:n", ns), "?")
                vorname = paris_extract_text(bm.find("b:Vorname", ns), "")
                gremium = paris_extract_text(bm.find("b:Gremium", ns), "?")
                funktion = paris_extract_text(bm.find("b:Funktion", ns), "Mitglied")
                partei = paris_extract_text(bm.find("b:Partei", ns), "")
                dauer_text = paris_extract_text(bm.find("b:Dauer/b:Text", ns), "?")

                display = f"**{vorname} {name}**" if vorname else f"**{name}**"
                if partei:
                    display += f" ({partei})"
                display += f" – {funktion}, {gremium}"
                display += f" (seit {dauer_text.split(' -')[0].strip()})" if " -" in dauer_text else ""

                lines.append(f"- {display}")

            return "\n".join(lines)

        else:
            # Search via Kontakt index
            cql_parts = []
            if params.name:
                cql_parts.append(f'NameVorname any "{params.name}"')
            if params.party:
                cql_parts.append(f'Partei any "{params.party}"')
            if params.active_only:
                cql_parts.append('AktivesRatsmitglied = "true"')

            if not cql_parts:
                cql_parts.append('AktivesRatsmitglied = "true"')

            cql = " AND ".join(cql_parts)

            root = await paris_search("kontakt", cql, max_results=params.max_results)
            num_hits = paris_get_num_hits(root)
            hits = root.findall("sr:Hit", ns)

            if not hits:
                return "Keine Ratsmitglieder gefunden."

            lines = [
                "## Gemeinderatsmitglieder",
                f"**{num_hits} Treffer** (zeige {len(hits)})\n",
            ]

            for hit in hits:
                kontakt = hit.find("k:Kontakt", ns)
                if kontakt is None:
                    continue

                name_vn = paris_extract_text(kontakt.find("k:NameVorname", ns), "?")
                partei = paris_extract_text(kontakt.find("k:Partei", ns), "")
                wahlkreis = paris_extract_text(kontakt.find("k:Wahlkreis", ns), "")

                display = f"**{name_vn}**"
                if partei:
                    display += f" ({partei})"
                if wahlkreis:
                    display += f" – Wahlkreis {wahlkreis}"

                # Mandate
                mandate = kontakt.findall("k:Behoerdenmandat/k:Behoerdenmandat", ns)
                if mandate:
                    mandate_list = []
                    for m in mandate[:5]:
                        gremium = paris_extract_text(m.find("k:GremiumName", ns), "?")
                        funktion = paris_extract_text(m.find("k:Funktion", ns), "")
                        mandate_list.append(f"{gremium}" + (f" ({funktion})" if funktion else ""))
                    display += f"\n  - Mandate: {', '.join(mandate_list)}"

                lines.append(f"- {display}")
                lines.append("")

            return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Mitgliedersuche Gemeinderat")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ZÜRICH TOURISMUS API – Attraktionen, Restaurants, Hotels
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TourismSearchInput(BaseModel):
    """Input für Zürich Tourismus Daten."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: str = Field(
        ...,
        description=(
            "Tourismus-Kategorie. Verfügbar: "
            + ", ".join(f"'{k}'" for k in sorted(ZT_CATEGORIES.keys()))
            + ". Oder eine numerische Kategorie-ID."
        ),
    )
    search_text: Optional[str] = Field(
        default=None,
        description="Optionaler Suchtext zur Filterung der Ergebnisse, z.B. 'Altstadt' oder 'vegan'",
    )
    max_results: int = Field(default=10, description="Maximale Anzahl Ergebnisse", ge=1, le=50)
    language: str = Field(
        default="de",
        description="Sprache der Ergebnisse: 'de', 'en', 'fr', 'it'",
    )


@mcp.tool(
    name="zurich_tourism",
    annotations={
        "title": "Zürich Tourismus Daten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_tourism(params: TourismSearchInput) -> str:
    """Sucht Attraktionen, Restaurants, Hotels und Events über die Zürich Tourismus API.

    Liefert Informationen zu Sehenswürdigkeiten, gastronomischen Angeboten,
    Unterkünften, Aktivitäten und Veranstaltungen in Zürich.
    Daten basieren auf Schema.org-Formaten.

    Returns:
        Markdown-formatierte Liste der Tourismus-Einträge
    """
    try:
        # Resolve category
        if params.category.isdigit():
            cat_id = int(params.category)
        elif params.category.lower() in ZT_CATEGORIES:
            cat_id = ZT_CATEGORIES[params.category.lower()]
        else:
            available = ", ".join(f"`{k}` ({v})" for k, v in sorted(ZT_CATEGORIES.items()))
            return f"Unbekannte Kategorie `{params.category}`. Verfügbar:\n{available}"

        data = await zt_get_data(cat_id)
        lang = params.language

        # Filter by search text
        if params.search_text:
            search_lower = params.search_text.lower()
            filtered = []
            for item in data:
                name = item.get("name", {}).get(lang, "") or ""
                desc = item.get("disambiguatingDescription", {}).get(lang, "") or ""
                categories = " ".join(item.get("category", {}).keys())
                if search_lower in name.lower() or search_lower in desc.lower() or search_lower in categories.lower():
                    filtered.append(item)
            data = filtered

        total = len(data)
        data = data[: params.max_results]

        if not data:
            return (
                f"Keine Tourismus-Einträge gefunden für Kategorie '{params.category}'"
                + (f" mit Filter '{params.search_text}'" if params.search_text else "")
                + "."
            )

        lines = [
            f"## Zürich Tourismus: {params.category}",
            f"**{total} Einträge** (zeige {len(data)})\n",
        ]

        for item in data:
            name = item.get("name", {}).get(lang, "Unbenannt")
            short_desc = item.get("disambiguatingDescription", {}).get(lang, "")
            item_type = item.get("@type", "")
            custom_type = item.get("@customType") or ""
            categories = list(item.get("category", {}).keys())

            # Address
            address = item.get("address", {})
            street = address.get("streetAddress", "") if isinstance(address, dict) else ""
            postal = address.get("postalCode", "") if isinstance(address, dict) else ""
            city = address.get("addressLocality", "") if isinstance(address, dict) else ""
            addr_str = f"{street}, {postal} {city}".strip(", ") if street else ""

            # Contact
            url = item.get("url", {}).get(lang, "") if isinstance(item.get("url"), dict) else ""
            phone = item.get("telephone", "")

            # Geo
            geo = item.get("geo", {})
            lat = geo.get("latitude") if isinstance(geo, dict) else None
            lon = geo.get("longitude") if isinstance(geo, dict) else None

            lines.append(f"### {name}")
            if custom_type:
                lines.append(f"- **Typ**: {custom_type}")
            elif item_type:
                lines.append(f"- **Typ**: {item_type}")
            if categories:
                lines.append(f"- **Kategorien**: {', '.join(categories[:5])}")
            if short_desc:
                lines.append(f"- **Beschreibung**: {short_desc[:250]}")
            if addr_str:
                lines.append(f"- **Adresse**: {addr_str}")
            if phone:
                lines.append(f"- **Telefon**: {phone}")
            if url:
                lines.append(f"- **Web**: {url}")
            if lat and lon:
                lines.append(f"- **Koordinaten**: {lat}, {lon}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Zürich Tourismus")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SPARQL – Linked Data / Statistiken
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SparqlQueryInput(BaseModel):
    """Input für SPARQL-Abfragen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description=(
            "SPARQL-Abfrage. Endpoint: ld.stadt-zuerich.ch. "
            "Beispiel: SELECT * WHERE { ?s ?p ?o } LIMIT 10. "
            "Tipp: GRAPH <https://linked.opendata.swiss/graph/zh/statistics> "
            "für Statistik-Daten verwenden."
        ),
        min_length=10,
        max_length=5000,
    )


@mcp.tool(
    name="zurich_sparql",
    annotations={
        "title": "SPARQL-Abfrage (Linked Data)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def zurich_sparql(params: SparqlQueryInput) -> str:
    """Führt eine SPARQL-Abfrage auf dem Linked-Data-Endpunkt der Stadt Zürich aus.

    Der Endpunkt (ld.stadt-zuerich.ch) enthält statistische Daten
    der Stadt Zürich als RDF Linked Data (Bevölkerung, Wirtschaft, Bildung etc.).

    Returns:
        Tabellarische Darstellung der SPARQL-Ergebnisse
    """
    try:
        # Safety: only allow SELECT queries
        query_upper = params.query.strip().upper()
        if not query_upper.startswith("SELECT") and not query_upper.startswith("PREFIX"):
            return "Nur SELECT-Abfragen sind erlaubt."

        result = await sparql_query(params.query)

        variables = result.get("head", {}).get("vars", [])
        bindings = result.get("results", {}).get("bindings", [])

        if not bindings:
            return "SPARQL-Abfrage lieferte keine Ergebnisse."

        lines = [
            "## SPARQL-Ergebnis",
            f"**{len(bindings)} Zeilen**, Variablen: {', '.join(variables)}\n",
        ]

        # Format as markdown table
        lines.append("| " + " | ".join(variables) + " |")
        lines.append("| " + " | ".join("---" for _ in variables) + " |")

        for binding in bindings[:100]:
            row = []
            for var in variables:
                cell = binding.get(var, {})
                value = cell.get("value", "")
                # Shorten URIs for readability
                if cell.get("type") == "uri" and "/" in value:
                    short = value.rsplit("/", 1)[-1]
                    if len(short) < 80:
                        value = short
                if len(value) > 100:
                    value = value[:97] + "..."
                row.append(value)
            lines.append("| " + " | ".join(row) + " |")

        if len(bindings) > 100:
            lines.append(f"\n*Zeige 100 von {len(bindings)} Zeilen*")

        lines.append(f"\n*Endpoint: {SPARQL_URL}*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "SPARQL-Abfrage")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RESOURCES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@mcp.resource("zurich://dataset/{name}")
async def get_dataset_resource(name: str) -> str:
    """Datensatz-Metadaten als MCP Resource."""
    result = await ckan_request("package_show", {"id": name})
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)


@mcp.resource("zurich://category/{group_id}")
async def get_category_resource(group_id: str) -> str:
    """Kategorie-Details als MCP Resource."""
    result = await ckan_request(
        "group_show",
        {
            "id": group_id,
            "include_datasets": True,
        },
    )
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)


@mcp.resource("zurich://parking")
async def get_parking_resource() -> str:
    """Aktuelle Parkplatz-Daten als MCP Resource."""
    data = await http_get_json(PARKENDD_URL)
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


@mcp.resource("zurich://geo/{layer_id}")
async def get_geo_resource(layer_id: str) -> str:
    """GeoJSON-Daten eines Geoportal-Layers als MCP Resource."""
    if layer_id not in GEOPORTAL_LAYERS:
        return json.dumps({"error": f"Unknown layer: {layer_id}"})
    service_name, typename, _ = GEOPORTAL_LAYERS[layer_id]
    data = await wfs_get_features(service_name, typename, max_features=500)
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


@mcp.resource("zurich://tourism/categories")
async def get_tourism_categories_resource() -> str:
    """Zürich Tourismus Kategorien als MCP Resource."""
    data = await zt_get_categories()
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTRYPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    """Start the Zurich Open Data MCP server."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()

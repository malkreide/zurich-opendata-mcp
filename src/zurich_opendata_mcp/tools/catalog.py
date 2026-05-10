"""CKAN catalog tools: dataset search, details, categories, tags, analysis."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import CKAN_BASE_URL, ZURICH_GROUPS, ZurichGroup
from ..formatters import format_dataset_summary, format_resource_info, handle_api_error
from ..http_client import ckan_request


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
    sort: str | None = Field(
        default=None,
        description="Sortierung, z.B. 'metadata_modified desc', 'title asc', 'score desc'",
    )
    filter_group: ZurichGroup | None = Field(
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
        # Solr behandelt q=* anders als q=*:* – nur letzteres liefert alle Datensätze
        query = "*:*" if params.query.strip() == "*" else params.query

        api_params: dict = {
            "q": query,
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


class ListGroupInput(BaseModel):
    """Input für Gruppen-/Kategorie-Details."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    group_id: ZurichGroup | None = Field(
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

    query: str | None = Field(
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

        # Pre-fetch per-dataset DataStore field info concurrently to avoid the
        # original N+1 fan-out (one sequential datastore_search per dataset).
        # The package_search response already contains `resources`, so the
        # extra package_show call has been removed.
        fields_per_ds: list[tuple[list[dict], int] | None]
        if params.include_structure:
            sem = asyncio.Semaphore(5)

            async def _fetch_first_datastore_fields(
                resources: list[dict],
            ) -> tuple[list[dict], int] | None:
                for res in resources:
                    if not res.get("datastore_active"):
                        continue
                    async with sem:
                        try:
                            info = await ckan_request(
                                "datastore_search",
                                {"resource_id": res["id"], "limit": 0},
                            )
                        except Exception:
                            return None
                    return info.get("fields", []), info.get("total", 0)
                return None

            fields_per_ds = await asyncio.gather(
                *(_fetch_first_datastore_fields(ds.get("resources") or []) for ds in datasets)
            )
        else:
            fields_per_ds = [None] * len(datasets)

        lines = [
            f"## Analyse: '{params.query}'",
            f"**{total} Datensätze gefunden**, Top {len(datasets)} analysiert:\n",
        ]

        for i, (ds, fields_info) in enumerate(zip(datasets, fields_per_ds), 1):
            name = ds.get("name", "")
            title = ds.get("title", "?")
            modified = ds.get("metadata_modified", "?")[:10]
            interval = ds.get("updateInterval", ["unbekannt"])
            resources = ds.get("resources") or []
            formats = sorted({r.get("format", "?") for r in resources})

            lines.append(f"### {i}. {title}")
            lines.append(f"- **ID**: `{name}`")
            lines.append(f"- **Formate**: {', '.join(formats)}")
            lines.append(f"- **Ressourcen**: {len(resources)}")

            for res in resources:
                res_id = res.get("id", "")
                res_name = res.get("name", "Unbenannt")
                res_format = res.get("format", "?")
                ds_active = "✔ DataStore" if res.get("datastore_active") else ""
                lines.append(f"  - `{res_id}` — {res_name} ({res_format}) {ds_active}")

            if params.include_freshness:
                lines.append(f"- **Letzte Änderung**: {modified}")
                lines.append(f"- **Aktualisierung**: {', '.join(interval)}")

            if params.include_structure and fields_info is not None:
                fields, total_records = fields_info
                field_list = [
                    f"`{f['id']}` ({f.get('type', '?')})"
                    for f in fields
                    if f["id"] != "_id"
                ]
                lines.append(f"- **DataStore-Einträge**: {total_records:,}")
                lines.append(f"- **Felder**: {', '.join(field_list[:15])}")
                if len(field_list) > 15:
                    lines.append(f"  *(und {len(field_list) - 15} weitere)*")

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

    topic: str | None = Field(
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

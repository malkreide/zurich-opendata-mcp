"""Stadtratsbeschlüsse (STRB) tools — search, by department, single decision."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import STRB_DEPARTEMENTE, STRB_RESOURCE_ID, OutputFormat
from ..formatters import handle_api_error
from ..http_client import ckan_request


def _sql_escape(value: str) -> str:
    # PostgreSQL string literals: double the single quote and escape backslashes.
    # Dates do not flow through here because they are regex-validated at the
    # Pydantic layer (^\d{4}-\d{2}-\d{2}$) and therefore cannot contain quotes.
    return value.replace("\\", "\\\\").replace("'", "''")


def _strb_where_clause(
    query: str | None = None,
    departement: str | None = None,
    datum_von: str | None = None,
    datum_bis: str | None = None,
) -> str:
    """Erstellt die WHERE-Klausel für STRB-SQL-Queries."""
    conditions: list[str] = []
    if query:
        conditions.append(f"\"Titel\" ILIKE '%{_sql_escape(query)}%'")
    if departement:
        conditions.append(f"\"Federfuhrendes Departement\" ILIKE '%{_sql_escape(departement)}%'")
    if datum_von:
        conditions.append(f"\"Beschlussdatum\" >= '{datum_von}'")
    if datum_bis:
        conditions.append(f"\"Beschlussdatum\" <= '{datum_bis}'")
    return " AND ".join(conditions) if conditions else "TRUE"


async def _strb_query(where: str, limit: int) -> tuple[list[dict], int]:
    """Führt Daten- und Count-Query aus und gibt (records, total) zurück."""
    sql_data = (
        f'SELECT "Titel", "Beschlussnummer", "Beschlussdatum", '
        f'"Federfuhrendes Departement", "Link" '
        f'FROM "{STRB_RESOURCE_ID}" '
        f"WHERE {where} "
        f'ORDER BY "Beschlussdatum" DESC '
        f"LIMIT {limit}"
    )
    sql_count = (
        f'SELECT COUNT(*) AS cnt FROM "{STRB_RESOURCE_ID}" WHERE {where}'
    )
    result_data = await ckan_request("datastore_search_sql", {"sql": sql_data})
    result_count = await ckan_request("datastore_search_sql", {"sql": sql_count})

    records = result_data.get("records", [])
    total = int(result_count["records"][0]["cnt"]) if result_count.get("records") else 0
    return records, total


def _format_strb_record(rec: dict) -> dict:
    """Normalisiert einen STRB-Datensatz für die Ausgabe."""
    return {
        "beschlussnummer": rec.get("Beschlussnummer", ""),
        "titel": rec.get("Titel", ""),
        "datum": rec.get("Beschlussdatum", ""),
        "departement": rec.get("Federfuhrendes Departement", ""),
        "link": rec.get("Link", ""),
    }


def _format_strb_markdown(records: list[dict], total: int, titel: str) -> str:
    """Formatiert STRB-Ergebnisse als lesbare Markdown-Liste."""
    lines = [
        f"## {titel}",
        "",
        f"**{total} Beschlüsse** gefunden (zeige {len(records)})",
        "",
    ]
    for rec in records:
        r = _format_strb_record(rec)
        lines.append(f"### [{r['beschlussnummer']}] {r['titel']}")
        lines.append(f"- **Datum:** {r['datum']}")
        lines.append(f"- **Departement:** {r['departement']}")
        lines.append(f"- **Link:** {r['link']}")
        lines.append("")
    return "\n".join(lines)


class SearchSTRBInput(BaseModel):
    """Input für die Volltextsuche in Stadtratsbeschlüssen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description=(
            "Suchbegriff im Beschlusstitel, z.B. 'Volksschule', 'Tagesschule', 'Baukredite'. "
            "Gross-/Kleinschreibung irrelevant. Teilstrings werden gefunden."
        ),
        min_length=1,
        max_length=200,
    )
    departement: str | None = Field(
        default=None,
        description=(
            "Optionaler Departement-Filter. Kürzel oder Teilname genügt, z.B. 'SSD', 'FD', 'PRD'. "
            "Vollständige Bezeichnungen: 'Schul- und Sportdepartement (SSD)', "
            "'Finanzdepartement (FD)', 'Präsidialdepartement (PRD)', usw."
        ),
        max_length=100,
    )
    datum_von: str | None = Field(
        default=None,
        description="Frühestes Beschlussdatum (ISO-Format: YYYY-MM-DD), z.B. '2025-01-01'.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    datum_bis: str | None = Field(
        default=None,
        description="Spätestes Beschlussdatum (ISO-Format: YYYY-MM-DD), z.B. '2025-12-31'.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    limit: int = Field(
        default=20,
        description="Max. Anzahl zurückgegebener Beschlüsse (Standard: 20, max. 100).",
        ge=1,
        le=100,
    )
    format: OutputFormat = Field(
        default="markdown",
        description="Ausgabeformat: 'markdown' (Standard, lesbar) oder 'json' (maschinenlesbar).",
    )


@mcp.tool(
    name="search_stadtratsbeschluesse",
    annotations={
        "title": "Stadtratsbeschlüsse durchsuchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def search_stadtratsbeschluesse(params: SearchSTRBInput) -> str:
    """Durchsucht die öffentlichen Stadtratsbeschlüsse (STRB) der Stadt Zürich per Volltext.

    Nutzt den CKAN Datastore SQL-Endpoint für flexible ILIKE-Suche im Beschlusstitel
    mit optionalen Filtern nach Departement und/oder Datumsbereich.

    Datenverfügbarkeit: öffentliche Beschlüsse ab Februar 2025, laufend aktualisiert.
    Lizenz: CC0 (gemeinfrei, keine Einschränkungen).

    Args:
        params (SearchSTRBInput): Suchparameter mit:
            - query (str): Suchbegriff im Titel (Pflicht)
            - departement (Optional[str]): Kürzel oder Teilname, z.B. 'SSD', 'FD'
            - datum_von (Optional[str]): Frühestes Datum YYYY-MM-DD
            - datum_bis (Optional[str]): Spätestes Datum YYYY-MM-DD
            - limit (int): Max. Ergebnisse (Standard: 20)
            - format (str): 'markdown' oder 'json'

    Returns:
        str: Formatierte Liste der Beschlüsse. Jeder Eintrag enthält:
            - beschlussnummer: z.B. '1203/2025'
            - titel: Vollständiger Beschlusstitel
            - datum: ISO-Datum des Beschlusses
            - departement: Federführendes Departement (mit Kürzel)
            - link: Direktlink auf stadt-zuerich.ch
    """
    try:
        where = _strb_where_clause(
            query=params.query,
            departement=params.departement,
            datum_von=params.datum_von,
            datum_bis=params.datum_bis,
        )
        records, total = await _strb_query(where, params.limit)

        if not records:
            return (
                f"Keine Stadtratsbeschlüsse gefunden für: '{params.query}'"
                + (f", Departement: '{params.departement}'" if params.departement else "")
                + (f", Zeitraum: {params.datum_von or '?'} – {params.datum_bis or '?'}"
                   if params.datum_von or params.datum_bis else "")
                + "\n\nHinweis: Das Archiv enthält öffentliche Beschlüsse ab Februar 2025."
            )

        if params.format == "json":
            return json.dumps(
                {
                    "query": params.query,
                    "total": total,
                    "count": len(records),
                    "beschluesse": [_format_strb_record(r) for r in records],
                },
                indent=2,
                ensure_ascii=False,
            )

        return _format_strb_markdown(records, total, f"Stadtratsbeschlüsse: «{params.query}»")

    except Exception as e:
        return handle_api_error(e, "Stadtratsbeschlüsse-Suche")


class BeschluesseDepartementInput(BaseModel):
    """Input für Beschlüsse-Abfrage nach Departement."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    departement: str = Field(
        ...,
        description=(
            "Kürzel oder Name des Departements. Beispiele: "
            "'SSD' → Schul- und Sportdepartement, "
            "'FD' → Finanzdepartement, "
            "'PRD' → Präsidialdepartement, "
            "'TED' → Tiefbau- und Entsorgungsdepartement, "
            "'HBD' → Hochbaudepartement, "
            "'GUD' → Gesundheits- und Umweltdepartement, "
            "'SID' → Sicherheitsdepartement, "
            "'SD' → Sozialdepartement, "
            "'SKZ' → Stadtkanzlei, "
            "'DIB' → Departement der Industriellen Betriebe, "
            "'RK' → Rechtskonsulent."
        ),
        min_length=2,
        max_length=100,
    )
    datum_von: str | None = Field(
        default=None,
        description="Frühestes Beschlussdatum (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    datum_bis: str | None = Field(
        default=None,
        description="Spätestes Beschlussdatum (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    limit: int = Field(
        default=50,
        description="Max. Anzahl zurückgegebener Beschlüsse (Standard: 50, max. 200).",
        ge=1,
        le=200,
    )
    format: OutputFormat = Field(
        default="markdown",
        description="Ausgabeformat: 'markdown' oder 'json'.",
    )


@mcp.tool(
    name="get_beschluesse_by_departement",
    annotations={
        "title": "STRB nach Departement abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def get_beschluesse_by_departement(params: BeschluesseDepartementInput) -> str:
    """Gibt alle öffentlichen Stadtratsbeschlüsse eines Departements zurück.

    Ideal für institutionelle Analysen, z.B. alle Beschlüsse des Schul- und
    Sportdepartements (SSD) in einem bestimmten Quartal oder Jahr.

    Args:
        params (BeschluesseDepartementInput): Parameter mit:
            - departement (str): Kürzel oder Name, z.B. 'SSD' (Pflicht)
            - datum_von (Optional[str]): Frühestes Datum YYYY-MM-DD
            - datum_bis (Optional[str]): Spätestes Datum YYYY-MM-DD
            - limit (int): Max. Ergebnisse (Standard: 50)
            - format (str): 'markdown' oder 'json'

    Returns:
        str: Liste aller Beschlüsse des Departements. Jeder Eintrag enthält:
            - beschlussnummer, titel, datum, departement, link
    """
    try:
        where = _strb_where_clause(
            departement=params.departement,
            datum_von=params.datum_von,
            datum_bis=params.datum_bis,
        )
        records, total = await _strb_query(where, params.limit)

        if not records:
            return (
                f"Keine Stadtratsbeschlüsse für Departement '{params.departement}' gefunden.\n\n"
                f"Verfügbare Departemente:\n"
                + "\n".join(f"- {d}" for d in STRB_DEPARTEMENTE)
            )

        if params.format == "json":
            return json.dumps(
                {
                    "departement_filter": params.departement,
                    "total": total,
                    "count": len(records),
                    "beschluesse": [_format_strb_record(r) for r in records],
                },
                indent=2,
                ensure_ascii=False,
            )

        return _format_strb_markdown(records, total, f"STRB – Departement: {params.departement}")

    except Exception as e:
        return handle_api_error(e, "STRB Departement-Abfrage")


class GetSTRBDetailInput(BaseModel):
    """Input für den Abruf eines einzelnen Stadtratsbeschlusses."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    beschlussnummer: str = Field(
        ...,
        description=(
            "Beschlussnummer im Format 'NNNN/JJJJ', z.B. '1203/2025' oder '472/2026'. "
            "Die Nummer steht im Titel des Beschlussdokuments."
        ),
        min_length=5,
        max_length=20,
        pattern=r"^\d+/\d{4}$",
    )


@mcp.tool(
    name="get_stadtratsbeschluss_detail",
    annotations={
        "title": "Einzelnen Stadtratsbeschluss abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def get_stadtratsbeschluss_detail(params: GetSTRBDetailInput) -> str:
    """Gibt die Metadaten eines einzelnen Stadtratsbeschlusses anhand der Beschlussnummer zurück.

    Liefert Titel, Datum, Departement und den direkten Link zum vollständigen
    Beschluss auf der offiziellen Website der Stadt Zürich (stadt-zuerich.ch).

    Args:
        params (GetSTRBDetailInput): Parameter mit:
            - beschlussnummer (str): Nummer im Format 'NNNN/JJJJ' (z.B. '1203/2025')

    Returns:
        str: Markdown-Detailansicht mit beschlussnummer, titel, datum, departement, link.
             Fehlermeldung wenn Beschluss nicht gefunden oder ausserhalb des Archivs (vor Feb 2025).
    """
    try:
        result = await ckan_request(
            "datastore_search",
            {
                "resource_id": STRB_RESOURCE_ID,
                "filters": {"Beschlussnummer": params.beschlussnummer},
                "limit": 1,
            },
        )
        records = result.get("records", [])

        if not records:
            return (
                f"Stadtratsbeschluss '{params.beschlussnummer}' nicht gefunden.\n\n"
                f"Mögliche Gründe:\n"
                f"- Das Archiv enthält öffentliche Beschlüsse ab Februar 2025\n"
                f"- Format prüfen: NNNN/JJJJ (z.B. '1203/2025')\n"
                f"- Nicht-öffentliche Beschlüsse sind nicht im Datensatz enthalten"
            )

        r = _format_strb_record(records[0])
        return "\n".join([
            f"## Stadtratsbeschluss {r['beschlussnummer']}",
            "",
            f"**Titel:** {r['titel']}",
            f"**Datum:** {r['datum']}",
            f"**Departement:** {r['departement']}",
            f"**Link:** {r['link']}",
        ])

    except Exception as e:
        return handle_api_error(e, f"STRB-Detail {params.beschlussnummer}")

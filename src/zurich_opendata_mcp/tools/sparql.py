"""SPARQL tool (currently disabled — endpoint not in production)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..clients.sparql import sparql_query
from ..config import SPARQL_URL
from ..formatters import handle_api_error


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
    """⚠️ NICHT PRODUKTIV – Der Linked-Data-Endpunkt (ld.stadt-zuerich.ch) ist
    noch nicht mit echten Daten befüllt. Abfragen liefern leere oder
    unvollständige Ergebnisse. Bitte stattdessen zurich_search_datasets oder
    zurich_datastore_query/zurich_datastore_sql verwenden.

    Returns:
        Hinweis auf nicht-produktiven Endpunkt
    """
    return (
        "⚠️ **SPARQL-Endpunkt nicht produktiv**\n\n"
        f"Der Linked-Data-Endpunkt (`{SPARQL_URL}`) ist derzeit noch nicht "
        "mit echten Daten befüllt. Abfragen liefern leere oder unvollständige Ergebnisse.\n\n"
        "**Alternativen:**\n"
        "- `zurich_search_datasets` – Datensätze suchen\n"
        "- `zurich_datastore_query` – Tabellarische Daten per Resource-UUID abfragen\n"
        "- `zurich_datastore_sql` – SQL-Abfragen auf DataStore-Ressourcen"
    )
    # ── Original-Implementation (deaktiviert bis Endpunkt produktiv) ──
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

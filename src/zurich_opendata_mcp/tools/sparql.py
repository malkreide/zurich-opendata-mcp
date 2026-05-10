"""SPARQL tool — currently disabled.

The Linked-Data endpoint at ``ld.stadt-zuerich.ch`` is reachable but not yet
populated with productive data. The tool is kept registered (so existing
clients keep discovering it) but always returns a static notice. When the
endpoint goes live, restore the implementation from git history (pre-Phase-3)
and flip ``idempotentHint`` back to ``False``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import SPARQL_URL


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
        "idempotentHint": True,
        "openWorldHint": False,
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

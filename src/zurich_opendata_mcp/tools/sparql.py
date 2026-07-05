"""SPARQL tool — opt-in via environment flag, endpoint not productive yet.

The Linked-Data endpoint at ``ld.stadt-zuerich.ch`` is reachable but not yet
populated with productive data, so the tool only returns a static notice. To
stop it from occupying tool-list context (and inviting useless calls) in
every MCP client, it is no longer registered by default: set
``ZURICH_OPENDATA_ENABLE_SPARQL=1`` to register it. When the endpoint goes
live, restore the implementation from git history (pre-Phase-3), flip
``idempotentHint`` back to ``False`` and register it unconditionally again.
"""

from __future__ import annotations

import os

from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import SPARQL_URL


def sparql_enabled() -> bool:
    """True when the opt-in flag for the (non-productive) SPARQL tool is set."""
    return os.environ.get("ZURICH_OPENDATA_ENABLE_SPARQL", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


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


def register_sparql_tool() -> bool:
    """Register ``zurich_sparql`` on the shared FastMCP instance if enabled.

    Split out of import time so tests can exercise both paths regardless of
    the environment the suite runs in. Returns whether it registered.
    """
    if not sparql_enabled():
        return False
    mcp.tool(
        name="zurich_sparql",
        annotations=ToolAnnotations(
            title="SPARQL-Abfrage (Linked Data)",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )(zurich_sparql)
    return True


register_sparql_tool()

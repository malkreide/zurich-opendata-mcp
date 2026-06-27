"""respx-backed unit tests for tools/strb.py (audit M-7).

The SQL-escape and WHERE-clause builders are unit-tested in test_server.py;
these cover the HTTP round-trip and rendering (markdown + json) for all three
STRB tools, including the data/count two-query split in `_strb_query`.
"""

from __future__ import annotations

import json

import httpx
import respx

from zurich_opendata_mcp.config import CKAN_API_URL
from zurich_opendata_mcp.tools.strb import (
    BeschluesseDepartementInput,
    GetSTRBDetailInput,
    SearchSTRBInput,
    get_beschluesse_by_departement,
    get_stadtratsbeschluss_detail,
    search_stadtratsbeschluesse,
)

_SQL = f"{CKAN_API_URL}/datastore_search_sql"
_SEARCH = f"{CKAN_API_URL}/datastore_search"

_REC = {
    "Titel": "Tagesschule 2025 Ausbau",
    "Beschlussnummer": "1203/2025",
    "Beschlussdatum": "2025-03-14",
    "Federfuhrendes Departement": "Schul- und Sportdepartement (SSD)",
    "Link": "https://stadt-zuerich.ch/strb/1203-2025",
}


def _ckan(result: dict) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "result": result})


def _sql_side_effect(records: list[dict], total: int):
    """Route the data query and the COUNT(*) query to different payloads."""

    def handler(request: httpx.Request) -> httpx.Response:
        sql = dict(request.url.params)["sql"]
        if "COUNT(*)" in sql:
            return _ckan({"records": [{"cnt": total}]})
        return _ckan({"records": records})

    return handler


# ─── search_stadtratsbeschluesse ─────────────────────────────────────────────


@respx.mock
async def test_strb_search_markdown():
    respx.get(_SQL).mock(side_effect=_sql_side_effect([_REC], total=5))

    result = await search_stadtratsbeschluesse(SearchSTRBInput(query="Tagesschule"))

    assert "## Stadtratsbeschlüsse: «Tagesschule»" in result
    assert "**5 Beschlüsse** gefunden (zeige 1)" in result
    assert "### [1203/2025] Tagesschule 2025 Ausbau" in result
    assert "Schul- und Sportdepartement (SSD)" in result
    assert "https://stadt-zuerich.ch/strb/1203-2025" in result


@respx.mock
async def test_strb_search_json_format():
    respx.get(_SQL).mock(side_effect=_sql_side_effect([_REC], total=1))

    result = await search_stadtratsbeschluesse(
        SearchSTRBInput(query="Tagesschule", format="json")
    )

    payload = json.loads(result)
    assert payload["query"] == "Tagesschule"
    assert payload["total"] == 1
    assert payload["beschluesse"][0]["beschlussnummer"] == "1203/2025"
    assert payload["beschluesse"][0]["departement"] == (
        "Schul- und Sportdepartement (SSD)"
    )


@respx.mock
async def test_strb_search_empty():
    respx.get(_SQL).mock(side_effect=_sql_side_effect([], total=0))

    result = await search_stadtratsbeschluesse(SearchSTRBInput(query="nichts"))

    assert "Keine Stadtratsbeschlüsse gefunden für: 'nichts'" in result
    assert "ab Februar 2025" in result


@respx.mock
async def test_strb_search_http_error():
    respx.get(_SQL).mock(return_value=httpx.Response(500))

    result = await search_stadtratsbeschluesse(SearchSTRBInput(query="x"))

    assert "Fehler bei Stadtratsbeschlüsse-Suche" in result


# ─── get_beschluesse_by_departement ──────────────────────────────────────────


@respx.mock
async def test_strb_by_departement_markdown():
    respx.get(_SQL).mock(side_effect=_sql_side_effect([_REC], total=1))

    result = await get_beschluesse_by_departement(
        BeschluesseDepartementInput(departement="SSD")
    )

    assert "## STRB – Departement: SSD" in result
    assert "[1203/2025]" in result


@respx.mock
async def test_strb_by_departement_json_format():
    respx.get(_SQL).mock(side_effect=_sql_side_effect([_REC], total=2))

    result = await get_beschluesse_by_departement(
        BeschluesseDepartementInput(departement="SSD", format="json")
    )

    payload = json.loads(result)
    assert payload["departement_filter"] == "SSD"
    assert payload["total"] == 2
    assert payload["beschluesse"][0]["beschlussnummer"] == "1203/2025"


@respx.mock
async def test_strb_by_departement_http_error():
    respx.get(_SQL).mock(return_value=httpx.Response(500))

    result = await get_beschluesse_by_departement(
        BeschluesseDepartementInput(departement="SSD")
    )

    assert "Fehler bei STRB Departement-Abfrage" in result


@respx.mock
async def test_strb_by_departement_empty_lists_departments():
    respx.get(_SQL).mock(side_effect=_sql_side_effect([], total=0))

    result = await get_beschluesse_by_departement(
        BeschluesseDepartementInput(departement="ZZ")
    )

    assert "Keine Stadtratsbeschlüsse für Departement 'ZZ'" in result
    # Falls back to listing the known departments.
    assert "Finanzdepartement (FD)" in result


# ─── get_stadtratsbeschluss_detail ───────────────────────────────────────────


@respx.mock
async def test_strb_detail_found():
    route = respx.get(_SEARCH).mock(return_value=_ckan({"records": [_REC]}))

    result = await get_stadtratsbeschluss_detail(
        GetSTRBDetailInput(beschlussnummer="1203/2025")
    )

    # The exact beschlussnummer is filtered server-side.
    assert "1203/2025" in dict(route.calls[0].request.url.params)["filters"]
    assert "## Stadtratsbeschluss 1203/2025" in result
    assert "**Titel:** Tagesschule 2025 Ausbau" in result
    assert "**Departement:** Schul- und Sportdepartement (SSD)" in result


@respx.mock
async def test_strb_detail_not_found():
    respx.get(_SEARCH).mock(return_value=_ckan({"records": []}))

    result = await get_stadtratsbeschluss_detail(
        GetSTRBDetailInput(beschlussnummer="9999/2025")
    )

    assert "'9999/2025' nicht gefunden" in result


@respx.mock
async def test_strb_detail_http_error():
    respx.get(_SEARCH).mock(return_value=httpx.Response(500))

    result = await get_stadtratsbeschluss_detail(
        GetSTRBDetailInput(beschlussnummer="1203/2025")
    )

    assert "Fehler bei STRB-Detail 1203/2025" in result

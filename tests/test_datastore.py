"""respx-backed unit tests for tools/datastore.py (audit M-7).

The SELECT-only gate (`_validate_select_only`) is covered by the unit tests
in test_server.py; these cover the HTTP round-trip and rendering for both
`zurich_datastore_query` and `zurich_datastore_sql`.
"""

from __future__ import annotations

import httpx
import respx
from fixture_data import fixture_json

from zurich_opendata_mcp.config import CKAN_API_URL
from zurich_opendata_mcp.tools.datastore import (
    DatastoreQueryInput,
    DatastoreSqlInput,
    zurich_datastore_query,
    zurich_datastore_sql,
)

_SEARCH = f"{CKAN_API_URL}/datastore_search"
_SQL = f"{CKAN_API_URL}/datastore_search_sql"


def _ckan(result: dict) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "result": result})


# ─── datastore_query ─────────────────────────────────────────────────────────


@respx.mock
async def test_datastore_query_renders_and_passes_params():
    route = respx.get(_SEARCH).mock(
        return_value=_ckan(
            {
                "total": 50,
                "fields": [
                    {"id": "_id", "type": "int"},
                    {"id": "Quartier", "type": "text"},
                    {"id": "Jahr", "type": "int"},
                ],
                "records": [{"_id": 1, "Quartier": "Wiedikon", "Jahr": 2024}],
            }
        )
    )

    result = await zurich_datastore_query(
        DatastoreQueryInput(
            resource_id="abc-uuid",
            filters='{"Quartier": "Wiedikon"}',
            query="schule",
            sort="Jahr desc",
            limit=20,
            offset=0,
        )
    )

    sent = dict(route.calls[0].request.url.params)
    assert sent["resource_id"] == "abc-uuid"
    assert sent["filters"] == '{"Quartier": "Wiedikon"}'
    assert sent["q"] == "schule"
    assert sent["sort"] == "Jahr desc"

    assert "## DataStore-Abfrage: 50 Einträge" in result
    # _id is dropped from the field listing.
    assert "`Quartier` (text)" in result
    assert "`_id`" not in result
    assert '"Quartier": "Wiedikon"' in result
    # total (50) > offset(0)+records(1) → pagination hint.
    assert "offset=1" in result


@respx.mock
async def test_datastore_query_invalid_filters_no_http_call():
    route = respx.get(_SEARCH).mock(return_value=_ckan({"total": 0, "records": []}))

    result = await zurich_datastore_query(
        DatastoreQueryInput(resource_id="abc", filters="not-json")
    )

    assert not route.called  # rejected before any request
    assert "muss gültiges JSON sein" in result


@respx.mock
async def test_datastore_query_empty():
    respx.get(_SEARCH).mock(return_value=_ckan({"total": 0, "records": [], "fields": []}))

    result = await zurich_datastore_query(DatastoreQueryInput(resource_id="abc"))

    assert "Keine Daten gefunden." == result


@respx.mock
async def test_datastore_query_http_error():
    respx.get(_SEARCH).mock(return_value=httpx.Response(404))

    result = await zurich_datastore_query(DatastoreQueryInput(resource_id="abc"))

    assert "Fehler bei DataStore-Abfrage" in result


# ─── datastore_sql ───────────────────────────────────────────────────────────


@respx.mock
async def test_datastore_sql_renders_rows():
    route = respx.get(_SQL).mock(
        return_value=_ckan(
            {
                "fields": [
                    {"id": "_id", "type": "int"},
                    {"id": "Jahr", "type": "int"},
                    {"id": "Anzahl", "type": "int"},
                ],
                "records": [{"_id": 1, "Jahr": 2024, "Anzahl": 7}],
            }
        )
    )

    result = await zurich_datastore_sql(
        DatastoreSqlInput(sql='SELECT "Jahr", "Anzahl" FROM "abc" LIMIT 1')
    )

    assert dict(route.calls[0].request.url.params)["sql"].startswith("SELECT")
    assert "## SQL-Ergebnis: 1 Zeilen" in result
    assert "**Spalten**: Jahr, Anzahl" in result
    assert '"Anzahl": 7' in result


async def test_datastore_sql_rejects_non_select_without_http():
    # respx with no routes: any HTTP call would raise, so this also proves
    # the gate short-circuits before the request.
    with respx.mock:
        result = await zurich_datastore_sql(DatastoreSqlInput(sql='DROP TABLE "abc"'))

    assert "Nur SELECT" in result


@respx.mock
async def test_datastore_sql_drops_ckans_full_text_index():
    """Against a recorded `SELECT *` (tests/fixtures/ckan_datastore_sql.json):
    CKAN returns its tsvector index `_full_text` as a column and in every
    row. It reaches neither the column list nor the records."""
    recorded = fixture_json("ckan_datastore_sql")
    assert "_full_text" in recorded["records"][0], "the recording must carry it"
    respx.get(_SQL).mock(return_value=_ckan(recorded))

    result = await zurich_datastore_sql(DatastoreSqlInput(sql=recorded["sql"]))

    assert "**Spalten**: Datum, Standort, Parameter, Intervall, Einheit, Wert, Status" in result
    assert "_full_text" not in result
    assert recorded["records"][0]["_full_text"] not in result
    assert f'"Standort": "{recorded["records"][0]["Standort"]}"' in result
    assert '"_id": ' in result  # only the column list drops `_id`, as before


@respx.mock
async def test_datastore_sql_keeps_a_column_the_caller_named_full_text():
    """Only CKAN's index goes, told apart by its type. The response below is
    what CKAN returned live on 2026-10-15 for
    `SELECT COUNT(*) AS "_full_text", MAX("Wert") AS "x" FROM <air quality>`:
    the same name, typed int8 — a column the caller asked for."""
    respx.get(_SQL).mock(
        return_value=_ckan(
            {
                "fields": [{"id": "_full_text", "type": "int8"}, {"id": "x", "type": "text"}],
                "records": [{"_full_text": 165432, "x": "NA"}],
            }
        )
    )

    result = await zurich_datastore_sql(
        DatastoreSqlInput(sql='SELECT COUNT(*) AS "_full_text", MAX("Wert") AS "x" FROM t')
    )

    assert "**Spalten**: _full_text, x" in result
    assert '"_full_text": 165432' in result


@respx.mock
async def test_datastore_sql_empty_result():
    respx.get(_SQL).mock(return_value=_ckan({"fields": [], "records": []}))

    result = await zurich_datastore_sql(DatastoreSqlInput(sql='SELECT * FROM "abc" WHERE 1=0'))

    assert "keine Ergebnisse" in result


@respx.mock
async def test_datastore_sql_http_error():
    respx.get(_SQL).mock(return_value=httpx.Response(500))

    result = await zurich_datastore_sql(DatastoreSqlInput(sql='SELECT * FROM "abc"'))

    assert "Fehler bei SQL-Abfrage" in result

"""
Tests for Zurich Open Data MCP Server.

API-hitting tests are marked as 'live'.
Run all tests:           PYTHONPATH=src pytest tests/ -m live
Run only non-live (CI):  PYTHONPATH=src pytest tests/ -m "not live"
"""

import pytest

import zurich_opendata_mcp.server as server_module
from zurich_opendata_mcp.server import (
    AirQualityInput,
    AnalyzeDatasetInput,
    FindSchoolDataInput,
    GeoFeaturesInput,
    GetDatasetInput,
    ListGroupInput,
    ParliamentMembersInput,
    ParliamentSearchInput,
    PedestrianInput,
    SearchDatasetsInput,
    SparqlQueryInput,
    TagSearchInput,
    TourismSearchInput,
    VBZPassengersInput,
    WaterWeatherInput,
    WeatherLiveInput,
    zurich_air_quality,
    zurich_analyze_datasets,
    zurich_catalog_stats,
    zurich_find_school_data,
    zurich_geo_features,
    zurich_geo_layers,
    zurich_get_dataset,
    zurich_list_categories,
    zurich_list_tags,
    zurich_parking_live,
    zurich_parliament_members,
    zurich_parliament_search,
    zurich_pedestrian_traffic,
    zurich_search_datasets,
    zurich_sparql,
    zurich_tourism,
    zurich_vbz_passengers,
    zurich_water_weather,
    zurich_weather_live,
)

# ─── Smoke tests (no network) ────────────────────────────────────────────────


def test_server_module_exposes_mcp_instance():
    """Importing the package and instantiating FastMCP must succeed offline."""
    assert hasattr(server_module, "mcp")
    assert server_module.mcp.name


# ─── CKAN Tools ──────────────────────────────────────────────────────────────


@pytest.mark.live
async def test_search_datasets():
    result = await zurich_search_datasets(SearchDatasetsInput(query="Schule", rows=3))
    assert "Datensätze" in result
    assert "Schul" in result


@pytest.mark.live
async def test_get_dataset():
    result = await zurich_get_dataset(GetDatasetInput(dataset_id="ssd_schulferien"))
    assert "Ferien" in result or "Schulferien" in result


@pytest.mark.live
async def test_list_categories_all():
    result = await zurich_list_categories(ListGroupInput())
    assert "Bildung" in result


@pytest.mark.live
async def test_list_categories_bildung():
    result = await zurich_list_categories(ListGroupInput(group_id="bildung"))
    assert "Bildung" in result


@pytest.mark.live
async def test_list_tags():
    result = await zurich_list_tags(TagSearchInput(query="schul"))
    assert "schul" in result.lower()


# ─── Real-Time Tools ────────────────────────────────────────────────────────


@pytest.mark.live
async def test_parking_live():
    result = await zurich_parking_live()
    assert "Parkhaus" in result or "Parkplatz" in result


@pytest.mark.live
async def test_weather_live():
    result = await zurich_weather_live(WeatherLiveInput(parameter="T", limit=5))
    assert "°C" in result
    assert "Fehler" not in result


@pytest.mark.live
async def test_air_quality():
    result = await zurich_air_quality(AirQualityInput(limit=10))
    assert "Luftqualität" in result
    assert "Fehler" not in result


@pytest.mark.live
async def test_water_weather():
    result = await zurich_water_weather(WaterWeatherInput(station="tiefenbrunnen", limit=2))
    assert "Wassertemperatur" in result
    assert "Fehler" not in result


@pytest.mark.live
async def test_pedestrian_traffic():
    result = await zurich_pedestrian_traffic(PedestrianInput(limit=5))
    assert "Passanten" in result or "Bahnhofstrasse" in result
    assert "Fehler" not in result


@pytest.mark.live
async def test_vbz_passengers():
    result = await zurich_vbz_passengers(VBZPassengersInput(limit=5))
    assert "VBZ" in result
    assert "Fehler" not in result


# ─── Geodata Tools ───────────────────────────────────────────────────────────


@pytest.mark.live
async def test_geo_layers():
    result = await zurich_geo_layers()
    assert "schulanlagen" in result
    assert "stadtkreise" in result


@pytest.mark.live
async def test_geo_features():
    result = await zurich_geo_features(GeoFeaturesInput(layer_id="schulanlagen", max_features=5))
    assert "Feature" in result or "Schulanlage" in result or "Koordinaten" in result


# ─── Parliament Tools ───────────────────────────────────────────────────────


@pytest.mark.live
async def test_parliament_search():
    result = await zurich_parliament_search(ParliamentSearchInput(query="Schule", max_results=5))
    assert "Schul" in result or "GR Nr" in result or "Treffer" in result


@pytest.mark.live
async def test_parliament_members():
    result = await zurich_parliament_members(ParliamentMembersInput(active_only=True))
    assert "Mitglied" in result or "Partei" in result or "Mandat" in result or "Gemeinderat" in result


# ─── Tourism & SPARQL ────────────────────────────────────────────────────────


@pytest.mark.live
async def test_tourism():
    result = await zurich_tourism(TourismSearchInput(category="restaurants", language="de"))
    assert "Zürich" in result or "Restaurant" in result or "Tourismus" in result


@pytest.mark.live
async def test_sparql():
    result = await zurich_sparql(SparqlQueryInput(query="SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"))
    assert "nicht produktiv" in result


# ─── Analysis Tools ──────────────────────────────────────────────────────────


@pytest.mark.live
async def test_analyze_datasets():
    result = await zurich_analyze_datasets(
        AnalyzeDatasetInput(query="Verkehr", max_datasets=3, include_structure=True)
    )
    assert "Analyse" in result


@pytest.mark.live
async def test_catalog_stats():
    result = await zurich_catalog_stats()
    assert "Katalog" in result


@pytest.mark.live
async def test_find_school_data():
    result = await zurich_find_school_data(FindSchoolDataInput())
    assert "Schulamt" in result or "Schul" in result


# ─── Schema / Validation Tests (no live API) ─────────────────────────────────


def test_search_datasets_input_defaults():
    params = SearchDatasetsInput(query="Schule")
    assert params.rows == 10
    assert params.offset == 0
    assert params.sort is None
    assert params.filter_group is None


def test_search_datasets_input_rejects_empty_query():
    with pytest.raises(ValueError):
        SearchDatasetsInput(query="")


def test_search_datasets_input_rejects_out_of_range_rows():
    with pytest.raises(ValueError):
        SearchDatasetsInput(query="x", rows=100)
    with pytest.raises(ValueError):
        SearchDatasetsInput(query="x", rows=0)


def test_get_dataset_input_strips_whitespace():
    params = GetDatasetInput(dataset_id="  ssd_schulferien  ")
    assert params.dataset_id == "ssd_schulferien"


def test_get_dataset_input_rejects_empty_id():
    with pytest.raises(ValueError):
        GetDatasetInput(dataset_id="")


def test_mcp_server_exposes_tools():
    """Smoke-Test: Server-Modul importierbar und MCP-Instanz vorhanden."""
    from zurich_opendata_mcp.server import mcp

    assert mcp is not None
    assert mcp.name


# ─── STRB SQL injection regression (no live API) ─────────────────────────────


def test_sql_escape_doubles_single_quotes():
    from zurich_opendata_mcp.tools.strb import _sql_escape

    assert _sql_escape("foo") == "foo"
    assert _sql_escape("o'brien") == "o''brien"
    assert _sql_escape("' OR 1=1 --") == "'' OR 1=1 --"
    assert _sql_escape("a\\b") == "a\\\\b"
    assert _sql_escape("a\\'b") == "a\\\\''b"


def test_strb_where_clause_neutralises_quote_injection():
    """The classic 'close-the-string' payload must end up inside the literal,
    not break out of it. The doubled quote ('') is a single literal apostrophe
    in PostgreSQL, so the whole payload is searched verbatim and returns zero
    rows — instead of the bare ' breaking out of the ILIKE pattern and
    appending a tautology."""
    from zurich_opendata_mcp.tools.strb import _strb_where_clause

    payload = "x%' OR 1=1 OR '%"
    where = _strb_where_clause(query=payload)

    # Exactly one ILIKE comparison — no extra clauses leaked into the WHERE.
    assert where.count(" ILIKE ") == 1
    assert " AND " not in where
    # Every single quote from the payload is doubled.
    assert where == "\"Titel\" ILIKE '%x%'' OR 1=1 OR ''%%'"


def test_strb_where_clause_neutralises_departement_injection():
    from zurich_opendata_mcp.tools.strb import _strb_where_clause

    where = _strb_where_clause(departement="SSD' UNION SELECT 1,2,3 --")
    # No second predicate appended.
    assert where.count(" ILIKE ") == 1
    assert " AND " not in where
    # Payload sits inside the literal with the quote doubled.
    assert where == (
        "\"Federfuhrendes Departement\" ILIKE "
        "'%SSD'' UNION SELECT 1,2,3 --%'"
    )


def test_strb_where_clause_dates_pass_through_unescaped():
    """Dates are regex-validated upstream (Pydantic ^\\d{4}-\\d{2}-\\d{2}$) so
    they cannot contain quotes; the WHERE clause uses them verbatim."""
    from zurich_opendata_mcp.tools.strb import _strb_where_clause

    where = _strb_where_clause(datum_von="2025-01-01", datum_bis="2025-12-31")
    assert where == (
        "\"Beschlussdatum\" >= '2025-01-01' AND "
        "\"Beschlussdatum\" <= '2025-12-31'"
    )


def test_strb_where_clause_combines_conditions_with_and():
    from zurich_opendata_mcp.tools.strb import _strb_where_clause

    where = _strb_where_clause(query="Volksschule", departement="SSD", datum_von="2025-02-01")
    assert where.count(" AND ") == 2
    assert "Volksschule" in where
    assert "SSD" in where
    assert "2025-02-01" in where


def test_strb_where_clause_empty_returns_true():
    from zurich_opendata_mcp.tools.strb import _strb_where_clause

    assert _strb_where_clause() == "TRUE"


# ─── Markdown cell escaping (audit M-6) ──────────────────────────────────────


def test_md_cell_escapes_pipe_and_newline():
    from zurich_opendata_mcp.formatters import md_cell

    assert md_cell("plain") == "plain"
    assert md_cell("a|b") == "a\\|b"
    assert md_cell("line1\nline2") == "line1 line2"
    assert md_cell("line1\r\nline2") == "line1 line2"
    assert md_cell("a\\b") == "a\\\\b"
    # Stringifies non-strings.
    assert md_cell(42) == "42"
    assert md_cell(None) == "None"


def test_md_cell_handles_real_world_breaks():
    """Parking-lot names like 'Parkhaus | City' must not split the column."""
    from zurich_opendata_mcp.formatters import md_cell

    cell = md_cell("Parkhaus | City\nUntergeschoss")
    assert "|" not in cell.replace("\\|", "")  # only escaped pipes survive
    assert "\n" not in cell


# ─── USER_AGENT format (audit M-1, L-4) ──────────────────────────────────────


def test_user_agent_uses_real_repo_url():
    from zurich_opendata_mcp.config import USER_AGENT

    assert "schulamt-zurich" not in USER_AGENT
    assert "github.com/malkreide/zurich-opendata-mcp" in USER_AGENT
    assert USER_AGENT.startswith("ZurichOpenDataMCP/")


def test_user_agent_version_matches_package():
    """USER_AGENT version is sourced from importlib.metadata, not hard-coded."""
    from importlib.metadata import PackageNotFoundError, version

    from zurich_opendata_mcp.config import USER_AGENT

    try:
        expected = version("zurich-opendata-mcp")
    except PackageNotFoundError:
        expected = "0.0.0+local"
    assert f"ZurichOpenDataMCP/{expected}" in USER_AGENT


# ─── SPARQL tool is now constant (audit M-4) ─────────────────────────────────


async def test_sparql_returns_disabled_notice_without_calling_endpoint():
    from zurich_opendata_mcp.tools.sparql import SparqlQueryInput, zurich_sparql

    result = await zurich_sparql(
        SparqlQueryInput(query="SELECT * WHERE { ?s ?p ?o } LIMIT 1")
    )
    assert "nicht produktiv" in result
    # The disabled notice should always cite the alternatives.
    assert "zurich_search_datasets" in result
    assert "zurich_datastore_query" in result


# ─── datastore_sql SELECT-only gate (audit M-8) ──────────────────────────────


def test_select_gate_accepts_plain_select():
    from zurich_opendata_mcp.tools.datastore import _validate_select_only

    assert _validate_select_only('SELECT * FROM "abc" LIMIT 10') is None
    assert _validate_select_only("  select 1  ") is None  # leading ws + lowercase


def test_select_gate_accepts_cte_with_clause():
    from zurich_opendata_mcp.tools.datastore import _validate_select_only

    assert _validate_select_only(
        'WITH counts AS (SELECT "Jahr" AS y, COUNT(*) AS c FROM "abc" GROUP BY 1) '
        "SELECT * FROM counts ORDER BY c DESC"
    ) is None


def test_select_gate_rejects_stacked_statements():
    from zurich_opendata_mcp.tools.datastore import _validate_select_only

    err = _validate_select_only("SELECT 1; DROP TABLE foo")
    assert err is not None
    assert "einzelne Statements" in err


def test_select_gate_rejects_drop():
    from zurich_opendata_mcp.tools.datastore import _validate_select_only

    err = _validate_select_only('DROP TABLE "abc"')
    assert err is not None
    assert "Nur SELECT" in err


def test_select_gate_rejects_insert_update_delete():
    from zurich_opendata_mcp.tools.datastore import _validate_select_only

    for stmt in [
        'INSERT INTO "abc" VALUES (1)',
        'UPDATE "abc" SET x = 1',
        'DELETE FROM "abc"',
    ]:
        err = _validate_select_only(stmt)
        assert err is not None, f"should have rejected: {stmt}"


def test_select_gate_rejects_empty():
    from zurich_opendata_mcp.tools.datastore import _validate_select_only

    err = _validate_select_only("   ")
    assert err is not None
    assert "leer" in err


# ─── analyze_datasets parallelism (audit M-5) ────────────────────────────────


# ─── Pydantic Literals — drift + rejection (audit L-9..L-13, M-?) ────────────


def test_literal_zurich_group_matches_runtime_list():
    from typing import get_args

    from zurich_opendata_mcp.config import ZURICH_GROUPS, ZurichGroup

    assert set(get_args(ZurichGroup)) == set(ZURICH_GROUPS), (
        "ZurichGroup Literal drifted from ZURICH_GROUPS — keep them in sync."
    )


def test_literal_geo_layer_id_matches_runtime_dict():
    from typing import get_args

    from zurich_opendata_mcp.config import GEOPORTAL_LAYERS, GeoLayerId

    assert set(get_args(GeoLayerId)) == set(GEOPORTAL_LAYERS.keys()), (
        "GeoLayerId Literal drifted from GEOPORTAL_LAYERS — keep them in sync."
    )


def test_search_datasets_filter_group_rejects_unknown():
    from zurich_opendata_mcp.tools.catalog import SearchDatasetsInput

    SearchDatasetsInput(query="x", filter_group="bildung")  # ok
    with pytest.raises(ValueError):
        SearchDatasetsInput(query="x", filter_group="not-a-group")


def test_geo_features_layer_id_rejects_unknown():
    from zurich_opendata_mcp.tools.geo import GeoFeaturesInput

    GeoFeaturesInput(layer_id="schulanlagen")  # ok
    with pytest.raises(ValueError):
        GeoFeaturesInput(layer_id="quartiere")  # never existed in code


def test_water_weather_station_rejects_typo():
    from zurich_opendata_mcp.tools.realtime import WaterWeatherInput

    WaterWeatherInput(station="tiefenbrunnen")
    WaterWeatherInput(station="mythenquai")
    with pytest.raises(ValueError):
        WaterWeatherInput(station="Tienfenbrunnen")  # typo silently mapped before


def test_tourism_language_rejects_unknown():
    from zurich_opendata_mcp.tools.tourism import TourismSearchInput

    for lang in ("de", "en", "fr", "it"):
        TourismSearchInput(category="restaurants", language=lang)
    with pytest.raises(ValueError):
        TourismSearchInput(category="restaurants", language="zh")


def test_strb_format_rejects_unknown():
    from zurich_opendata_mcp.tools.strb import (
        BeschluesseDepartementInput,
        SearchSTRBInput,
    )

    SearchSTRBInput(query="x", format="markdown")
    SearchSTRBInput(query="x", format="json")
    BeschluesseDepartementInput(departement="SSD", format="markdown")
    with pytest.raises(ValueError):
        SearchSTRBInput(query="x", format="xml")


# ─── idempotentHint consistency (audit follow-up) ────────────────────────────


def test_live_data_tools_are_not_idempotent():
    """Tools that return upstream timestamps (weather, air, water,
    pedestrian, VBZ, parking) cannot satisfy the MCP idempotent contract
    (same input -> same output). They must declare idempotentHint=False."""
    from zurich_opendata_mcp.app import mcp

    expected_non_idempotent = {
        "zurich_parking_live",
        "zurich_weather_live",
        "zurich_air_quality",
        "zurich_water_weather",
        "zurich_pedestrian_traffic",
        "zurich_vbz_passengers",
        "zurich_datastore_sql",
    }
    tools = mcp._tool_manager.list_tools()  # type: ignore[attr-defined]
    by_name = {t.name: t for t in tools}
    for name in expected_non_idempotent:
        assert name in by_name, f"tool not registered: {name}"
        annotations = getattr(by_name[name], "annotations", None) or {}
        if hasattr(annotations, "idempotentHint"):
            value = annotations.idempotentHint
        else:
            value = annotations.get("idempotentHint") if isinstance(annotations, dict) else None
        assert value is False, (
            f"{name}: idempotentHint={value!r} but tool returns live timestamps"
        )


async def test_analyze_datasets_does_not_call_package_show():
    """Audit M-5: the package_show fan-out per dataset has been removed.
    package_search already includes `resources`, and per-dataset
    datastore_search calls now run concurrently via asyncio.gather."""
    import zurich_opendata_mcp.http_client as http_client_module
    from zurich_opendata_mcp.tools.catalog import (
        AnalyzeDatasetInput,
        zurich_analyze_datasets,
    )

    calls: list[tuple[str, dict]] = []

    async def fake_ckan(action, params=None):
        calls.append((action, params or {}))
        if action == "package_search":
            return {
                "count": 2,
                "results": [
                    {
                        "name": "ds-1",
                        "title": "Dataset 1",
                        "metadata_modified": "2026-01-01T00:00:00",
                        "updateInterval": ["jährlich"],
                        "resources": [
                            {
                                "id": "res-1",
                                "name": "Resource 1",
                                "format": "CSV",
                                "datastore_active": True,
                            }
                        ],
                    },
                    {
                        "name": "ds-2",
                        "title": "Dataset 2",
                        "metadata_modified": "2026-02-01T00:00:00",
                        "updateInterval": ["monatlich"],
                        "resources": [
                            {
                                "id": "res-2",
                                "name": "Resource 2",
                                "format": "JSON",
                                "datastore_active": False,
                            }
                        ],
                    },
                ],
            }
        if action == "datastore_search":
            return {
                "fields": [
                    {"id": "_id", "type": "int"},
                    {"id": "Jahr", "type": "int"},
                ],
                "total": 100,
            }
        raise AssertionError(f"unexpected ckan_request action: {action}")

    original = http_client_module.ckan_request
    http_client_module.ckan_request = fake_ckan
    # Patch the symbol that was imported at module load time too.
    import zurich_opendata_mcp.tools.catalog as catalog_module
    catalog_module.ckan_request = fake_ckan
    try:
        result = await zurich_analyze_datasets(
            AnalyzeDatasetInput(query="x", max_datasets=2, include_structure=True)
        )
    finally:
        http_client_module.ckan_request = original
        catalog_module.ckan_request = original

    actions = [c[0] for c in calls]
    assert actions.count("package_show") == 0, "M-5: package_show must not be called"
    assert actions.count("package_search") == 1
    # Only the datastore-active resource (res-1) triggers a datastore_search.
    assert actions.count("datastore_search") == 1
    assert "Dataset 1" in result
    assert "Dataset 2" in result
    assert "DataStore-Einträge" in result  # field info rendered for ds-1

"""
Tests for Zurich Open Data MCP Server.

All tests are marked as 'live' because they hit real APIs.
Run with: PYTHONPATH=src pytest tests/ -m live
Skip in CI with: PYTHONPATH=src pytest tests/ -m "not live"
"""

import pytest

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

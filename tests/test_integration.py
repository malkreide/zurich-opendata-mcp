"""
Integration tests for Zurich Open Data MCP Server.
Tests all tools against the live CKAN API.
"""

import asyncio
import sys

# Add src to path
sys.path.insert(0, "src")

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


async def test_search():
    print("=" * 60)
    print("TEST 1: zurich_search_datasets('Schule')")
    print("=" * 60)
    result = await zurich_search_datasets(SearchDatasetsInput(query="Schule", rows=3))
    print(result[:500])
    assert "Datensätze" in result
    assert "Schul" in result
    print("✅ PASSED\n")


async def test_get_dataset():
    print("=" * 60)
    print("TEST 2: zurich_get_dataset('ssd_schulferien')")
    print("=" * 60)
    result = await zurich_get_dataset(GetDatasetInput(dataset_id="ssd_schulferien"))
    print(result[:500])
    assert "Ferien" in result or "Schulferien" in result
    print("✅ PASSED\n")


async def test_categories():
    print("=" * 60)
    print("TEST 3: zurich_list_categories() - all")
    print("=" * 60)
    result = await zurich_list_categories(ListGroupInput())
    print(result[:500])
    assert "Bildung" in result
    assert "Mobilität" in result or "mobilitat" in result.lower()
    print("✅ PASSED\n")


async def test_category_bildung():
    print("=" * 60)
    print("TEST 4: zurich_list_categories('bildung')")
    print("=" * 60)
    result = await zurich_list_categories(ListGroupInput(group_id="bildung"))
    print(result[:500])
    assert "Bildung" in result
    print("✅ PASSED\n")


async def test_tags():
    print("=" * 60)
    print("TEST 5: zurich_list_tags('schul')")
    print("=" * 60)
    result = await zurich_list_tags(TagSearchInput(query="schul"))
    print(result[:400])
    assert "schul" in result.lower()
    print("✅ PASSED\n")


async def test_parking():
    print("=" * 60)
    print("TEST 6: zurich_parking_live()")
    print("=" * 60)
    result = await zurich_parking_live()
    print(result[:600])
    assert "Parkhaus" in result or "Parkplatz" in result
    print("✅ PASSED\n")


async def test_analyze():
    print("=" * 60)
    print("TEST 7: zurich_analyze_datasets('Verkehr')")
    print("=" * 60)
    result = await zurich_analyze_datasets(AnalyzeDatasetInput(
        query="Verkehr", max_datasets=3, include_structure=True
    ))
    print(result[:600])
    assert "Analyse" in result
    print("✅ PASSED\n")


async def test_catalog_stats():
    print("=" * 60)
    print("TEST 8: zurich_catalog_stats()")
    print("=" * 60)
    result = await zurich_catalog_stats()
    print(result[:600])
    assert "Katalog" in result
    print("✅ PASSED\n")


async def test_school_data():
    print("=" * 60)
    print("TEST 9: zurich_find_school_data()")
    print("=" * 60)
    result = await zurich_find_school_data(FindSchoolDataInput())
    print(result[:800])
    assert "Schulamt" in result or "Schul" in result
    print("✅ PASSED\n")


async def test_weather_live():
    print("=" * 60)
    print("TEST 10: zurich_weather_live (Temperatur)")
    print("=" * 60)
    result = await zurich_weather_live(WeatherLiveInput(parameter="T", limit=5))
    print(result[:300])
    assert "°C" in result, "Wetterdaten sollten Temperatur enthalten"
    assert "Fehler" not in result, f"API-Fehler: {result}"
    print("✅ PASSED\n")


async def test_air_quality():
    print("=" * 60)
    print("TEST 11: zurich_air_quality")
    print("=" * 60)
    result = await zurich_air_quality(AirQualityInput(limit=10))
    print(result[:300])
    assert "Luftqualität" in result
    assert "Fehler" not in result
    print("✅ PASSED\n")


async def test_water_weather():
    print("=" * 60)
    print("TEST 12: zurich_water_weather (Tiefenbrunnen)")
    print("=" * 60)
    result = await zurich_water_weather(WaterWeatherInput(station="tiefenbrunnen", limit=2))
    print(result[:300])
    assert "Wassertemperatur" in result
    assert "Fehler" not in result
    print("✅ PASSED\n")


async def test_pedestrian():
    print("=" * 60)
    print("TEST 13: zurich_pedestrian_traffic")
    print("=" * 60)
    result = await zurich_pedestrian_traffic(PedestrianInput(limit=5))
    print(result[:300])
    assert "Passanten" in result or "Bahnhofstrasse" in result
    assert "Fehler" not in result
    print("✅ PASSED\n")


async def test_vbz_passengers():
    print("=" * 60)
    print("TEST 14: zurich_vbz_passengers")
    print("=" * 60)
    result = await zurich_vbz_passengers(VBZPassengersInput(limit=5))
    print(result[:300])
    assert "VBZ" in result
    assert "Fehler" not in result
    print("✅ PASSED\n")


# ── New API Tests ──────────────────────────────────────────

async def test_geo_layers():
    print("=" * 60)
    print("TEST 15: zurich_geo_layers")
    print("=" * 60)
    result = await zurich_geo_layers()
    print(result[:500])
    assert "schulanlagen" in result
    assert "stadtkreise" in result
    print("✅ PASSED\n")


async def test_geo_features():
    print("=" * 60)
    print("TEST 16: zurich_geo_features (schulanlagen)")
    print("=" * 60)
    result = await zurich_geo_features(GeoFeaturesInput(
        layer_id="schulanlagen", max_features=5
    ))
    print(result[:500])
    assert "Feature" in result or "Schulanlage" in result or "Koordinaten" in result
    print("✅ PASSED\n")


async def test_parliament_search():
    print("=" * 60)
    print("TEST 17: zurich_parliament_search ('Schule')")
    print("=" * 60)
    result = await zurich_parliament_search(ParliamentSearchInput(
        query="Schule", max_results=5
    ))
    print(result[:600])
    assert "Schul" in result or "GR Nr" in result or "Treffer" in result
    print("✅ PASSED\n")


async def test_parliament_members():
    print("=" * 60)
    print("TEST 18: zurich_parliament_members")
    print("=" * 60)
    result = await zurich_parliament_members(ParliamentMembersInput(
        active_only=True
    ))
    print(result[:500])
    assert "Mitglied" in result or "Partei" in result or "Mandat" in result or "Gemeinderat" in result
    print("✅ PASSED\n")


async def test_tourism():
    print("=" * 60)
    print("TEST 19: zurich_tourism (restaurants)")
    print("=" * 60)
    result = await zurich_tourism(TourismSearchInput(
        category="restaurants", language="de"
    ))
    print(result[:500])
    assert "Zürich" in result or "Restaurant" in result or "Tourismus" in result
    print("✅ PASSED\n")


async def test_sparql():
    print("=" * 60)
    print("TEST 20: zurich_sparql (nicht-produktiv Warnung)")
    print("=" * 60)
    result = await zurich_sparql(SparqlQueryInput(
        query="SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"
    ))
    print(result[:500])
    assert "nicht produktiv" in result, "Sollte Warnung über nicht-produktiven Endpunkt zeigen"
    print("✅ PASSED\n")


async def main():
    print("\n🏙️ Zurich Open Data MCP Server – Integration Tests\n")

    tests = [
        test_search,
        test_get_dataset,
        test_categories,
        test_category_bildung,
        test_tags,
        test_parking,
        test_analyze,
        test_catalog_stats,
        test_school_data,
        test_weather_live,
        test_air_quality,
        test_water_weather,
        test_pedestrian,
        test_vbz_passengers,
        # New API tests
        test_geo_layers,
        test_geo_features,
        test_parliament_search,
        test_parliament_members,
        test_tourism,
        test_sparql,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"Ergebnis: {passed} bestanden, {failed} fehlgeschlagen von {len(tests)}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

"""respx-backed unit tests for tools/realtime.py (audit M-7 continuation).

Covers the ParkenDD JSON source and the CKAN DataStore-backed tools
(weather, air, water, pedestrian, VBZ) end-to-end without network access.
"""

from __future__ import annotations

import json
import time

import httpx
import pytest
import respx

from zurich_opendata_mcp import resolver
from zurich_opendata_mcp.config import (
    AIR_QUALITY_DATASET_SLUG,
    AIR_QUALITY_RESOURCE_ID,
    CKAN_API_URL,
    METEO_DATASET_SLUG,
    METEO_RESOURCE_ID,
    PARKENDD_URL,
    VBZ_HALTESTELLEN_ID,
    WATER_TIEFENBRUNNEN_ID,
)
from zurich_opendata_mcp.tools.realtime import (
    AirQualityInput,
    ParkingLiveInput,
    PedestrianInput,
    VBZPassengersInput,
    WaterWeatherInput,
    WeatherLiveInput,
    zurich_air_quality,
    zurich_parking_live,
    zurich_pedestrian_traffic,
    zurich_vbz_passengers,
    zurich_water_weather,
    zurich_weather_live,
)

_DATASTORE = f"{CKAN_API_URL}/datastore_search"


def _ckan(result: dict) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "result": result})


@pytest.fixture(autouse=True)
def _seed_resolver_cache():
    """Pin the yearly UGZ resource IDs so the weather/air tests exercise only
    the datastore round-trip. Resolver behaviour (package_show lookup, year
    picking, fallback) is covered in test_resolver.py."""
    deadline = time.monotonic() + 3600
    resolver._cache[METEO_DATASET_SLUG] = (METEO_RESOURCE_ID, deadline)
    resolver._cache[AIR_QUALITY_DATASET_SLUG] = (AIR_QUALITY_RESOURCE_ID, deadline)
    yield
    resolver.clear_cache()


# ─── http_get_json query-string preservation (regression) ────────────────────


@respx.mock
async def test_http_get_json_preserves_url_query_string():
    """Regression: passing an empty dict to httpx replaces the query string,
    which silently dropped query params baked into the URL (e.g. the tourism
    client's `?id=<category>`). `http_get_json` must leave them intact."""
    from zurich_opendata_mcp.http_client import http_get_json

    route = respx.get("https://example.test/data").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    await http_get_json("https://example.test/data?id=166")

    assert dict(route.calls[0].request.url.params) == {"id": "166"}


# ─── ParkenDD parking ────────────────────────────────────────────────────────


@respx.mock
async def test_parking_live_renders_table_sorted():
    respx.get(PARKENDD_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "last_updated": "2026-06-27T10:00:00",
                "lots": [
                    {"name": "Urania", "free": 50, "total": 100, "state": "open"},
                    {"name": "Akku", "free": 0, "total": 200, "state": "closed"},
                ],
            },
        )
    )

    result = await zurich_parking_live()

    assert "## Parkplatzbelegung Zürich" in result
    assert "2026-06-27T10:00:00" in result
    # Sorted alphabetically: Akku before Urania.
    assert result.index("Akku") < result.index("Urania")
    # 50/100 free → 50% occupied; open → green icon.
    assert "| Urania | 50 | 100 | 50% | 🟢 open |" in result
    assert "| Akku | 0 | 200 | 100% | 🔴 closed |" in result
    assert "**Gesamt**: 2 Parkhäuser" in result


@respx.mock
async def test_parking_live_http_error():
    respx.get(PARKENDD_URL).mock(return_value=httpx.Response(503))

    result = await zurich_parking_live()

    assert "Fehler bei Parkplatz-Daten" in result


# ─── Weather (DataStore) ─────────────────────────────────────────────────────


@respx.mock
async def test_weather_live_groups_and_labels():
    route = respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 2,
                "records": [
                    {
                        "Datum": "2026-06-27T09:00",
                        "Standort": "Zch_Stampfenbachstrasse",
                        "Parameter": "T",
                        "Wert": 21.4,
                        "Status": "provisorisch",
                    }
                ],
            }
        )
    )

    result = await zurich_weather_live(
        WeatherLiveInput(station="Zch_Stampfenbachstrasse", parameter="T", limit=5)
    )

    # Correct resource and filters reached the wire.
    sent = route.calls[0].request.url
    assert METEO_RESOURCE_ID in str(sent)
    assert json.loads(dict(sent.params)["filters"]) == {
        "Standort": "Zch_Stampfenbachstrasse",
        "Parameter": "T",
    }
    # Human-readable parameter label + unit; 'provisorisch' status is hidden.
    assert "🌡️ Temperatur" in result
    assert "21.4 °C" in result
    assert "⚠️" not in result


@respx.mock
async def test_weather_live_queries_resolved_yearly_resource():
    """End-to-end wiring: the datastore call uses the resource ID resolved
    from package_show, not the pinned fallback constant."""
    resolver.clear_cache()  # bypass the seeded cache from the autouse fixture
    respx.get(f"{CKAN_API_URL}/package_show").mock(
        return_value=_ckan(
            {
                "resources": [
                    # Years in the past on purpose: the test must not depend
                    # on the wall-clock year, so the newest one wins.
                    {
                        "id": "meteo-2020",
                        "name": "ugz_ogd_meteo_h1_2020.csv",
                        "datastore_active": True,
                    },
                    {
                        "id": "meteo-2021",
                        "name": "ugz_ogd_meteo_h1_2021.csv",
                        "datastore_active": True,
                    },
                ]
            }
        )
    )
    route = respx.get(_DATASTORE).mock(return_value=_ckan({"total": 0, "records": []}))

    await zurich_weather_live(WeatherLiveInput())

    assert dict(route.calls[0].request.url.params)["resource_id"] == "meteo-2021"


@respx.mock
async def test_weather_live_empty():
    respx.get(_DATASTORE).mock(return_value=_ckan({"total": 0, "records": []}))

    result = await zurich_weather_live(WeatherLiveInput())

    assert "Keine Wetterdaten" in result


# ─── Air quality (DataStore) ─────────────────────────────────────────────────


@respx.mock
async def test_air_quality_groups_by_station():
    route = respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 1,
                "records": [
                    {
                        "Datum": "2026-06-27T09:00",
                        "Standort": "Zch_Rosengartenstrasse",
                        "Parameter": "NO2",
                        "Wert": 18,
                        "Einheit": "µg/m³",
                    }
                ],
            }
        )
    )

    result = await zurich_air_quality(AirQualityInput(limit=10))

    assert AIR_QUALITY_RESOURCE_ID in str(route.calls[0].request.url)
    assert "## 🌬️ Luftqualität Zürich" in result
    assert "**Zch_Rosengartenstrasse**: NO2=18 µg/m³" in result


# ─── Water weather (DataStore) ───────────────────────────────────────────────


@respx.mock
async def test_water_weather_none_becomes_dash():
    route = respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 1,
                "records": [
                    {
                        "timestamp_cet": "2026-06-27 11:00",
                        "water_temperature": 22.1,
                        "air_temperature": None,
                    }
                ],
            }
        )
    )

    result = await zurich_water_weather(
        WaterWeatherInput(station="tiefenbrunnen", limit=2)
    )

    assert WATER_TIEFENBRUNNEN_ID in str(route.calls[0].request.url)
    assert "Zürichsee Wetterstation Tiefenbrunnen" in result
    assert "**Wassertemperatur**: 22.1 °C" in result
    # Missing value renders as an en-dash placeholder, not "None".
    assert "**Lufttemperatur**: –" in result
    assert "None" not in result


# ─── Pedestrian (DataStore) ──────────────────────────────────────────────────


@respx.mock
async def test_pedestrian_traffic_table():
    respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 1,
                "records": [
                    {
                        "timestamp": "2026-06-27T08:00:00",
                        "location_name": "Bahnhofstrasse Mitte",
                        "pedestrians_count": 1234,
                        "temperature": 19,
                        "weather_condition": "sunny",
                    }
                ],
            }
        )
    )

    result = await zurich_pedestrian_traffic(PedestrianInput(limit=5))

    assert "Passantenfrequenzen Bahnhofstrasse" in result
    assert "Bahnhofstrasse Mitte" in result
    assert "1234" in result
    assert "19°C" in result


# ─── VBZ passengers (DataStore) ──────────────────────────────────────────────


@respx.mock
async def test_vbz_passengers_json_block_and_fields():
    respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 1,
                "fields": [
                    {"id": "_id", "type": "int"},
                    {"id": "Linienname", "type": "text"},
                    {"id": "Einsteiger", "type": "int"},
                ],
                "records": [{"_id": 1, "Linienname": "4", "Einsteiger": 999}],
            }
        )
    )

    result = await zurich_vbz_passengers(VBZPassengersInput(limit=20))

    assert "## 🚊 VBZ Fahrgastzahlen" in result
    # _id is filtered out of the advertised field list.
    assert "**Felder**: Linienname, Einsteiger" in result
    assert "```json" in result
    assert '"Linienname": "4"' in result


# ─── Coverage: empty + error + filter branches ───────────────────────────────


@respx.mock
async def test_weather_error_path():
    respx.get(_DATASTORE).mock(return_value=httpx.Response(500))
    result = await zurich_weather_live(WeatherLiveInput())
    assert "Fehler bei Wetterdaten" in result


@respx.mock
async def test_air_quality_filters_and_empty():
    route = respx.get(_DATASTORE).mock(return_value=_ckan({"total": 0, "records": []}))
    result = await zurich_air_quality(
        AirQualityInput(station="Zch_Rosengartenstrasse", parameter="NO2")
    )
    # station+parameter populate the filters payload.
    sent = dict(route.calls[0].request.url.params)
    assert '"Standort": "Zch_Rosengartenstrasse"' in sent["filters"]
    assert '"Parameter": "NO2"' in sent["filters"]
    assert "Keine Luftqualitätsdaten gefunden." == result


@respx.mock
async def test_air_quality_error_path():
    respx.get(_DATASTORE).mock(return_value=httpx.Response(500))
    result = await zurich_air_quality(AirQualityInput())
    assert "Fehler bei Luftqualität" in result


@respx.mock
async def test_water_empty_and_error():
    respx.get(_DATASTORE).mock(return_value=_ckan({"total": 0, "records": []}))
    empty = await zurich_water_weather(WaterWeatherInput(station="mythenquai"))
    assert "Keine Daten für Station Mythenquai gefunden." == empty


@respx.mock
async def test_water_error_path():
    respx.get(_DATASTORE).mock(return_value=httpx.Response(500))
    result = await zurich_water_weather(WaterWeatherInput())
    assert "Fehler bei Wasserwetter" in result


@respx.mock
async def test_pedestrian_empty_and_error():
    respx.get(_DATASTORE).mock(return_value=_ckan({"total": 0, "records": []}))
    result = await zurich_pedestrian_traffic(PedestrianInput())
    assert "Keine Passantenfrequenz-Daten gefunden." == result


@respx.mock
async def test_pedestrian_error_path():
    respx.get(_DATASTORE).mock(return_value=httpx.Response(500))
    result = await zurich_pedestrian_traffic(PedestrianInput())
    assert "Fehler bei Passantenfrequenzen" in result


@respx.mock
async def test_vbz_query_and_pagination():
    route = respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 100,
                "fields": [{"id": "_id", "type": "int"}, {"id": "Linie", "type": "text"}],
                "records": [{"_id": 1, "Linie": "4"}],
            }
        )
    )
    result = await zurich_vbz_passengers(VBZPassengersInput(query="Paradeplatz", limit=20))
    # Full-text query reaches the wire; total>limit shows the pagination hint.
    assert dict(route.calls[0].request.url.params)["q"] == "Paradeplatz"
    assert "weitere Einträge verfügbar" in result


@respx.mock
async def test_vbz_empty_and_error():
    respx.get(_DATASTORE).mock(return_value=_ckan({"total": 0, "records": [], "fields": []}))
    empty = await zurich_vbz_passengers(VBZPassengersInput())
    assert "Keine VBZ-Fahrgastzahlen gefunden." == empty


@respx.mock
async def test_vbz_error_path():
    respx.get(_DATASTORE).mock(return_value=httpx.Response(500))
    result = await zurich_vbz_passengers(VBZPassengersInput())
    assert "Fehler bei VBZ-Fahrgastzahlen" in result


# ─── format="json" across the realtime family (F-5) ─────────────────────────


@respx.mock
async def test_parking_live_json_format():
    respx.get(PARKENDD_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "last_updated": "2026-06-27T10:00:00",
                "lots": [{"name": "Urania", "free": 50, "total": 100, "state": "open"}],
            },
        )
    )

    payload = json.loads(await zurich_parking_live(ParkingLiveInput(format="json")))

    assert payload["last_updated"] == "2026-06-27T10:00:00"
    assert payload["count"] == 1
    assert payload["lots"][0]["name"] == "Urania"


@respx.mock
async def test_weather_live_json_format_strips_internal_id():
    respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 7,
                "records": [
                    {"_id": 1, "Datum": "2026-06-27T09:00", "Parameter": "T", "Wert": 21.4}
                ],
            }
        )
    )

    payload = json.loads(await zurich_weather_live(WeatherLiveInput(format="json")))

    assert payload["total"] == 7
    assert payload["count"] == 1
    assert payload["measurements"][0]["Wert"] == 21.4
    assert "_id" not in payload["measurements"][0]


@respx.mock
async def test_air_quality_json_format():
    respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 1,
                "records": [{"_id": 9, "Parameter": "NO2", "Wert": 18, "Einheit": "µg/m³"}],
            }
        )
    )

    payload = json.loads(await zurich_air_quality(AirQualityInput(format="json")))

    assert payload["measurements"] == [{"Parameter": "NO2", "Wert": 18, "Einheit": "µg/m³"}]


@respx.mock
async def test_water_weather_json_format():
    respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 1,
                "records": [{"timestamp_cet": "2026-06-27 11:00", "water_temperature": 22.1}],
            }
        )
    )

    payload = json.loads(
        await zurich_water_weather(WaterWeatherInput(station="mythenquai", format="json"))
    )

    assert payload["station"] == "Mythenquai"
    assert payload["measurements"][0]["water_temperature"] == 22.1


@respx.mock
async def test_pedestrian_json_format():
    respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 3,
                "records": [{"_id": 4, "location_name": "Mitte", "pedestrians_count": 1234}],
            }
        )
    )

    payload = json.loads(await zurich_pedestrian_traffic(PedestrianInput(format="json")))

    assert payload["total"] == 3
    assert payload["records"] == [{"location_name": "Mitte", "pedestrians_count": 1234}]


@respx.mock
async def test_vbz_json_format_includes_fields():
    respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {
                "total": 1,
                "fields": [{"id": "_id", "type": "int"}, {"id": "Linienname", "type": "text"}],
                "records": [{"_id": 1, "Linienname": "4"}],
            }
        )
    )

    payload = json.loads(await zurich_vbz_passengers(VBZPassengersInput(format="json")))

    assert payload["fields"] == ["Linienname"]
    assert payload["records"] == [{"Linienname": "4"}]


# ─── UGZ station/parameter Literals (F-7) ────────────────────────────────────

from typing import get_args  # noqa: E402

from pydantic import ValidationError  # noqa: E402

from zurich_opendata_mcp.config import (  # noqa: E402
    AIR_PARAMETERS,
    METEO_PARAMETERS,
    UGZ_STATIONS,
    AirParameter,
    MeteoParameter,
    UgzStation,
)


def test_ugz_literals_match_runtime_lists():
    assert list(get_args(UgzStation)) == UGZ_STATIONS
    assert list(get_args(MeteoParameter)) == METEO_PARAMETERS
    assert list(get_args(AirParameter)) == AIR_PARAMETERS


def test_invalid_station_and_parameter_rejected_upfront():
    # Previously documented-but-nonexistent values (Zch_Kaserne, SO2) used to
    # slip through and return "Keine Daten gefunden"; now Pydantic rejects
    # them before any HTTP call.
    with pytest.raises(ValidationError):
        WeatherLiveInput(station="Zch_Kaserne")
    with pytest.raises(ValidationError):
        WeatherLiveInput(parameter="XY")
    with pytest.raises(ValidationError):
        AirQualityInput(parameter="SO2")


@pytest.mark.live
async def test_live_ugz_literals_match_distinct_values():
    """Drift alarm: fails when the UGZ measurement network or parameter set
    changes, so the Literal types can be updated."""
    from zurich_opendata_mcp import resolver
    from zurich_opendata_mcp.config import (
        AIR_QUALITY_DATASET_SLUG,
        AIR_QUALITY_RESOURCE_PREFIX,
        METEO_DATASET_SLUG,
        METEO_RESOURCE_PREFIX,
    )
    from zurich_opendata_mcp.http_client import ckan_request

    async def distinct(resource_id: str, column: str) -> list[str]:
        result = await ckan_request(
            "datastore_search_sql",
            {"sql": f'SELECT DISTINCT "{column}" FROM "{resource_id}"'},
        )
        return sorted(rec[column] for rec in result["records"] if rec[column])

    meteo_id = await resolver.resolve_yearly_resource(
        METEO_DATASET_SLUG, METEO_RESOURCE_PREFIX, METEO_RESOURCE_ID
    )
    air_id = await resolver.resolve_yearly_resource(
        AIR_QUALITY_DATASET_SLUG, AIR_QUALITY_RESOURCE_PREFIX, AIR_QUALITY_RESOURCE_ID
    )

    assert await distinct(meteo_id, "Standort") == UGZ_STATIONS
    assert await distinct(meteo_id, "Parameter") == METEO_PARAMETERS
    assert await distinct(air_id, "Standort") == UGZ_STATIONS
    assert await distinct(air_id, "Parameter") == AIR_PARAMETERS


# ─── VBZ line/stop filters (previously dead parameters) ─────────────────────


@respx.mock
async def test_vbz_line_filter_reaches_the_wire():
    route = respx.get(_DATASTORE).mock(
        return_value=_ckan(
            {"total": 1, "fields": [], "records": [{"Linienname": "4", "Einsteiger": 9}]}
        )
    )

    result = await zurich_vbz_passengers(VBZPassengersInput(line="4", limit=5))

    sent = dict(route.calls[0].request.url.params)
    assert json.loads(sent["filters"]) == {"Linienname": "4"}
    assert "**Linie**: 4" in result


@respx.mock
async def test_vbz_stop_resolves_haltestellen_ids():
    def handler(request: httpx.Request) -> httpx.Response:
        p = dict(request.url.params)
        if p["resource_id"] == VBZ_HALTESTELLEN_ID:
            assert p["q"] == "Paradeplatz"
            return _ckan(
                {
                    "records": [
                        {
                            "Haltestellen_Id": "206",
                            "Haltestellenlangname": "Zürich, Paradeplatz",
                        }
                    ]
                }
            )
        # Second call: REISENDE filtered by the resolved ID list.
        assert json.loads(p["filters"]) == {"Haltestellen_Id": ["206"]}
        return _ckan(
            {"total": 2, "fields": [{"id": "Linienname", "type": "text"}], "records": [{"Linienname": "7"}]}
        )

    respx.get(_DATASTORE).mock(side_effect=handler)

    result = await zurich_vbz_passengers(VBZPassengersInput(stop="Paradeplatz"))

    assert "**Haltestelle(n)**: Zürich, Paradeplatz" in result


@respx.mock
async def test_vbz_unknown_stop_short_circuits():
    route = respx.get(_DATASTORE).mock(return_value=_ckan({"records": []}))

    result = await zurich_vbz_passengers(VBZPassengersInput(stop="Nirgendwo"))

    assert "Keine VBZ-Haltestelle gefunden für 'Nirgendwo'" in result
    # The REISENDE query is never sent.
    assert route.call_count == 1


@respx.mock
async def test_vbz_many_stops_truncate_and_json_payload():
    stops = [
        {"Haltestellen_Id": str(i), "Haltestellenlangname": f"Halt {i}"} for i in range(7)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        p = dict(request.url.params)
        if p["resource_id"] == VBZ_HALTESTELLEN_ID:
            return _ckan({"records": stops})
        return _ckan({"total": 1, "fields": [], "records": [{"Einsteiger": 1}]})

    respx.get(_DATASTORE).mock(side_effect=handler)

    md = await zurich_vbz_passengers(VBZPassengersInput(stop="Halt"))
    assert "(+2 weitere)" in md

    payload = json.loads(
        await zurich_vbz_passengers(
            VBZPassengersInput(stop="Halt", line="4", format="json")
        )
    )
    assert payload["line"] == "4"
    assert payload["haltestellen"][0] == "Halt 0"
    assert len(payload["haltestellen"]) == 7

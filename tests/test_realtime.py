"""respx-backed unit tests for tools/realtime.py (audit M-7 continuation).

Covers the ParkenDD JSON source and the CKAN DataStore-backed tools
(weather, air, water, pedestrian, VBZ) end-to-end without network access.
"""

from __future__ import annotations

import json

import httpx
import respx

from zurich_opendata_mcp.config import (
    AIR_QUALITY_RESOURCE_ID,
    CKAN_API_URL,
    METEO_RESOURCE_ID,
    PARKENDD_URL,
    WATER_TIEFENBRUNNEN_ID,
)
from zurich_opendata_mcp.tools.realtime import (
    AirQualityInput,
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
                        "Standort": "Zch_Kaserne",
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
    assert "**Zch_Kaserne**: NO2=18 µg/m³" in result


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

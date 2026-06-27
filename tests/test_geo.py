"""respx-backed unit tests for tools/geo.py + clients/wfs.py (audit M-7).

Covers the WFS GeoJSON round-trip — request building, feature rendering,
the CQL filter passthrough, truncation, empty and error branches — plus the
pure (no-HTTP) layer listing.
"""

from __future__ import annotations

import httpx
import respx

from zurich_opendata_mcp.config import GEOPORTAL_LAYERS, WFS_BASE_URL
from zurich_opendata_mcp.tools.geo import (
    GeoFeaturesInput,
    zurich_geo_features,
    zurich_geo_layers,
)

# schulanlagen → ("Schulanlagen", "poi_kindergarten_view", "Schulstandorte …")
_SERVICE, _TYPENAME, _DESC = GEOPORTAL_LAYERS["schulanlagen"]
_WFS_URL = f"{WFS_BASE_URL}/{_SERVICE}"


def _point(name: str, lon: float, lat: float, **props) -> dict:
    return {
        "properties": {"name": name, **props},
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


# ─── Layer listing (no HTTP) ─────────────────────────────────────────────────


async def test_geo_layers_lists_all():
    result = await zurich_geo_layers()

    assert "## Verfügbare Geoportal-Layer (WFS)" in result
    assert f"**Anzahl**: {len(GEOPORTAL_LAYERS)}" in result
    # A couple of known layers render in the table.
    assert "`schulanlagen`" in result
    assert "`stadtkreise`" in result


# ─── Feature fetch ───────────────────────────────────────────────────────────


@respx.mock
async def test_geo_features_renders_points_and_fields():
    route = respx.get(_WFS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "features": [
                    _point(
                        "Schulhaus A",
                        8.54,
                        47.37,
                        kategorie="Schulhaus",
                        adresse="Musterstr 1",
                    )
                ]
            },
        )
    )

    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="schulanlagen", max_features=50)
    )

    # Correct WFS service + typename on the wire.
    params = dict(route.calls[0].request.url.params)
    assert params["typename"] == _TYPENAME
    assert params["outputFormat"] == "GeoJSON"
    assert params["maxFeatures"] == "50"

    assert f"## Geodaten: {_DESC}" in result
    assert f"`schulanlagen` ({_TYPENAME})" in result
    assert "**Features**: 1" in result
    # name (kategorie) – adresse + Point coords (lat, lon, 5dp).
    assert "**Schulhaus A** (Schulhaus) – Musterstr 1 📍 [47.37000, 8.54000]" in result
    assert "**Verfügbare Felder**: name, kategorie, adresse" in result
    assert "zurich://geo/schulanlagen" in result


@respx.mock
async def test_geo_features_passes_cql_filter():
    route = respx.get(_WFS_URL).mock(
        return_value=httpx.Response(200, json={"features": []})
    )

    result = await zurich_geo_features(
        GeoFeaturesInput(
            layer_id="schulanlagen",
            property_filter="kategorie = 'Kindergarten'",
        )
    )

    assert dict(route.calls[0].request.url.params)["CQL_FILTER"] == (
        "kategorie = 'Kindergarten'"
    )
    assert "**Filter**: `kategorie = 'Kindergarten'`" in result


@respx.mock
async def test_geo_features_truncates_after_20():
    feats = [_point(f"P{i}", 8.5, 47.3) for i in range(21)]
    respx.get(_WFS_URL).mock(return_value=httpx.Response(200, json={"features": feats}))

    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="schulanlagen", max_features=500)
    )

    assert "**Features**: 21" in result
    assert "… und 1 weitere Features" in result


@respx.mock
async def test_geo_features_empty():
    respx.get(_WFS_URL).mock(return_value=httpx.Response(200, json={"features": []}))

    result = await zurich_geo_features(GeoFeaturesInput(layer_id="schulanlagen"))

    assert "**Features**: 0" in result
    # No feature rows → no field listing.
    assert "Verfügbare Felder" not in result


@respx.mock
async def test_geo_features_http_error():
    respx.get(_WFS_URL).mock(return_value=httpx.Response(500))

    result = await zurich_geo_features(GeoFeaturesInput(layer_id="schulanlagen"))

    assert "Fehler bei Geodaten-Abfrage" in result

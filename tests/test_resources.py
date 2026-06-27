"""respx-backed unit tests for tools/resources.py (audit M-7).

The `zurich://` MCP resource handlers are thin client → JSON wrappers; these
cover each one's happy path plus the unknown-layer short-circuit.
"""

from __future__ import annotations

import json

import httpx
import respx

from zurich_opendata_mcp.config import (
    CKAN_API_URL,
    PARKENDD_URL,
    WFS_BASE_URL,
    ZT_API_URL,
)
from zurich_opendata_mcp.tools.resources import (
    get_category_resource,
    get_dataset_resource,
    get_geo_resource,
    get_parking_resource,
    get_tourism_categories_resource,
)


def _ckan(result: dict) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "result": result})


@respx.mock
async def test_dataset_resource():
    respx.get(f"{CKAN_API_URL}/package_show").mock(
        return_value=_ckan({"name": "ssd_schulferien", "title": "Schulferien"})
    )

    out = json.loads(await get_dataset_resource("ssd_schulferien"))

    assert out["name"] == "ssd_schulferien"


@respx.mock
async def test_category_resource():
    respx.get(f"{CKAN_API_URL}/group_show").mock(
        return_value=_ckan({"name": "bildung", "title": "Bildung", "packages": []})
    )

    out = json.loads(await get_category_resource("bildung"))

    assert out["name"] == "bildung"


@respx.mock
async def test_parking_resource():
    respx.get(PARKENDD_URL).mock(
        return_value=httpx.Response(200, json={"lots": [{"name": "Urania"}]})
    )

    out = json.loads(await get_parking_resource())

    assert out["lots"][0]["name"] == "Urania"


@respx.mock
async def test_geo_resource_known_layer():
    service, _typename, _ = ("Schulanlagen", "poi_kindergarten_view", "")
    respx.get(f"{WFS_BASE_URL}/{service}").mock(
        return_value=httpx.Response(200, json={"features": []})
    )

    out = json.loads(await get_geo_resource("schulanlagen"))

    assert "features" in out


async def test_geo_resource_unknown_layer_no_http():
    # No respx routes → any HTTP call raises, proving the short-circuit.
    with respx.mock:
        out = json.loads(await get_geo_resource("does-not-exist"))

    assert out["error"] == "Unknown layer: does-not-exist"


@respx.mock
async def test_tourism_categories_resource():
    respx.get(ZT_API_URL).mock(
        return_value=httpx.Response(200, json=[{"id": 166, "name": "Restaurants"}])
    )

    out = json.loads(await get_tourism_categories_resource())

    assert out[0]["id"] == 166

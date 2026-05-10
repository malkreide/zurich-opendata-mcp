"""MCP Resource handlers (zurich:// URIs)."""

from __future__ import annotations

import json

from ..app import mcp
from ..clients.tourism import zt_get_categories
from ..clients.wfs import wfs_get_features
from ..config import GEOPORTAL_LAYERS, PARKENDD_URL
from ..http_client import ckan_request, http_get_json


@mcp.resource("zurich://dataset/{name}")
async def get_dataset_resource(name: str) -> str:
    """Datensatz-Metadaten als MCP Resource."""
    result = await ckan_request("package_show", {"id": name})
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)


@mcp.resource("zurich://category/{group_id}")
async def get_category_resource(group_id: str) -> str:
    """Kategorie-Details als MCP Resource."""
    result = await ckan_request(
        "group_show",
        {
            "id": group_id,
            "include_datasets": True,
        },
    )
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)


@mcp.resource("zurich://parking")
async def get_parking_resource() -> str:
    """Aktuelle Parkplatz-Daten als MCP Resource."""
    data = await http_get_json(PARKENDD_URL)
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


@mcp.resource("zurich://geo/{layer_id}")
async def get_geo_resource(layer_id: str) -> str:
    """GeoJSON-Daten eines Geoportal-Layers als MCP Resource."""
    if layer_id not in GEOPORTAL_LAYERS:
        return json.dumps({"error": f"Unknown layer: {layer_id}"})
    service_name, typename, _ = GEOPORTAL_LAYERS[layer_id]
    data = await wfs_get_features(service_name, typename, max_features=500)
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


@mcp.resource("zurich://tourism/categories")
async def get_tourism_categories_resource() -> str:
    """Zürich Tourismus Kategorien als MCP Resource."""
    data = await zt_get_categories()
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)

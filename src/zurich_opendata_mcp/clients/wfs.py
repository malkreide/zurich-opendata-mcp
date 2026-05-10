"""Geoportal WFS client."""

from __future__ import annotations

from typing import Any

from ..config import WFS_BASE_URL
from ..http_client import _get_client


async def wfs_get_features(
    service_name: str,
    typename: str,
    max_features: int = 50,
    output_format: str = "GeoJSON",
    cql_filter: str | None = None,
) -> dict[str, Any]:
    """Fetch features from the Zurich Geoportal WFS."""
    url = f"{WFS_BASE_URL}/{service_name}"
    params: dict[str, str] = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typename": typename,
        "outputFormat": output_format,
        "maxFeatures": str(max_features),
    }
    if cql_filter:
        params["CQL_FILTER"] = cql_filter

    async with await _get_client() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

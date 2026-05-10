"""Shared HTTP client and CKAN helpers."""

from __future__ import annotations

from typing import Any

import httpx

from .config import CKAN_API_URL, REQUEST_TIMEOUT, USER_AGENT


def get_client() -> httpx.AsyncClient:
    """Create a configured async HTTP client."""
    return httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


async def ckan_request(action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make a CKAN API request and return the result."""
    async with get_client() as client:
        url = f"{CKAN_API_URL}/{action}"
        response = await client.get(url, params=params or {})
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            error_msg = data.get("error", {}).get("message", "Unknown CKAN error")
            raise RuntimeError(f"CKAN API error: {error_msg}")

        return data["result"]


async def http_get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """Generic JSON GET request for non-CKAN APIs."""
    async with get_client() as client:
        response = await client.get(url, params=params or {})
        response.raise_for_status()
        return response.json()

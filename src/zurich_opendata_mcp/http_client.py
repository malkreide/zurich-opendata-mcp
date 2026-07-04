"""Shared HTTP client and CKAN helpers.

All upstream calls go through one process-wide ``httpx.AsyncClient`` so they
reuse pooled TCP/TLS connections instead of re-handshaking on every request.
The pool is closed on server shutdown via the FastMCP lifespan in ``app.py``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .config import CKAN_API_URL, REQUEST_TIMEOUT, USER_AGENT

# Pooled connections are bound to the event loop they were opened on, so the
# client is recreated whenever the running loop changes. The server only ever
# runs one loop; a loop change happens only in test suites, where each test
# gets a fresh loop (the orphaned client holds no real sockets under respx).
_client: httpx.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def get_client() -> httpx.AsyncClient:
    """Return the shared async HTTP client, (re)creating it when needed.

    Callers must not close the returned client — shutdown is handled by
    ``close_client()`` via the FastMCP lifespan.
    """
    global _client, _client_loop
    loop = asyncio.get_running_loop()
    if _client is None or _client.is_closed or _client_loop is not loop:
        _client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
        _client_loop = loop
    return _client


async def close_client() -> None:
    """Close the shared client and its connection pool (lifespan shutdown)."""
    global _client, _client_loop
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
    _client_loop = None


async def ckan_request(action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make a CKAN API request and return the result."""
    client = get_client()
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
    client = get_client()
    # Pass params through as-is: httpx treats an *empty* dict as "replace
    # the query string", which would strip a query already baked into the
    # URL (e.g. zt_get_data's `?id=<category>`). `None` leaves it intact.
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()

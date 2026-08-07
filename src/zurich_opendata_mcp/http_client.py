"""Shared HTTP client and CKAN helpers.

All upstream calls go through one process-wide ``httpx.AsyncClient`` so they
reuse pooled TCP/TLS connections instead of re-handshaking on every request.
The pool is closed on server shutdown via the MCPServer lifespan in ``app.py``.

Resilience: the retry policy lives in ``retry.py`` and is the **only** level
that retries. The transport layer is explicitly set to zero retries — it used
to sit at 2 underneath this module's own loop, and two retrying levels
multiply rather than add.

All requests are idempotent GETs against public APIs, so a retry is always
safe. What is retried, how fast and how long is documented in ``retry.py``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .config import CKAN_API_URL, REQUEST_TIMEOUT, USER_AGENT
from .retry import fetch_with_retry

# Exactly one level may retry, and it is `retry.fetch_with_retry`. httpx
# retries connect failures itself when a transport is built with `retries>0`;
# stacked under our own loop that is 3 x 4 attempts, not 3 + 4.
CONNECT_RETRIES = 0

# Pooled connections are bound to the event loop they were opened on, so the
# client is recreated whenever the running loop changes. The server only ever
# runs one loop; a loop change happens only in test suites, where each test
# gets a fresh loop (the orphaned client holds no real sockets under respx).
_client: httpx.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def get_client() -> httpx.AsyncClient:
    """Return the shared async HTTP client, (re)creating it when needed.

    Callers must not close the returned client — shutdown is handled by
    ``close_client()`` via the MCPServer lifespan.
    """
    global _client, _client_loop
    loop = asyncio.get_running_loop()
    if _client is None or _client.is_closed or _client_loop is not loop:
        _client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            transport=httpx.AsyncHTTPTransport(retries=CONNECT_RETRIES),
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


async def http_get(url: str, params: dict[str, Any] | None = None) -> httpx.Response:
    """GET through the shared client, with the retry policy from ``retry.py``.

    Raises ``httpx.HTTPStatusError`` for any non-2xx final response, and
    ``httpx.RequestError`` when the upstream could not be reached at all —
    both unwrapped, so callers can branch on the type.

    Note on ``params``: passed through as-is — httpx treats an *empty* dict
    as "replace the query string", which would strip a query already baked
    into the URL (e.g. zt_get_data's ``?id=<category>``). ``None`` leaves it
    intact.
    """
    return await fetch_with_retry(get_client(), url, params=params)


async def ckan_request(action: str, params: dict[str, Any] | None = None) -> Any:
    """Make a CKAN API request and return the ``result`` field.

    Typed ``Any`` on purpose: CKAN returns a dict for most actions but a
    plain list for e.g. ``group_list``/``tag_list``.
    """
    response = await http_get(f"{CKAN_API_URL}/{action}", params=params or {})
    data = response.json()

    if not data.get("success"):
        error_msg = data.get("error", {}).get("message", "Unknown CKAN error")
        raise RuntimeError(f"CKAN API error: {error_msg}")

    return data["result"]


async def http_get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """Generic JSON GET request for non-CKAN APIs."""
    response = await http_get(url, params=params)
    return response.json()

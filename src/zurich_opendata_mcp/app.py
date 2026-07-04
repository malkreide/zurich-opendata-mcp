"""Shared FastMCP instance.

Lives in its own module so tool/resource modules can import it without
creating a cycle through ``server.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from .http_client import close_client


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Close the shared HTTP client's connection pool on server shutdown."""
    try:
        yield
    finally:
        await close_client()


mcp = FastMCP("zurich_opendata_mcp", lifespan=_lifespan)

"""Shared MCPServer instance.

Lives in its own module so tool/resource modules can import it without
creating a cycle through ``server.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer

from .http_client import close_client


@asynccontextmanager
async def _lifespan(_server: MCPServer) -> AsyncIterator[None]:
    """Close the shared HTTP client's connection pool on server shutdown."""
    try:
        yield
    finally:
        await close_client()


mcp = MCPServer("zurich_opendata_mcp", lifespan=_lifespan)

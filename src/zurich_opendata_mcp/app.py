"""Shared MCPServer instance.

Lives in its own module so tool/resource modules can import it without
creating a cycle through ``server.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.caching import CacheableMethod, CacheHint
from mcp.server.mcpserver import MCPServer

from .http_client import close_client


@asynccontextmanager
async def _lifespan(_server: MCPServer) -> AsyncIterator[None]:
    """Close the shared HTTP client's connection pool on server shutdown."""
    try:
        yield
    finally:
        await close_client()


# SEP-2549, Spec 2026-07-28: die auflistenden Methoden tragen `ttlMs` und
# `cacheScope`. Das SDK setzt beides auf «sofort veraltet, nie geteilt» — ein
# Server ohne `cache_hints` verhaelt sich also nicht neutral, sondern laesst
# jeden Client bei jeder Verbindung neu auflisten, fuer Verzeichnisse, die beim
# Import feststehen und sich zur Laufzeit des Prozesses nicht aendern koennen.
#
# `public` folgt aus der Sache, nicht aus Bequemlichkeit: die 10 Tools werden
# per Dekorator beim Import registriert, es gibt keine Filterung nach Aufrufer.
# Sobald eine Liste vom Aufrufer abhaengt, muss der Scope im selben Commit auf
# `private` wechseln.
#
# `resources/read` und `prompts/get` stehen bewusst nicht dabei: das waere eine
# Zusicherung ueber den INHALT statt ueber das Verzeichnis.
LIST_CACHE_TTL_MS = 300_000

# Annotiert, nicht inferiert: `MCPServer` nimmt
# `Mapping[CacheableMethod, CacheHint]`, und ein Dict-Literal ohne Annotation
# inferiert mypy als `str`. Zur Laufzeit stimmt beides — ein `mypy src/`-Gate
# meldet den Unterschied, die Tests nicht.
CACHE_HINTS: dict[CacheableMethod, CacheHint] = {
    "tools/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "resources/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "resources/templates/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "server/discover": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
}

mcp = MCPServer("zurich_opendata_mcp", lifespan=_lifespan, cache_hints=CACHE_HINTS)

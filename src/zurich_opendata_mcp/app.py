"""Shared FastMCP instance.

Lives in its own module so tool/resource modules can import it without
creating a cycle through ``server.py``.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("zurich_opendata_mcp")

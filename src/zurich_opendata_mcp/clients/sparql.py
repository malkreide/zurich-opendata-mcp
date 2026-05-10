"""SPARQL endpoint client."""

from __future__ import annotations

from typing import Any

from ..config import SPARQL_URL, USER_AGENT
from ..http_client import get_client


async def sparql_query(query: str) -> dict[str, Any]:
    """Execute a SPARQL query against the Zurich Linked Data endpoint."""
    async with get_client() as client:
        response = await client.get(
            SPARQL_URL,
            params={"query": query},
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        response.raise_for_status()
        return response.json()

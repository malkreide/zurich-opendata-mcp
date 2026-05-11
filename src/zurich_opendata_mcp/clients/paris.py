"""Paris API client (Gemeinderat parliamentary information)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..config import PARIS_API_URL
from ..http_client import get_client


def cql_escape(value: str) -> str:
    # CQL string literals are wrapped in double quotes; escape backslashes
    # first (so the new escapes we add are not double-escaped) and then
    # double quotes. Without this, payloads like 'foo" OR Titel any "bar'
    # break out of the literal and append a second predicate.
    return value.replace("\\", "\\\\").replace('"', '\\"')


async def paris_search(
    index: str,
    cql_query: str,
    start: int = 1,
    max_results: int = 10,
) -> ET.Element:
    """Search the Paris parliamentary information API."""
    url = f"{PARIS_API_URL}/{index}/searchdetails"
    params = {
        "q": cql_query,
        "l": "de-CH",
        "s": str(start),
        "m": str(max_results),
    }
    async with get_client() as client:
        response = await client.get(url, params=params, follow_redirects=True)
        response.raise_for_status()
        return ET.fromstring(response.content)


def paris_extract_text(element: ET.Element | None, default: str = "") -> str:
    """Safely extract text from an XML element."""
    if element is not None and element.text:
        return element.text.strip()
    return default


def paris_get_num_hits(root: ET.Element) -> int:
    """Get total number of hits from Paris API response."""
    return int(root.get("numHits", "0"))

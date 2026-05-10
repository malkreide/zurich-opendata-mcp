"""Zürich Tourismus API client."""

from __future__ import annotations

from ..config import ZT_API_URL
from ..http_client import http_get_json


async def zt_get_categories() -> list[dict]:
    """Get all Zürich Tourismus categories."""
    return await http_get_json(ZT_API_URL)


async def zt_get_data(category_id: int) -> list[dict]:
    """Get data for a specific ZT category."""
    return await http_get_json(f"{ZT_API_URL}?id={category_id}")

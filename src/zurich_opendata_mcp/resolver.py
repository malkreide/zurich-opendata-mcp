"""Runtime resolution of year-bound CKAN resource IDs.

The UGZ hourly datasets (meteo, air quality) publish one CSV resource per
calendar year (``ugz_ogd_meteo_h1_2026.csv``, ``ugz_ogd_air_h1_2027.csv``, …),
so a hard-coded resource UUID silently goes stale every January. This module
looks up the right resource in the dataset's resource list at call time:

- prefer the resource for the current calendar year,
- otherwise fall back to the newest year available (covers early January,
  before the new year's resource has been published),
- and if CKAN is unreachable or the dataset shape changed, fall back to the
  pinned resource ID from ``config.py`` so the tool still answers.

Successful lookups are cached in-process for ``CACHE_TTL_SECONDS`` to avoid
an extra CKAN round-trip on every tool call; failures are never cached.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import UTC, datetime
from typing import Any

from .http_client import ckan_request

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 24 * 60 * 60

# dataset slug -> (resolved resource ID, monotonic expiry)
_cache: dict[str, tuple[str, float]] = {}


def clear_cache() -> None:
    """Drop all cached resolutions (used by tests)."""
    _cache.clear()


def _pick_yearly_resource(
    resources: list[dict[str, Any]], name_prefix: str, current_year: int
) -> str | None:
    """Pick the resource ID for ``current_year``, else the newest year."""
    candidates: list[tuple[int, str]] = []
    for res in resources:
        if not res.get("datastore_active"):
            continue
        match = re.match(rf"^{re.escape(name_prefix)}(\d{{4}})", res.get("name") or "")
        if match:
            candidates.append((int(match.group(1)), res["id"]))
    if not candidates:
        return None
    for year, res_id in candidates:
        if year == current_year:
            return res_id
    return max(candidates)[1]


async def resolve_yearly_resource(dataset_slug: str, name_prefix: str, fallback_id: str) -> str:
    """Resolve the current resource ID of a per-year CKAN dataset.

    Returns ``fallback_id`` when the lookup fails or no resource matches
    ``name_prefix`` — never raises.
    """
    now = time.monotonic()
    cached = _cache.get(dataset_slug)
    if cached is not None and cached[1] > now:
        return cached[0]

    try:
        dataset = await ckan_request("package_show", {"id": dataset_slug})
        resource_id = _pick_yearly_resource(
            dataset.get("resources", []),
            name_prefix,
            datetime.now(UTC).year,
        )
    except Exception as e:
        logger.warning(
            "Yearly resource resolution for dataset %r failed (%s: %s); "
            "using pinned fallback ID",
            dataset_slug,
            type(e).__name__,
            e,
        )
        return fallback_id

    if resource_id is None:
        logger.warning(
            "No datastore resource matching %r* in dataset %r; using pinned fallback ID",
            name_prefix,
            dataset_slug,
        )
        return fallback_id

    _cache[dataset_slug] = (resource_id, now + CACHE_TTL_SECONDS)
    return resource_id

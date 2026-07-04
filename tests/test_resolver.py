"""Tests for resolver.resolve_yearly_resource (year-bound UGZ resource IDs)."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import httpx
import pytest
import respx

from zurich_opendata_mcp import resolver
from zurich_opendata_mcp.config import (
    AIR_QUALITY_DATASET_SLUG,
    AIR_QUALITY_RESOURCE_PREFIX,
    CKAN_API_URL,
    METEO_DATASET_SLUG,
    METEO_RESOURCE_PREFIX,
)

_PACKAGE_SHOW = f"{CKAN_API_URL}/package_show"
_PREFIX = "ugz_ogd_meteo_h1_"
_CURRENT_YEAR = datetime.now(UTC).year


def _ckan(result: dict) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "result": result})


def _res(year: int, res_id: str, datastore: bool = True) -> dict:
    return {"id": res_id, "name": f"{_PREFIX}{year}.csv", "datastore_active": datastore}


@pytest.fixture(autouse=True)
def _clean_cache():
    resolver.clear_cache()
    yield
    resolver.clear_cache()


@respx.mock
async def test_prefers_current_year_resource():
    respx.get(_PACKAGE_SHOW).mock(
        return_value=_ckan(
            {"resources": [_res(_CURRENT_YEAR - 1, "old"), _res(_CURRENT_YEAR, "current")]}
        )
    )

    assert await resolver.resolve_yearly_resource("ds", _PREFIX, "fb") == "current"


@respx.mock
async def test_falls_back_to_newest_year_when_current_missing():
    # Early-January shape: the new year's resource has not been published yet.
    respx.get(_PACKAGE_SHOW).mock(
        return_value=_ckan(
            {"resources": [_res(_CURRENT_YEAR - 2, "older"), _res(_CURRENT_YEAR - 1, "newest")]}
        )
    )

    assert await resolver.resolve_yearly_resource("ds", _PREFIX, "fb") == "newest"


@respx.mock
async def test_skips_non_datastore_and_non_matching_resources():
    respx.get(_PACKAGE_SHOW).mock(
        return_value=_ckan(
            {
                "resources": [
                    _res(_CURRENT_YEAR, "not-in-datastore", datastore=False),
                    {"id": "meta", "name": "uzg_ogd_metadaten.json", "datastore_active": True},
                    {"id": "unnamed", "datastore_active": True},
                    _res(_CURRENT_YEAR - 1, "pick-me"),
                ]
            }
        )
    )

    assert await resolver.resolve_yearly_resource("ds", _PREFIX, "fb") == "pick-me"


@respx.mock
async def test_no_matching_resource_returns_fallback_and_is_not_cached():
    route = respx.get(_PACKAGE_SHOW).mock(return_value=_ckan({"resources": []}))

    assert await resolver.resolve_yearly_resource("ds", _PREFIX, "fb") == "fb"
    assert await resolver.resolve_yearly_resource("ds", _PREFIX, "fb") == "fb"
    # Failures are retried on the next call instead of being cached.
    assert route.call_count == 2


@respx.mock
async def test_upstream_error_returns_fallback():
    respx.get(_PACKAGE_SHOW).mock(return_value=httpx.Response(500))

    assert await resolver.resolve_yearly_resource("ds", _PREFIX, "fb") == "fb"


@respx.mock
async def test_successful_resolution_is_cached():
    route = respx.get(_PACKAGE_SHOW).mock(
        return_value=_ckan({"resources": [_res(_CURRENT_YEAR, "hit")]})
    )

    assert await resolver.resolve_yearly_resource("ds", _PREFIX, "fb") == "hit"
    assert await resolver.resolve_yearly_resource("ds", _PREFIX, "fb") == "hit"
    assert route.call_count == 1


@respx.mock
async def test_expired_cache_entry_refetches():
    route = respx.get(_PACKAGE_SHOW).mock(
        return_value=_ckan({"resources": [_res(_CURRENT_YEAR, "hit")]})
    )

    await resolver.resolve_yearly_resource("ds", _PREFIX, "fb")
    resource_id, _ = resolver._cache["ds"]
    resolver._cache["ds"] = (resource_id, time.monotonic() - 1)
    await resolver.resolve_yearly_resource("ds", _PREFIX, "fb")

    assert route.call_count == 2


@pytest.mark.live
async def test_live_ugz_datasets_still_publish_recent_yearly_resources():
    """Stale alarm: fails when the UGZ datasets stop publishing per-year
    resources under the expected naming scheme (then the resolver would fall
    back to the pinned, aging resource IDs)."""
    from zurich_opendata_mcp.http_client import ckan_request

    year = datetime.now(UTC).year
    for slug, prefix in [
        (METEO_DATASET_SLUG, METEO_RESOURCE_PREFIX),
        (AIR_QUALITY_DATASET_SLUG, AIR_QUALITY_RESOURCE_PREFIX),
    ]:
        dataset = await ckan_request("package_show", {"id": slug})
        names = [r.get("name") or "" for r in dataset.get("resources", [])]
        assert any(
            n.startswith(f"{prefix}{year}") or n.startswith(f"{prefix}{year - 1}")
            for n in names
        ), f"{slug}: no {prefix}<recent-year> resource found — naming scheme changed?"

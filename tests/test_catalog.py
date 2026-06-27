"""respx-backed unit tests for the Markdown-only catalog tools (audit M-7).

The three structured-output tools (search/get/analyze) are covered in
test_server.py; these cover the remaining CKAN catalog tools:
list_categories, list_tags, catalog_stats and find_school_data.
"""

from __future__ import annotations

import httpx
import respx

from zurich_opendata_mcp.config import CKAN_API_URL
from zurich_opendata_mcp.tools.catalog import (
    FindSchoolDataInput,
    ListGroupInput,
    TagSearchInput,
    zurich_catalog_stats,
    zurich_find_school_data,
    zurich_list_categories,
    zurich_list_tags,
)


def _ckan(result) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "result": result})


# ─── list_categories ─────────────────────────────────────────────────────────


@respx.mock
async def test_list_categories_all():
    respx.get(f"{CKAN_API_URL}/group_list").mock(
        return_value=_ckan(
            [
                {"name": "bildung", "title": "Bildung", "package_count": 42},
                {"name": "mobilitat", "title": "Mobilität", "package_count": 17},
            ]
        )
    )

    result = await zurich_list_categories(ListGroupInput())

    assert "## Datenkategorien der Stadt Zürich" in result
    assert "**Bildung** (`bildung`) – 42 Datensätze" in result


@respx.mock
async def test_list_categories_single_group():
    respx.get(f"{CKAN_API_URL}/group_show").mock(
        return_value=_ckan(
            {
                "title": "Bildung",
                "package_count": 2,
                "packages": [
                    {"name": "ssd_schulferien", "title": "Schulferien"},
                ],
            }
        )
    )

    result = await zurich_list_categories(ListGroupInput(group_id="bildung"))

    assert "## Kategorie: Bildung" in result
    assert "**Schulferien** (`ssd_schulferien`)" in result


# ─── list_tags ───────────────────────────────────────────────────────────────


@respx.mock
async def test_list_tags():
    respx.get(f"{CKAN_API_URL}/tag_list").mock(
        return_value=_ckan(["schule", "schulweg", "volksschule"])
    )

    result = await zurich_list_tags(TagSearchInput(query="schul", limit=2))

    assert "## Tags (2 Ergebnisse)" in result
    assert "`schule`" in result
    # Limited to 2 → third tag omitted.
    assert "`volksschule`" not in result


@respx.mock
async def test_list_tags_empty():
    respx.get(f"{CKAN_API_URL}/tag_list").mock(return_value=_ckan([]))

    result = await zurich_list_tags(TagSearchInput(query="zzz"))

    assert "Keine Tags gefunden" in result


# ─── catalog_stats ───────────────────────────────────────────────────────────


@respx.mock
async def test_catalog_stats():
    respx.get(f"{CKAN_API_URL}/package_search").mock(
        return_value=_ckan(
            {
                "count": 900,
                "search_facets": {
                    "groups": {
                        "items": [
                            {"name": "bildung", "display_name": "Bildung", "count": 42}
                        ]
                    },
                    "res_format": {
                        "items": [{"name": "CSV", "display_name": "CSV", "count": 500}]
                    },
                },
            }
        )
    )

    result = await zurich_catalog_stats()

    assert "## Open Data Katalog – Stadt Zürich" in result
    assert "**Gesamtzahl Datensätze**: 900" in result
    assert "**Bildung**: 42" in result
    assert "**CSV**: 500" in result


# ─── find_school_data ────────────────────────────────────────────────────────


@respx.mock
async def test_find_school_data_groups_by_author():
    # Every search term hits package_search; one Schulamt dataset + one other.
    respx.get(f"{CKAN_API_URL}/package_search").mock(
        return_value=_ckan(
            {
                "count": 2,
                "results": [
                    {
                        "name": "ssd_schulanlagen",
                        "title": "Schulanlagen",
                        "author": "Schulamt der Stadt Zürich",
                    },
                    {
                        "name": "stat_bevoelkerung",
                        "title": "Bevölkerung",
                        "author": "Statistik Stadt Zürich",
                    },
                ],
            }
        )
    )

    result = await zurich_find_school_data(FindSchoolDataInput())

    assert "## Schulrelevante Datensätze" in result
    # Schulamt author → dedicated section; deduped across the many term queries.
    assert "### Vom Schulamt / SSD" in result
    assert "Schulanlagen" in result
    assert "### Weitere relevante Datensätze" in result
    assert "Bevölkerung" in result


@respx.mock
async def test_find_school_data_with_topic():
    respx.get(f"{CKAN_API_URL}/package_search").mock(
        return_value=_ckan({"count": 0, "results": []})
    )

    result = await zurich_find_school_data(FindSchoolDataInput(topic="Musikschule"))

    assert "## Schulrelevante Datensätze" in result
    assert "**0 Treffer**" in result

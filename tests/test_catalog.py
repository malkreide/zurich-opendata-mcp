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
    AnalyzeDatasetInput,
    FindSchoolDataInput,
    GetDatasetInput,
    ListGroupInput,
    SearchDatasetsInput,
    TagSearchInput,
    zurich_analyze_datasets,
    zurich_catalog_stats,
    zurich_find_school_data,
    zurich_get_dataset,
    zurich_list_categories,
    zurich_list_tags,
    zurich_search_datasets,
)

_SEARCH = f"{CKAN_API_URL}/package_search"
_DATASTORE = f"{CKAN_API_URL}/datastore_search"


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


# ─── search: sort + filter_group params (coverage) ───────────────────────────


@respx.mock
async def test_search_passes_sort_and_filter_group():
    route = respx.get(_SEARCH).mock(return_value=_ckan({"count": 0, "results": []}))

    await zurich_search_datasets(
        SearchDatasetsInput(query="x", sort="title asc", filter_group="bildung")
    )

    params = dict(route.calls[0].request.url.params)
    assert params["sort"] == "title asc"
    assert params["fq"] == "groups:bildung"


# ─── error paths (handle_api_error branches) ─────────────────────────────────


@respx.mock
async def test_get_dataset_error_path():
    respx.get(f"{CKAN_API_URL}/package_show").mock(return_value=httpx.Response(500))

    result = await zurich_get_dataset(GetDatasetInput(dataset_id="x"))

    assert result.isError is True
    assert "Fehler bei Datensatz-Details" in result.content[0].text


@respx.mock
async def test_list_categories_error_path():
    respx.get(f"{CKAN_API_URL}/group_list").mock(return_value=httpx.Response(500))

    result = await zurich_list_categories(ListGroupInput())

    assert "Fehler bei Kategorien" in result


@respx.mock
async def test_list_tags_error_path():
    respx.get(f"{CKAN_API_URL}/tag_list").mock(return_value=httpx.Response(500))

    result = await zurich_list_tags(TagSearchInput(query="x"))

    assert "Fehler bei Tag-Suche" in result


@respx.mock
async def test_catalog_stats_error_path():
    respx.get(_SEARCH).mock(return_value=httpx.Response(500))

    result = await zurich_catalog_stats()

    assert "Fehler bei Katalog-Statistiken" in result


@respx.mock
async def test_find_school_data_error_path():
    respx.get(_SEARCH).mock(return_value=httpx.Response(500))

    result = await zurich_find_school_data(FindSchoolDataInput())

    assert "Fehler bei Schuldaten-Suche" in result


# ─── catalog_stats: facets returned as lists (legacy shape) ──────────────────


@respx.mock
async def test_catalog_stats_facets_as_lists():
    respx.get(_SEARCH).mock(
        return_value=_ckan(
            {
                "count": 10,
                # Legacy `facets` (not `search_facets`) with list values.
                "facets": {
                    "groups": [{"name": "bildung", "count": 5}],
                    "res_format": [{"name": "CSV", "count": 8}],
                },
            }
        )
    )

    result = await zurich_catalog_stats()

    assert "**bildung**: 5" in result
    assert "**CSV**: 8" in result


# ─── analyze: empty, structure off, datastore failure, >15 fields, error ─────


@respx.mock
async def test_analyze_empty():
    respx.get(_SEARCH).mock(return_value=_ckan({"count": 0, "results": []}))

    result = await zurich_analyze_datasets(AnalyzeDatasetInput(query="zzz"))

    assert "Keine Datensätze gefunden" in result.content[0].text
    assert result.structuredContent["total"] == 0


@respx.mock
async def test_analyze_without_structure():
    respx.get(_SEARCH).mock(
        return_value=_ckan(
            {
                "count": 1,
                "results": [{"name": "ds", "title": "DS", "resources": []}],
            }
        )
    )

    result = await zurich_analyze_datasets(
        AnalyzeDatasetInput(query="x", include_structure=False)
    )

    assert result.structuredContent["datasets"][0]["fields"] is None


@respx.mock
async def test_analyze_datastore_failure_is_tolerated():
    respx.get(_SEARCH).mock(
        return_value=_ckan(
            {
                "count": 1,
                "results": [
                    {
                        "name": "ds",
                        "title": "DS",
                        "resources": [
                            {"id": "r1", "name": "R", "format": "CSV", "datastore_active": True}
                        ],
                    }
                ],
            }
        )
    )
    respx.get(_DATASTORE).mock(return_value=httpx.Response(500))

    result = await zurich_analyze_datasets(AnalyzeDatasetInput(query="x"))

    # datastore_search failing → field info simply absent, tool still succeeds.
    assert result.structuredContent["datasets"][0]["datastore_records"] is None


@respx.mock
async def test_analyze_truncates_long_field_list():
    fields = [{"id": "_id", "type": "int"}] + [
        {"id": f"f{i}", "type": "text"} for i in range(17)
    ]
    respx.get(_SEARCH).mock(
        return_value=_ckan(
            {
                "count": 1,
                "results": [
                    {
                        "name": "ds",
                        "title": "DS",
                        "resources": [
                            {"id": "r1", "name": "R", "format": "CSV", "datastore_active": True}
                        ],
                    }
                ],
            }
        )
    )
    respx.get(_DATASTORE).mock(return_value=_ckan({"fields": fields, "total": 1}))

    result = await zurich_analyze_datasets(AnalyzeDatasetInput(query="x"))

    # 17 non-_id fields → markdown notes the 2 beyond the first 15.
    assert "und 2 weitere" in result.content[0].text


@respx.mock
async def test_analyze_error_path():
    respx.get(_SEARCH).mock(return_value=httpx.Response(500))

    result = await zurich_analyze_datasets(AnalyzeDatasetInput(query="x"))

    assert result.isError is True
    assert "Fehler bei Datensatz-Analyse" in result.content[0].text

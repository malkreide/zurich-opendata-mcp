"""respx-backed unit tests for tools/tourism.py (audit M-7 continuation).

Covers category resolution (name + numeric), search-text filtering, language
selection, the unknown-category short-circuit (no HTTP call), and the empty
result branch.
"""

from __future__ import annotations

import httpx
import respx

from zurich_opendata_mcp.config import ZT_API_URL, ZT_CATEGORIES
from zurich_opendata_mcp.tools.tourism import (
    TourismSearchInput,
    zurich_tourism,
)


def _item(
    name_de: str,
    name_en: str = "",
    *,
    desc_de: str = "",
    categories: tuple[str, ...] = ("Altstadt",),
) -> dict:
    return {
        "@type": "Restaurant",
        "name": {"de": name_de, "en": name_en or name_de},
        "disambiguatingDescription": {"de": desc_de, "en": ""},
        "category": {c: {} for c in categories},
        "address": {
            "streetAddress": "Bahnhofstrasse 1",
            "postalCode": "8001",
            "addressLocality": "Zürich",
        },
        "url": {"de": "https://example.ch/de", "en": "https://example.ch/en"},
        "telephone": "+41 44 000 00 00",
        "geo": {"latitude": 47.37, "longitude": 8.54},
    }


@respx.mock
async def test_tourism_resolves_named_category_and_renders():
    route = respx.get(ZT_API_URL).mock(
        return_value=httpx.Response(200, json=[_item("Kornhaus", desc_de="Feines Essen")])
    )

    result = await zurich_tourism(
        TourismSearchInput(category="restaurants", language="de")
    )

    # 'restaurants' resolves to its numeric id on the wire.
    assert dict(route.calls[0].request.url.params)["id"] == str(
        ZT_CATEGORIES["restaurants"]
    )
    assert "## Zürich Tourismus: restaurants" in result
    assert "### Kornhaus" in result
    assert "Feines Essen" in result
    assert "Bahnhofstrasse 1, 8001 Zürich" in result
    assert "+41 44 000 00 00" in result
    assert "47.37, 8.54" in result


@respx.mock
async def test_tourism_numeric_category_passes_through():
    route = respx.get(ZT_API_URL).mock(
        return_value=httpx.Response(200, json=[_item("Test")])
    )

    await zurich_tourism(TourismSearchInput(category="166"))

    assert dict(route.calls[0].request.url.params)["id"] == "166"


@respx.mock
async def test_tourism_search_text_filters():
    respx.get(ZT_API_URL).mock(
        return_value=httpx.Response(
            200,
            json=[
                _item("Vegan Spot", desc_de="rein pflanzlich"),
                _item("Steakhouse", desc_de="Fleisch"),
            ],
        )
    )

    result = await zurich_tourism(
        TourismSearchInput(category="restaurants", search_text="vegan")
    )

    assert "Vegan Spot" in result
    assert "Steakhouse" not in result


@respx.mock
async def test_tourism_language_selection():
    respx.get(ZT_API_URL).mock(
        return_value=httpx.Response(
            200, json=[_item("Kornhaus", name_en="Granary")]
        )
    )

    result = await zurich_tourism(
        TourismSearchInput(category="restaurants", language="en")
    )

    assert "Granary" in result
    assert "Kornhaus" not in result


async def test_tourism_unknown_category_no_http_call():
    # respx with assert_all_called=False and no routes: any HTTP call raises.
    with respx.mock:
        result = await zurich_tourism(TourismSearchInput(category="raumschiff"))

    assert "Unbekannte Kategorie `raumschiff`" in result
    # The known categories are listed as a hint.
    assert "restaurants" in result


@respx.mock
async def test_tourism_empty_result():
    respx.get(ZT_API_URL).mock(return_value=httpx.Response(200, json=[]))

    result = await zurich_tourism(TourismSearchInput(category="restaurants"))

    assert "Keine Tourismus-Einträge gefunden" in result


@respx.mock
async def test_tourism_http_error():
    respx.get(ZT_API_URL).mock(return_value=httpx.Response(500))

    result = await zurich_tourism(TourismSearchInput(category="restaurants"))

    assert "Fehler bei Zürich Tourismus" in result


@respx.mock
async def test_tourism_custom_type_takes_precedence():
    item = _item("Kornhaus")
    item["@customType"] = "Sehenswürdigkeit"
    respx.get(ZT_API_URL).mock(return_value=httpx.Response(200, json=[item]))

    result = await zurich_tourism(TourismSearchInput(category="restaurants"))

    # @customType wins over @type for the rendered Typ line.
    assert "- **Typ**: Sehenswürdigkeit" in result

"""Zürich Tourismus tool."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..clients.tourism import zt_get_data
from ..config import ZT_CATEGORIES
from ..formatters import handle_api_error


class TourismSearchInput(BaseModel):
    """Input für Zürich Tourismus Daten."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: str = Field(
        ...,
        description=(
            "Tourismus-Kategorie. Verfügbar: "
            + ", ".join(f"'{k}'" for k in sorted(ZT_CATEGORIES.keys()))
            + ". Oder eine numerische Kategorie-ID."
        ),
    )
    search_text: str | None = Field(
        default=None,
        description="Optionaler Suchtext zur Filterung der Ergebnisse, z.B. 'Altstadt' oder 'vegan'",
    )
    max_results: int = Field(default=10, description="Maximale Anzahl Ergebnisse", ge=1, le=50)
    language: str = Field(
        default="de",
        description="Sprache der Ergebnisse: 'de', 'en', 'fr', 'it'",
    )


@mcp.tool(
    name="zurich_tourism",
    annotations={
        "title": "Zürich Tourismus Daten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_tourism(params: TourismSearchInput) -> str:
    """Sucht Attraktionen, Restaurants, Hotels und Events über die Zürich Tourismus API.

    Liefert Informationen zu Sehenswürdigkeiten, gastronomischen Angeboten,
    Unterkünften, Aktivitäten und Veranstaltungen in Zürich.
    Daten basieren auf Schema.org-Formaten.

    Returns:
        Markdown-formatierte Liste der Tourismus-Einträge
    """
    try:
        # Resolve category
        if params.category.isdigit():
            cat_id = int(params.category)
        elif params.category.lower() in ZT_CATEGORIES:
            cat_id = ZT_CATEGORIES[params.category.lower()]
        else:
            available = ", ".join(f"`{k}` ({v})" for k, v in sorted(ZT_CATEGORIES.items()))
            return f"Unbekannte Kategorie `{params.category}`. Verfügbar:\n{available}"

        data = await zt_get_data(cat_id)
        lang = params.language

        # Filter by search text
        if params.search_text:
            search_lower = params.search_text.lower()
            filtered = []
            for item in data:
                name = item.get("name", {}).get(lang, "") or ""
                desc = item.get("disambiguatingDescription", {}).get(lang, "") or ""
                categories = " ".join(item.get("category", {}).keys())
                if search_lower in name.lower() or search_lower in desc.lower() or search_lower in categories.lower():
                    filtered.append(item)
            data = filtered

        total = len(data)
        data = data[: params.max_results]

        if not data:
            return (
                f"Keine Tourismus-Einträge gefunden für Kategorie '{params.category}'"
                + (f" mit Filter '{params.search_text}'" if params.search_text else "")
                + "."
            )

        lines = [
            f"## Zürich Tourismus: {params.category}",
            f"**{total} Einträge** (zeige {len(data)})\n",
        ]

        for item in data:
            name = item.get("name", {}).get(lang, "Unbenannt")
            short_desc = item.get("disambiguatingDescription", {}).get(lang, "")
            item_type = item.get("@type", "")
            custom_type = item.get("@customType") or ""
            categories = list(item.get("category", {}).keys())

            # Address
            address = item.get("address", {})
            street = address.get("streetAddress", "") if isinstance(address, dict) else ""
            postal = address.get("postalCode", "") if isinstance(address, dict) else ""
            city = address.get("addressLocality", "") if isinstance(address, dict) else ""
            addr_str = f"{street}, {postal} {city}".strip(", ") if street else ""

            # Contact
            url = item.get("url", {}).get(lang, "") if isinstance(item.get("url"), dict) else ""
            phone = item.get("telephone", "")

            # Geo
            geo = item.get("geo", {})
            lat = geo.get("latitude") if isinstance(geo, dict) else None
            lon = geo.get("longitude") if isinstance(geo, dict) else None

            lines.append(f"### {name}")
            if custom_type:
                lines.append(f"- **Typ**: {custom_type}")
            elif item_type:
                lines.append(f"- **Typ**: {item_type}")
            if categories:
                lines.append(f"- **Kategorien**: {', '.join(categories[:5])}")
            if short_desc:
                lines.append(f"- **Beschreibung**: {short_desc[:250]}")
            if addr_str:
                lines.append(f"- **Adresse**: {addr_str}")
            if phone:
                lines.append(f"- **Telefon**: {phone}")
            if url:
                lines.append(f"- **Web**: {url}")
            if lat and lon:
                lines.append(f"- **Koordinaten**: {lat}, {lon}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Zürich Tourismus")

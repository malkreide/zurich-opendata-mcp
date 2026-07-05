"""Zürich Tourismus tool."""

from __future__ import annotations

from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..clients.tourism import zt_get_data
from ..config import ZT_CATEGORIES, OutputFormat, TourismLanguage
from ..formatters import FORMAT_FIELD_DESC, handle_api_error, json_out


def _tourism_record(item: dict, lang: str) -> dict:
    """Normalise one Schema.org tourism item into a flat record."""
    address = item.get("address", {})
    geo = item.get("geo", {})
    url = item.get("url", {})
    street = address.get("streetAddress", "") if isinstance(address, dict) else ""
    postal = address.get("postalCode", "") if isinstance(address, dict) else ""
    city = address.get("addressLocality", "") if isinstance(address, dict) else ""
    return {
        "name": item.get("name", {}).get(lang, "Unbenannt"),
        "typ": item.get("@customType") or item.get("@type", ""),
        "kategorien": list(item.get("category", {}).keys()),
        "beschreibung": item.get("disambiguatingDescription", {}).get(lang, ""),
        "adresse": f"{street}, {postal} {city}".strip(", ") if street else "",
        "telefon": item.get("telephone", ""),
        "web": url.get(lang, "") if isinstance(url, dict) else "",
        "lat": geo.get("latitude") if isinstance(geo, dict) else None,
        "lon": geo.get("longitude") if isinstance(geo, dict) else None,
    }


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
    language: TourismLanguage = Field(
        default="de",
        description="Sprache der Ergebnisse: 'de', 'en', 'fr', 'it'",
    )
    format: OutputFormat = Field(default="markdown", description=FORMAT_FIELD_DESC)


@mcp.tool(
    name="zurich_tourism",
    annotations=ToolAnnotations(
        title="Zürich Tourismus Daten",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
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

        records = [_tourism_record(item, lang) for item in data]

        if params.format == "json":
            return json_out(
                {
                    "category": params.category,
                    "total": total,
                    "count": len(records),
                    "eintraege": records,
                }
            )

        lines = [
            f"## Zürich Tourismus: {params.category}",
            f"**{total} Einträge** (zeige {len(records)})\n",
        ]

        for rec in records:
            lines.append(f"### {rec['name']}")
            if rec["typ"]:
                lines.append(f"- **Typ**: {rec['typ']}")
            if rec["kategorien"]:
                lines.append(f"- **Kategorien**: {', '.join(rec['kategorien'][:5])}")
            if rec["beschreibung"]:
                lines.append(f"- **Beschreibung**: {rec['beschreibung'][:250]}")
            if rec["adresse"]:
                lines.append(f"- **Adresse**: {rec['adresse']}")
            if rec["telefon"]:
                lines.append(f"- **Telefon**: {rec['telefon']}")
            if rec["web"]:
                lines.append(f"- **Web**: {rec['web']}")
            if rec["lat"] and rec["lon"]:
                lines.append(f"- **Koordinaten**: {rec['lat']}, {rec['lon']}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Zürich Tourismus")

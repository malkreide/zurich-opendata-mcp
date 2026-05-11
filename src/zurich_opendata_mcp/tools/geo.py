"""Geoportal WFS tools."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..clients.wfs import wfs_get_features
from ..config import GEOPORTAL_LAYERS, GeoLayerId
from ..formatters import handle_api_error


@mcp.tool(
    name="zurich_geo_layers",
    annotations={
        "title": "Verfügbare Geodaten-Layer",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def zurich_geo_layers() -> str:
    """Listet alle verfügbaren WFS-Layer des Geoportals der Stadt Zürich auf.

    Zeigt Layer-ID, WFS-Service-Name, Typename und Beschreibung für jeden
    verfügbaren Geodatensatz. Die IDs können mit dem Tool zurich_geo_features
    verwendet werden.

    Returns:
        Markdown-formatierte Liste aller Geodaten-Layer
    """
    lines = [
        "## Verfügbare Geoportal-Layer (WFS)",
        f"**Anzahl**: {len(GEOPORTAL_LAYERS)}\n",
        "| Layer-ID | Beschreibung | WFS-Service |",
        "|---|---|---|",
    ]
    for layer_id, (service, typename, desc) in sorted(GEOPORTAL_LAYERS.items()):
        lines.append(f"| `{layer_id}` | {desc} | {service} |")

    lines.append("\n*Nutze `zurich_geo_features` mit einer Layer-ID, um GeoJSON-Daten abzurufen.*")
    return "\n".join(lines)


class GeoFeaturesInput(BaseModel):
    """Input für Geodaten-Abfragen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    layer_id: GeoLayerId = Field(
        ...,
        description=f"Layer-ID. Verfügbar: {', '.join(sorted(GEOPORTAL_LAYERS.keys()))}",
    )
    max_features: int = Field(
        default=50,
        description="Maximale Anzahl Features (max. 500)",
        ge=1,
        le=500,
    )
    property_filter: str | None = Field(
        default=None,
        description=(
            "CQL-Filter für Eigenschaften, z.B. \"kategorie = 'Kindergarten'\" "
            "oder \"name LIKE '%Wasser%'\". Feldnamen hängen vom Layer ab."
        ),
    )


@mcp.tool(
    name="zurich_geo_features",
    annotations={
        "title": "Geodaten abrufen (GeoJSON)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def zurich_geo_features(params: GeoFeaturesInput) -> str:
    """Ruft Geodaten aus dem WFS-Geoportal der Stadt Zürich als GeoJSON ab.

    Liefert geografische Features (Punkte, Polygone) mit Eigenschaften
    wie Name, Adresse, Kategorie etc. Nützlich für Schulanlagen,
    Stadtkreise, Spielplätze, Veloprüfstrecken und mehr.

    Returns:
        GeoJSON FeatureCollection mit Features und ihren Eigenschaften
    """
    try:
        # `layer_id` is a `Literal` matching GEOPORTAL_LAYERS.keys() (enforced
        # by Pydantic at validation time + a drift test in test_server.py),
        # so a missing key here would be a programming error, not user input.
        service_name, typename, description = GEOPORTAL_LAYERS[params.layer_id]

        geojson = await wfs_get_features(
            service_name=service_name,
            typename=typename,
            max_features=params.max_features,
            cql_filter=params.property_filter,
        )

        features = geojson.get("features", [])
        total = len(features)

        lines = [
            f"## Geodaten: {description}",
            f"**Layer**: `{params.layer_id}` ({typename})",
            f"**Features**: {total}\n",
        ]

        if params.property_filter:
            lines.append(f"**Filter**: `{params.property_filter}`\n")

        # Show summary of first features
        for i, feat in enumerate(features[:20], 1):
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            geom_type = geom.get("type", "?")
            coords = geom.get("coordinates", [])

            name = props.get("name") or props.get("bezeichnung") or props.get("einheit") or f"Feature {i}"
            kategorie = props.get("kategorie") or props.get("typ") or ""
            adresse = props.get("adresse") or props.get("strasse") or ""

            label = f"**{name}**"
            if kategorie:
                label += f" ({kategorie})"
            if adresse:
                label += f" – {adresse}"

            if geom_type == "Point" and coords:
                label += f" 📍 [{coords[1]:.5f}, {coords[0]:.5f}]"

            lines.append(f"{i}. {label}")

        if total > 20:
            lines.append(f"\n*… und {total - 20} weitere Features*")

        # Show property names from first feature
        if features:
            prop_keys = [k for k in features[0].get("properties", {}).keys() if k not in ("objectid", "geometrie_gdo")]
            lines.append(f"\n**Verfügbare Felder**: {', '.join(prop_keys[:20])}")

        lines.append(f"\n*Volle GeoJSON-Daten via `zurich://geo/{params.layer_id}` Resource*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Geodaten-Abfrage")

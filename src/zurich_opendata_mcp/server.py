#!/usr/bin/env python3
"""
Zurich Open Data MCP Server — v0.2.0

AI-nativer Zugang zu Open Data der Stadt Zürich:
  · CKAN:       data.stadt-zuerich.ch — 900+ offene Datensätze
  · ParkenDD:   Echtzeit-Parkplatzbelegung (36 Parkhäuser)
  · Geoportal:  WFS Geodaten (Schulanlagen, Quartiere, Spielplätze etc.)
  · Paris API:  Parlamentsinformationen des Gemeinderats
  · Tourismus:  Attraktionen, Restaurants, Hotels (Zürich Tourismus)
  · SPARQL:     Linked Data / Statistiken (ld.stadt-zuerich.ch)

Kein API-Schlüssel erforderlich. Alle Daten öffentlich zugänglich unter offenen Lizenzen.

Entry point — tool/resource implementations live in ``zurich_opendata_mcp.tools.*``
and register themselves on the shared FastMCP instance via decorator side-effects.
"""

from __future__ import annotations

from .app import mcp

# Importing the tool modules registers them on `mcp` via @mcp.tool / @mcp.resource.
from .tools import (  # noqa: F401
    catalog,
    datastore,
    geo,
    parliament,
    realtime,
    resources,
    sparql,
    strb,
    tourism,
)

# Re-exports — kept for backward compatibility with tests and external imports
# that previously pulled symbols directly from `zurich_opendata_mcp.server`.
from .tools.catalog import (  # noqa: F401
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
from .tools.datastore import (  # noqa: F401
    DatastoreQueryInput,
    DatastoreSqlInput,
    zurich_datastore_query,
    zurich_datastore_sql,
)
from .tools.geo import (  # noqa: F401
    GeoFeaturesInput,
    zurich_geo_features,
    zurich_geo_layers,
)
from .tools.parliament import (  # noqa: F401
    ParliamentMembersInput,
    ParliamentSearchInput,
    zurich_parliament_members,
    zurich_parliament_search,
)
from .tools.realtime import (  # noqa: F401
    AirQualityInput,
    PedestrianInput,
    VBZPassengersInput,
    WaterWeatherInput,
    WeatherLiveInput,
    zurich_air_quality,
    zurich_parking_live,
    zurich_pedestrian_traffic,
    zurich_vbz_passengers,
    zurich_water_weather,
    zurich_weather_live,
)
from .tools.sparql import SparqlQueryInput, zurich_sparql  # noqa: F401
from .tools.strb import (  # noqa: F401
    BeschluesseDepartementInput,
    GetSTRBDetailInput,
    SearchSTRBInput,
    get_beschluesse_by_departement,
    get_stadtratsbeschluss_detail,
    search_stadtratsbeschluesse,
)
from .tools.tourism import TourismSearchInput, zurich_tourism  # noqa: F401


def main() -> None:
    """Console entry point."""
    import sys

    if "--http" in sys.argv:
        port_idx = sys.argv.index("--port") + 1 if "--port" in sys.argv else None
        port = int(sys.argv[port_idx]) if port_idx else 8000
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()

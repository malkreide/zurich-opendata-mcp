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


def _port(value: str) -> int:
    p = int(value)
    if not 1 <= p <= 65535:
        import argparse
        raise argparse.ArgumentTypeError(f"port must be in 1..65535, got {p}")
    return p


def _parse_args(argv: list[str] | None = None):
    import argparse

    parser = argparse.ArgumentParser(
        prog="zurich-opendata-mcp",
        description="Zurich Open Data MCP Server (stdio by default).",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run over Streamable HTTP instead of stdio.",
    )
    parser.add_argument(
        "--port",
        type=_port,
        default=8000,
        help="HTTP port (1-65535, default: 8000; only used with --http).",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Console entry point."""
    import logging
    import os
    import sys

    # Logs go to stderr so they don't collide with the MCP stdio framing on
    # stdout. Level can be overridden via ZURICH_OPENDATA_LOG_LEVEL.
    logging.basicConfig(
        level=os.environ.get("ZURICH_OPENDATA_LOG_LEVEL", "WARNING").upper(),
        stream=sys.stderr,
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
    )

    args = _parse_args()
    if args.http:
        mcp.run(transport="streamable-http", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()

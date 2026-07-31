#!/usr/bin/env python3
"""
Zurich Open Data MCP Server

AI-nativer Zugang zu Open Data der Stadt Zürich:
  · CKAN:       data.stadt-zuerich.ch — 900+ offene Datensätze
  · ParkenDD:   Echtzeit-Parkplatzbelegung (36 Parkhäuser)
  · Geoportal:  WFS Geodaten (Schulanlagen, Quartiere, Spielplätze etc.)
  · Paris API:  Parlamentsinformationen des Gemeinderats
  · Tourismus:  Attraktionen, Restaurants, Hotels (Zürich Tourismus)
  · SPARQL:     Linked Data / Statistiken (ld.stadt-zuerich.ch)

Kein API-Schlüssel erforderlich. Alle Daten öffentlich zugänglich unter offenen Lizenzen.

Entry point — tool/resource implementations live in ``zurich_opendata_mcp.tools.*``
and register themselves on the shared MCPServer instance via decorator side-effects.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping

from mcp.server.transport_security import TransportSecuritySettings

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
    GeoLayersInput,
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
    ParkingLiveInput,
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
    zurich_strb_by_department,
    zurich_strb_detail,
    zurich_strb_search,
)
from .tools.tourism import TourismSearchInput, zurich_tourism  # noqa: F401

logger = logging.getLogger(__name__)

# Loopback spellings, in the three forms the SDK also treats as local.
_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def _port(value: str) -> int:
    p = int(value)
    if not 1 <= p <= 65535:
        import argparse
        raise argparse.ArgumentTypeError(f"port must be in 1..65535, got {p}")
    return p


def _resolve_allowed_hosts(env: Mapping[str, str] | None = None) -> list[str]:
    """Inbound Host allow-list from ``MCP_ALLOWED_HOSTS``.

    Comma-separated and compared verbatim, so an entry carries its port —
    ``zurich.example.ch:8000``. Empty by default.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    return [h.strip() for h in source.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]


def _build_transport_security(
    host: str, port: int, env: Mapping[str, str] | None = None
) -> TransportSecuritySettings | None:
    """Host/Origin allow-list for the HTTP transport.

    Guards against DNS rebinding: a page on the operator's network resolves its
    own name to this server's address and then talks to it from the browser.
    The check asks under *which name* the server was addressed — a question no
    origin rule and no token can answer, because the attacking page is a
    legitimate browser context.

    Three cases, in the order decided:

    - ``MCP_ALLOWED_HOSTS`` set — that list verbatim, plus loopback so
      container health checks keep working.
    - loopback bind, no list — loopback only. The SDK infers exactly this from
      a loopback ``host``; stating it makes the protection independent of that
      inference.
    - non-loopback bind, no list — ``None``, i.e. the check stays off, and
      ``main()`` warns. That is the gateway-fronted deployment, where whatever
      terminates TLS validates ``Host``.

    The last case is deliberately not a guess. On ``0.0.0.0`` the reachable
    name is unknowable in-process, and a guessed list rejects the very
    deployment it is meant to protect — HTTP 421 on every real request.

    Unlike the sibling servers in this portfolio there is no CORS layer here to
    fold in: this server has no configurable origin list, so the transport's
    origins are derived from the host list alone.
    """
    loopback = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}
    configured = _resolve_allowed_hosts(env)
    if configured:
        hosts = set(configured) | loopback
    elif host in _LOOPBACK_HOSTS:
        hosts = loopback | {f"{host}:{port}"}
    else:
        return None

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(hosts),
        allowed_origins=sorted(f"http://{h}" for h in hosts),
    )


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
        "--host",
        default="127.0.0.1",
        help=(
            "HTTP bind address (default: 127.0.0.1; only used with --http). "
            "The loopback default is deliberate — binding 0.0.0.0 exposes the "
            "server on every interface. When you do, set MCP_ALLOWED_HOSTS to "
            "the names it is reachable under, or Host validation is left to "
            "whatever fronts it."
        ),
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
        security = _build_transport_security(args.host, args.port)
        if security is None:
            logger.warning(
                "binding HTTP server to non-loopback host %s with no "
                "MCP_ALLOWED_HOSTS — Host/Origin validation is off and left to "
                "whatever fronts this server; set MCP_ALLOWED_HOSTS to the "
                "names it is reachable under (e.g. 'zurich.example.ch:%d') to "
                "enforce it here as well",
                args.host,
                args.port,
            )
        # mcp 2.x: the bind address is a run() kwarg — MCPServer.settings no
        # longer carries host/port. `host` must be the address uvicorn actually
        # binds, because the SDK derives its DNS-rebinding allow-list from it:
        # leaving it at the default while binding 0.0.0.0 would answer every
        # real request with 421. `transport_security` travels the same way, so
        # the allow-list is stated here rather than inferred from that default.
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            transport_security=security,
        )
    else:
        mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()

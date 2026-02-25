"""
Shared HTTP client and utilities for Zurich Open Data APIs.

Supported APIs:
- CKAN (data.stadt-zuerich.ch) – Open Data catalog
- ParkenDD – Real-time parking data
- Geoportal WFS – Geodata (GeoJSON)
- Paris API – Parliamentary information system (Gemeinderat)
- Zürich Tourismus API v2 – Attractions, restaurants, accommodation
- SPARQL (ld.stadt-zuerich.ch) – Linked Data / statistics
"""

import xml.etree.ElementTree as ET
from typing import Any, Optional

import httpx

# ─── Constants ────────────────────────────────────────────────────────────────

CKAN_BASE_URL = "https://data.stadt-zuerich.ch"
CKAN_API_URL = f"{CKAN_BASE_URL}/api/3/action"
PARKENDD_URL = "https://api.parkendd.de/Zuerich"
WFS_BASE_URL = "https://www.ogd.stadt-zuerich.ch/wfs/geoportal"
PARIS_API_URL = "https://www.gemeinderat-zuerich.ch/api"
ZT_API_URL = "https://www.zuerich.com/en/api/v2/data"
SPARQL_URL = "https://ld.stadt-zuerich.ch/query"

REQUEST_TIMEOUT = 30.0
USER_AGENT = "ZurichOpenDataMCP/0.3 (MCP Server; +https://github.com/schulamt-zurich)"

ZURICH_GROUPS = [
    "arbeit-und-erwerb",
    "basiskarten",
    "bauen-und-wohnen",
    "bevolkerung",
    "bildung",
    "energie",
    "finanzen",
    "freizeit",
    "gesundheit",
    "kriminalitat",
    "kultur",
    "mobilitat",
    "politik",
    "preise",
    "soziales",
    "tourismus",
    "umwelt",
    "verwaltung",
    "volkswirtschaft",
]

# Geoportal WFS layers – dataset name → (WFS service name, primary typename, description)
GEOPORTAL_LAYERS: dict[str, tuple[str, str, str]] = {
    "schulanlagen": ("Schulanlagen", "poi_kindergarten_view", "Schulstandorte (Kindergärten, Schulhäuser, Horte)"),
    "schulkreise": ("Schulkreise", "adm_schulkreise_a", "Schulkreis-Grenzen (Polygone)"),
    "schulwege": ("Schulweguebergaenge", "poi_schulweg_att", "Schulweg-Übergänge und Gefahrenstellen"),
    "stadtkreise": ("Stadtkreise", "adm_stadtkreise_a", "Stadtkreis-Grenzen (Polygone)"),
    "spielplaetze": ("POI_oeffentliche_Spielplaetze", "poi_oeffentl_spielplatz_view", "Öffentliche Spielplätze"),
    "kreisbuero": ("Kreisbuero", "poi_kreisbuero_view", "Kreisbüros der Stadt Zürich"),
    "sammelstelle": ("Sammelstelle", "poi_sammelstelle_view", "Abfall-Sammelstellen"),
    "sport": ("Sport", "poi_sport_view", "Sportanlagen und -einrichtungen"),
    "klimadaten": ("Klimadaten", "klimadaten_raster", "Klimadaten (Raster, Temperaturen, Hitzeinseln)"),
    "lehrpfade": ("Lehrpfade", "poi_lehrpfad_view", "Lehrpfade und Bildungswege"),
    "stimmlokale": ("Stimmlokale", "poi_stimmlokale_view", "Abstimmungs- und Wahllokale"),
    "sozialzentrum": ("Sozialzentrum", "poi_sozialzentrum_view", "Sozialzentren"),
    "velopruefstrecken": ("Velopruefstrecken", "poi_velopruefstrecke_view", "Veloprüfstrecken für Schulen"),
    "familienberatung": ("Treffpunkt_Familienberatung", "poi_familienberatung_view", "Familienberatungs-Treffpunkte"),
}


# ─── HTTP Client ──────────────────────────────────────────────────────────────


async def _get_client() -> httpx.AsyncClient:
    """Create a configured async HTTP client."""
    return httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


async def ckan_request(action: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Make a CKAN API request and return the result.

    Args:
        action: CKAN API action name (e.g. 'package_search')
        params: Query parameters

    Returns:
        The 'result' field from the CKAN response

    Raises:
        RuntimeError: If the CKAN API returns an error
    """
    async with await _get_client() as client:
        url = f"{CKAN_API_URL}/{action}"
        response = await client.get(url, params=params or {})
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            error_msg = data.get("error", {}).get("message", "Unknown CKAN error")
            raise RuntimeError(f"CKAN API error: {error_msg}")

        return data["result"]


async def http_get_json(url: str, params: Optional[dict[str, Any]] = None) -> Any:
    """Generic JSON GET request for non-CKAN APIs."""
    async with await _get_client() as client:
        response = await client.get(url, params=params or {})
        response.raise_for_status()
        return response.json()


# ─── Formatting Helpers ───────────────────────────────────────────────────────


def format_dataset_summary(dataset: dict[str, Any]) -> str:
    """Format a CKAN dataset into a readable Markdown summary."""
    title = dataset.get("title", "Unbekannt")
    name = dataset.get("name", "")
    author = dataset.get("author", "Unbekannt")
    notes = (dataset.get("notes") or "")[:300]
    license_title = dataset.get("license_title", "Unbekannt")
    num_resources = dataset.get("num_resources", 0)
    modified = dataset.get("metadata_modified", "")[:10]
    update_interval = dataset.get("updateInterval", [])
    groups = [g.get("title", g.get("name", "")) for g in dataset.get("groups", [])]
    tags = [t.get("display_name", t.get("name", "")) for t in dataset.get("tags", [])]

    url = f"{CKAN_BASE_URL}/dataset/{name}"

    lines = [
        f"### {title}",
        f"- **ID**: `{name}`",
        f"- **Autor**: {author}",
        f"- **Lizenz**: {license_title}",
        f"- **Ressourcen**: {num_resources}",
        f"- **Letzte Änderung**: {modified}",
    ]
    if update_interval:
        lines.append(f"- **Aktualisierung**: {', '.join(update_interval)}")
    if groups:
        lines.append(f"- **Kategorien**: {', '.join(groups)}")
    if tags:
        lines.append(f"- **Tags**: {', '.join(tags[:10])}")
    if notes:
        lines.append(f"- **Beschreibung**: {notes}...")
    lines.append(f"- **URL**: {url}")

    return "\n".join(lines)


def format_resource_info(resource: dict[str, Any]) -> str:
    """Format a CKAN resource into a readable summary."""
    return (
        f"  - **{resource.get('name', 'Unbenannt')}** "
        f"({resource.get('format', '?')}) – "
        f"{resource.get('url', 'Keine URL')}"
    )


def handle_api_error(e: Exception, context: str = "") -> str:
    """Consistent error formatting."""
    prefix = f"Fehler bei {context}: " if context else "Fehler: "
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 404:
            return f"{prefix}Ressource nicht gefunden. Bitte ID/Name prüfen."
        elif status == 403:
            return f"{prefix}Zugriff verweigert."
        elif status == 429:
            return f"{prefix}Zu viele Anfragen. Bitte warten."
        return f"{prefix}HTTP-Fehler {status}"
    elif isinstance(e, httpx.TimeoutException):
        return f"{prefix}Zeitüberschreitung. Bitte erneut versuchen."
    return f"{prefix}{type(e).__name__}: {e}"


# ─── Geoportal WFS Client ────────────────────────────────────────────────────


async def wfs_get_features(
    service_name: str,
    typename: str,
    max_features: int = 50,
    output_format: str = "GeoJSON",
    cql_filter: Optional[str] = None,
) -> dict[str, Any]:
    """Fetch features from the Zurich Geoportal WFS."""
    url = f"{WFS_BASE_URL}/{service_name}"
    params: dict[str, str] = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typename": typename,
        "outputFormat": output_format,
        "maxFeatures": str(max_features),
    }
    if cql_filter:
        params["CQL_FILTER"] = cql_filter

    async with await _get_client() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


# ─── Paris API Client (Gemeinderat) ──────────────────────────────────────────

PARIS_NAMESPACES = {
    "sr": "http://www.cmiag.ch/cdws/searchDetailResponse",
    "g": "http://www.cmiag.ch/cdws/Geschaeft",
    "k": "http://www.cmiag.ch/cdws/Kontakt",
    "b": "http://www.cmiag.ch/cdws/Behoerdenmandat",
}


async def paris_search(
    index: str,
    cql_query: str,
    start: int = 1,
    max_results: int = 10,
) -> ET.Element:
    """Search the Paris parliamentary information API.

    Args:
        index: Index name (geschaeft, kontakt, behoerdenmandat, sitzung, etc.)
        cql_query: CQL query string
        start: First result number (1-based)
        max_results: Maximum number of results

    Returns:
        Parsed XML ElementTree root
    """
    url = f"{PARIS_API_URL}/{index}/searchdetails"
    params = {
        "q": cql_query,
        "l": "de-CH",
        "s": str(start),
        "m": str(max_results),
    }
    async with await _get_client() as client:
        response = await client.get(url, params=params, follow_redirects=True)
        response.raise_for_status()
        return ET.fromstring(response.content)


def paris_extract_text(element: Optional[ET.Element], default: str = "") -> str:
    """Safely extract text from an XML element."""
    if element is not None and element.text:
        return element.text.strip()
    return default


def paris_get_num_hits(root: ET.Element) -> int:
    """Get total number of hits from Paris API response."""
    return int(root.get("numHits", "0"))


# ─── Zürich Tourismus API Client ─────────────────────────────────────────────

# Major ZT category IDs for quick reference
ZT_CATEGORIES = {
    "uebernachten": 71,
    "aktivitaeten": 99,
    "restaurants": 166,
    "shopping": 130,
    "nachtleben": 139,
    "kultur": 145,
    "events": 136,
    "touren": 189,
    "natur": 157,
    "sport": 159,
    "familien": 175,
    "museen": 152,
}


async def zt_get_categories() -> list[dict]:
    """Get all Zürich Tourismus categories."""
    return await http_get_json(ZT_API_URL)


async def zt_get_data(category_id: int) -> list[dict]:
    """Get data for a specific ZT category."""
    return await http_get_json(f"{ZT_API_URL}?id={category_id}")


# ─── SPARQL Client ───────────────────────────────────────────────────────────


async def sparql_query(query: str) -> dict[str, Any]:
    """Execute a SPARQL query against the Zurich Linked Data endpoint."""
    async with await _get_client() as client:
        response = await client.get(
            SPARQL_URL,
            params={"query": query},
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        response.raise_for_status()
        return response.json()

"""Endpoints, layer maps and other static configuration."""

from __future__ import annotations

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

PARIS_NAMESPACES = {
    "sr": "http://www.cmiag.ch/cdws/searchDetailResponse",
    "g": "http://www.cmiag.ch/cdws/Geschaeft",
    "k": "http://www.cmiag.ch/cdws/Kontakt",
    "b": "http://www.cmiag.ch/cdws/Behoerdenmandat",
}

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

# --- Resource IDs for realtime DataStore sources ---
METEO_RESOURCE_ID = "f9aa1373-404f-443b-b623-03ff02d2d0b7"  # ugz_ogd_meteo_h1_2026
AIR_QUALITY_RESOURCE_ID = "90410203-4b4f-4a65-9015-1fca2792e04d"  # ugz_ogd_air_h1_2026
WATER_TIEFENBRUNNEN_ID = "f86b3581-6fbc-4337-ab1a-b6ead9d15daf"
WATER_MYTHENQUAI_ID = "61e26c94-c521-473f-b7bf-bb0d73f21e9f"
PEDESTRIAN_RESOURCE_ID = "ec1fc740-8e54-4116-aab7-3394575b4666"  # hystreet
VBZ_REISENDE_ID = "38b0c1e5-1f4e-444d-975c-61a462aa8ca6"
VBZ_LINIE_ID = "463f92e0-5b20-44b3-b27f-59499e331e8d"
VBZ_HALTESTELLEN_ID = "948b6347-8988-4705-9b08-45f0208a15da"

# Stadtratsbeschlüsse (STRB)
STRB_RESOURCE_ID = "35c97bec-f8de-4521-814e-704dc98f71a2"

STRB_DEPARTEMENTE = [
    "Departement der Industriellen Betriebe (DIB)",
    "Finanzdepartement (FD)",
    "Gesundheits- und Umweltdepartement (GUD)",
    "Hochbaudepartement (HBD)",
    "Präsidialdepartement (PRD)",
    "Rechtskonsulent (RK)",
    "Schul- und Sportdepartement (SSD)",
    "Sicherheitsdepartement (SID)",
    "Sozialdepartement (SD)",
    "Stadtkanzlei (SKZ)",
    "Tiefbau- und Entsorgungsdepartement (TED)",
]

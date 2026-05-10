"""Real-time tools: parking, weather, air quality, water, pedestrians, VBZ."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import (
    AIR_QUALITY_RESOURCE_ID,
    METEO_RESOURCE_ID,
    PARKENDD_URL,
    PEDESTRIAN_RESOURCE_ID,
    VBZ_HALTESTELLEN_ID,
    VBZ_LINIE_ID,
    VBZ_REISENDE_ID,
    WATER_MYTHENQUAI_ID,
    WATER_TIEFENBRUNNEN_ID,
    WaterStation,
)
from ..formatters import handle_api_error, md_cell
from ..http_client import ckan_request, http_get_json


@mcp.tool(
    name="zurich_parking_live",
    annotations={
        "title": "Echtzeit-Parkplatzdaten Zürich",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def zurich_parking_live() -> str:
    """Ruft Echtzeit-Parkplatz-Belegungsdaten für die Stadt Zürich ab.

    Liefert aktuelle Daten von 36 Parkhäusern und Parkplätzen:
    freie Plätze, Gesamtkapazität, Standort und Status.
    Datenquelle: ParkenDD API.

    Returns:
        Markdown-Tabelle mit aktuellen Parkhaus-Belegungen
    """
    try:
        data = await http_get_json(PARKENDD_URL)
        lots = data.get("lots", [])
        last_updated = data.get("last_updated", "unbekannt")

        lines = [
            "## Parkplatzbelegung Zürich",
            f"*Stand: {last_updated}*\n",
            "| Parkhaus | Frei | Total | Belegt % | Status |",
            "|----------|------|-------|----------|--------|",
        ]

        for lot in sorted(lots, key=lambda x: x.get("name", "")):
            name = md_cell(lot.get("name", "?"))
            free = lot.get("free", 0)
            total = lot.get("total", 0)
            state = lot.get("state", "?")
            pct = round((1 - free / total) * 100) if total > 0 else 0
            status_icon = "🟢" if state == "open" else "🔴"
            lines.append(f"| {name} | {free} | {total} | {pct}% | {status_icon} {md_cell(state)} |")

        lines.append(f"\n**Gesamt**: {len(lots)} Parkhäuser")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Parkplatz-Daten")


class WeatherLiveInput(BaseModel):
    """Input für Live-Wetterdaten."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    station: str | None = Field(
        default=None,
        description=(
            "Messstation filtern (z.B. 'Zch_Stampfenbachstrasse', "
            "'Zch_Schimmelstrasse', 'Zch_Rosengartenstrasse'). "
            "Leer = alle Stationen."
        ),
    )
    parameter: str | None = Field(
        default=None,
        description=(
            "Messparameter filtern: 'T' (Temperatur °C), 'Hr' (Luftfeuchte %), "
            "'p' (Luftdruck hPa), 'RainDur' (Regendauer min). Leer = alle."
        ),
    )
    limit: int = Field(default=20, description="Anzahl Messwerte (max. 100)", ge=1, le=100)


@mcp.tool(
    name="zurich_weather_live",
    annotations={
        "title": "Aktuelle Wetterdaten Zürich",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def zurich_weather_live(params: WeatherLiveInput) -> str:
    """Liefert stündlich aktualisierte Wetterdaten der UGZ-Messstationen Zürich.

    Datenquelle: Umwelt- und Gesundheitsschutz Stadt Zürich (UGZ).
    Messstationen: Stampfenbachstrasse, Schimmelstrasse, Rosengartenstrasse,
    Heubeeribüel, Kaserne.

    Returns:
        Aktuelle Temperatur, Luftfeuchte, Luftdruck, Regendauer je Station
    """
    try:
        api_params: dict = {
            "resource_id": METEO_RESOURCE_ID,
            "sort": "Datum desc",
            "limit": params.limit,
        }
        filters = {}
        if params.station:
            filters["Standort"] = params.station
        if params.parameter:
            filters["Parameter"] = params.parameter
        if filters:
            api_params["filters"] = json.dumps(filters)

        result = await ckan_request("datastore_search", api_params)
        records = result.get("records", [])

        if not records:
            return "Keine Wetterdaten gefunden. Standort/Parameter prüfen."

        lines = ["## 🌤️ Aktuelle Wetterdaten Zürich\n"]
        lines.append(f"*Quelle: UGZ Messnetz – {result.get('total', '?')} Messwerte total*\n")

        # Group by timestamp for better readability
        by_time: dict[str, list] = {}
        for r in records:
            ts = r.get("Datum", "?")
            by_time.setdefault(ts, []).append(r)

        for ts, measurements in list(by_time.items())[:5]:
            lines.append(f"### {ts}")
            for m in measurements:
                station = m.get("Standort", "?")
                param = m.get("Parameter", "?")
                value = m.get("Wert", "?")
                status = m.get("Status", "")

                # Human-readable parameter names
                param_names = {
                    "T": "🌡️ Temperatur",
                    "Hr": "💧 Luftfeuchte",
                    "p": "📊 Luftdruck",
                    "RainDur": "🌧️ Regendauer",
                }
                display = param_names.get(param, param)
                unit = {"T": "°C", "Hr": "%", "p": "hPa", "RainDur": "min"}.get(param, "")
                status_str = f" ⚠️ {status}" if status and status != "provisorisch" else ""

                lines.append(f"- **{station}** – {display}: **{value} {unit}**{status_str}")
            lines.append("")

        lines.append("---")
        lines.append("*Daten: data.stadt-zuerich.ch – stündlich aktualisiert*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Wetterdaten")


class AirQualityInput(BaseModel):
    """Input für Live-Luftqualitätsdaten."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    station: str | None = Field(
        default=None,
        description=(
            "Messstation: 'Zch_Stampfenbachstrasse', 'Zch_Schimmelstrasse', "
            "'Zch_Rosengartenstrasse', 'Zch_Heubeeribüel', 'Zch_Kaserne'. "
            "Leer = alle."
        ),
    )
    parameter: str | None = Field(
        default=None,
        description=(
            "Schadstoff: 'NO2' (Stickstoffdioxid), 'O3' (Ozon), "
            "'PM10' (Feinstaub), 'PM2.5', 'NOx', 'SO2', 'CO'. Leer = alle."
        ),
    )
    limit: int = Field(default=30, description="Anzahl Messwerte (max. 100)", ge=1, le=100)


@mcp.tool(
    name="zurich_air_quality",
    annotations={
        "title": "Luftqualität Zürich (Echtzeit)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def zurich_air_quality(params: AirQualityInput) -> str:
    """Liefert stündlich aktualisierte Luftqualitätsmessungen aus Zürich.

    Datenquelle: Umwelt- und Gesundheitsschutz Stadt Zürich (UGZ).
    Parameter: NO2, O3, PM10, PM2.5, NOx, SO2, CO u.a.

    Returns:
        Aktuelle Schadstoffwerte je Station mit Einheiten
    """
    try:
        api_params: dict = {
            "resource_id": AIR_QUALITY_RESOURCE_ID,
            "sort": "Datum desc",
            "limit": params.limit,
        }
        filters = {}
        if params.station:
            filters["Standort"] = params.station
        if params.parameter:
            filters["Parameter"] = params.parameter
        if filters:
            api_params["filters"] = json.dumps(filters)

        result = await ckan_request("datastore_search", api_params)
        records = result.get("records", [])

        if not records:
            return "Keine Luftqualitätsdaten gefunden."

        lines = ["## 🌬️ Luftqualität Zürich\n"]
        lines.append(f"*Quelle: UGZ Messnetz – {result.get('total', '?')} Messwerte total*\n")

        # Group by timestamp
        by_time: dict[str, list] = {}
        for r in records:
            ts = r.get("Datum", "?")
            by_time.setdefault(ts, []).append(r)

        for ts, measurements in list(by_time.items())[:3]:
            lines.append(f"### {ts}")

            # Sub-group by station
            by_station: dict[str, list] = {}
            for m in measurements:
                st = m.get("Standort", "?")
                by_station.setdefault(st, []).append(m)

            for station, meas in by_station.items():
                values = []
                for m in meas:
                    param = m.get("Parameter", "?")
                    value = m.get("Wert", "?")
                    unit = m.get("Einheit", "")
                    if value is not None and value != "":
                        values.append(f"{param}={value} {unit}")
                if values:
                    lines.append(f"- **{station}**: {', '.join(values)}")
            lines.append("")

        # WHO guideline hints
        lines.append("---")
        lines.append("*WHO-Grenzwerte (24h): PM2.5 ≤15 µg/m³, PM10 ≤45 µg/m³, NO₂ ≤25 µg/m³*")
        lines.append("*Daten: data.stadt-zuerich.ch – stündlich aktualisiert*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Luftqualität")


class WaterWeatherInput(BaseModel):
    """Input für Wasserschutzpolizei-Wetterstationen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    station: WaterStation = Field(
        default="tiefenbrunnen",
        description="Messstation: 'tiefenbrunnen' oder 'mythenquai'",
    )
    limit: int = Field(default=6, description="Anzahl Messwerte (max. 50)", ge=1, le=50)


@mcp.tool(
    name="zurich_water_weather",
    annotations={
        "title": "See-/Wasserwetter Zürich",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def zurich_water_weather(params: WaterWeatherInput) -> str:
    """Liefert Echtzeit-Wetterdaten der Wasserschutzpolizei Zürich.

    Stationen am Zürichsee: Tiefenbrunnen und Mythenquai.
    10-Minuten-Intervall mit See- und Lufttemperatur, Wind, Wasserstand,
    Niederschlag, Luftdruck, Taupunkt, Globalstrahlung.

    Returns:
        Aktuelle See-Messwerte mit Wasser- und Lufttemperatur, Wind, Pegel
    """
    try:
        resource_id = WATER_TIEFENBRUNNEN_ID if params.station == "tiefenbrunnen" else WATER_MYTHENQUAI_ID
        station_name = "Tiefenbrunnen" if params.station == "tiefenbrunnen" else "Mythenquai"

        result = await ckan_request(
            "datastore_search",
            {
                "resource_id": resource_id,
                "sort": "timestamp_utc desc",
                "limit": params.limit,
            },
        )
        records = result.get("records", [])

        if not records:
            return f"Keine Daten für Station {station_name} gefunden."

        lines = [f"## 🌊 Zürichsee Wetterstation {station_name}\n"]
        lines.append("*Wasserschutzpolizei Zürich – alle 10 Min. aktualisiert*\n")

        for r in records:
            ts = r.get("timestamp_cet", r.get("timestamp_utc", "?"))
            lines.append(f"### {ts}")

            def v(key: str, unit: str = "") -> str:
                """Format value, replacing None with '–'."""
                val = r.get(key)
                return f"{val} {unit}".strip() if val is not None else "–"

            lines.append(f"- 🌊 **Wassertemperatur**: {v('water_temperature', '°C')}")
            lines.append(f"- 🌡️ **Lufttemperatur**: {v('air_temperature', '°C')}")
            lines.append(f"- 📊 **Wasserstand**: {v('water_level', 'm ü.M.')}")
            wind_speed = v("wind_speed_avg_10min", "m/s")
            wind_gust = v("wind_gust_max_10min", "m/s")
            lines.append(f"- 💨 **Wind**: {wind_speed} (Böen: {wind_gust})")
            lines.append(f"- 🧭 **Windrichtung**: {v('wind_direction', '°')}")
            lines.append(f"- 💧 **Luftfeuchte**: {v('humidity', '%')}")
            lines.append(f"- 🌧️ **Niederschlag**: {v('precipitation', 'mm')}")
            lines.append(f"- 📏 **Luftdruck**: {v('barometric_pressure_qfe', 'hPa')}")
            lines.append(f"- 🌡️ **Taupunkt**: {v('dew_point', '°C')}")
            lines.append(f"- ☀️ **Globalstrahlung**: {v('global_radiation', 'W/m²')}")
            lines.append("")

        lines.append("---")
        lines.append("*Daten: data.stadt-zuerich.ch – 10-Min.-Intervall*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Wasserwetter")


class PedestrianInput(BaseModel):
    """Input für Passantenfrequenzen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    limit: int = Field(default=24, description="Anzahl Stundenwerte (max. 168)", ge=1, le=168)


@mcp.tool(
    name="zurich_pedestrian_traffic",
    annotations={
        "title": "Passantenfrequenzen Bahnhofstrasse",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def zurich_pedestrian_traffic(params: PedestrianInput) -> str:
    """Liefert stündliche Passantenfrequenzen an der Zürcher Bahnhofstrasse.

    Datenquelle: hystreet.com Sensoren an 3 Standorten (Nord, Mitte, Süd).
    Misst die Anzahl Fussgänger:innen pro Stunde inkl. Richtung und Wetter.

    Returns:
        Stundenwerte der Passantenfrequenz (neueste zuerst)
    """
    try:
        result = await ckan_request(
            "datastore_search",
            {
                "resource_id": PEDESTRIAN_RESOURCE_ID,
                "sort": "timestamp desc",
                "limit": params.limit,
            },
        )
        records = result.get("records", [])

        if not records:
            return "Keine Passantenfrequenz-Daten gefunden."

        lines = ["## 🚶 Passantenfrequenzen Bahnhofstrasse Zürich\n"]
        lines.append("*hystreet.com Sensoren – stündlich aktualisiert*\n")

        # Show compact table
        lines.append("| Zeitpunkt | Standort | Passanten | Temp. | Wetter |")
        lines.append("| --- | --- | ---: | ---: | --- |")
        for r in records:
            ts = md_cell(str(r.get("timestamp", "?"))[:16])
            loc = md_cell(r.get("location_name", "?"))
            count = r.get("pedestrians_count", "?")
            temp = r.get("temperature", "?")
            weather = md_cell(r.get("weather_condition", "?"))
            lines.append(f"| {ts} | {loc} | {count} | {temp}°C | {weather} |")

        lines.append("")
        lines.append(f"*{result.get('total', '?')} Messwerte total*")
        lines.append("*Daten: data.stadt-zuerich.ch*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Passantenfrequenzen")


class VBZPassengersInput(BaseModel):
    """Input für VBZ-Fahrgastzahlen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    line: str | None = Field(
        default=None,
        description=("Liniennummer filtern, z.B. '4' (Tram 4), '33' (Bus 33). Leer = alle Linien."),
    )
    stop: str | None = Field(
        default=None,
        description=(
            "Haltestelle filtern (Name oder Teilname), z.B. 'Paradeplatz', 'Central', 'Bellevue'. Leer = alle."
        ),
    )
    query: str | None = Field(
        default=None,
        description="Volltextsuche über alle Felder",
    )
    limit: int = Field(default=20, description="Anzahl Ergebnisse (max. 100)", ge=1, le=100)


@mcp.tool(
    name="zurich_vbz_passengers",
    annotations={
        "title": "VBZ Fahrgastzahlen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def zurich_vbz_passengers(params: VBZPassengersInput) -> str:
    """Fragt Fahrgastzahlen der Verkehrsbetriebe Zürich (VBZ) ab.

    Jährlich aktualisierte Ein-/Aussteiger-Zahlen pro Linie und Haltestelle.
    Die Daten umfassen Tram, Bus, Trolleybus und Seilbahnen.

    Returns:
        Fahrgastzahlen mit Linien- und Haltestellendetails
    """
    try:
        api_params: dict = {
            "resource_id": VBZ_REISENDE_ID,
            "limit": params.limit,
        }
        if params.query:
            api_params["q"] = params.query

        result = await ckan_request("datastore_search", api_params)
        records = result.get("records", [])
        fields = result.get("fields", [])

        if not records:
            return "Keine VBZ-Fahrgastzahlen gefunden."

        field_names = [f["id"] for f in fields if f["id"] != "_id"]

        lines = ["## 🚊 VBZ Fahrgastzahlen\n"]
        lines.append(f"*Verkehrsbetriebe Zürich – {result.get('total', '?')} Einträge*\n")
        lines.append(f"**Felder**: {', '.join(field_names)}\n")

        # Render data
        lines.append("```json")
        lines.append(json.dumps(records, indent=2, ensure_ascii=False, default=str))
        lines.append("```")

        if result.get("total", 0) > params.limit:
            lines.append(f"\n*→ {result['total'] - params.limit} weitere Einträge verfügbar*")

        lines.append("\n---")
        lines.append(
            f"*Tipp: Für Haltestellendetails `zurich_datastore_query` mit Resource `{VBZ_HALTESTELLEN_ID}` verwenden.*"
        )
        lines.append(f"*Für Liniendetails: Resource `{VBZ_LINIE_ID}`*")
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "VBZ-Fahrgastzahlen")

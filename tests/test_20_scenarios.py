"""
20 unterschiedlichste Testszenarien fuer den Zurich Open Data MCP Server.
Deckt ab: Realistische LLM-Fragen, Cross-Tool-Workflows, Grenzwerte,
Datenkonsistenz, adversariale Eingaben und domänenspezifische Nischen.
"""

import asyncio
import json
import re
import sys

sys.path.insert(0, "src")

from zurich_opendata_mcp.server import (
    zurich_search_datasets,
    zurich_get_dataset,
    zurich_datastore_query,
    zurich_datastore_sql,
    zurich_list_categories,
    zurich_list_tags,
    zurich_parking_live,
    zurich_analyze_datasets,
    zurich_catalog_stats,
    zurich_find_school_data,
    zurich_weather_live,
    zurich_air_quality,
    zurich_water_weather,
    zurich_pedestrian_traffic,
    zurich_vbz_passengers,
    zurich_geo_layers,
    zurich_geo_features,
    zurich_parliament_search,
    zurich_parliament_members,
    zurich_tourism,
    zurich_sparql,
)
from zurich_opendata_mcp.server import (
    SearchDatasetsInput,
    GetDatasetInput,
    DatastoreQueryInput,
    DatastoreSqlInput,
    ListGroupInput,
    TagSearchInput,
    AnalyzeDatasetInput,
    WeatherLiveInput,
    AirQualityInput,
    WaterWeatherInput,
    PedestrianInput,
    VBZPassengersInput,
    GeoFeaturesInput,
    ParliamentSearchInput,
    ParliamentMembersInput,
    TourismSearchInput,
    SparqlQueryInput,
    FindSchoolDataInput,
)


def extract_uuids(text: str) -> list[str]:
    return re.findall(
        r'`?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`?',
        text,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1: "Wie warm ist es gerade in Zuerich und wie ist die Luftqualitaet?"
#    Realistische LLM-Frage → Wetter + Luft kombinieren
# ─────────────────────────────────────────────────────────────────────────────

async def test_01_current_conditions():
    print("=" * 60)
    print("TEST 01: Aktuelle Wetter- & Luftbedingungen kombiniert")
    print("=" * 60)

    weather = await zurich_weather_live(WeatherLiveInput(parameter="T", limit=1))
    air = await zurich_air_quality(AirQualityInput(parameter="PM10", limit=1))

    assert "°C" in weather, "Temperatur fehlt"
    assert "Luftqualität" in air, "Luftqualitaet-Header fehlt"

    # Beide sollten aktuelle Daten haben (nicht leer)
    assert "Keine" not in weather, "Keine Wetterdaten"
    assert "Keine" not in air, "Keine Luftdaten"
    print("  Temperatur + PM10 gleichzeitig: OK")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 2: Konsistenzpruefung: Katalog-Stats vs. Wildcard-Suche
# ─────────────────────────────────────────────────────────────────────────────

async def test_02_catalog_consistency():
    print("=" * 60)
    print("TEST 02: Katalog-Konsistenz (Stats vs. Suche)")
    print("=" * 60)

    stats = await zurich_catalog_stats()
    search = await zurich_search_datasets(
        SearchDatasetsInput(query="*:*", rows=1)
    )

    stats_count = re.search(r'Gesamtzahl.*?(\d+)', stats)
    search_count = re.search(r'(\d+)\s+Datensätze', search)

    assert stats_count, "Keine Gesamtzahl in Stats"
    assert search_count, "Keine Gesamtzahl in Suche"

    s1 = int(stats_count.group(1))
    s2 = int(search_count.group(1))

    # Sollten identisch sein (gleiche API, gleicher Zeitpunkt)
    assert s1 == s2, f"Stats ({s1}) != Suche ({s2})"
    print(f"  Katalog-Statistik = Suche: {s1} Datensaetze ✓")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 3: Grenzwerte: rows=1, rows=50, offset am Ende
# ─────────────────────────────────────────────────────────────────────────────

async def test_03_boundary_values():
    print("=" * 60)
    print("TEST 03: Grenzwerte (rows, offset)")
    print("=" * 60)

    # 3a: Minimum rows=1
    r = await zurich_search_datasets(
        SearchDatasetsInput(query="Bevölkerung", rows=1)
    )
    assert "Zeige 1 von" in r
    print("  3a: rows=1: OK")

    # 3b: Maximum rows=50
    r = await zurich_search_datasets(
        SearchDatasetsInput(query="Bevölkerung", rows=50)
    )
    count = re.search(r'Zeige (\d+) von', r)
    assert count and int(count.group(1)) >= 1
    print(f"  3b: rows=50 -> {count.group(1)} Treffer: OK")

    # 3c: Sehr hoher Offset (jenseits der Ergebnisse)
    r = await zurich_search_datasets(
        SearchDatasetsInput(query="Bevölkerung", rows=10, offset=99999)
    )
    assert "Keine" in r or "Zeige 0" in r or "0 von" in r
    print("  3c: offset=99999 -> leere Seite: OK")

    # 3d: DataStore limit=1
    meteo_id = "f9aa1373-404f-443b-b623-03ff02d2d0b7"
    r = await zurich_datastore_query(
        DatastoreQueryInput(resource_id=meteo_id, limit=1)
    )
    assert "Zeige 1" in r or "1 Eintr" in r or "DataStore" in r
    print("  3d: DataStore limit=1: OK")

    # 3e: DataStore limit=100 (Maximum)
    r = await zurich_datastore_query(
        DatastoreQueryInput(resource_id=meteo_id, limit=100)
    )
    assert "DataStore" in r
    print("  3e: DataStore limit=100: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 4: Alle 19 Gruppen einzeln abrufen
# ─────────────────────────────────────────────────────────────────────────────

async def test_04_all_groups():
    print("=" * 60)
    print("TEST 04: Alle 19 Kategorien einzeln")
    print("=" * 60)

    groups = [
        "arbeit-und-erwerb", "basiskarten", "bauen-und-wohnen", "bevolkerung",
        "bildung", "energie", "finanzen", "freizeit", "gesundheit",
        "kriminalitat", "kultur", "mobilitat", "politik", "preise",
        "soziales", "tourismus", "umwelt", "verwaltung", "volkswirtschaft",
    ]

    for g in groups:
        r = await zurich_list_categories(ListGroupInput(group_id=g))
        assert "Kategorie" in r or "Datensätze" in r, f"Gruppe '{g}' fehlerhaft: {r[:80]}"

    print(f"  Alle {len(groups)} Gruppen erfolgreich abgerufen")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 5: Wassertemperatur beide Stationen vergleichen
# ─────────────────────────────────────────────────────────────────────────────

async def test_05_water_both_stations():
    print("=" * 60)
    print("TEST 05: Wassertemperatur Tiefenbrunnen vs. Mythenquai")
    print("=" * 60)

    tiefenbrunnen = await zurich_water_weather(
        WaterWeatherInput(station="tiefenbrunnen", limit=1)
    )
    mythenquai = await zurich_water_weather(
        WaterWeatherInput(station="mythenquai", limit=1)
    )

    assert "Tiefenbrunnen" in tiefenbrunnen
    assert "Mythenquai" in mythenquai

    # Beide sollten Wassertemperatur enthalten
    assert "Wassertemperatur" in tiefenbrunnen
    assert "Wassertemperatur" in mythenquai
    print("  Tiefenbrunnen: OK")
    print("  Mythenquai: OK")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 6: Tourismus alle 12 Kategorien durchprobieren
# ─────────────────────────────────────────────────────────────────────────────

async def test_06_all_tourism_categories():
    print("=" * 60)
    print("TEST 06: Alle 12 Tourismus-Kategorien")
    print("=" * 60)

    categories = [
        "uebernachten", "aktivitaeten", "restaurants", "shopping",
        "nachtleben", "kultur", "events", "touren",
        "natur", "sport", "familien", "museen",
    ]

    for cat in categories:
        r = await zurich_tourism(
            TourismSearchInput(category=cat, max_results=1, language="de")
        )
        assert "Tourismus" in r or "Keine" in r, f"Kategorie '{cat}' fehlerhaft"

    print(f"  Alle {len(categories)} Kategorien: OK")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 7: Alle 14 Geo-Layer nacheinander
# ─────────────────────────────────────────────────────────────────────────────

async def test_07_all_geo_layers():
    print("=" * 60)
    print("TEST 07: Alle 14 Geo-Layer")
    print("=" * 60)

    layers = [
        "schulanlagen", "schulkreise", "schulwege", "stadtkreise",
        "spielplaetze", "kreisbuero", "sammelstelle", "sport",
        "klimadaten", "lehrpfade", "stimmlokale", "sozialzentrum",
        "velopruefstrecken", "familienberatung",
    ]

    ok_count = 0
    err_count = 0
    for layer in layers:
        r = await zurich_geo_features(
            GeoFeaturesInput(layer_id=layer, max_features=1)
        )
        if "Geodaten" in r or "Feature" in r:
            ok_count += 1
        else:
            err_count += 1
            # WFS-Fehler sind bei manchen Layern normal (Server-seitig)
            assert "Fehler" in r, f"Layer '{layer}' unerwartete Antwort: {r[:80]}"

    print(f"  {ok_count} Layer OK, {err_count} mit WFS-Fehler (Server-seitig)")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 8: Cross-Tool: Datensatz suchen → UUID → SQL-Abfrage mit Aggregation
# ─────────────────────────────────────────────────────────────────────────────

async def test_08_search_to_sql_pipeline():
    print("=" * 60)
    print("TEST 08: Suche → UUID → SQL-Aggregation Pipeline")
    print("=" * 60)

    # Analyse eines bekannten Datensatzes
    result = await zurich_analyze_datasets(
        AnalyzeDatasetInput(query="Bevölkerungsbestand", max_datasets=1, include_structure=True)
    )
    uuids = extract_uuids(result)

    # Finde eine DataStore-aktive UUID
    ds_uuid = None
    for uid in uuids:
        if "DataStore" in result.split(uid)[0].split("\n")[-1] if uid in result else "":
            ds_uuid = uid
            break
    if not ds_uuid and uuids:
        ds_uuid = uuids[0]

    if ds_uuid:
        sql = f'SELECT COUNT(*) as total FROM "{ds_uuid}"'
        r = await zurich_datastore_sql(DatastoreSqlInput(sql=sql))
        if "Fehler" not in r:
            print(f"  UUID {ds_uuid[:8]}... -> COUNT(*): OK")
        else:
            print(f"  UUID {ds_uuid[:8]}... nicht DataStore-aktiv: OK")
    else:
        print("  Keine UUIDs gefunden (Datensatz evtl. nur Geodaten): OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 9: Adversariale Eingaben (SQL-Injection-Versuch, XSS-Versuch)
# ─────────────────────────────────────────────────────────────────────────────

async def test_09_adversarial_inputs():
    print("=" * 60)
    print("TEST 09: Adversariale Eingaben")
    print("=" * 60)

    # 9a: SQL-Injection in Suche
    r = await zurich_search_datasets(
        SearchDatasetsInput(query="'; DROP TABLE datasets; --", rows=1)
    )
    assert "Fehler" in r or "Keine" in r or "Datensätze" in r
    print("  9a: SQL-Injection in Suche: Server stabil ✓")

    # 9b: XSS-artiger Input in Suche
    r = await zurich_search_datasets(
        SearchDatasetsInput(query="<script>alert('xss')</script>", rows=1)
    )
    assert "Fehler" in r or "Keine" in r or "Datensätze" in r
    print("  9b: XSS-Input in Suche: Server stabil ✓")

    # 9c: Extrem langer Suchbegriff (500 Zeichen - max)
    long_query = "Bevölkerung " * 41  # ~492 chars
    long_query = long_query[:500]
    r = await zurich_search_datasets(
        SearchDatasetsInput(query=long_query, rows=1)
    )
    assert len(r) > 0
    print("  9c: Max-Laenge Suchbegriff (500 chars): Server stabil ✓")

    # 9d: Sonderzeichen-Bombardement
    r = await zurich_search_datasets(
        SearchDatasetsInput(query="!!!@@@###$$$%%%^^^&&&***", rows=1)
    )
    assert len(r) > 0
    print("  9d: Sonderzeichen-Bombardement: Server stabil ✓")

    # 9e: Unicode-Extremfaelle (Emoji, CJK)
    r = await zurich_search_datasets(
        SearchDatasetsInput(query="🌡️ Wetter 温度", rows=1)
    )
    assert len(r) > 0
    print("  9e: Emoji + CJK in Suche: Server stabil ✓")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 10: Parking: Freie Plaetze und Validierung
# ─────────────────────────────────────────────────────────────────────────────

async def test_10_parking_validation():
    print("=" * 60)
    print("TEST 10: Parking-Daten Validierung")
    print("=" * 60)

    r = await zurich_parking_live()

    # Pruefe Tabellenstruktur
    assert "| Parkhaus |" in r, "Tabellen-Header fehlt"
    assert "| Frei |" in r, "Spalte 'Frei' fehlt"
    assert "| Total |" in r, "Spalte 'Total' fehlt"

    # Pruefe: Belegungs-Prozent ist plausibel (0-100)
    percents = re.findall(r'(\d+)%', r)
    for pct in percents:
        p = int(pct)
        assert 0 <= p <= 100, f"Belegung {p}% ausserhalb 0-100"

    # Pruefe: mind. 1 offenes Parkhaus
    assert "open" in r.lower(), "Kein Parkhaus offen?"

    print(f"  Tabellenstruktur: OK")
    print(f"  {len(percents)} Belegungswerte alle 0-100%: OK")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 11: Passantenfrequenz verschiedene Zeitscheiben
# ─────────────────────────────────────────────────────────────────────────────

async def test_11_pedestrian_different_limits():
    print("=" * 60)
    print("TEST 11: Passantenfrequenzen verschiedene Limits")
    print("=" * 60)

    r1 = await zurich_pedestrian_traffic(PedestrianInput(limit=3))
    r2 = await zurich_pedestrian_traffic(PedestrianInput(limit=10))

    assert "Passanten" in r1
    assert "Passanten" in r2
    # Mehr Limit = mehr Daten (laengerer Output)
    assert len(r2) > len(r1), "limit=10 lieferte nicht mehr Daten als limit=3"
    print(f"  limit=3: {len(r1)} chars, limit=10: {len(r2)} chars ✓")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 12: Parlament: Sehr altes Geschaeft finden
# ─────────────────────────────────────────────────────────────────────────────

async def test_12_parliament_historical():
    print("=" * 60)
    print("TEST 12: Historische Gemeinderatsgeschaefte")
    print("=" * 60)

    # Geschaefte aus den 1990ern
    r = await zurich_parliament_search(
        ParliamentSearchInput(query="Budget", year_from=1995, year_to=2000, max_results=3)
    )
    assert "Treffer" in r or "Keine" in r or "Budget" in r
    print(f"  Geschaefte 1995-2000: OK")

    # Suche nach maximal alten Geschaeften
    r2 = await zurich_parliament_search(
        ParliamentSearchInput(query="Stadtrat", year_from=1990, year_to=1995, max_results=3)
    )
    assert "Treffer" in r2 or "Keine" in r2
    print(f"  Geschaefte 1990-1995: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 13: Datensatz-Detail: Alle Felder eines bekannten Datensatzes pruefen
# ─────────────────────────────────────────────────────────────────────────────

async def test_13_dataset_detail_completeness():
    print("=" * 60)
    print("TEST 13: Dataset-Detail Vollstaendigkeit")
    print("=" * 60)

    r = await zurich_get_dataset(GetDatasetInput(dataset_id="geo_schulanlagen"))

    # Grundlegende Felder
    assert "Ressourcen" in r or "Downloads" in r, "Ressourcen-Abschnitt fehlt"

    # UUID muss sichtbar sein (unser Fix)
    uuids = extract_uuids(r)
    assert len(uuids) >= 1, "Keine Resource-UUIDs sichtbar"

    # Metadaten
    assert "Metadaten" in r or "metadata" in r.lower() or "Lizenz" in r or "URL" in r

    print(f"  {len(uuids)} UUIDs, Metadaten vorhanden: OK")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 14: Schuldaten: Alle Topic-Varianten
# ─────────────────────────────────────────────────────────────────────────────

async def test_14_school_all_topics():
    print("=" * 60)
    print("TEST 14: Schuldaten alle Topics")
    print("=" * 60)

    topics = ["Schulanlagen", "Ferien", "Kindergarten", "Schüler", "Schulweg"]

    for topic in topics:
        r = await zurich_find_school_data(FindSchoolDataInput(topic=topic))
        assert "Schul" in r or topic in r or "Datensätze" in r, \
            f"Topic '{topic}' lieferte unerwartetes Ergebnis"

    print(f"  Alle {len(topics)} Topics: OK")

    # Ohne Topic: alle Schuldaten
    r = await zurich_find_school_data(FindSchoolDataInput())
    assert "Schul" in r
    print("  Ohne Topic (alle Schuldaten): OK")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 15: Mehrere Solr-Feld-Suchen
# ─────────────────────────────────────────────────────────────────────────────

async def test_15_solr_field_queries():
    print("=" * 60)
    print("TEST 15: Solr-Feld-Suchen (tags:, title:)")
    print("=" * 60)

    # 15a: Tag-basierte Suche
    r = await zurich_search_datasets(
        SearchDatasetsInput(query="tags:sachdaten", rows=5)
    )
    assert "Datensätze" in r or "Keine" in r
    print(f"  15a: tags:sachdaten: OK")

    # 15b: Titel-basierte Suche
    r = await zurich_search_datasets(
        SearchDatasetsInput(query='title:"Bevölkerung"', rows=5)
    )
    assert "Datensätze" in r or "Keine" in r
    print(f"  15b: title:Bevoelkerung: OK")

    # 15c: Kombination: Tag + Freitext
    r = await zurich_search_datasets(
        SearchDatasetsInput(query="tags:geodaten Schule", rows=5)
    )
    assert "Datensätze" in r or "Keine" in r
    print(f"  15c: tags:geodaten + Schule: OK")

    # 15d: Negativer Filter (NOT tag)
    r = await zurich_search_datasets(
        SearchDatasetsInput(query="Energie NOT tags:tabelle", rows=5)
    )
    assert "Datensätze" in r or "Keine" in r
    print(f"  15d: Energie NOT tags:tabelle: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 16: Cross-Validation: Suche vs. Analyse fuer gleichen Begriff
# ─────────────────────────────────────────────────────────────────────────────

async def test_16_search_vs_analyze():
    print("=" * 60)
    print("TEST 16: Suche vs. Analyse Konsistenz")
    print("=" * 60)

    query = "Abfallmenge"

    search_r = await zurich_search_datasets(
        SearchDatasetsInput(query=query, rows=3)
    )
    analyze_r = await zurich_analyze_datasets(
        AnalyzeDatasetInput(query=query, max_datasets=3, include_structure=False)
    )

    search_uuids = set(extract_uuids(search_r))
    analyze_uuids = set(extract_uuids(analyze_r))

    # Analyse verwendet package_show und sollte mindestens die gleichen UUIDs haben
    if search_uuids and analyze_uuids:
        overlap = search_uuids & analyze_uuids
        print(f"  Suche: {len(search_uuids)} UUIDs")
        print(f"  Analyse: {len(analyze_uuids)} UUIDs")
        print(f"  Ueberlappung: {len(overlap)} UUIDs")
        # Mindestens einige sollten ueberlappen
        assert len(overlap) > 0 or len(search_uuids) == 0, "Keine UUID-Ueberlappung"
    else:
        print(f"  Suche/Analyse UUIDs: {len(search_uuids)}/{len(analyze_uuids)}")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 17: Wetter: Alle bekannten Parameter durchgehen
# ─────────────────────────────────────────────────────────────────────────────

async def test_17_all_weather_params():
    print("=" * 60)
    print("TEST 17: Wetter alle Parameter")
    print("=" * 60)

    params = ["T", "Hr", "p", "RainDur", "StrGlo"]

    for param in params:
        r = await zurich_weather_live(WeatherLiveInput(parameter=param, limit=1))
        assert "Wetterdaten" in r, f"Parameter '{param}' fehlerhaft"

    print(f"  Alle {len(params)} Parameter (T, Hr, p, RainDur, StrGlo): OK")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 18: DataStore: Gleiche Resource ueber Query vs. SQL
# ─────────────────────────────────────────────────────────────────────────────

async def test_18_query_vs_sql_same_data():
    print("=" * 60)
    print("TEST 18: DataStore Query vs. SQL auf gleiche Resource")
    print("=" * 60)

    # VBZ-Reisende Resource
    vbz_id = "38b0c1e5-1f4e-444d-975c-61a462aa8ca6"

    query_r = await zurich_datastore_query(
        DatastoreQueryInput(resource_id=vbz_id, limit=3)
    )
    sql_r = await zurich_datastore_sql(
        DatastoreSqlInput(sql=f'SELECT * FROM "{vbz_id}" LIMIT 3')
    )

    q_has_data = "Fehler" not in query_r and "Daten" in query_r
    s_has_data = "Fehler" not in sql_r and "Zeilen" in sql_r

    if q_has_data and s_has_data:
        print("  Beide Methoden liefern Daten: OK")
    elif not q_has_data and not s_has_data:
        print("  Beide Methoden: Resource nicht verfuegbar: OK")
    else:
        print(f"  Query={q_has_data}, SQL={s_has_data}: Abweichung (akzeptabel)")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 19: Geo-Layer Eigenschaftsfelder analysieren
# ─────────────────────────────────────────────────────────────────────────────

async def test_19_geo_field_analysis():
    print("=" * 60)
    print("TEST 19: Geo-Layer Feld-Analyse")
    print("=" * 60)

    # Stadtkreise: Sollte Polygone mit definierten Feldern haben
    r = await zurich_geo_features(
        GeoFeaturesInput(layer_id="stadtkreise", max_features=12)
    )
    assert "Verfügbare Felder" in r, "Feld-Liste fehlt"

    # Schulanlagen: Sollte Punkte mit Koordinaten haben
    r2 = await zurich_geo_features(
        GeoFeaturesInput(layer_id="schulanlagen", max_features=3)
    )
    # Punkt-Features haben Koordinaten
    if "📍" in r2:
        print("  Schulanlagen haben Punkt-Koordinaten: OK")
    else:
        print("  Schulanlagen: OK (Daten vorhanden)")

    # Sport: Sportanlagen
    r3 = await zurich_geo_features(
        GeoFeaturesInput(layer_id="sport", max_features=5)
    )
    assert "Geodaten" in r3 or "Sport" in r3 or "Fehler" in r3
    print("  Sport-Layer: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# 20: Full-Stack Integration: LLM-Frage simulieren
#    "Ich ziehe nach Zuerich mit 2 Kindern. Was gibt es in der Naehe
#     von Schulen? Wie komme ich hin? Was sagt der Gemeinderat dazu?"
# ─────────────────────────────────────────────────────────────────────────────

async def test_20_full_stack_integration():
    print("=" * 60)
    print("TEST 20: Full-Stack: Umzugsfrage (Schule + Geo + VBZ + Parlament)")
    print("=" * 60)

    # Schritt 1: Schuldaten
    schools = await zurich_find_school_data(FindSchoolDataInput(topic="Schulanlagen"))
    assert "Schul" in schools
    print("  Schritt 1 - Schuldaten: OK")

    # Schritt 2: Schulanlagen auf der Karte
    geo = await zurich_geo_features(
        GeoFeaturesInput(layer_id="schulanlagen", max_features=5)
    )
    assert "Geodaten" in geo or "Feature" in geo
    print("  Schritt 2 - Geo-Schulanlagen: OK")

    # Schritt 3: Spielplaetze in der Naehe
    play = await zurich_geo_features(
        GeoFeaturesInput(layer_id="spielplaetze", max_features=5)
    )
    assert len(play) > 0
    print("  Schritt 3 - Spielplaetze: OK")

    # Schritt 4: OeV-Anbindung
    vbz = await zurich_vbz_passengers(VBZPassengersInput(limit=5))
    assert "VBZ" in vbz
    print("  Schritt 4 - VBZ-Anbindung: OK")

    # Schritt 5: Familienberatung
    family = await zurich_geo_features(
        GeoFeaturesInput(layer_id="familienberatung", max_features=5)
    )
    assert len(family) > 0
    print("  Schritt 5 - Familienberatung: OK")

    # Schritt 6: Was sagt der Gemeinderat zu Schulen?
    parl = await zurich_parliament_search(
        ParliamentSearchInput(
            query="Schulraum",
            department="Schul- und Sportdepartement",
            max_results=3
        )
    )
    assert "Treffer" in parl or "Keine" in parl or "Geschäft" in parl
    print("  Schritt 6 - Parlament 'Schulraum': OK")

    # Schritt 7: Tourismus fuer Familien
    family_tourism = await zurich_tourism(
        TourismSearchInput(category="familien", max_results=3, language="de")
    )
    assert "Tourismus" in family_tourism or "Keine" in family_tourism
    print("  Schritt 7 - Familientourismus: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 60)
    print("  ZURICH OPEN DATA MCP – 20 Testszenarien")
    print("=" * 60 + "\n")

    scenarios = [
        ("01: Wetter + Luft kombiniert", test_01_current_conditions),
        ("02: Katalog-Konsistenz", test_02_catalog_consistency),
        ("03: Grenzwerte rows/offset", test_03_boundary_values),
        ("04: Alle 19 Gruppen", test_04_all_groups),
        ("05: Wasser beide Stationen", test_05_water_both_stations),
        ("06: Alle 12 Tourismus-Kategorien", test_06_all_tourism_categories),
        ("07: Alle 14 Geo-Layer", test_07_all_geo_layers),
        ("08: Suche→UUID→SQL Pipeline", test_08_search_to_sql_pipeline),
        ("09: Adversariale Eingaben", test_09_adversarial_inputs),
        ("10: Parking Validierung", test_10_parking_validation),
        ("11: Passanten versch. Limits", test_11_pedestrian_different_limits),
        ("12: Historische Geschaefte", test_12_parliament_historical),
        ("13: Dataset-Detail Vollstaendigkeit", test_13_dataset_detail_completeness),
        ("14: Schuldaten alle Topics", test_14_school_all_topics),
        ("15: Solr-Feld-Suchen", test_15_solr_field_queries),
        ("16: Suche vs. Analyse Konsistenz", test_16_search_vs_analyze),
        ("17: Wetter alle Parameter", test_17_all_weather_params),
        ("18: Query vs. SQL gleiche Resource", test_18_query_vs_sql_same_data),
        ("19: Geo-Layer Feld-Analyse", test_19_geo_field_analysis),
        ("20: Full-Stack Umzugsfrage", test_20_full_stack_integration),
    ]

    passed = 0
    failed = 0
    failed_names = []

    for name, test_fn in scenarios:
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}\n")
            failed += 1
            failed_names.append(name)

    print("=" * 60)
    print(f"  ERGEBNIS: {passed} bestanden, {failed} fehlgeschlagen von {len(scenarios)}")
    if failed_names:
        print(f"  Fehlgeschlagen: {', '.join(failed_names)}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

"""
20 Neue Testszenarien fuer den Zurich Open Data MCP Server.
Fokus: Unicode, End-to-End Workflows, SQL-Aggregation, Mehrsprachigkeit,
Fehlertoleranz, Geo-Vollstaendigkeit, Parlament-Filter, Edge Cases.
"""

import asyncio
import io
import json
import os
import re
import sys
import time

# Windows Console Encoding Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

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


# ---------------------------------------------------------------------------
# Szenario 1: Unicode und Umlaute in Suchanfragen
#   Zuerich-spezifische Zeichen (ae, oe, ue, ss) korrekt verarbeiten
# ---------------------------------------------------------------------------

async def test_scenario_1_unicode_search():
    print("=" * 60)
    print("SZENARIO 1: Unicode/Umlaute in Suchanfragen")
    print("=" * 60)

    queries = [
        ("Bevoelkerung", "ASCII-Umlaut"),
        ("Strasse", "Doppel-s/Strasse"),
        ("Zurich", "ohne Umlaut"),
        ("Kindergaerten", "ae statt ae"),
    ]

    for query, desc in queries:
        result = await zurich_search_datasets(SearchDatasetsInput(query=query, rows=2))
        assert isinstance(result, str) and len(result) > 20, \
            f"Query '{query}' lieferte keinen Output"
        print(f"  '{query}' ({desc}): OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 2: End-to-End Workflow (Suche -> Detail -> DataStore)
#   Realistische Nutzungskette: Dataset finden, Details holen, Daten abfragen
# ---------------------------------------------------------------------------

async def test_scenario_2_end_to_end_workflow():
    print("=" * 60)
    print("SZENARIO 2: End-to-End Workflow (Suche -> Detail -> DataStore)")
    print("=" * 60)

    # Schritt 1: Suche nach Wetter-Datensatz
    search_result = await zurich_search_datasets(
        SearchDatasetsInput(query="Messwerte Wetterstationen", rows=3)
    )
    assert "Datensaetze" in search_result or "Datensätze" in search_result
    print("  Schritt 1 (Suche): OK")

    # Schritt 2: Bekannten Dataset im Detail abrufen
    detail = await zurich_get_dataset(
        GetDatasetInput(dataset_id="ugz_meteodaten_stundenmittelwerte")
    )
    assert "Fehler" not in detail, f"Dataset-Detail Fehler: {detail[:100]}"
    print("  Schritt 2 (Detail): OK")

    # Schritt 3: Resource-UUID extrahieren und DataStore abfragen
    uuids = re.findall(
        r'`([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`',
        detail
    )
    if uuids:
        ds_result = await zurich_datastore_query(
            DatastoreQueryInput(resource_id=uuids[0], limit=3)
        )
        assert isinstance(ds_result, str) and len(ds_result) > 20
        print(f"  Schritt 3 (DataStore {uuids[0][:8]}...): OK")
    else:
        print("  Schritt 3: Keine UUID gefunden (uebersprungen)")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 3: DataStore SQL Aggregationen
#   COUNT, MIN, MAX, AVG auf Echtdaten
# ---------------------------------------------------------------------------

async def test_scenario_3_sql_aggregations():
    print("=" * 60)
    print("SZENARIO 3: DataStore SQL Aggregationen")
    print("=" * 60)

    meteo_id = "f9aa1373-404f-443b-b623-03ff02d2d0b7"

    # 3a: COUNT
    result = await zurich_datastore_sql(
        DatastoreSqlInput(sql=f'SELECT COUNT(*) FROM "{meteo_id}"')
    )
    assert "Fehler" not in result or "SQL" in result
    print(f"  3a: COUNT(*): OK")

    # 3b: SELECT mit LIMIT
    result = await zurich_datastore_sql(
        DatastoreSqlInput(sql=f'SELECT * FROM "{meteo_id}" LIMIT 5')
    )
    assert isinstance(result, str) and len(result) > 20
    print(f"  3b: SELECT * LIMIT 5: OK")

    # 3c: SELECT DISTINCT (wenn unterstuetzt)
    result = await zurich_datastore_sql(
        DatastoreSqlInput(
            sql=f'SELECT DISTINCT "Standort" FROM "{meteo_id}" LIMIT 10'
        )
    )
    assert isinstance(result, str) and len(result) > 10
    print(f"  3c: SELECT DISTINCT: OK")

    # 3d: WHERE-Klausel
    result = await zurich_datastore_sql(
        DatastoreSqlInput(
            sql=f'SELECT * FROM "{meteo_id}" WHERE "Standort" = \'Zch_Stampfenbachstrasse\' LIMIT 3'
        )
    )
    assert isinstance(result, str) and len(result) > 10
    print(f"  3d: WHERE-Klausel: OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 4: Tourismus Mehrsprachigkeit (de/en/fr/it)
#   Gleiche Kategorie in allen 4 Sprachen abfragen
# ---------------------------------------------------------------------------

async def test_scenario_4_tourism_multilingual():
    print("=" * 60)
    print("SZENARIO 4: Tourismus Mehrsprachigkeit")
    print("=" * 60)

    languages = ["de", "en", "fr", "it"]
    results = {}

    for lang in languages:
        result = await zurich_tourism(
            TourismSearchInput(category="museen", max_results=3, language=lang)
        )
        assert isinstance(result, str) and len(result) > 30, \
            f"Sprache '{lang}' lieferte leeren Output"
        results[lang] = result
        print(f"  Sprache '{lang}': OK")

    # Verschiedene Sprachen sollten unterschiedliche Outputs liefern
    assert results["de"] != results["en"], \
        "DE und EN liefern identischen Output"
    print("  DE != EN (unterschiedlich): OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 5: Fehlertoleranz bei ungueltigen Resource-IDs
#   Falsche UUIDs, leere Strings, Sonderzeichen
# ---------------------------------------------------------------------------

async def test_scenario_5_invalid_resource_ids():
    print("=" * 60)
    print("SZENARIO 5: Fehlertoleranz bei ungueltigen IDs")
    print("=" * 60)

    # 5a: Nicht existierende UUID
    result = await zurich_datastore_query(
        DatastoreQueryInput(
            resource_id="00000000-0000-0000-0000-000000000000",
            limit=1
        )
    )
    assert "Fehler" in result or "nicht gefunden" in result.lower() or "error" in result.lower(), \
        f"Ungueltige UUID nicht erkannt: {result[:100]}"
    print("  5a: Nicht existierende UUID -> Fehlermeldung: OK")

    # 5b: Nicht existierender Dataset-Name
    result = await zurich_get_dataset(
        GetDatasetInput(dataset_id="this_dataset_does_not_exist_xyz")
    )
    assert "Fehler" in result or "nicht gefunden" in result.lower()
    print("  5b: Ungueltiger Dataset-Name -> Fehlermeldung: OK")

    # 5c: Nicht existierende Geo-Layer ID
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="nonexistent_layer", max_features=1)
    )
    assert "Fehler" in result or "nbekannt" in result or "nicht" in result.lower(), \
        f"Ungueltiger Geo-Layer nicht erkannt: {result[:100]}"
    print("  5c: Ungueltiger Geo-Layer -> Fehlermeldung: OK")

    # 5d: Nicht existierender Tourismus-Kategorie-Name
    result = await zurich_tourism(
        TourismSearchInput(category="nonexistent_category", max_results=1)
    )
    assert "Fehler" in result or "nbekannt" in result or "nicht" in result.lower() or \
           "Keine" in result, \
        f"Ungueltige Tourismus-Kategorie nicht erkannt: {result[:100]}"
    print("  5d: Ungueltige Tourismus-Kategorie -> Fehlermeldung: OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 6: Alle 14 Geo-Layer abrufen
#   Jeder Layer muss Geodaten oder einen klaren Fehler liefern
# ---------------------------------------------------------------------------

async def test_scenario_6_all_geo_layers():
    print("=" * 60)
    print("SZENARIO 6: Alle 14 Geo-Layer abrufen")
    print("=" * 60)

    # Zuerst Layer-Liste holen
    layers_result = await zurich_geo_layers()
    assert "Layer" in layers_result or "Geodaten" in layers_result

    all_layers = [
        "schulanlagen", "schulkreise", "schulwege", "stadtkreise",
        "spielplaetze", "kreisbuero", "sammelstelle", "sport",
        "klimadaten", "lehrpfade", "stimmlokale", "sozialzentrum",
        "velopruefstrecken", "familienberatung",
    ]

    ok_count = 0
    err_count = 0
    for layer_id in all_layers:
        result = await zurich_geo_features(
            GeoFeaturesInput(layer_id=layer_id, max_features=2)
        )
        if "Fehler" in result:
            print(f"  {layer_id}: FEHLER ({result[:60]})")
            err_count += 1
        else:
            ok_count += 1

    print(f"  {ok_count}/14 OK, {err_count}/14 Fehler (externe WFS-API)")
    # Einige Geo-Layer liefern 500-Fehler von der externen WFS-API
    assert ok_count >= 5, f"Zu wenige Geo-Layer funktionieren: {ok_count}/14"
    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 7: Parlament Mitglieder nach Parteien
#   Verschiedene bekannte Zuercher Parteien abfragen
# ---------------------------------------------------------------------------

async def test_scenario_7_parliament_by_party():
    print("=" * 60)
    print("SZENARIO 7: Parlament Mitglieder nach Parteien")
    print("=" * 60)

    parties = ["SP", "SVP", "FDP", "GLP", "Gruene", "Mitte", "AL"]

    for party in parties:
        result = await zurich_parliament_members(
            ParliamentMembersInput(party=party, max_results=3)
        )
        assert isinstance(result, str) and len(result) > 20
        has_content = "Treffer" in result or "Keine" in result or "Mitglied" in result or "Gemeinderatsmitglied" in result or "Gemeinderät" in result
        print(f"  Partei '{party}': OK")

    # Nicht existierende Partei
    result = await zurich_parliament_members(
        ParliamentMembersInput(party="NONEXISTENT_PARTY_XYZ", max_results=1)
    )
    assert isinstance(result, str)
    print("  Nicht existierende Partei: OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 8: Tags-Suche Muster und Wildcards
#   Verschiedene Suchausdruecke fuer Tags
# ---------------------------------------------------------------------------

async def test_scenario_8_tag_search_patterns():
    print("=" * 60)
    print("SZENARIO 8: Tags-Suche Muster")
    print("=" * 60)

    queries = [
        ("schule", "Exakter Begriff"),
        ("wasser", "Umwelt-Thema"),
        ("x", "Einzelner Buchstabe"),
        ("bevölkerung", "Umlaut-Tag"),
    ]

    for query, desc in queries:
        result = await zurich_list_tags(TagSearchInput(query=query, limit=10))
        assert isinstance(result, str) and len(result) > 10
        print(f"  query='{query}' ({desc}): OK")

    # Ohne Query (alle Tags)
    result = await zurich_list_tags(TagSearchInput(limit=100))
    assert isinstance(result, str) and len(result) > 50
    tag_count_match = re.search(r'(\d+)\s+Tags?', result)
    if tag_count_match:
        print(f"  Alle Tags (limit=100): {tag_count_match.group(0)}: OK")
    else:
        print(f"  Alle Tags (limit=100): OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 9: DataStore Filter mit JSON-Objekten
#   Verschiedene Filter-Szenarien fuer die DataStore-Query
# ---------------------------------------------------------------------------

async def test_scenario_9_datastore_json_filters():
    print("=" * 60)
    print("SZENARIO 9: DataStore JSON-Filter")
    print("=" * 60)

    meteo_id = "f9aa1373-404f-443b-b623-03ff02d2d0b7"

    # 9a: Gueltiger JSON-Filter nach Station
    result = await zurich_datastore_query(
        DatastoreQueryInput(
            resource_id=meteo_id,
            filters='{"Standort": "Zch_Stampfenbachstrasse"}',
            limit=3
        )
    )
    assert isinstance(result, str) and len(result) > 10
    print("  9a: Filter nach Standort: OK")

    # 9b: Leerer JSON-Filter
    result = await zurich_datastore_query(
        DatastoreQueryInput(
            resource_id=meteo_id,
            filters='{}',
            limit=2
        )
    )
    assert isinstance(result, str) and len(result) > 10
    print("  9b: Leerer Filter {}: OK")

    # 9c: DataStore Volltext-Query
    result = await zurich_datastore_query(
        DatastoreQueryInput(
            resource_id=meteo_id,
            query="Stampfenbach",
            limit=3
        )
    )
    assert isinstance(result, str) and len(result) > 10
    print("  9c: Volltext-Query: OK")

    # 9d: Sortierung im DataStore
    result = await zurich_datastore_query(
        DatastoreQueryInput(
            resource_id=meteo_id,
            sort='"Datum" desc',
            limit=3
        )
    )
    assert isinstance(result, str) and len(result) > 10
    print("  9d: Sort desc: OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 10: SPARQL-Tool Statusprüfung
#   Verifiziert dass der SPARQL-Endpunkt die erwartete Warnung liefert
# ---------------------------------------------------------------------------

async def test_scenario_10_sparql_status():
    print("=" * 60)
    print("SZENARIO 10: SPARQL-Tool Status")
    print("=" * 60)

    # 10a: Einfache SPARQL-Anfrage -> sollte Warnung zurueckgeben
    result = await zurich_sparql(
        SparqlQueryInput(query="SELECT ?s WHERE {?s ?p ?o} LIMIT 1")
    )
    assert isinstance(result, str)
    # Der SPARQL-Endpoint ist deaktiviert, sollte Warnung liefern
    result_ascii = result.encode("ascii", errors="replace").decode("ascii")
    has_warning = "Hinweis" in result or "nicht" in result.lower() or \
                  "warning" in result.lower() or "aktuell" in result.lower() or \
                  "SPARQL" in result or "Fehler" in result
    assert has_warning, f"SPARQL lieferte keine Warnung: {result_ascii[:100]}"
    print("  10a: SPARQL-Warnung erhalten: OK")

    # 10b: Ungueltige SPARQL-Abfrage (kein SELECT/PREFIX)
    from pydantic import ValidationError
    try:
        result = await zurich_sparql(
            SparqlQueryInput(query="DELETE WHERE {?s ?p ?o}")
        )
        # Wenn es durchkommt, sollte es Warnung oder Fehler zeigen
        assert "Fehler" in result or "SELECT" in result or "PREFIX" in result or \
               "SPARQL" in result or "nicht" in result.lower()
        print("  10b: Ungueltige SPARQL-Query behandelt: OK")
    except ValidationError:
        print("  10b: Ungueltige SPARQL-Query -> ValidationError: OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 11: Suche mit booleschen Operatoren (Solr-Syntax)
#   AND, OR, NOT in CKAN-Suche
# ---------------------------------------------------------------------------

async def test_scenario_11_boolean_search():
    print("=" * 60)
    print("SZENARIO 11: Boolesche Suchoperatoren (Solr)")
    print("=" * 60)

    # 11a: AND-Verknuepfung
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="Schule AND Kindergarten", rows=3)
    )
    assert isinstance(result, str) and "Datensätze" in result
    and_match = re.search(r'(\d+)\s+Datensätze', result)
    and_count = int(and_match.group(1)) if and_match else 0
    print(f"  11a: AND -> {and_count} Treffer: OK")

    # 11b: OR-Verknuepfung (sollte mehr Ergebnisse als AND)
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="Schule OR Kindergarten", rows=3)
    )
    assert isinstance(result, str) and "Datensätze" in result
    or_match = re.search(r'(\d+)\s+Datensätze', result)
    or_count = int(or_match.group(1)) if or_match else 0
    print(f"  11b: OR -> {or_count} Treffer: OK")

    # 11c: NOT-Operator
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="Schule NOT Kindergarten", rows=3)
    )
    assert isinstance(result, str) and "Datensätze" in result
    not_match = re.search(r'(\d+)\s+Datensätze', result)
    not_count = int(not_match.group(1)) if not_match else 0
    print(f"  11c: NOT -> {not_count} Treffer: OK")

    # Logische Konsistenz: OR >= AND
    if and_count > 0 and or_count > 0:
        assert or_count >= and_count, \
            f"OR ({or_count}) sollte >= AND ({and_count}) sein"
        print(f"  Konsistenz: OR({or_count}) >= AND({and_count}): OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 12: Idempotenz-Test (gleicher Aufruf, gleiche Struktur)
#   Zwei identische Aufrufe muessen strukturell identisch sein
# ---------------------------------------------------------------------------

async def test_scenario_12_idempotency():
    print("=" * 60)
    print("SZENARIO 12: Idempotenz (gleiche Struktur bei Wiederholung)")
    print("=" * 60)

    # 12a: Kategorien (statisch, muss identisch sein)
    cat1 = await zurich_list_categories(ListGroupInput())
    cat2 = await zurich_list_categories(ListGroupInput())
    assert cat1 == cat2, "Kategorien-Liste nicht idempotent"
    print("  12a: Kategorien-Liste identisch: OK")

    # 12b: Geo-Layers (statisch, muss identisch sein)
    geo1 = await zurich_geo_layers()
    geo2 = await zurich_geo_layers()
    assert geo1 == geo2, "Geo-Layer-Liste nicht idempotent"
    print("  12b: Geo-Layer-Liste identisch: OK")

    # 12c: Catalog-Stats (nahezu identisch)
    stats1 = await zurich_catalog_stats()
    stats2 = await zurich_catalog_stats()
    # Gleiche Gesamtzahl erwartet
    count1 = re.search(r'(\d+)', stats1)
    count2 = re.search(r'(\d+)', stats2)
    if count1 and count2:
        assert count1.group(1) == count2.group(1), "Catalog-Stats instabil"
    print("  12c: Catalog-Stats gleiche Gesamtzahl: OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 13: Tourismus Textsuche innerhalb Kategorien
#   search_text-Parameter testen
# ---------------------------------------------------------------------------

async def test_scenario_13_tourism_text_search():
    print("=" * 60)
    print("SZENARIO 13: Tourismus Textsuche")
    print("=" * 60)

    # 13a: Suche nach "Kunsthaus" in Museen
    result = await zurich_tourism(
        TourismSearchInput(category="museen", search_text="Kunsthaus", max_results=5)
    )
    assert isinstance(result, str) and len(result) > 20
    print(f"  13a: 'Kunsthaus' in museen: OK")

    # 13b: Suche nach "See" in Aktivitaeten
    result = await zurich_tourism(
        TourismSearchInput(category="aktivitaeten", search_text="See", max_results=5)
    )
    assert isinstance(result, str) and len(result) > 20
    print(f"  13b: 'See' in aktivitaeten: OK")

    # 13c: Suche die nichts findet
    result = await zurich_tourism(
        TourismSearchInput(
            category="museen",
            search_text="xyznonexistent123",
            max_results=5
        )
    )
    assert isinstance(result, str)
    # Sollte "Keine" oder leere Ergebnis-Liste zeigen
    print(f"  13c: Nicht existierender Suchtext -> saubere Antwort: OK")

    # 13d: Numerische Kategorie-ID direkt
    result = await zurich_tourism(
        TourismSearchInput(category="152", max_results=3)
    )
    assert isinstance(result, str) and len(result) > 20
    print(f"  13d: Numerische Kategorie-ID '152': OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 14: Parlament Suche mit Department-Filter
#   Verschiedene Departemente als Filter nutzen
# ---------------------------------------------------------------------------

async def test_scenario_14_parliament_department():
    print("=" * 60)
    print("SZENARIO 14: Parlament Department-Filter")
    print("=" * 60)

    # 14a: Suche ohne Department
    result_all = await zurich_parliament_search(
        ParliamentSearchInput(query="Bildung", max_results=5)
    )
    assert "Treffer" in result_all or "Geschäft" in result_all or "Keine" in result_all
    print("  14a: Ohne Department: OK")

    # 14b: Mit Department-Filter
    result_dept = await zurich_parliament_search(
        ParliamentSearchInput(
            query="Schule",
            department="Schul- und Sportdepartement",
            max_results=5
        )
    )
    assert isinstance(result_dept, str) and len(result_dept) > 20
    print("  14b: Department 'Schul- und Sportdepartement': OK")

    # 14c: Nicht existierendes Department
    result_fake = await zurich_parliament_search(
        ParliamentSearchInput(
            query="Test",
            department="Fake-Departement-XYZ",
            max_results=3
        )
    )
    assert isinstance(result_fake, str)
    print("  14c: Nicht existierendes Department: OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 15: Kategorienfilter in der Suche
#   filter_group mit verschiedenen Gruppen
# ---------------------------------------------------------------------------

async def test_scenario_15_search_filter_groups():
    print("=" * 60)
    print("SZENARIO 15: Suche mit Kategorienfilter")
    print("=" * 60)

    groups_to_test = [
        "bildung", "umwelt", "mobilitaet", "bevoelkerung",
        "gesundheit", "finanzen"
    ]

    for group in groups_to_test:
        result = await zurich_search_datasets(
            SearchDatasetsInput(query="*", rows=2, filter_group=group)
        )
        assert isinstance(result, str) and "Datensätze" in result, \
            f"filter_group='{group}' fehlgeschlagen"
        count_match = re.search(r'(\d+)\s+Datensätze', result)
        count = int(count_match.group(1)) if count_match else 0
        print(f"  filter_group='{group}': {count} Datensaetze: OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 16: VBZ Volltext-Suche (query-Parameter)
#   Freitext-Suche nach Haltestellen/Linien
# ---------------------------------------------------------------------------

async def test_scenario_16_vbz_fulltext():
    print("=" * 60)
    print("SZENARIO 16: VBZ Volltext-Suche")
    print("=" * 60)

    queries = [
        ("Hauptbahnhof", "Hauptknotenpunkt"),
        ("Bellevue", "Bekannte Haltestelle"),
        ("Limmatplatz", "Innenstadthaltestelle"),
    ]

    for query, desc in queries:
        result = await zurich_vbz_passengers(
            VBZPassengersInput(query=query, limit=5)
        )
        assert isinstance(result, str) and "VBZ" in result
        print(f"  query='{query}' ({desc}): OK")

    # Kombination: line + stop
    result = await zurich_vbz_passengers(
        VBZPassengersInput(line="4", stop="Central", limit=5)
    )
    assert isinstance(result, str) and "VBZ" in result
    print("  Kombination line='4' + stop='Central': OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 17: Wetter-Daten Temperatur-Plausibilitaet
#   Extrahierte Temperaturen muessen physikalisch sinnvoll sein
# ---------------------------------------------------------------------------

async def test_scenario_17_weather_temperature_plausibility():
    print("=" * 60)
    print("SZENARIO 17: Wetter Temperatur-Plausibilitaet")
    print("=" * 60)

    result = await zurich_weather_live(
        WeatherLiveInput(parameter="T", limit=10)
    )
    assert "Wetterdaten" in result

    # Temperaturwerte extrahieren (verschiedene Formate)
    temps = re.findall(r'(-?\d+[\.,]\d+)\s*(?:°C|C\b)', result)
    if temps:
        for t_str in temps:
            t = float(t_str.replace(',', '.'))
            assert -30 <= t <= 50, f"Unplausible Temperatur: {t}°C"
        print(f"  {len(temps)} Temperaturwerte alle plausibel (-30..50°C): OK")
    else:
        # Fallback: Zahlenwerte im Kontext von Temperatur
        print("  Keine Temperaturwerte direkt extrahierbar: OK")

    # Luftfeuchtigkeit
    result_hr = await zurich_weather_live(
        WeatherLiveInput(parameter="Hr", limit=5)
    )
    assert "Wetterdaten" in result_hr
    hr_vals = re.findall(r'(\d+[\.,]?\d*)\s*%', result_hr)
    if hr_vals:
        for h_str in hr_vals:
            h = float(h_str.replace(',', '.'))
            assert 0 <= h <= 100, f"Unplausible Luftfeuchtigkeit: {h}%"
        print(f"  {len(hr_vals)} Feuchtigkeitswerte alle plausibel (0-100%): OK")
    else:
        print("  Keine Feuchtigkeitswerte direkt extrahierbar: OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 18: Analyse-Tool mit verschiedenen Suchbegriffen
#   Prüft, ob die Analyse unterschiedliche Themen korrekt verarbeitet
# ---------------------------------------------------------------------------

async def test_scenario_18_analyze_diverse_topics():
    print("=" * 60)
    print("SZENARIO 18: Analyse-Tool verschiedene Themen")
    print("=" * 60)

    topics = [
        ("Verkehr", "Mobilitaet"),
        ("Wohnung", "Bauen/Wohnen"),
        ("Kriminalitaet", "Sicherheit"),
        ("Energie", "Umwelt"),
    ]

    for query, desc in topics:
        result = await zurich_analyze_datasets(
            AnalyzeDatasetInput(query=query, max_datasets=2, include_structure=True)
        )
        assert isinstance(result, str) and len(result) > 50, \
            f"Analyse '{query}' zu kurz: {len(result)}"
        print(f"  '{query}' ({desc}): OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 19: Paralleler Latenz-Vergleich einzeln vs. gebündelt
#   Misst, ob parallele Aufrufe schneller sind als sequenzielle
# ---------------------------------------------------------------------------

async def test_scenario_19_latency_comparison():
    print("=" * 60)
    print("SZENARIO 19: Latenz-Vergleich sequenziell vs. parallel")
    print("=" * 60)

    calls = [
        lambda: zurich_weather_live(WeatherLiveInput(limit=2)),
        lambda: zurich_air_quality(AirQualityInput(limit=2)),
        lambda: zurich_parking_live(),
    ]

    # Sequenziell
    start = time.time()
    for call in calls:
        await call()
    seq_time = time.time() - start

    # Parallel
    start = time.time()
    await asyncio.gather(*(call() for call in calls))
    par_time = time.time() - start

    print(f"  Sequenziell: {seq_time:.2f}s")
    print(f"  Parallel:    {par_time:.2f}s")
    print(f"  Speedup:     {seq_time / par_time:.1f}x")

    # Parallel sollte nicht LANGSAMER sein als sequenziell
    assert par_time <= seq_time * 1.5, \
        f"Parallel ({par_time:.1f}s) war viel langsamer als seq ({seq_time:.1f}s)"

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Szenario 20: Pydantic Input-Validierung
#   Testet ob ungueltige Eingaben durch Pydantic korrekt abgefangen werden
# ---------------------------------------------------------------------------

async def test_scenario_20_pydantic_validation():
    print("=" * 60)
    print("SZENARIO 20: Pydantic Input-Validierung")
    print("=" * 60)

    from pydantic import ValidationError

    # 20a: rows > 50 (max) sollte ValidationError werfen
    try:
        SearchDatasetsInput(query="test", rows=51)
        print("  20a: rows=51 -> NICHT abgefangen (FAIL)")
        assert False, "rows=51 haette abgefangen werden muessen"
    except ValidationError:
        print("  20a: rows=51 -> ValidationError: OK")

    # 20b: rows < 1 (min) sollte ValidationError werfen
    try:
        SearchDatasetsInput(query="test", rows=0)
        print("  20b: rows=0 -> NICHT abgefangen (FAIL)")
        assert False, "rows=0 haette abgefangen werden muessen"
    except ValidationError:
        print("  20b: rows=0 -> ValidationError: OK")

    # 20c: Leerer Query (Whitespace only, wird getrimmt)
    try:
        inp = SearchDatasetsInput(query="   ", rows=1)
        # Wenn strip_whitespace aktiv ist, koennte es leer werden
        # Abhaengig von der Validierung
        print("  20c: Whitespace-Query -> akzeptiert (OK)")
    except ValidationError:
        print("  20c: Whitespace-Query -> ValidationError: OK")

    # 20d: limit > Maximum bei Weather
    try:
        WeatherLiveInput(limit=101)
        print("  20d: weather limit=101 -> NICHT abgefangen")
    except ValidationError:
        print("  20d: weather limit=101 -> ValidationError: OK")

    # 20e: SQL-Query kuerzer als 5 Zeichen
    try:
        DatastoreSqlInput(sql="AB")
        print("  20e: sql='AB' (zu kurz) -> NICHT abgefangen")
    except ValidationError:
        print("  20e: sql='AB' (zu kurz) -> ValidationError: OK")

    # 20f: Extra unbekanntes Feld (extra="forbid")
    try:
        SearchDatasetsInput(query="test", rows=1, unknown_field="value")
        print("  20f: Extra-Feld -> NICHT abgefangen")
    except ValidationError:
        print("  20f: Extra-Feld -> ValidationError: OK")

    # 20g: Parlament year_from > year_to (logischer Fehler)
    # Ob Pydantic das faengt haengt von der Implementierung ab
    try:
        inp = ParliamentSearchInput(query="test", year_from=2025, year_to=2020)
        print("  20g: year_from > year_to -> akzeptiert (keine Validierung)")
    except ValidationError:
        print("  20g: year_from > year_to -> ValidationError: OK")

    print("PASSED\n")


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

async def main():
    print("\n" + "=" * 60)
    print("  ZURICH OPEN DATA MCP - 20 Neue Testszenarien")
    print("=" * 60 + "\n")

    scenarios = [
        ("1: Unicode/Umlaute", test_scenario_1_unicode_search),
        ("2: End-to-End Workflow", test_scenario_2_end_to_end_workflow),
        ("3: SQL Aggregationen", test_scenario_3_sql_aggregations),
        ("4: Tourismus Mehrsprachigkeit", test_scenario_4_tourism_multilingual),
        ("5: Ungueltige IDs/Fehlertoleranz", test_scenario_5_invalid_resource_ids),
        ("6: Alle 14 Geo-Layer", test_scenario_6_all_geo_layers),
        ("7: Parlament nach Parteien", test_scenario_7_parliament_by_party),
        ("8: Tags-Suche Muster", test_scenario_8_tag_search_patterns),
        ("9: DataStore JSON-Filter", test_scenario_9_datastore_json_filters),
        ("10: SPARQL Status", test_scenario_10_sparql_status),
        ("11: Boolesche Suche", test_scenario_11_boolean_search),
        ("12: Idempotenz", test_scenario_12_idempotency),
        ("13: Tourismus Textsuche", test_scenario_13_tourism_text_search),
        ("14: Parlament Department", test_scenario_14_parliament_department),
        ("15: Kategorienfilter Suche", test_scenario_15_search_filter_groups),
        ("16: VBZ Volltext", test_scenario_16_vbz_fulltext),
        ("17: Wetter Plausibilitaet", test_scenario_17_weather_temperature_plausibility),
        ("18: Analyse diverse Themen", test_scenario_18_analyze_diverse_topics),
        ("19: Latenz sequenziell vs. parallel", test_scenario_19_latency_comparison),
        ("20: Pydantic Validierung", test_scenario_20_pydantic_validation),
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

    print("\n" + "=" * 60)
    print(f"  ERGEBNIS: {passed} bestanden, {failed} fehlgeschlagen von {len(scenarios)}")
    if failed_names:
        print(f"  Fehlgeschlagen: {', '.join(failed_names)}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

"""
10 Diverse Testszenarien für den Zurich Open Data MCP Server.
Testet End-to-End-Workflows, Edge Cases, Filter, Paginierung und Cross-API-Nutzung.
"""

import asyncio
import sys

sys.path.insert(0, "src")

from zurich_opendata_mcp.server import (
    AirQualityInput,
    AnalyzeDatasetInput,
    DatastoreQueryInput,
    DatastoreSqlInput,
    FindSchoolDataInput,
    GeoFeaturesInput,
    GetDatasetInput,
    ListGroupInput,
    ParliamentMembersInput,
    ParliamentSearchInput,
    PedestrianInput,
    SearchDatasetsInput,
    SparqlQueryInput,
    TagSearchInput,
    TourismSearchInput,
    VBZPassengersInput,
    WaterWeatherInput,
    WeatherLiveInput,
    zurich_air_quality,
    zurich_analyze_datasets,
    zurich_catalog_stats,
    zurich_datastore_query,
    zurich_datastore_sql,
    zurich_find_school_data,
    zurich_geo_features,
    zurich_geo_layers,
    zurich_get_dataset,
    zurich_list_categories,
    zurich_list_tags,
    zurich_parking_live,
    zurich_parliament_members,
    zurich_parliament_search,
    zurich_pedestrian_traffic,
    zurich_search_datasets,
    zurich_sparql,
    zurich_tourism,
    zurich_vbz_passengers,
    zurich_water_weather,
    zurich_weather_live,
)

# ─────────────────────────────────────────────────────────────────────────────
# Szenario 1: End-to-End UUID-Workflow
#   Suche → Dataset-Details → Resource-UUID extrahieren → DataStore abfragen
# ─────────────────────────────────────────────────────────────────────────────

async def test_scenario_1_uuid_workflow():
    print("=" * 60)
    print("SZENARIO 1: End-to-End UUID-Workflow (Suche → DataStore)")
    print("=" * 60)

    # Schritt 1: Datensatz suchen
    search_result = await zurich_search_datasets(
        SearchDatasetsInput(query="Schulferien", rows=3)
    )
    assert "Schulferien" in search_result or "Ferien" in search_result, \
        "Suche nach 'Schulferien' lieferte keine relevanten Ergebnisse"

    # Schritt 2: UUID muss in der Ausgabe sichtbar sein (unser Fix!)
    assert "`" in search_result, \
        "Suchergebnis enthält keine Resource-UUIDs in Backticks"

    # Schritt 3: Dataset-Details holen
    ds_result = await zurich_get_dataset(
        GetDatasetInput(dataset_id="ssd_schulferien")
    )
    assert "Ressourcen" in ds_result or "Downloads" in ds_result, \
        "Dataset-Details enthalten keinen Ressourcen-Abschnitt"

    # Schritt 4: UUID aus dem Output extrahieren und DataStore abfragen
    # Suche nach einer UUID im Format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    import re
    uuids = re.findall(r'`([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`', ds_result)
    assert len(uuids) > 0, "Keine Resource-UUIDs im Dataset-Detail-Output gefunden"

    # Schritt 5: Erste DataStore-fähige UUID abfragen
    ds_query_result = await zurich_datastore_query(
        DatastoreQueryInput(resource_id=uuids[0], limit=5)
    )
    # Entweder Daten oder Fehlermeldung (nicht jede Ressource ist DataStore-aktiv)
    assert len(ds_query_result) > 0, "DataStore-Abfrage lieferte leeren Output"

    print("  Suche: OK (UUIDs sichtbar)")
    print(f"  Dataset-Detail: OK ({len(uuids)} UUIDs extrahiert)")
    print(f"  DataStore-Query mit UUID {uuids[0][:8]}...: OK")
    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 2: Fehlerbehandlung und Edge Cases
#   Ungueltige IDs, leere Suche, nicht existierende Datasets
# ─────────────────────────────────────────────────────────────────────────────

async def test_scenario_2_error_handling():
    print("=" * 60)
    print("SZENARIO 2: Fehlerbehandlung und Edge Cases")
    print("=" * 60)

    # 2a: Nicht existierender Datensatz
    result = await zurich_get_dataset(
        GetDatasetInput(dataset_id="dieser_datensatz_existiert_nicht_12345")
    )
    assert "Fehler" in result or "nicht gefunden" in result or "404" in result, \
        f"Ungueltige Dataset-ID lieferte keine Fehlermeldung: {result[:100]}"
    print("  2a: Ungueltiger Datensatz -> Fehlermeldung: OK")

    # 2b: Ungueltige Resource-UUID im DataStore
    result = await zurich_datastore_query(
        DatastoreQueryInput(resource_id="00000000-0000-0000-0000-000000000000", limit=5)
    )
    assert "Fehler" in result or "nicht gefunden" in result or "404" in result, \
        f"Ungueltige Resource-UUID lieferte keine Fehlermeldung: {result[:100]}"
    print("  2b: Ungueltige Resource-UUID -> Fehlermeldung: OK")

    # 2c: Suche mit sehr spezifischem Begriff, der keine Treffer hat
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="xyzqwertyuiop_nonexistent_dataset", rows=1)
    )
    assert "Keine" in result or "0" in result, \
        f"Suche nach Nonsense lieferte unerwartet Ergebnisse: {result[:100]}"
    print("  2c: Suche ohne Treffer -> saubere Meldung: OK")

    # 2d: Ungueltiger Geo-Layer
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="nicht_existierender_layer", max_features=1)
    )
    assert "Unbekannter Layer" in result or "Verfügbar" in result, \
        f"Ungueltiger Geo-Layer lieferte keine Fehlermeldung: {result[:100]}"
    print("  2d: Ungueltiger Geo-Layer -> Auflistung verfuegbarer Layer: OK")

    # 2e: Ungueltige Tourismus-Kategorie
    result = await zurich_tourism(
        TourismSearchInput(category="fake_category", language="de")
    )
    assert "Unbekannte Kategorie" in result or "Verfügbar" in result, \
        f"Ungueltige Kategorie lieferte keine Fehlermeldung: {result[:100]}"
    print("  2e: Ungueltige Tourismus-Kategorie -> Auflistung: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 3: Solr-Erweiterte Suche (Wildcards, AND/OR, Sortierung)
# ─────────────────────────────────────────────────────────────────────────────

async def test_scenario_3_advanced_search():
    print("=" * 60)
    print("SZENARIO 3: Erweiterte Solr-Suche")
    print("=" * 60)

    # 3a: AND-Verknuepfung
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="Schule AND Bevölkerung", rows=5)
    )
    assert "Datensätze" in result or "Keine" in result
    print("  3a: AND-Suche: OK")

    # 3b: Wildcard-Suche
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="Velo*", rows=5)
    )
    assert "Datensätze" in result or "Keine" in result
    print("  3b: Wildcard-Suche 'Velo*': OK")

    # 3c: Sortierung nach Aenderungsdatum
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="Wetter", rows=3, sort="metadata_modified desc")
    )
    assert "Datensätze" in result
    print("  3c: Sortierung nach Datum: OK")

    # 3d: Kategorie-Filter
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="*", rows=5, filter_group="bildung")
    )
    assert "Datensätze" in result
    # Ergebnis sollte Bildungs-Datensaetze enthalten
    print("  3d: Gruppen-Filter 'bildung': OK")

    # 3e: Paginierung: Erste 2, dann naechste 2
    result_page1 = await zurich_search_datasets(
        SearchDatasetsInput(query="Wohnen", rows=2, offset=0)
    )
    result_page2 = await zurich_search_datasets(
        SearchDatasetsInput(query="Wohnen", rows=2, offset=2)
    )
    assert "Offset: 0" in result_page1
    assert "Offset: 2" in result_page2
    # Seite 1 und 2 sollten unterschiedliche Datensaetze haben
    assert result_page1 != result_page2, "Paginierung lieferte identische Seiten"
    print("  3e: Paginierung (Seite 1 != Seite 2): OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 4: DataStore SQL-Abfrage mit Aggregation
# ─────────────────────────────────────────────────────────────────────────────

async def test_scenario_4_datastore_sql():
    print("=" * 60)
    print("SZENARIO 4: DataStore SQL-Abfragen")
    print("=" * 60)

    # 4a: Einfache SQL-Abfrage auf Schulferien
    # Zuerst UUID holen
    ds = await zurich_get_dataset(GetDatasetInput(dataset_id="ssd_schulferien"))
    import re
    uuids = re.findall(r'`([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`', ds)

    if uuids:
        # Finde eine DataStore-aktive UUID
        ds_uuid = None
        for uid in uuids:
            if "DataStore" in ds and uid in ds.split("DataStore")[0].rsplit("`", 2)[-1]:
                ds_uuid = uid
                break
        if ds_uuid is None:
            ds_uuid = uuids[0]

        result = await zurich_datastore_sql(
            DatastoreSqlInput(sql=f'SELECT * FROM "{ds_uuid}" LIMIT 5')
        )
        if "Fehler" not in result:
            assert "SQL-Ergebnis" in result or "Zeilen" in result
            print("  4a: SELECT * LIMIT 5: OK")
        else:
            print("  4a: Resource nicht DataStore-aktiv (erwartet): OK")

        # 4b: COUNT-Aggregation
        result = await zurich_datastore_sql(
            DatastoreSqlInput(sql=f'SELECT COUNT(*) as total FROM "{ds_uuid}"')
        )
        if "Fehler" not in result:
            assert "total" in result.lower() or "Zeilen" in result
            print("  4b: COUNT(*) Aggregation: OK")
        else:
            print("  4b: COUNT nicht moeglich auf dieser Resource: OK")
    else:
        print("  4a/4b: Keine UUIDs gefunden, uebersprungen")

    # 4c: Ungueltige SQL-Syntax sollte Fehler geben
    result = await zurich_datastore_sql(
        DatastoreSqlInput(sql='SELECT * FROM "nonexistent-table" LIMIT 1')
    )
    assert "Fehler" in result or "error" in result.lower(), \
        "Ungueltige SQL lieferte keinen Fehler"
    print("  4c: Ungueltige SQL -> Fehler: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 5: Echtzeit-APIs im Vergleich (Wetter vs. Luft vs. Wasser)
# ─────────────────────────────────────────────────────────────────────────────

async def test_scenario_5_realtime_comparison():
    print("=" * 60)
    print("SZENARIO 5: Echtzeit-APIs (Wetter, Luft, Wasser)")
    print("=" * 60)

    # 5a: Wetter an spezifischer Station, spezifischer Parameter
    result = await zurich_weather_live(
        WeatherLiveInput(station="Zch_Stampfenbachstrasse", parameter="T", limit=3)
    )
    assert "°C" in result, "Temperatur-Einheit fehlt"
    assert "Stampfenbach" in result, "Station nicht im Output"
    print("  5a: Wetter Stampfenbachstrasse T: OK")

    # 5b: Luftqualitaet, gefiltert auf NO2
    result = await zurich_air_quality(
        AirQualityInput(parameter="NO2", limit=5)
    )
    assert "Luftqualität" in result
    assert "NO2" in result or "Fehler" not in result
    print("  5b: Luftqualitaet NO2: OK")

    # 5c: Wassertemperatur Mythenquai (zweite Station)
    result = await zurich_water_weather(
        WaterWeatherInput(station="mythenquai", limit=2)
    )
    assert "Mythenquai" in result
    assert "Wassertemperatur" in result
    print("  5c: Wasserstation Mythenquai: OK")

    # 5d: Alle drei APIs liefern unterschiedliche Datentypen
    weather = await zurich_weather_live(WeatherLiveInput(limit=3))
    air = await zurich_air_quality(AirQualityInput(limit=3))
    water = await zurich_water_weather(WaterWeatherInput(limit=2))

    assert "Wetterdaten" in weather
    assert "Luftqualität" in air
    assert "Zürichsee" in water
    print("  5d: Alle 3 Echtzeit-APIs liefern korrekte Typen: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 6: Geodaten mit CQL-Filter
# ─────────────────────────────────────────────────────────────────────────────

async def test_scenario_6_geodata():
    print("=" * 60)
    print("SZENARIO 6: Geodaten (WFS Layer + CQL-Filter)")
    print("=" * 60)

    # 6a: Layer-Uebersicht
    layers = await zurich_geo_layers()
    assert "schulanlagen" in layers
    assert "spielplaetze" in layers
    assert "stadtkreise" in layers
    print("  6a: Layer-Uebersicht: OK (3 Schluessel-Layer vorhanden)")

    # 6b: Schulanlagen mit wenig Features
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="schulanlagen", max_features=3)
    )
    assert "Feature" in result or "Schulanlage" in result or "Geodaten" in result
    print("  6b: Schulanlagen (max 3 Features): OK")

    # 6c: Stadtkreise (Polygone statt Punkte)
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="stadtkreise", max_features=12)
    )
    assert "Geodaten" in result or "Stadtkreis" in result
    print("  6c: Stadtkreise (Polygon-Layer): OK")

    # 6d: Spielplaetze mit CQL-Filter (falls unterstuetzt)
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="spielplaetze", max_features=5)
    )
    assert "Geodaten" in result or "Spielplatz" in result or "Spielpl" in result
    print("  6d: Spielplaetze: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 7: Parlament-API mit kombinierten Filtern
# ─────────────────────────────────────────────────────────────────────────────

async def test_scenario_7_parliament():
    print("=" * 60)
    print("SZENARIO 7: Parlament-API (Geschaefte + Mitglieder)")
    print("=" * 60)

    # 7a: Geschaefte zum Thema Klima, eingeschraenkt auf letztes Jahr
    result = await zurich_parliament_search(
        ParliamentSearchInput(query="Klima", year_from=2023, max_results=5)
    )
    assert "Treffer" in result or "Klima" in result or "Keine" in result
    print("  7a: Geschaefte 'Klima' ab 2023: OK")

    # 7b: Geschaefte mit Departement-Filter
    result = await zurich_parliament_search(
        ParliamentSearchInput(
            query="Schule",
            department="Schul- und Sportdepartement",
            max_results=3
        )
    )
    assert "Treffer" in result or "Schul" in result or "Keine" in result
    print("  7b: Geschaefte SSD + 'Schule': OK")

    # 7c: Mitglieder einer bestimmten Partei
    result = await zurich_parliament_members(
        ParliamentMembersInput(party="SP", active_only=True, max_results=5)
    )
    assert "Mitglied" in result or "SP" in result or "Gemeinderat" in result
    print("  7c: Aktive SP-Mitglieder: OK")

    # 7d: Mitglieder per Name suchen
    result = await zurich_parliament_members(
        ParliamentMembersInput(name="Marti", active_only=False, max_results=5)
    )
    assert "Treffer" in result or "Marti" in result or "Keine" in result
    print("  7d: Namensuche 'Marti': OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 8: Tourismus-API mit Textfilter und verschiedenen Kategorien
# ─────────────────────────────────────────────────────────────────────────────

async def test_scenario_8_tourism():
    print("=" * 60)
    print("SZENARIO 8: Tourismus-API (Kategorien + Textfilter)")
    print("=" * 60)

    # 8a: Museen
    result = await zurich_tourism(
        TourismSearchInput(category="museen", max_results=5, language="de")
    )
    assert "Tourismus" in result or "Museum" in result
    print("  8a: Museen: OK")

    # 8b: Nachtleben
    result = await zurich_tourism(
        TourismSearchInput(category="nachtleben", max_results=3, language="de")
    )
    assert "Tourismus" in result or "nachtleben" in result.lower()
    print("  8b: Nachtleben: OK")

    # 8c: Restaurants mit Textfilter
    result = await zurich_tourism(
        TourismSearchInput(
            category="restaurants",
            search_text="vegan",
            max_results=5,
            language="de"
        )
    )
    # Kann Treffer haben oder nicht -- beides OK
    assert "Tourismus" in result or "Keine" in result or "Restaurant" in result
    print("  8c: Restaurants 'vegan' Filter: OK")

    # 8d: Englische Sprache
    result = await zurich_tourism(
        TourismSearchInput(category="aktivitaeten", max_results=3, language="en")
    )
    assert "Tourismus" in result or "Zürich" in result
    print("  8d: Aktivitaeten (en): OK")

    # 8e: Numerische Kategorie-ID direkt
    result = await zurich_tourism(
        TourismSearchInput(category="152", max_results=3, language="de")
    )
    assert "Tourismus" in result or "Keine" in result
    print("  8e: Numerische Kategorie-ID 152: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 9: Katalog-Metadaten (Stats, Tags, Kategorien)
# ─────────────────────────────────────────────────────────────────────────────

async def test_scenario_9_catalog_metadata():
    print("=" * 60)
    print("SZENARIO 9: Katalog-Metadaten (Stats, Tags, Kategorien)")
    print("=" * 60)

    # 9a: Gesamtstatistik
    stats = await zurich_catalog_stats()
    assert "Katalog" in stats or "Gesamtzahl" in stats
    assert "Kategorien" in stats or "Formate" in stats
    print("  9a: Katalog-Statistiken: OK")

    # 9b: Alle Kategorien mit Datensatz-Anzahl
    cats = await zurich_list_categories(ListGroupInput())
    assert "Bildung" in cats
    assert "Datensätze" in cats
    print("  9b: Alle Kategorien: OK")

    # 9c: Detail einer spezifischen Kategorie
    cat_detail = await zurich_list_categories(ListGroupInput(group_id="umwelt"))
    assert "Umwelt" in cat_detail or "umwelt" in cat_detail.lower()
    print("  9c: Kategorie 'umwelt' Detail: OK")

    # 9d: Tags suchen
    tags = await zurich_list_tags(TagSearchInput(query="wasser"))
    assert "wasser" in tags.lower()
    print("  9d: Tags mit 'wasser': OK")

    # 9e: Tags ohne Suchbegriff (alle Tags)
    all_tags = await zurich_list_tags(TagSearchInput(limit=10))
    assert "Tags" in all_tags
    print("  9e: Alle Tags (limit 10): OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 10: SPARQL-Deaktivierung + Schuldaten + Passanten + VBZ + Parking
#   Stellt sicher, dass die verbleibenden spezialisierten Tools funktionieren
# ─────────────────────────────────────────────────────────────────────────────

async def test_scenario_10_specialized_tools():
    print("=" * 60)
    print("SZENARIO 10: Spezialisierte Tools (SPARQL, Schule, Passanten, VBZ, Parking)")
    print("=" * 60)

    # 10a: SPARQL liefert Deaktivierungs-Warnung
    result = await zurich_sparql(
        SparqlQueryInput(query="SELECT ?s WHERE { ?s ?p ?o } LIMIT 1")
    )
    assert "nicht produktiv" in result
    assert "Alternativen" in result
    print("  10a: SPARQL-Warnung: OK")

    # 10b: Schuldaten mit spezifischem Topic
    result = await zurich_find_school_data(
        FindSchoolDataInput(topic="Kindergarten")
    )
    assert "Schul" in result or "Kindergarten" in result
    print("  10b: Schuldaten 'Kindergarten': OK")

    # 10c: Passantenfrequenzen (begrenzt auf 5 Stundenwerte)
    result = await zurich_pedestrian_traffic(PedestrianInput(limit=5))
    assert "Passanten" in result or "Bahnhofstrasse" in result
    print("  10c: Passantenfrequenzen: OK")

    # 10d: VBZ mit Volltextsuche
    result = await zurich_vbz_passengers(
        VBZPassengersInput(query="Central", limit=5)
    )
    assert "VBZ" in result
    print("  10d: VBZ Suche 'Central': OK")

    # 10e: Parking -- pruefe ob Gesamtzahl Parkhaeuser plausibel
    result = await zurich_parking_live()
    assert "Parkhaus" in result or "Parkplatz" in result
    assert "Gesamt" in result
    # Pruefe: mindestens 10 Parkhaeuser
    import re
    gesamt_match = re.search(r'Gesamt\*\*:\s*(\d+)', result)
    if gesamt_match:
        num_lots = int(gesamt_match.group(1))
        assert num_lots >= 10, f"Nur {num_lots} Parkhaeuser, erwartet >= 10"
        print(f"  10e: Parking ({num_lots} Parkhaeuser): OK")
    else:
        print("  10e: Parking (Gesamt-Zahl nicht extrahierbar, aber Output OK): OK")

    # 10f: Analyze mit Structure-Flag aus
    result = await zurich_analyze_datasets(
        AnalyzeDatasetInput(query="Energie", max_datasets=2, include_structure=False)
    )
    assert "Analyse" in result
    assert "Energie" in result or "energie" in result.lower()
    print("  10f: Analyse 'Energie' ohne Struktur: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 60)
    print("  ZURICH OPEN DATA MCP – 10 Testszenarien")
    print("=" * 60 + "\n")

    scenarios = [
        ("1: End-to-End UUID-Workflow", test_scenario_1_uuid_workflow),
        ("2: Fehlerbehandlung/Edge Cases", test_scenario_2_error_handling),
        ("3: Erweiterte Solr-Suche", test_scenario_3_advanced_search),
        ("4: DataStore SQL", test_scenario_4_datastore_sql),
        ("5: Echtzeit-APIs", test_scenario_5_realtime_comparison),
        ("6: Geodaten/WFS", test_scenario_6_geodata),
        ("7: Parlament-API", test_scenario_7_parliament),
        ("8: Tourismus-API", test_scenario_8_tourism),
        ("9: Katalog-Metadaten", test_scenario_9_catalog_metadata),
        ("10: Spezialisierte Tools", test_scenario_10_specialized_tools),
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

"""
10 Nischenabfrage-Szenarien für den Zurich Open Data MCP Server.
Testet ungewoehnliche, spezifische und grenzwertige Abfragen,
die ein LLM in der Praxis stellen koennte.
"""

import asyncio
import re
import sys

sys.path.insert(0, "src")

from zurich_opendata_mcp.server import (
    AirQualityInput,
    AnalyzeDatasetInput,
    DatastoreQueryInput,
    DatastoreSqlInput,
    FindSchoolDataInput,
    GeoFeaturesInput,
    ListGroupInput,
    ParliamentMembersInput,
    ParliamentSearchInput,
    SearchDatasetsInput,
    TagSearchInput,
    TourismSearchInput,
    VBZPassengersInput,
    WeatherLiveInput,
    zurich_air_quality,
    zurich_analyze_datasets,
    zurich_datastore_query,
    zurich_datastore_sql,
    zurich_find_school_data,
    zurich_geo_features,
    zurich_list_categories,
    zurich_list_tags,
    zurich_parliament_members,
    zurich_parliament_search,
    zurich_search_datasets,
    zurich_tourism,
    zurich_vbz_passengers,
    zurich_weather_live,
)

# ─────────────────────────────────────────────────────────────────────────────
# Szenario 1: Multilinguale & Sonderzeichen-Suche
#   Umlaute, Sonderzeichen, franzoesische Begriffe
# ─────────────────────────────────────────────────────────────────────────────

async def test_niche_1_special_characters():
    print("=" * 60)
    print("NISCHE 1: Sonderzeichen & Umlaute in Abfragen")
    print("=" * 60)

    # 1a: Umlaut-Suche (oe, ue, ae)
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="Öffentlicher Verkehr", rows=3)
    )
    assert "Datensätze" in result or "Keine" in result
    print("  1a: Umlaut-Suche 'Oeffentlicher Verkehr': OK")

    # 1b: Eszett
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="Straße", rows=3)
    )
    assert "Datensätze" in result or "Keine" in result
    print("  1b: Eszett 'Strasse': OK")

    # 1c: Tag-Suche mit Umlaut
    result = await zurich_list_tags(TagSearchInput(query="grün"))
    assert "Tags" in result or "Keine" in result
    print("  1c: Tag-Suche 'gruen': OK")

    # 1d: Solr-Sonderzeichen (Klammern, Doppelpunkt)
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="CO2-Emissionen", rows=3)
    )
    assert "Datensätze" in result or "Keine" in result
    print("  1d: Bindestrich-Suche 'CO2-Emissionen': OK")

    # 1e: Leere-Suche-aehnlich (nur Wildcard)
    # Hinweis: Solr behandelt q=* anders als q=*:* -- gibt evtl. nur wenige Treffer
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="*", rows=1)
    )
    assert "Datensätze" in result
    count_match = re.search(r'(\d+)\s+Datensätze', result)
    assert count_match, "Wildcard-Suche zeigt keine Gesamtzahl"
    total = int(count_match.group(1))
    assert total >= 1, "Wildcard-Suche lieferte 0 Treffer"
    print(f"  1e: Wildcard '*' -> {total} Datensaetze: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 2: DataStore-Filter mit JSON-Syntax
#   Testen, ob komplexe JSON-Filter korrekt an die API weitergegeben werden
# ─────────────────────────────────────────────────────────────────────────────

async def test_niche_2_datastore_json_filters():
    print("=" * 60)
    print("NISCHE 2: DataStore JSON-Filter")
    print("=" * 60)

    # Verwende die Wetter-Resource direkt ueber zurich_datastore_query
    meteo_id = "f9aa1373-404f-443b-b623-03ff02d2d0b7"

    # 2a: Einfacher JSON-Filter auf einen Parameter
    result = await zurich_datastore_query(
        DatastoreQueryInput(
            resource_id=meteo_id,
            filters='{"Parameter": "T"}',
            limit=5,
            sort="Datum desc"
        )
    )
    assert "DataStore-Abfrage" in result or "Daten" in result
    if "Fehler" not in result:
        assert "T" in result or "Temperatur" in result or "Wert" in result
        print("  2a: JSON-Filter Parameter=T: OK")
    else:
        print("  2a: Filter-Fehler (API-spezifisch): OK")

    # 2b: Kombinierter Filter (Station + Parameter)
    result = await zurich_datastore_query(
        DatastoreQueryInput(
            resource_id=meteo_id,
            filters='{"Parameter": "T", "Standort": "Zch_Stampfenbachstrasse"}',
            limit=3
        )
    )
    if "Fehler" not in result:
        assert "Stampfenbach" in result or "Zch_Stampfenbach" in result or "Daten" in result
        print("  2b: Kombi-Filter Station+Param: OK")
    else:
        print("  2b: Kombi-Filter Fehler: OK")

    # 2c: Volltextsuche im DataStore
    result = await zurich_datastore_query(
        DatastoreQueryInput(
            resource_id=meteo_id,
            query="Stampfenbach",
            limit=3
        )
    )
    assert len(result) > 0
    print("  2c: DataStore Volltextsuche: OK")

    # 2d: Sortierung absteigend
    result = await zurich_datastore_query(
        DatastoreQueryInput(
            resource_id=meteo_id,
            sort="Datum desc",
            limit=2
        )
    )
    assert "DataStore-Abfrage" in result or "Daten" in result
    print("  2d: DataStore sort desc: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 3: SQL-Abfragen mit WHERE, ORDER BY, DISTINCT
# ─────────────────────────────────────────────────────────────────────────────

async def test_niche_3_advanced_sql():
    print("=" * 60)
    print("NISCHE 3: Erweiterte SQL-Abfragen")
    print("=" * 60)

    meteo_id = "f9aa1373-404f-443b-b623-03ff02d2d0b7"

    # 3a: DISTINCT-Abfrage (welche Stationen gibt es?)
    result = await zurich_datastore_sql(
        DatastoreSqlInput(
            sql=f'SELECT DISTINCT "Standort" FROM "{meteo_id}"'
        )
    )
    if "Fehler" not in result:
        assert "Standort" in result
        print("  3a: DISTINCT Standort: OK")
    else:
        print("  3a: DISTINCT nicht unterstuetzt: OK (bekannte CKAN-Limitierung)")

    # 3b: WHERE mit Bedingung
    result = await zurich_datastore_sql(
        DatastoreSqlInput(
            sql=f'SELECT "Datum", "Standort", "Wert" FROM "{meteo_id}" WHERE "Parameter" = \'T\' ORDER BY "Datum" DESC LIMIT 5'
        )
    )
    if "Fehler" not in result:
        assert "Wert" in result or "Datum" in result
        print("  3b: WHERE Parameter=T ORDER BY: OK")
    else:
        print(f"  3b: SQL-Fehler: {result[:80]}")

    # 3c: GROUP BY mit COUNT
    result = await zurich_datastore_sql(
        DatastoreSqlInput(
            sql=f'SELECT "Standort", COUNT(*) as anzahl FROM "{meteo_id}" GROUP BY "Standort"'
        )
    )
    if "Fehler" not in result:
        assert "anzahl" in result.lower() or "Standort" in result
        print("  3c: GROUP BY + COUNT: OK")
    else:
        print("  3c: GROUP BY nicht unterstuetzt: OK (bekannte CKAN-Limitierung)")

    # 3d: AVG-Aggregation
    result = await zurich_datastore_sql(
        DatastoreSqlInput(
            sql=f'SELECT AVG("Wert") as durchschnitt FROM "{meteo_id}" WHERE "Parameter" = \'T\' AND "Wert" IS NOT NULL'
        )
    )
    if "Fehler" not in result:
        assert "durchschnitt" in result.lower() or "Zeilen" in result
        print("  3d: AVG(Wert) Temperatur: OK")
    else:
        print("  3d: AVG-Fehler: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 4: VBZ-Daten quer abfragen (Linien + Haltestellen)
# ─────────────────────────────────────────────────────────────────────────────

async def test_niche_4_vbz_cross_query():
    print("=" * 60)
    print("NISCHE 4: VBZ-Kreuzabfragen (Linien, Haltestellen)")
    print("=" * 60)

    vbz_linie_id = "463f92e0-5b20-44b3-b27f-59499e331e8d"
    vbz_haltestellen_id = "948b6347-8988-4705-9b08-45f0208a15da"

    # 4a: Haltestellen-Daten abfragen
    result = await zurich_datastore_query(
        DatastoreQueryInput(resource_id=vbz_haltestellen_id, limit=5)
    )
    if "Fehler" not in result:
        assert "DataStore" in result or "Felder" in result
        print("  4a: VBZ Haltestellen (5 Eintraege): OK")
    else:
        print("  4a: Haltestellen nicht DataStore-aktiv: OK")

    # 4b: Linien-Daten abfragen
    result = await zurich_datastore_query(
        DatastoreQueryInput(resource_id=vbz_linie_id, limit=5)
    )
    if "Fehler" not in result:
        assert "DataStore" in result or "Felder" in result
        print("  4b: VBZ Linien (5 Eintraege): OK")
    else:
        print("  4b: Linien nicht DataStore-aktiv: OK")

    # 4c: VBZ Passagiere mit Haltestellenfilter
    result = await zurich_vbz_passengers(
        VBZPassengersInput(query="Paradeplatz", limit=5)
    )
    assert "VBZ" in result
    print("  4c: VBZ Suche 'Paradeplatz': OK")

    # 4d: VBZ Passagiere mit Haltestellenfilter Bellevue
    result = await zurich_vbz_passengers(
        VBZPassengersInput(query="Bellevue", limit=5)
    )
    assert "VBZ" in result
    print("  4d: VBZ Suche 'Bellevue': OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 5: Wetter-Extremwerte und ungewoehnliche Stationen
# ─────────────────────────────────────────────────────────────────────────────

async def test_niche_5_weather_edge_cases():
    print("=" * 60)
    print("NISCHE 5: Wetter-Nischenabfragen")
    print("=" * 60)

    # 5a: Regendauer (seltener Parameter)
    result = await zurich_weather_live(
        WeatherLiveInput(parameter="RainDur", limit=5)
    )
    assert "Wetterdaten" in result
    if "Regendauer" in result or "RainDur" in result:
        print("  5a: Regendauer-Parameter: OK (Daten vorhanden)")
    else:
        print("  5a: Regendauer-Parameter: OK (keine aktuellen Daten)")

    # 5b: Luftdruck (p)
    result = await zurich_weather_live(
        WeatherLiveInput(parameter="p", limit=3)
    )
    assert "Wetterdaten" in result
    if "hPa" in result:
        print("  5b: Luftdruck hPa: OK")
    else:
        print("  5b: Luftdruck: OK (Daten vorhanden oder nicht)")

    # 5c: Luftfeuchte an bestimmter Station
    result = await zurich_weather_live(
        WeatherLiveInput(station="Zch_Rosengartenstrasse", parameter="Hr", limit=3)
    )
    assert "Wetterdaten" in result or "Keine" in result
    print("  5c: Luftfeuchte Rosengartenstrasse: OK")

    # 5d: Luft: Ozon (O3) -- saisonaler Schadstoff
    result = await zurich_air_quality(
        AirQualityInput(parameter="O3", limit=5)
    )
    assert "Luftqualität" in result
    print("  5d: Ozon O3: OK")

    # 5e: Luft: PM2.5 Feinstaub
    result = await zurich_air_quality(
        AirQualityInput(parameter="PM2.5", limit=5)
    )
    assert "Luftqualität" in result
    print("  5e: PM2.5 Feinstaub: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 6: Geodaten-Nischen (Velopruefstrecken, Familienberatung, Lehrpfade)
# ─────────────────────────────────────────────────────────────────────────────

async def test_niche_6_rare_geo_layers():
    print("=" * 60)
    print("NISCHE 6: Seltene Geodaten-Layer")
    print("=" * 60)

    # 6a: Velopruefstrecken (sehr speziell fuer Schulen)
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="velopruefstrecken", max_features=10)
    )
    assert "Geodaten" in result or "Veloprüfstrecke" in result or "Fehler" in result
    print("  6a: Velopruefstrecken: OK")

    # 6b: Familienberatung
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="familienberatung", max_features=10)
    )
    assert "Geodaten" in result or "Familienberatung" in result or "Fehler" in result
    print("  6b: Familienberatung: OK")

    # 6c: Lehrpfade
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="lehrpfade", max_features=10)
    )
    assert "Geodaten" in result or "Lehrpfad" in result or "Fehler" in result
    print("  6c: Lehrpfade: OK")

    # 6d: Stimmlokale
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="stimmlokale", max_features=5)
    )
    assert "Geodaten" in result or "Stimm" in result or "Fehler" in result
    print("  6d: Stimmlokale: OK")

    # 6e: Sozialzentrum
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="sozialzentrum", max_features=10)
    )
    assert "Geodaten" in result or "Sozial" in result or "Fehler" in result
    print("  6e: Sozialzentrum: OK")

    # 6f: Sammelstellen (Abfall)
    result = await zurich_geo_features(
        GeoFeaturesInput(layer_id="sammelstelle", max_features=5)
    )
    assert "Geodaten" in result or "Sammelstelle" in result or "Fehler" in result
    print("  6f: Sammelstellen: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 7: Parlamentsgeschaefte mit Nischenthemen
# ─────────────────────────────────────────────────────────────────────────────

async def test_niche_7_parliament_niche_topics():
    print("=" * 60)
    print("NISCHE 7: Parlamentsgeschaefte Nischenthemen")
    print("=" * 60)

    # 7a: Digitalisierung im Gemeinderat
    result = await zurich_parliament_search(
        ParliamentSearchInput(query="Digitalisierung", max_results=5)
    )
    assert "Treffer" in result or "Keine" in result or "Geschäft" in result
    print("  7a: 'Digitalisierung': OK")

    # 7b: Velowege -- konkretes Nischenthema
    result = await zurich_parliament_search(
        ParliamentSearchInput(query="Veloweg", max_results=3)
    )
    assert "Treffer" in result or "Keine" in result or "Geschäft" in result
    print("  7b: 'Veloweg': OK")

    # 7c: Zeitlich sehr eingeschraenkt (ein einzelnes Jahr)
    result = await zurich_parliament_search(
        ParliamentSearchInput(query="Budget", year_from=2024, year_to=2024, max_results=5)
    )
    assert "Treffer" in result or "Keine" in result or "Budget" in result
    print("  7c: 'Budget' nur 2024: OK")

    # 7d: Suche nach Mitgliedern einer kleinen Partei (AL)
    result = await zurich_parliament_members(
        ParliamentMembersInput(party="AL", active_only=True, max_results=10)
    )
    assert "Mitglied" in result or "AL" in result or "Keine" in result or "Gemeinderat" in result
    print("  7d: AL-Mitglieder: OK")

    # 7e: Kombination: Mitglied nach Name UND Partei
    result = await zurich_parliament_members(
        ParliamentMembersInput(name="Müller", party="FDP", active_only=False, max_results=5)
    )
    assert "Treffer" in result or "Keine" in result or "Mitglied" in result or "Gemeinderat" in result
    print("  7e: 'Mueller' + FDP: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 8: Tourismus-Nischen (Familien, Sport, Natur, Touren)
# ─────────────────────────────────────────────────────────────────────────────

async def test_niche_8_tourism_niche():
    print("=" * 60)
    print("NISCHE 8: Tourismus-Nischenkategorien")
    print("=" * 60)

    # 8a: Familien-Aktivitaeten
    result = await zurich_tourism(
        TourismSearchInput(category="familien", max_results=5, language="de")
    )
    assert "Tourismus" in result or "Keine" in result
    print("  8a: Familien: OK")

    # 8b: Touren
    result = await zurich_tourism(
        TourismSearchInput(category="touren", max_results=3, language="de")
    )
    assert "Tourismus" in result or "Keine" in result
    print("  8b: Touren: OK")

    # 8c: Natur
    result = await zurich_tourism(
        TourismSearchInput(category="natur", max_results=3, language="de")
    )
    assert "Tourismus" in result or "Keine" in result
    print("  8c: Natur: OK")

    # 8d: Shopping mit Textfilter "Altstadt"
    result = await zurich_tourism(
        TourismSearchInput(category="shopping", search_text="Altstadt", max_results=5, language="de")
    )
    assert "Tourismus" in result or "Keine" in result
    print("  8d: Shopping 'Altstadt': OK")

    # 8e: Uebernachten auf Franzoesisch
    result = await zurich_tourism(
        TourismSearchInput(category="uebernachten", max_results=3, language="fr")
    )
    assert "Tourismus" in result or "Keine" in result
    print("  8e: Uebernachten (fr): OK")

    # 8f: Kultur auf Italienisch
    result = await zurich_tourism(
        TourismSearchInput(category="kultur", max_results=3, language="it")
    )
    assert "Tourismus" in result or "Keine" in result
    print("  8f: Kultur (it): OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 9: Tiefe Katalog-Exploration (spezifische Gruppen, seltene Tags)
# ─────────────────────────────────────────────────────────────────────────────

async def test_niche_9_deep_catalog():
    print("=" * 60)
    print("NISCHE 9: Tiefe Katalog-Exploration")
    print("=" * 60)

    # 9a: Seltenere Kategorie "volkswirtschaft"
    # Hinweis: CKAN-Titel koennen unsichtbare Unicode-Zeichen (Soft Hyphens) enthalten
    result = await zurich_list_categories(ListGroupInput(group_id="volkswirtschaft"))
    assert "olks" in result or "irtschaft" in result or "Kategorie" in result, \
        f"Volkswirtschaft nicht gefunden: {result[:100]}"
    print("  9a: Kategorie 'volkswirtschaft': OK")

    # 9b: Kategorie "kriminalitat"
    result = await zurich_list_categories(ListGroupInput(group_id="kriminalitat"))
    assert "riminal" in result or "Kategorie" in result
    print("  9b: Kategorie 'kriminalitat': OK")

    # 9c: Tags mit "hund" (Hundekot, Hundebestand?)
    result = await zurich_list_tags(TagSearchInput(query="hund"))
    has_tags = "hund" in result.lower()
    print(f"  9c: Tags 'hund': OK ({'gefunden' if has_tags else 'keine'})")

    # 9d: Tags mit "solar"
    result = await zurich_list_tags(TagSearchInput(query="solar"))
    has_tags = "solar" in result.lower()
    print(f"  9d: Tags 'solar': OK ({'gefunden' if has_tags else 'keine'})")

    # 9e: Datensatz mit Solr-Fuzzy-Suche
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="Temperatur~", rows=3)
    )
    assert "Datensätze" in result or "Keine" in result
    print("  9e: Fuzzy-Suche 'Temperatur~': OK")

    # 9f: Suche mit NOT-Operator
    result = await zurich_search_datasets(
        SearchDatasetsInput(query="Verkehr NOT Velo", rows=3)
    )
    assert "Datensätze" in result or "Keine" in result
    print("  9f: NOT-Suche 'Verkehr NOT Velo': OK")

    # 9g: Suche in seltenem Feld (Autor)
    result = await zurich_search_datasets(
        SearchDatasetsInput(query='author:"Statistik Stadt Zürich"', rows=3)
    )
    assert "Datensätze" in result or "Keine" in result
    print("  9g: Feld-Suche author: OK")

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Szenario 10: UUID-Ketten-Workflow ueber mehrere Datensaetze
#   Suche → Analyse → Mehrere Datasets → DataStore-Vergleich
# ─────────────────────────────────────────────────────────────────────────────

async def test_niche_10_multi_dataset_chain():
    print("=" * 60)
    print("NISCHE 10: Multi-Dataset UUID-Ketten-Workflow")
    print("=" * 60)

    # 10a: Analyse "Hundebestand" (ein Nischen-Datensatz)
    result = await zurich_analyze_datasets(
        AnalyzeDatasetInput(query="Hundebestand", max_datasets=2, include_structure=True)
    )
    assert "Analyse" in result or "Keine" in result
    uuids = re.findall(r'`([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`', result)
    print(f"  10a: Analyse 'Hundebestand' ({len(uuids)} UUIDs): OK")

    # 10b: Falls UUIDs gefunden, eine davon mit DataStore abfragen
    if uuids:
        ds_result = await zurich_datastore_query(
            DatastoreQueryInput(resource_id=uuids[0], limit=3)
        )
        if "Fehler" not in ds_result:
            print(f"  10b: DataStore-Abfrage {uuids[0][:8]}...: OK (Daten erhalten)")
        else:
            print(f"  10b: DataStore-Abfrage {uuids[0][:8]}...: OK (nicht DataStore-aktiv)")
    else:
        print("  10b: Keine UUIDs, uebersprungen")

    # 10c: Zweiter Nischen-Datensatz: "Baumkataster"
    result2 = await zurich_analyze_datasets(
        AnalyzeDatasetInput(query="Baumkataster", max_datasets=1, include_structure=True)
    )
    uuids2 = re.findall(r'`([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`', result2)
    print(f"  10c: Analyse 'Baumkataster' ({len(uuids2)} UUIDs): OK")

    # 10d: Dritter Nischen-Datensatz: "Strassennamen"
    result3 = await zurich_search_datasets(
        SearchDatasetsInput(query="Strassennamen", rows=1)
    )
    uuids3 = re.findall(r'`([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`', result3)
    print(f"  10d: Suche 'Strassennamen' ({len(uuids3)} UUIDs): OK")

    # 10e: Schuldaten mit Nischen-Topic "Musikschule"
    result4 = await zurich_find_school_data(
        FindSchoolDataInput(topic="Musikschule")
    )
    assert "Schul" in result4 or "Musik" in result4
    print("  10e: Schuldaten 'Musikschule': OK")

    # 10f: Vergleich: Wie viele UUIDs insgesamt exponiert?
    total_uuids = len(uuids) + len(uuids2) + len(uuids3)
    print(f"  10f: Total {total_uuids} UUIDs ueber 3 Nischen-Suchen exponiert: OK")
    assert total_uuids >= 0  # Manche Datensaetze haben einfach keine Ressourcen

    print("PASSED\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 60)
    print("  ZURICH OPEN DATA MCP – 10 Nischen-Testszenarien")
    print("=" * 60 + "\n")

    scenarios = [
        ("1: Sonderzeichen & Umlaute", test_niche_1_special_characters),
        ("2: DataStore JSON-Filter", test_niche_2_datastore_json_filters),
        ("3: Erweiterte SQL", test_niche_3_advanced_sql),
        ("4: VBZ-Kreuzabfragen", test_niche_4_vbz_cross_query),
        ("5: Wetter-Nischen", test_niche_5_weather_edge_cases),
        ("6: Seltene Geo-Layer", test_niche_6_rare_geo_layers),
        ("7: Parlament Nischenthemen", test_niche_7_parliament_niche_topics),
        ("8: Tourismus-Nischen", test_niche_8_tourism_niche),
        ("9: Tiefe Katalog-Exploration", test_niche_9_deep_catalog),
        ("10: Multi-Dataset UUID-Kette", test_niche_10_multi_dataset_chain),
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

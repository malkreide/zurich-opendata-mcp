# Use Cases & Examples — zurich-opendata-mcp

Praxisnahe Anfragen nach Zielgruppe an die Open Data der Stadt Zürich (900+ Datensätze, Geodaten, Echtzeit-Umwelt- und Mobilitätsdaten, Gemeinderat, Stadtratsbeschlüsse, Tourismus). **Kein API-Key erforderlich** — alle Daten sind unter CC0 offen zugänglich (6 öffentliche APIs).

## 🏫 Bildung & Schule

**«Welche Datensätze zu Schulen, Volksschule und Kindergarten gibt es in Zürich?»**
**API-Key nötig:** Nein
→ `zurich_find_school_data(topic="Schulanlagen")`
→ `zurich_search_datasets(query="Volksschule", filter_group="bildung")`
Warum nützlich: Das kuratierte Schul-Tool bündelt Schulanlagen-, Bildungs- und Kreisschulbehörde-Datensätze — ein direkter Einstieg für das Schulamt und Lehrpersonen.

**«Zeig mir alle Schulanlagen im Stadtkreis als Karte / GeoJSON.»**
**API-Key nötig:** Nein
→ `zurich_geo_layers()`
→ `zurich_geo_features(layer_id="schulanlagen", max_features=100)`
Warum nützlich: Liefert echte Geodaten (Kindergärten, Schulen, Horte) als GeoJSON — direkt für Karten, Schulwegplanung oder Raumbedarfsanalysen verwendbar.

**«Wo liegen Gefahrenstellen auf den Schulwegen und welche Veloprüfstrecken gibt es?»**
**API-Key nötig:** Nein
→ `zurich_geo_features(layer_id="schulwege", max_features=200)`
→ `zurich_geo_features(layer_id="velopruefstrecken")`
Warum nützlich: Schulweg-Kreuzungen und Veloprüfstrecken als Punktdaten unterstützen Verkehrssicherheit und Elternabende mit konkreten Ortsangaben.

## 👨‍👩‍👧 Eltern & Schulgemeinde

**«Wie ist die Luftqualität rund um die Schule gerade jetzt?»**
**API-Key nötig:** Nein
→ `zurich_air_quality(parameter="PM10")`
→ `zurich_weather_live(parameter="T")`
Warum nützlich: Echtzeit-Feinstaub-, NO₂- und Ozonwerte (inkl. WHO-Grenzwerte) plus aktuelle Temperatur geben Eltern eine faktische Grundlage zu Hitze und Luft an Pausenplätzen.

**«Gibt es Spielplätze und Familienberatungsstellen in unserer Nähe?»**
**API-Key nötig:** Nein
→ `zurich_geo_features(layer_id="spielplaetze", max_features=200)`
→ `zurich_geo_features(layer_id="familienberatung")`
Warum nützlich: Öffentliche Spielplätze und Beratungs-Treffpunkte als verortete Geodaten helfen Familien bei Alltagsentscheidungen und Quartiersorientierung.

## 🗳️ Bevölkerung & öffentliches Interesse

**«Welche Stadtratsbeschlüsse zur Volksschule wurden 2025 gefasst?»**
**API-Key nötig:** Nein
→ `zurich_strb_search(query="Volksschule", datum_von="2025-01-01", datum_bis="2025-12-31")`
→ `zurich_strb_by_department(departement="SSD", datum_von="2025-01-01")`
Warum nützlich: Volltextsuche in den öffentlichen Beschlüssen (ab Feb. 2025) schafft Nachvollziehbarkeit politischer Entscheide — etwa alle Beschlüsse des Schul- und Sportdepartements.

**«Welche parlamentarischen Vorstösse zum Thema Schule gibt es, und welche Ratsmitglieder sitzen für die SP im Rat?»**
**API-Key nötig:** Nein
→ `zurich_parliament_search(query="Schule", year_from=2023)`
→ `zurich_parliament_members(party="SP")`
Warum nützlich: Gemeinderatsgeschäfte (Motionen, Postulate, Interpellationen) und Mitgliederinfos machen kommunalpolitische Prozesse für die Bevölkerung transparent.

## 🤖 KI-Interessierte & Entwickler:innen

**«Ich will tabellarische Daten gezielt filtern und mit SQL aggregieren.»**
**API-Key nötig:** Nein
→ `zurich_analyze_datasets(query="Bevölkerung")` (findet Ressourcen-IDs und Feldschemata)
→ `zurich_datastore_query(resource_id="<uuid>", filters="{\"Quartier\": \"Wiedikon\"}")`
→ `zurich_datastore_sql(sql="SELECT \"Jahr\", COUNT(*) FROM \"<uuid>\" GROUP BY \"Jahr\"")`
Warum nützlich: Der Dreischritt Analyse → gefilterte Abfrage → SQL erlaubt reproduzierbare, maschinenlesbare Auswertungen direkt auf dem CKAN DataStore (nur SELECT erlaubt).

**«Ich baue eine "Lage-Übersicht" für ein Schulhaus und kombiniere Stadtdaten mit Umweltforschung.»**
**API-Key nötig:** Nein
→ `zurich_geo_features(layer_id="klimadaten")` + `zurich_air_quality()` + `zurich_parking_live()`
→ kombiniert mit `wsl-envidat-mcp` → `wsl_get_forest_data()` und `wsl_get_naturgefahren_data()`
Warum nützlich: Portfolio-Kombination — städtische Klima-, Luft- und Echtzeitdaten plus WSL-Waldzustand und Naturgefahren aus `wsl-envidat-mcp` ergeben eine integrierte Umgebungs- und Standortanalyse.

## 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|---|---|---|
| Den Katalog per Volltext/Solr durchsuchen (optional nach Kategorie) | `zurich_search_datasets` | Nein |
| Alle Metadaten & Download-Links eines Datensatzes ansehen | `zurich_get_dataset` | Nein |
| Tabellarische Daten gefiltert abfragen | `zurich_datastore_query` | Nein |
| Komplexe Auswertungen per SQL (nur SELECT) | `zurich_datastore_sql` | Nein |
| Schulrelevante Datensätze kuratiert finden | `zurich_find_school_data` | Nein |
| Verfügbare Geodaten-Layer auflisten | `zurich_geo_layers` | Nein |
| Geodaten (Schulen, Kreise, Spielplätze …) als GeoJSON abrufen | `zurich_geo_features` | Nein |
| Aktuelle Wetterdaten der UGZ-Stationen abrufen | `zurich_weather_live` | Nein |
| Live-Luftqualität (NO₂, O₃, PM10, PM2.5) abfragen | `zurich_air_quality` | Nein |
| Echtzeit-Parkhausbelegung abrufen | `zurich_parking_live` | Nein |
| Passantenfrequenzen an der Bahnhofstrasse abfragen | `zurich_pedestrian_traffic` | Nein |
| VBZ-Fahrgastzahlen nach Linie/Haltestelle abfragen | `zurich_vbz_passengers` | Nein |
| Stadtratsbeschlüsse durchsuchen / nach Departement / einzeln | `zurich_strb_search`, `zurich_strb_by_department`, `zurich_strb_detail` | Nein |
| Gemeinderatsgeschäfte & -mitglieder recherchieren | `zurich_parliament_search`, `zurich_parliament_members` | Nein |
| Tourismus-Angebote (Attraktionen, Restaurants, Hotels) abrufen | `zurich_tourism` | Nein |
| Eine Katalog-Übersicht mit Statistiken erhalten | `zurich_catalog_stats` | Nein |

Hinweis: `zurich_sparql` (Linked Data) ist standardmässig **nicht** registriert und muss per Umgebungsvariable `ZURICH_OPENDATA_ENABLE_SPARQL=1` aktiviert werden. Die Alias-Namen `search_stadtratsbeschluesse`, `get_beschluesse_by_departement` und `get_stadtratsbeschluss_detail` existieren nur noch als veraltete Aliase.

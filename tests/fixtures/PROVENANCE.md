# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-10-14** von `https://data.stadt-zuerich.ch/api/3/action`.

Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht
mehr zu unterscheiden — die Datei sieht gleich aus, und niemand weiss,
ob sie den Stand von gestern zeigt oder den von vor drei
Schema-Wechseln.

**Es sind Ausschnitte, keine Vollabzuege.** Die Auswahlregel steht je
Datei dabei. Wo gekuerzt wurde, bleiben die Zaehlfelder (`count`,
`package_count`) auf dem echten Wert — eine Fixture, die stillschweigend
behauptet, der Bestand sei kleiner, waere genau der Fehler, gegen den
diese Aufzeichnung angeht.

## `ckan_group_list.json`

- **Quelle:** `https://data.stadt-zuerich.ch/api/3/action/group_list?all_fields=true`
- **Aufgezeichnet:** 2026-10-14
- **Auswahl:** vollstaendig, 21 Kategorien
- **Groesse:** 11839 B
- **SHA-256:** `5abf4f1deccddd8eb0399a490f438d7db2fe27ef63774fa70a027bf3bf96a472`

## `ckan_group_show.json`

- **Quelle:** `https://data.stadt-zuerich.ch/api/3/action/group_show?id=mobilitat&include_datasets=true`
- **Aufgezeichnet:** 2026-10-14
- **Auswahl:** Kategorie «mobilitat»; `packages` auf die ersten 3 von 10 gekuerzt, `package_count` unveraendert
- **Groesse:** 21276 B
- **SHA-256:** `2ae26db641aefcd4ff058bfebae71b270c5631988814f3b29468c2d3ffea875f`

## `ckan_package_search.json`

- **Quelle:** `https://data.stadt-zuerich.ch/api/3/action/package_search?q=verkehr&rows=3`
- **Aufgezeichnet:** 2026-10-14
- **Auswahl:** Suche «verkehr» mit explizitem rows=3; `count` ist der echte Gesamtbestand der Suche (104), `results` sind 3
- **Groesse:** 39963 B
- **SHA-256:** `7bdff7ea327f0af2e5b1fd4efe4f36cb0979b3bcc46bed3ccd74cd19e143fc3a`

## `ckan_package_search_no_rows.json`

- **Quelle:** `https://data.stadt-zuerich.ch/api/3/action/package_search?q=verkehr (ohne rows)`
- **Aufgezeichnet:** 2026-10-14
- **Auswahl:** nur die beiden Zahlen: wie viele es gibt und wie viele ohne `rows` kommen. Der Beleg dafuer, dass das Weglassen des Parameters eine willkuerliche Teilmenge liefert und keine Vollmenge
- **Groesse:** 37 B
- **SHA-256:** `eba20d3cf2293538de481ec8ca67651bc36533ee09e48a2008885e8a73a0b307`

## `ckan_datastore_sql.json`

- **Quelle:** `https://data.stadt-zuerich.ch/api/3/action/datastore_search_sql?sql=SELECT * FROM "90410203-4b4f-4a65-9015-1fca2792e04d" LIMIT 3`
- **Aufgezeichnet:** 2026-10-14
- **Auswahl:** Luftqualitaet stuendlich, `SELECT *` mit LIMIT 3; vollstaendig, samt der internen Spalten `_id` und `_full_text`
- **Groesse:** 1795 B
- **SHA-256:** `cdac6e5035446ad46b67c3e33795b23869c897afcff651ce2c90298b4ee519af`

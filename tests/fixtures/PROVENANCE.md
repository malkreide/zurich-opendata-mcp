# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-07** von `https://data.stadt-zuerich.ch/api/3/action`.

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
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** vollstaendig, 21 Kategorien
- **Groesse:** 11839 B
- **SHA-256:** `b51103b720f8fa2042772ee91c9600bc3ef5e6bd6957c8d754325fed144f3b2a`

## `ckan_group_show.json`

- **Quelle:** `https://data.stadt-zuerich.ch/api/3/action/group_show?id=mobilitat&include_datasets=true`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** Kategorie «mobilitat»; `packages` auf die ersten 3 von 10 gekuerzt, `package_count` unveraendert
- **Groesse:** 21285 B
- **SHA-256:** `15e3787256282528ea88e9471056d4167baaaaa36e460ddd2d277f2207bea431`

## `ckan_package_search.json`

- **Quelle:** `https://data.stadt-zuerich.ch/api/3/action/package_search?q=verkehr&rows=3`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** Suche «verkehr» mit explizitem rows=3; `count` ist der echte Gesamtbestand der Suche (102), `results` sind 3
- **Groesse:** 39963 B
- **SHA-256:** `e1a1883f5d3353967983a77664b79adecc240224e1471d80badf208325e7bc8e`

## `ckan_package_search_no_rows.json`

- **Quelle:** `https://data.stadt-zuerich.ch/api/3/action/package_search?q=verkehr (ohne rows)`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** nur die beiden Zahlen: wie viele es gibt und wie viele ohne `rows` kommen. Der Beleg dafuer, dass das Weglassen des Parameters eine willkuerliche Teilmenge liefert und keine Vollmenge
- **Groesse:** 37 B
- **SHA-256:** `6e1275f8033c33301f472877fed466d1e97226f5d9385557a4bd9e70d20d9132`

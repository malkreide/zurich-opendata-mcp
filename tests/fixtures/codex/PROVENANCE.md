# Herkunft der Codex-Fixtures

**Von Hand aufgezeichnet — anders als `tests/fixtures/*.json` eine Etage
höher, die `scripts/record_fixtures.py` erzeugt.** Es gibt hier nichts
aufzuzeichnen, was ein Skript holen könnte: Die Texte stammen aus
GitHub-Kommentaren, die nur einmal entstehen, und teils aus Läufen, die
Monate zurückliegen.

Aufgezeichnet am **2026-09-20**. Ohne Datum ist «aufgezeichnet» nach zwei
Jahren von «ausgedacht» nicht mehr zu unterscheiden.

Jede Datei ist ein Ereignis-Objekt für `scripts/check_codex_verdict.py`:
`head_sha`, `reviews`, `comments`, `labels`. Die Kommentar-Körper sind
gekürzt — der Infokasten unter jedem Codex-Kommentar ist weggelassen, weil
das Skript ihn nicht liest. Alles, was es liest, steht wörtlich so da, wie
es beobachtet wurde.

## Direkt beobachtet in `malkreide/zurich-opendata-mcp`, 19./20.9.2026

| Datei | Quelle | Was sie festhält |
|---|---|---|
| `pr115_befundlos.json` | PR #115, Kommentare 5734441910 + 5734496246 | Der **einzige** Fall mit Verdikt: Tabelle `Completed` **und** Befundlos-Zeile mit `Reviewed commit: 65fd46b4bc`. |
| `pr116_completed_ohne_verdikt.json` | PR #116, Kommentar 5743798073 | Tabelle `Completed`, sonst nichts. Der Review lief auf dem schon geschlossenen PR zu Ende. `get_reviews` war leer. |
| `pr118_running.json` | PR #118, Kommentar 5748763679 | Tabelle `Running`. So sah es aus, als gemergt wurde. |

Der Commit in der Tabelle ist auf sieben Zeichen gekürzt, der in der
Befundlos-Zeile auf zehn — beides so beobachtet. Genau deshalb vergleicht
das Skript über ein gemeinsames Präfix und nicht wörtlich.

## Wortlaut aus `CLAUDE.md`, dort im August 2026 aufgezeichnet

| Datei | Was sie festhält |
|---|---|
| `kontingent.json` | «You have reached your Codex usage limits for code reviews.» |
| `environment.json` | «To use Codex here, create an environment for this repo.» |
| `befund_review_objekt.json` | Ein Review-**Objekt** mit `commit_id` — die Form, die ein Befund annimmt. Am 23.8. im Portfolio 36-mal gesehen. |

## Konstruiert, und als solches gekennzeichnet

| Datei | Warum |
|---|---|
| `leer.json` | Der Zustand direkt nach «ready for review». Nichts zu beobachten, weil nichts da ist. |
| `verdikt_zu_altem_commit.json` | Ein Verdikt zu `3fdce1b`, während der Head auf `cd90442` steht. Diese Kombination ist im Repo nie aufgetreten, weil nach einem Review nie gepusht wurde — sie ist aber der Fall, gegen den der Commit-Vergleich existiert. Beide SHAs sind echte Commits dieses Repos. |

Die letzte Zeile ist der Grund, warum diese Tabelle dreigeteilt ist: Eine
konstruierte Fixture ist brauchbar, solange niemand sie später für eine
Messung hält.

## Nachtrag 20.9.2026 — zwei zusammengesetzte Abläufe

`kontingent_dann_verdikt.json` und `environment_dann_verdikt.json` sind
**zusammengesetzt, nicht mitgeschrieben**. Die drei Kommentartexte darin sind
je einzeln belegt — die Ausfallmeldung aus `kontingent.json` bzw.
`environment.json`, Tabelle und Befundlos-Zeile wörtlich aus #115 —, die
*Reihenfolge* ist konstruiert.

Sie bilden den Ablauf ab, den die Ausfallmeldung selbst empfiehlt: Kontingent
weg, später «@codex review», Review läuft durch. Genau diesen Ablauf konnte
das Skript bis zum 20.9. nicht grün bewerten, weil es auf der alten
Ausfallmeldung sofort negativ zurückkehrte und die spätere Befundlos-Meldung
nie erreichte. Gefunden hat das ein Codex-Review auf PR #119 (P1,
`scripts/check_codex_verdict.py`), nicht ein eigener Test.

Dass hier zusammengesetzt wurde, hat einen Grund: Ein echter Mitschnitt
bräuchte ein erschöpftes Kontingent, und das lässt sich nicht herbeiführen.
Aufzuzeichnen wäre er trotzdem, sobald er einmal vorkommt.

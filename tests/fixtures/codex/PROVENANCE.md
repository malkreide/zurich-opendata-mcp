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

## Nachtrag 20.9.2026 — `pr119_thread_antwort_kein_review.json`

**Wörtlich mitgeschrieben** von PR #119, aus `get_reviews` gelesen, alle Zeiten
UTC. Der Anlass ist ein Falsch-Positiv im eigenen Entwurf.

GitHub verpackt jede Antwort auf einen Inline-Kommentar als **Review-Objekt**,
und dieses trägt den aktuellen Head:

| Zeit | Autor | `commit_id` | Body |
|---|---|---|---|
| 12:57:36 | Codex | `6dc81d17cc` | «💡 Codex Review … **Reviewed commit:** `6dc81d17cc`» |
| 13:03:05 | malkreide | `b64b96d2…` | — (Thread-Antwort) |
| 13:03:12 | Codex | `b64b96d2…` | — (Thread-Antwort) |

Die dritte Zeile ist das Problem. Codex hat `b64b96d` **nie geprüft** — es
antwortete nur im Thread mit seiner Environment-Meldung. Die alte Regel prüfte
Bot-Login und `commit_id`, also schaltete der Gate grün. Gemessen, nicht
vermutet: `check_codex_verdict.py` gegen diesen Zustand endete mit Exit 0.

Unterscheidbar sind die Fälle am Body: ein echtes Review trägt die Überschrift
und nennt den geprüften Commit im Text, eine Thread-Antwort hat gar keinen
Body. Der Text schlägt seither `commit_id`.

Und eine Beobachtung, die nicht in die vier Gründe aus `CLAUDE.md` passt: Die
Environment-Meldung kam hier als **Review-Kommentar an einer Datei-Zeile**, nicht
als gewöhnlicher Issue-Kommentar — und das, während wenige Minuten zuvor ein
GitHub-getriggerter Code-Review derselben PR sauber durchlief. «Environment
fehlt» hiess hier also nicht «kein Review möglich». Der Gate wertet
Review-Kommentare deshalb bewusst nicht als Ausfallmeldung aus; er würde sonst
einen Ausfall melden, den es nicht gab. Bislang eine einzelne Beobachtung.

## Nachtrag 20.9.2026 — `kontingent_allgemein.json`

**Wörtlich mitgeschrieben** von PR #120, Kommentar 5751230887, 16:54:52 UTC.

Bis dahin war nur ein Wortlaut der Kontingent-Meldung belegt, der in
`kontingent.json`. Auf demselben PR kamen beide, 230 Sekunden auseinander:

```
16:54:52  You have reached your Codex usage limits.
16:58:42  You have reached your Codex usage limits for code reviews.
```

Der zweite ist der bekannte; der erste war neu. Das Muster im Skript sitzt auf
dem gemeinsamen Teil und erkennt beide — das war Glück, denn belegt war nur
die lange Fassung, und ein Pin darauf hätte nahegelegen. Die kurze wäre dann
als unbekannter Text durchgelaufen: kein Fehlalarm, aber der Gate hätte
«Kontingent» nicht mehr benennen können und nur noch «sonst noch gesehen»
gemeldet.

Der erste Kommentar stand auf einem PR, der noch **Draft** war. `CLAUDE.md`
sagt, auf einem Draft laufe Codex nicht an; das bleibt für den Review richtig,
für den Kommentarzähler nicht. Was die Meldung ausgelöst hat, ist ungeklärt —
dreizehn Sekunden davor lag ein eigener Kommentar, davor ein Push. Belegt ist
keines von beidem, deshalb steht hier nur die Beobachtung.

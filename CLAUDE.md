# Project conventions for Claude

## Teil 1 — Portfolio-Konventionen

### Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.

Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  `asyncio` selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

### Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Wie lange die Sperre dauerte, geben die Beobachtungen nur als Spanne her. Vier
Zeitpunkte sind belegt: letzter gelungener Review am 21.8. um 08:41, erste
Limit-Meldung um 09:48, letzte beobachtete Limit-Meldung am 22.8. um 11:03,
erste *andere* Meldung am 23.8. um 08:22.

Daraus folgt eine Untergrenze von gut **25 Stunden** — so weit liegen erste und
letzte Limit-Meldung auseinander. Die längste mit den Beobachtungen verträgliche
Sperre reicht dagegen vom letzten Erfolg um 08:41 bis zur abweichenden Meldung
um 08:22, also **47 h 41 min**. Wer stattdessen ab der ersten Limit-Meldung
rechnet, unterschlägt die 67 Minuten, in denen das Kontingent schon weg gewesen
sein kann, und nennt die Spanne zwischen zwei Beobachtungen eine Obergrenze.

Und die Untergrenze belegt keine *ununterbrochene* Sperre. Zwischen zwei
Limit-Meldungen kann sich ein Fenster geöffnet und durch neue Auslöser wieder
geschlossen haben. Beobachtungspunkte sind keine Messreihe — die 21 Stunden vor
der abweichenden Meldung liefen ganz ohne Codex-Auslöser, dort hat niemand
gemessen.

In der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden,
ohne dass jemand hineingesehen hat, und am 22.8. noch einmal 43.

**Vier** Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann reagiert er mit 👍 und schreibt nichts.
- **Der PR ist ein Draft** — darauf läuft Codex nicht an.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.
- **Für das Repo fehlt eine Environment** — dann schreibt er:

  ```
  To use Codex here, create an environment for this repo.
  ```

Der vierte kam erst zum Vorschein, als der dritte wegfiel, und das ist kein
Zufall: Die Prüfungen liegen hintereinander. Dass es diese Reihenfolge ist und
nicht die umgekehrte, lässt sich an einem einzigen Repo ablesen — in
`swiss-public-data-mcp` bekam PR #54 am 22.8. um 10:56:55 die Kontingent-Meldung
und PR #56 am 23.8. um 08:22:20 die Environment-Meldung. Läge die
Environment-Prüfung vorn, hätte #54 sie schon am Vortag gesehen; die Environment
fehlte ja bereits. Zwei Meldungen aus demselben Repo schlagen hier jede
Vermutung über die Reihenfolge.

Praktisch heisst das: **Eine verschwundene Limit-Meldung ist keine Entwarnung.**
Sie kann bedeuten, dass das Kontingent wieder da ist — und dass jetzt etwas
anderes den Review verhindert. Belegt ist eine Prüfung erst durch ein
Review-Objekt **oder** die 👍-Reaktion. Wer nur das Objekt gelten lässt, zählt
jeden befundlosen Review als ungeprüft — und baut sich denselben Fehlalarm ein,
den dieser Abschnitt verhindern soll, nur in die andere Richtung.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein Review **mit** Befund ist ein Review-Objekt
(«💡 Codex Review», mit Commit-Angabe), ein Review **ohne** Befund eine
👍-Reaktion, und die beiden Ausfallmeldungen — Kontingent wie Environment —
sind gewöhnliche Issue-Kommentare. Beim Draft gibt es überhaupt nichts, weil
Codex nicht anläuft; ein kommentarloser Draft ist deshalb kein Beleg, sondern
ein nicht durchgeführter Test.

Das sind verschiedene Abfragen — `get_reviews` gegen `get_comments`, und für
die Reaktion keine von beiden; wer nur eine nimmt, übersieht den Rest. Genau so
ist die Limit-Meldung zuerst durchgerutscht.

Der Kommentarzähler allein reicht ohnehin nicht: `comments: 1` kann die
Kontingent- **oder** die Environment-Meldung sein. Den Text lesen, nicht die
Zahl. Und einen unbekannten dritten Text wörtlich zitieren, statt ihn in eine
der bekannten Schubladen zu zwingen — dieser Abschnitt musste schon einmal von
drei auf vier Gründe wachsen.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden. Codex wird beim Umschalten von Draft auf ready ausgelöst und
braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review
nicht abgewartet.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Welches hier griff, ist **offen**. Die 25 Stunden
oben schliessen das Fünf-Stunden-Fenster nicht aus: Es kann sich
zwischendurch geöffnet und durch neue Auslöser wieder erschöpft haben. Das
auszuschliessen bräuchte den Nachweis, dass in der ganzen Spanne kein einziger
Review durchlief — den gibt es nicht, weil nur Fehlschläge beobachtet wurden.
Eine lange Sperre belegt eine lange Sperre, nicht ihre Ursache.

Zeigt das Dashboard freies Kontingent, während Reviews weiter scheitern, ist
das ein bekannter Fehler bei mehreren verbundenen Konten — dann den
GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

Die Environment legt man unter `chatgpt.com/codex/cloud/settings/environments`
an, und zwar **je Repo**. Die Meldung sagt es selbst («for this repo»), und am
23.8. war es genau so: In `swiss-public-data-mcp` fehlte sie, dort kam kein
Review; in den übrigen Repos lief Codex am selben Morgen durch. Eine
Environment fürs Konto genügt also nicht — wer eine anlegt und den Rest für
erledigt hält, mergt weiter Ungeprüftes.

### Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Teil 2 — Dieses Repo

**ruff: eine Quelle.** `pyproject.toml` `[dev]` pinnt `ruff==0.16.3`, `uv.lock`
hält dieselbe Version. `ci.yml` rief ruff vorher per
`uv run --with ruff==0.16.1` auf, während der Lock auf `0.15.18` stand — das
überschrieb nur diesen einen Aufruf, und wer lokal `uv run ruff check` fuhr,
lintete mit 0.15.18 gegen ein Gate, das 0.16.1 fuhr. Beim Anheben:
`pyproject.toml` ändern, `uv lock`, `ruff format`, alles zusammen committen.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

**Kein `.pre-commit-config.yaml`.** Es gibt also keinen zweiten Ort, an dem
eine abweichende ruff-Version stehen könnte — aber auch nichts, das die Gates
vor dem Commit erzwingt. `scripts/check_ruff_pin.py` schützt den Pin nur, wenn
es aufgerufen wird: lokal von Hand, sonst erst in der CI auf dem PR.

**Gates, wörtlich aus `ci.yml`** (Matrix: Python 3.11 / 3.12 / 3.13):

```
uv sync --extra dev
uv run python scripts/check_ruff_pin.py
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/ scripts/
uv run mypy
uv run pytest
python scripts/check_version_sync.py
```

`uv run pytest` ist mehr, als dasteht: `addopts` in `pyproject.toml` trägt
`-m 'not live'` **und** `--cov-fail-under=100`. Der Marker-Ausschluss steht
also nicht im Befehl, und ein Lauf über eine einzelne Testdatei fällt am
Coverage-Gate statt am Test.

**`ci.yml` hat keinen `push`-Trigger** — nur `pull_request`, `schedule`,
`workflow_dispatch`. Ein Push direkt auf `main` löst hier nichts aus; was
grün ist, wurde es auf einem PR. Der Job `check` trägt zusätzlich
`if: github.event_name == 'pull_request'`, im Wochenlauf laufen also nur
`fresh-install` und `audit`. Ein grüner Montagslauf sagt nichts über die
Suite oben.

Dritter Job: **`audit`** (pip-audit) — mit `continue-on-error: true` und
damit kein Gate. Rot heisst dort «Advisory anschauen», nicht «Merge
blockiert»; required ist die `check`-Matrix. Beide Matrizen setzen
`fail-fast: false`, Actions sind SHA-gepinnt.

Dazu ein zweiter Job «Fresh-resolve install smoke»: Wheel in ein leeres venv
ohne Lockfile und mit kaltem Cache, dann ein echter MCP-Handshake über
`scripts/smoke_installed.py`. Der Lockfile-Lauf oben kann nicht bemerken, wenn
eine Abhängigkeitsspanne für Fremde kaputt auflöst; dieser Job kann es.

**Live-Tests: geplanter Workflow vorhanden.** `.github/workflows/live-tests.yml`,
`cron: "43 4 * * 1"` (wöchentlich Mo, 04:43 UTC). `ci.yml` hat zusätzlich einen
eigenen Zeitplan (`17 6 * * 1`). DRIFT-005 ist hier erfüllt — die Live-Suite ist
nicht bloss per Marker ausgeschlossen. `schedule` greift nur auf dem
Default-Branch: Workflow-Änderungen wirken erst nach dem Merge.

`live-tests.yml` pinnt seine Actions per Tag (`@v7`), nicht per SHA — die
SHA-Pins gelten für `ci.yml` und `publish.yml`.

## Changelog discipline

Every code change must include a matching entry in `CHANGELOG.md` under the
`[Unreleased]` block, in the same commit/PR as the change itself.

- Use Keep-a-Changelog sections: `### Added`, `### Changed`, `### Fixed`,
  `### Security`, `### Removed`, `### Deprecated`.
- Pure documentation tweaks, audits, and CI hardening do not need an entry.
  Anything that ships in the wheel does.
- Reference the audit finding ID (`H-1`, `M-3`, …) when fixing one, so the
  changelog tracks back to `audits/zurich-opendata-mcp-audit.md`.
- When cutting a release, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`
  and add a new empty `[Unreleased]` block at the top.

## Audit follow-ups

All known review backlogs are closed:

- Both audits (`audits/zurich-opendata-mcp-audit.md` and its rerun) shipped
  across PRs #9, #11–#15: H-1 SQL injection, H-2 CQL injection, all Mediums
  and Lows. The M-7 coverage goal is complete — the suite gates at
  `--cov-fail-under=100`.
- The July 2026 solution review (F-1 – F-13) shipped across PRs #40–#54 and
  was released as `0.5.0`: runtime resolution of year-bound UGZ resource
  IDs, shared HTTP client + retries, `zurich_` naming with deprecated STRB
  aliases, `format=json` on every data-bearing tool, SPARQL opt-in flag,
  Literal-typed UGZ filters, ILIKE wildcard escaping (rerun §2.3 — fixed,
  no longer documentation-only), defusedxml, SHA-pinned CI + pip-audit,
  metadata drift guards, and a mypy gate with zero per-module exemptions.

Invariants to preserve in new work: coverage stays at 100%, mypy has no
`ignore_errors` exemptions, doc counts are pinned by drift-guard tests
(update docs and tests together when the tool surface changes), and the
live-marked drift alarms (UGZ yearly resources, UGZ measurement network)
should be run before cutting a release.

Each substantive change should still land as its own PR with a CHANGELOG
entry, referencing the finding ID where one applies.

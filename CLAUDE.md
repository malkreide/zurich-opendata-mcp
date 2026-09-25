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

**Ein 4xx ist kein Nein.** Am 29.8.2026 antwortete `past-publications` in
`swiss-procurement-mcp` auf jede Publikation mit Losen mit HTTP 400. Daraus war
geschlossen worden, die Quelle verweigere diese Auskunft; der Befund stand
datiert im Fixture-Nachweis, ein Test bestätigte ihn, alles blieb grün. Die
Spec desselben Endpunkts führt einen als *optional* deklarierten Parameter
`lotId` — für Publikationen mit Losen ist er Pflicht. Mit ihm antwortet
dieselbe Publikation mit 200. Ein Projekt trug sieben Vorgängerpublikationen,
die der Server als «Quelle nicht erreichbar» wegwarf.

Drei Handgriffe daraus:

- **Die Parameterliste der Spec durchgehen, bevor ein Statuscode eingeordnet
  wird.** «Optional» heisst dort oft «optional für die Mehrheit».
- **Einer deterministischen Absage keinen Wiederholungsrat geben.** «Nicht
  erreichbar, bitte später erneut» ist bei einem 400 falsch und liest sich für
  das Modell wie eine Störung. Den Status mitführen und den fehlenden
  Parameter benennen — den Status, nicht den Antwortkörper.
- **Beide Antworten aufzeichnen, mit und ohne den Parameter.** Eine
  Aufzeichnung nur des Fehlschlags kann nicht zeigen, dass er vermeidbar war;
  dass nur der 400er aufgezeichnet war, ist der Grund, warum der falsche
  Befund nicht auffiel.

**Und ein 403 ist gar keine Auskunft.** Am 29.8.2026 sollten für 42 Repos die
Dependabot-Labels nachgemessen werden. Alle 13 Abfragen des ersten Stapels
kamen zurück als:

```
Failed to find label: API rate limit already exceeded for user ID 8864492.
```

Der gefährliche Teil steht vorn: Das Werkzeug verpackt eine Sperre als
Fund-Fehlschlag. Wer die Zeile überfliegt oder nur auf ein leeres Ergebnis
prüft, zählt 39 Repos als «Label fehlt» und hat seine eigene Erschöpfung
gemessen. Das Limit hängt am Konto, nicht am Repo — derselbe Vormittag hatte
es mit 42 eröffneten und 42 gemergten PRs verbraucht.

Das ist der Absatz darüber, andersherum gelesen: dort war ein 400 eine echte,
wiederholbare Antwort und galt als Störung; hier ist eine Störung als Antwort
verpackt. Entscheidend ist nie der Statuscode, sondern ob die Quelle überhaupt
geantwortet hat.

- **Positivkontrolle im selben Repo.** Ein «nicht gefunden» wird erst dadurch
  zur Messung, dass eine gleichzeitige Abfrage etwas findet.
- **Die Messung entlang der Sperre teilen.** `raw.githubusercontent.com` ist
  ein CDN und nicht die REST-API. Um 11:19:27 UTC lieferte es für
  `register-mcp` HTTP 200, während die Label-Abfrage desselben Repos in
  derselben Minute die Sperre meldete. Alle 42 `dependabot.yml` kamen so
  durch, während die Label-Hälfte stand.
- **Am Token vorbei geht es nicht.** Beide Umwege enden am Agent-Proxy, und
  jeder mit einer eigenen irreführenden Begründung. `api.github.com` ohne
  Zugangsdaten:

  ```
  GitHub access is not enabled for this session. An org admin must connect
  the Claude GitHub App for this organization.
  ```

  Das ist keine Aussage über die Organisation, sondern das, was ohne Token
  kommt. Wer ihr folgt, sucht einen Admin für ein Problem, das keiner hat.
  Die HTML-Seite `github.com/<owner>/<repo>/labels` fällt ebenfalls, aber
  anders:

  ```
  This GitHub API path is not available: sessions are bound to their
  configured repositories. Use repository-scoped endpoints
  (repos/{owner}/{repo}/...).
  ```

  Der Proxy behandelt also auch `github.com` als API-Pfad; die zweite Meldung
  klingt nach einem Scope-Problem und ist doch nur dieselbe Sackgasse. Den
  Token aus der Umgebung in einen curl-Header zu setzen, blockiert der
  Klassifikator. Ob es überhaupt hülfe, ist offen: die Sperre nennt ein
  Nutzerkonto, und ob der Token zu diesem gehört, wurde nie geprüft.
- **Die Sperre gilt nicht dem Dienst, sondern dem Zugangspfad.** Unmittelbar
  nachdem eine Abfrage der Checks eines PR sauber durchlief, meldete die
  Label-Abfrage weiter die Sperre. Von einem blockierten Werkzeug also nicht
  auf «GitHub ist zu» schliessen — und umgekehrt eine gelungene Abfrage nicht
  als Entwarnung für die gesperrte nehmen.

Wann die Sperre fällt, geben diese Beobachtungen nicht her. Die Meldung nennt
keinen Zeitpunkt, und die `X-RateLimit`-Kopfzeilen sind hinter dem Proxy nicht
zu sehen. Belegt sind drei gesperrte Zeitpunkte — 11:14, 11:16 und 11:19 UTC.
Wer daraus eine Dauer macht, hat sie erfunden.

**Dieselbe Falle bei einer Konfigurationsoption: die Vorgabe lesen, bevor man
einen Schlüssel für wirkungslos hält.** Am 29.8.2026 fielen die
`labels:`-Zeilen aus den `dependabot.yml` des Portfolios, begründet mit
«Dependabot legt Labels nicht an». Eine Messung danach zeigte, dass
`dependencies` in 36 von 42 Repos sehr wohl existiert, 35 davon mit GitHubs
Standardbeschreibung. Das las sich zuerst wie ein Beleg, dass die Aktion
falsch war.

Die Optionsreferenz kehrt es um:

```
Dependabot creates these default labels automatically, as necessary in
your repository.

If you define more than one package manager, an additional label for the
ecosystem or language is added to each pull request.

The labels specified are used instead of the default labels.
```

Ohne `labels:` vergibt Dependabot also `dependencies` — und, sobald mehr als
ein Paketmanager deklariert ist, zusätzlich ein Ökosystem-Label — und legt sie
selbst an; eine eigene Liste **ersetzt** diesen Satz, und «if any of these
labels is not defined in the repository, it is ignored». Die Zeile war nicht
wirkungslos — sie tauschte einen sich selbst pflegenden Vorgabesatz gegen eine
starre Liste.

**Die Bedingung nicht weglassen.** Bei nur einem Paketmanager steht das
Ökosystem-Label gar nicht zu; wer es dort trotzdem erwartet, schreibt genau
den Fehlbefund auf, gegen den dieser Abschnitt geschrieben ist — der Abschnitt
liefe an sich selbst vorbei. Im Portfolio deklariert jede `dependabot.yml`
zwei (`pip` und `github-actions`), die Bedingung ist hier also überall
erfüllt; anderswo nicht unbedingt. Aufgefallen ist die fehlende Bedingung
nicht beim Schreiben, sondern durch einen Codex-Review auf
`swiss-environment-mcp` PR #113 — vierzehn Sekunden vor dem Merge desselben
PR.

Was das kostet, ist an `openlex-mcp` gemessen: zwei Ökosysteme deklariert,
also stünden `dependencies` **und** ein Ökosystem-Label zu; vorhanden ist nur
das erste, `github-actions` und `github_actions` fehlen beide (Kontrolle `bug`
vorhanden). `register-mcp` ist die Gegenprobe: dort existieren alle vier
deklarierten Namen mit handgeschriebener Beschreibung, die Liste ist gewollt
und vollständig.

**Dreimal falsch eingeordnet, in drei Richtungen.** Erst die Zeile für bloss
wirkungslos gehalten. Dann die gefundenen Labels für einen Widerspruch. Dann,
auf denselben Fund gestützt, einen richtigen PR geschlossen mit dem Argument,
das Label existiere ja — obwohl es existiert, *weil* die Vorgabe es anlegt.
Der dritte Fehler ist der teuerste, weil er wie eine Messung aussah.

Was die Messung **nicht** hergibt: wer die 36 Labels angelegt hat. Die
Referenz sagt, Dependabot tue es; die Objekt-IDs liegen aber so dicht
beieinander, dass sie eher aus einem Stapellauf stammen. Beides passt zum
Befund, keines ist belegt — die Herkunft blieb ungemessen.

Beim Aufräumen gilt deshalb dieselbe Frage wie bei `lotId`: Was ist die
*Vorgabe*, wenn man das Ding weglässt — nicht bloss, ob der aktuelle Wert
etwas bewirkt.

**`results[0]` ist nur so verlässlich wie die Zusicherung danach.** Pinnt die
Abfrage einen bekannten Datensatz, ist der erste Treffer eine Drift-Wache und
in Ordnung. Hängt die Zusicherung dagegen davon ab, *welche* Variante die
Quelle heute zuoberst hat, prüft der Test den Tag: am 25.8.2026 rot, weil die
neueste Zürcher Publikation zufällig Lose hatte, am 26.8. grün, ohne dass sich
etwas geändert hätte. Den Fall gezielt wählen und beide Zweige fahren.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

**Bei einem blockierten PR nennt der Merge-Versuch den Blocker, jede Ableitung
rät.** `mergeable_state: blocked` bei grüner CI heisst: ein required Kontext
fehlt oder steht nicht auf grün. Welcher, sagt die Einstellung — und die sperrt
der Agent-Proxy mit HTTP 403, ein MCP-Werkzeug dafür gibt es nicht. Der Ausweg
ist nicht Indizienarbeit, sondern ein Merge-Versuch über die API:

```
PUT /repos/<owner>/<repo>/pulls/<n>/merge
405 Required status check "Codex hat diesen Head geprueft" is expected.
```

Der Name steht dort wörtlich so, wie er in der Branch Protection eingetragen
ist. Scheitert der Versuch, kostet er nichts.

Am 24./25.9.2026 über drei Repos vermessen, nachdem ein Gate-Workflow entfernt
worden war und seinen required Kontext ohne Berichterstatter zurückliess:

| Repo | eingetragener Kontext | Art |
|---|---|---|
| `register-mcp` | `Codex hat den PR angesehen` | Check-Run |
| `srgssr-mcp` | `review-abgeschlossen` | Check-Run |
| `fedlex-mcp` | `Codex hat diesen Head geprueft` | Check-Run |

**Warum Ableiten hier systematisch fehlgeht.** GitHub nimmt als Check-Run-Name
den **Job**-Namen, nicht den des Workflows. Zwei der drei Kontexte enthalten die
Zeichenfolge «codex-gate» nicht, obwohl sie aus `codex-gate.yml` stammen; wer in
den Einstellungen danach sucht, findet nichts und hält die Regel für abwesend.
Trug der Job kein `name:`, nimmt GitHub die Job-ID — daher `review-abgeschlossen`.

Zwei Fehlschlüsse sind dabei belegt, beide aus **einer** Beobachtung gezogen:

- Aus einem Commit-Status auf den required Kontext geschlossen. In `fedlex-mcp`
  stand der Status `codex-gate` auf dem Head auf `success` und blockierte
  nichts, während der fehlende Check-Run den Merge hielt. Am Kontroll-PR waren
  beide rot — dort ist nicht zu unterscheiden, welcher von beiden eingetragen
  ist. Genommen wurde der auffälligere.
- Aus einer Check-Run-Liste auf den required Kontext geschlossen. Die Liste
  zeigt, was **berichtet** wurde; eingetragen sein kann ein Name, der gerade
  gar nicht erscheint. Genau das ist der Fall, um den es geht.

**Ein Vorbehalt, der zur Methode gehört:** Die Absage nennt immer nur den
**ersten** fehlenden Kontext. Ist ein zweiter eingetragen, zeigt ihn erst der
nächste Versuch. Nach jeder Änderung an der Einstellung also erneut versuchen,
bis der Merge durchgeht oder ein neuer Name fällt.

Die Kosten der Ableitung sind gemessen: ein Arbeitstag, an dem der PR-Text den
falschen Namen trug und in den Einstellungen nach einer Zeichenfolge gesucht
wurde, die dort nicht steht.

**Was nur beim Release läuft, bricht beim Release.** Am 19.9.2026 scheiterte
der Release-Lauf von `zurich-opendata-mcp` 0.8.0 — und der Fehler stand am
Ende von sechzig Zeilen Docker-Pull:

```
Checking dist/zurich_opendata_mcp-0.8.0-py3-none-any.whl:
InvalidDistribution: Invalid distribution metadata:
'2.5' is not a valid metadata version
```

Im Repo hatte sich nichts geändert. `[build-system] requires` nennt
`hatchling` ohne Obergrenze, `python -m build` holt also beim Release die
jeweils neuste: `hatchling 1.32.3` schreibt `Metadata-Version: 2.5`, wo
`1.31.0` noch `2.4` schrieb. Die tag-gepinnte `pypa/gh-action-pypi-publish`
stand auf `v1.14.1` und bringt twine 6.1.0 mit, die 2.5 nicht kennt.

**Nicht PyPI hat abgelehnt, sondern das Prüfwerkzeug.** Positivkontrolle:
`hatchling 1.32.3` liegt selbst auf PyPI mit genau dieser Metadata-Version,
während andere Pakete im selben Lauf 2.4 zeigen — die Sonde unterscheidet
also. Die richtige Antwort war deshalb, die Action zu heben (`v1.14.2`,
twine 7), **nicht** das Backend zurückzupinnen. Ein Rückpin bindet das Repo
dauerhaft an eine alte Metadaten-Generation, um ein anderswo gelöstes
Problem zu umgehen.

Vier Handgriffe daraus:

- **Wandern zwei Dinge unabhängig und treffen sich nur beim Release, gehört
  ihr Zusammenspiel in einen Check, der öfter läuft als das Release.** Hier
  in den Job, der ohnehin frei auflöst (`fresh-install`), also auf jedem PR
  und wöchentlich. Dieselbe Klasse wie der 0.5.1-Defekt, nur eine Schicht
  weiter aussen: dort das Artefakt, hier das Werkzeug, das es prüft.
- **Ein Release-Lauf benutzt die Workflow-Datei AM TAG.** Eine Korrektur auf
  dem Standard-Branch rettet einen fehlgeschlagenen Lauf nie rückwirkend, und
  «Re-run jobs» wiederholt exakt denselben Fehler. Der Weg ist
  `workflow_dispatch` vom Standard-Branch — falls der Workflow ihn vorhält.
- **Eine gescheiterte Publikation verbraucht die Versionsnummer nicht, eine
  gelungene ist unwiderruflich.** Deshalb vor dem zweiten Anlauf *alle* Jobs
  lesen, nicht nur den gescheiterten. Hier leitete der Registry-Job seine
  Version sonst aus dem Tag-Namen ab und hätte bei einem Branch-Dispatch
  «main» hineingeschrieben; er fing es selbst ab, aber das wusste vorher
  niemand.
- **Ein Log ist erst gelesen, wenn man beim letzten Fehler angekommen ist.**
  Der Image-Pull davor sieht nach Inhalt aus und ist keiner.

**Eine Quelle ist nicht die Quelle.** Nach dem geglückten Neuanlauf meldete
PyPIs JSON-API (`/pypi/<name>/json`) weiterhin die alte Version, während der
Simple-Index (`/simple/<name>/`) Wheel und sdist der neuen bereits führte und
ein `pip install <name>==<neu>` durchlief. Die JSON-API hängt hinter einem
eigenen Cache. Wer nur sie fragt, widerspricht einem Menschen, der recht hat.
Bei einem Widerspruch zwischen zwei Diensten entscheidet der, der die Sache
*tut* — hier die Installation.

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

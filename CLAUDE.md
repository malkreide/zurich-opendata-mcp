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

## Teil 2 — Dieses Repo

**ruff: eine Quelle.** `pyproject.toml` `[dev]` pinnt `ruff==0.16.1`, `uv.lock`
hält dieselbe Version. `ci.yml` rief ruff vorher per
`uv run --with ruff==0.16.1` auf, während der Lock auf `0.15.18` stand — das
überschrieb nur diesen einen Aufruf, und wer lokal `uv run ruff check` fuhr,
lintete mit 0.15.18 gegen ein Gate, das 0.16.1 fuhr. Beim Anheben:
`pyproject.toml` ändern, `uv lock`, `ruff format`, alles zusammen committen.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

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

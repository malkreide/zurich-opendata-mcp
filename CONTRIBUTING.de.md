# Mitwirken an zurich-opendata-mcp

🌐 **[English](CONTRIBUTING.md)** | **Deutsch**

Vielen Dank für Ihr Interesse an einem Beitrag! Dieser Server ist Teil des
[Swiss Public Data MCP Portfolios](https://github.com/malkreide).

---

## Probleme melden

Nutzen Sie die [GitHub Issues](https://github.com/malkreide/zurich-opendata-mcp/issues),
um Fehler zu melden oder Features vorzuschlagen.

Bitte geben Sie an:
- Python-Version und Betriebssystem
- Vollständige Fehlermeldung oder Beschreibung des unerwarteten Verhaltens
- Schritte zur Reproduktion

---

## Entwicklungsumgebung einrichten

```bash
git clone https://github.com/malkreide/zurich-opendata-mcp.git
cd zurich-opendata-mcp

# Virtuelle Umgebung erstellen
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Mit Dev-Dependencies installieren
pip install -e ".[dev]"
```

---

## Pull Requests

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feat/mein-feature`
3. Nehmen Sie Ihre Änderungen vor und fügen Sie Tests hinzu
4. Stellen Sie sicher, dass alle Tests bestehen: `pytest tests/ -m "not live"`
5. Stellen Sie sicher, dass das Linting sauber ist: `ruff check src/ tests/`
6. Committen Sie nach [Conventional Commits](https://www.conventionalcommits.org/): `feat: neues Tool hinzufügen`
7. Pushen Sie und eröffnen Sie einen Pull Request gegen `main`

Pro Feature/Bugfix ein PR, und aktualisieren Sie die Dokumentation **sowohl** auf
Englisch als auch auf Deutsch (`README.md` / `README.de.md`).

### Der Check `Codex-Verdikt`: warum Ihr PR zwei Minuten rot stehen kann

Wer einen Draft auf «ready» schaltet, löst einen Codex-Review aus, und der
braucht **zwei bis drei Minuten**. Der Merge-Button wartet darauf nicht.
Zwischen dem 18. und 20.9.2026 wurde die Zeile «Codex-Review beantwortet» in
diesem Repo viermal in Folge gesetzt, ohne dass ein Review stattgefunden
hätte; bei dreien begann er überhaupt erst *nach* dem Merge — abgelesen an den
Zeitstempeln, die Codex selbst in seiner Summary-Tabelle veröffentlicht.

Der Review ist deshalb jetzt ein Check und keine Checkbox.
`.github/workflows/codex-gate.yml` meldet einen Check-Run namens
`Codex-Verdikt`, und `scripts/check_codex_verdict.py` entscheidet, was zählt:

| Beobachtet | Zählt als Verdikt? |
|---|---|
| Review-Objekt auf dem aktuellen Head | ja — es gibt Befunde, beantworten Sie sie |
| «Didn't find any major issues» mit dem aktuellen Commit | ja |
| Summary-Tabelle auf `Completed`, sonst nichts | **nein** |
| Summary-Tabelle auf `Running` | nein, läuft noch |
| Kontingent- oder Environment-Meldung | nein, der Review fand nicht statt |

Die dritte Zeile ist die, die man kennen sollte. Läuft ein Review auf einem
bereits geschlossenen PR zu Ende, steht die Tabelle auf `Completed`, und ein
Verdikt kommt nie — «completed» sagt, dass der Lauf fertig ist, nicht wie er
ausging.

Der Commit zählt mit: Ein Push löst **keinen** neuen Codex-Review aus. Ein
Verdikt zu einem früheren Commit ist kein Verdikt zu Ihrem; nachtriggern mit
einem Kommentar `@codex review`.

Der Check liest den PR-Zustand bei jedem Lauf frisch über die API. Steht er
rot, obwohl Codex inzwischen geantwortet hat, genügt deshalb *Actions →
Codex-Verdikt → den Lauf öffnen → «Re-run all jobs»*; ein leerer Commit ist
dafür nicht nötig.

**Wenn Sie wirklich ohne Review mergen müssen** — das Kontingent ist weg, oder
die Änderung kann nicht warten — setzen Sie das Label `codex-review-waived`.
Der Check wird dann grün und hält in seiner Zusammenfassung fest, dass
gewaivert wurde. Eine Hintertür, die im Log steht, ist besser als eine, die
niemand bemerkt.

---

## Ein neues Tool hinzufügen

1. **API-Client** (`src/zurich_opendata_mcp/clients/`): Bei Anbindung einer neuen
   API das Client-Modul ergänzen und Konstanten in `config.py` hinterlegen.
2. **Tool-Modul** (`src/zurich_opendata_mcp/tools/`):
   - Ein Pydantic-`BaseModel` für die Eingaben definieren (`extra="forbid"`)
   - Eine `@mcp.tool()`-Funktion mit `readOnlyHint: True` implementieren
   - Eine Markdown-formatierte Antwort über die Helfer in `formatters.py` zurückgeben
3. **Tests** (`tests/test_server.py`): Unit-Tests hinzufügen; die Upstream-API mit
   `respx` mocken. Live-Integrationstests sind mit `@pytest.mark.live` markiert.
4. **README.md / README.de.md**: Tool-Beschreibung und eine Beispiel-Abfrage in
   beiden Sprachen ergänzen.
5. **CHANGELOG.md**: Einen Eintrag unter `[Unreleased]` hinzufügen (siehe `CLAUDE.md`).

---

## Code-Stil

- Python 3.11+
- [Ruff](https://github.com/astral-sh/ruff) für Linting und Formatierung
- Type-Hints für alle öffentlichen Funktionen erforderlich
- Tests für neue Tools erforderlich (`tests/test_server.py`)
- Den bestehenden FastMCP- / Pydantic-v2-Mustern in `src/zurich_opendata_mcp/` folgen

---

## Datenquellen

Alle genutzten APIs sind öffentlich zugänglich und erfordern keine
Authentifizierung. Die Daten stehen unter CC0 oder vergleichbaren offenen Lizenzen.

| Quelle | Dokumentation |
|--------|--------------|
| CKAN | [data.stadt-zuerich.ch/api/3/](https://data.stadt-zuerich.ch/api/3/) |
| Geoportal WFS | [www.ogd.stadt-zuerich.ch/wfs/geoportal](https://www.ogd.stadt-zuerich.ch/wfs/geoportal) |
| Paris (Gemeinderat) | [www.gemeinderat-zuerich.ch/api](https://www.gemeinderat-zuerich.ch/api) |
| Zürich Tourismus | [www.zuerich.com/en/api/v2/data](https://www.zuerich.com/en/api/v2/data) |
| SPARQL | [ld.stadt-zuerich.ch/query](https://ld.stadt-zuerich.ch/query) |
| ParkenDD | [api.parkendd.de/Zuerich](https://api.parkendd.de/Zuerich) |

---

## Die Live-Suite: wann sie läuft, und wer ein rotes Ergebnis sieht

**Kadenz:** jeden Montag um 04:43 UTC, dazu jederzeit von Hand über *Actions → Live-Tests → Run
workflow*. Siehe [`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml).

**Wer es sieht:** Ein roter Lauf öffnet ein Issue mit dem Label `upstream` und dem stabilen Titel «Live-Tests gegen data.stadt-zuerich.ch rot (<Datum>)». Ein zweiter roter Lauf erkennt das offene Issue am Titelanfang und hängt sich an denselben Thread, statt ein zweites aufzumachen. Wird die Suite wieder grün, schliesst sich das Issue selbst.

**Drei Antworten, nicht zwei.** `scripts/classify_live_run.py` liest das JUnit-XML statt des
Exit-Codes und unterscheidet: `clear` (gelaufen, grün), `finding` (gelaufen,
etwas gefallen) und `unknown` (nicht gelaufen — Installation gescheitert, null
Tests eingesammelt, alle übersprungen). Ein `unknown` schliesst nie ein Issue:
Zuzumachen hiesse zu behaupten, der Vergleich sei gelaufen.

**Ein roter Live-Lauf heisst nicht zwingend «unser Fehler».** Er heisst: Der
Vertrag mit der Quelle hat sich geändert, oder die Quelle ist gerade aus. Beides
gehört gesehen, nur das Erste gehört gefixt. Bitte den Lauf lesen, bevor der Job
deaktiviert wird — so stirbt dieser Check, und er ist der einzige im Repo, der
einer falschen Grundannahme über data.stadt-zuerich.ch widersprechen kann. Jeder andere Test
prüft gegen eine Fixture, und die Fixture ist aus derselben Annahme geschrieben
wie der Code.

## Lizenz

Mit Ihrem Beitrag erklären Sie sich damit einverstanden, dass Ihre Beiträge unter
der [MIT-Lizenz](LICENSE) lizenziert werden.

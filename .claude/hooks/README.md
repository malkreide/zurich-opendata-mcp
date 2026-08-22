# SessionStart-Hook: Klon-Aktualität

`check-clone-freshness.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<default-branch>` liegt. Registriert ist er in
`.claude/settings.json` unter `hooks.SessionStart`; der Grund für die Ausnahme
vom sonst kommentarlosen JSON steht hier statt dort, weil `settings.json` keine
Kommentare erlaubt.

## Warum

Am 3.8.2026 hat ein veralteter Klon zweimal eine rote CI erzeugt, deren Ursache
nicht im Diff stand — die fehlenden Commits waren jeweils genau die, die das
Gate einführten, an dem der Branch scheiterte. Die Fehlersuche lief beide Male
in den falschen Dateien. Die Prüfung kostet eine Sekunde und ersetzt diese
Suche. `CLAUDE.md` verlangt sie ohnehin vor der Arbeit; der Hook erledigt sie,
statt sich darauf zu verlassen, dass jemand daran denkt.

## Verhalten

| Situation | Verhalten |
| --- | --- |
| Stand liegt N ≥ 1 Commits zurück | Meldung mit N und dem `git fetch`-Einzeiler |
| Stand ist aktuell (N = 0) | keine Ausgabe |
| kein Netz, kein Remote, DNS flattert, Timeout | keine Ausgabe, Exit 0 |
| detached HEAD | zählt, wenn möglich; sonst keine Ausgabe |
| kein `git`, kein Repo, leeres Repo | keine Ausgabe, Exit 0 |
| Quelle `clear` / `compact` | keine Ausgabe, kein Netzaufruf |

**Der Hook blockiert die Session nie.** Kein `set -e`, jeder Pfad endet in
`exit 0`, jeder Netzaufruf läuft unter einem kurzen Timeout (Vorgabe 5 s, per
`CLAUDE_FRESHNESS_TIMEOUT` überschreibbar; `timeout` wird benutzt, wenn
vorhanden, sonst greift ein Hintergrundprozess-Fallback). Zusätzlich steht in
`settings.json` ein `timeout` von 15 s als zweites Netz. Git läuft mit
`GIT_TERMINAL_PROMPT=0` und `BatchMode`, damit keine Credential-Abfrage auf ein
geschlossenes TTY wartet. Ein Hook, der bei Netzproblemen die Arbeit anhält,
wird nach dem zweiten Mal abgeschaltet und schützt danach gar nichts.

## Default-Branch

Der Default-Branch wird ermittelt, nicht als `main` angenommen: erst aus dem
lokalen `refs/remotes/origin/HEAD` (ohne Netz), sonst per
`git ls-remote --symref origin HEAD`. Drei Server im Portfolio (`openlex-mcp`,
`swiss-courts-mcp`, `swisstopo-mcp`) heissen ihren Default-Branch `master`;
genau die `main`-Annahme hat dort schon einmal einen Branch 15 Commits alt
werden lassen.

## Testen

Die Zusicherungen sind in `tests/test_clone_freshness_hook.py` gedeckt (echte
Git-Repos in `tmp_path`, kein Netz). Von Hand:

```bash
CLAUDE_PROJECT_DIR="$PWD" .claude/hooks/check-clone-freshness.sh </dev/null
```

Nichts auf stdout heisst: aktuell (oder still durchgegangen).

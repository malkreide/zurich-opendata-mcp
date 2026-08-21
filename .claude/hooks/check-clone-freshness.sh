#!/usr/bin/env bash
#
# SessionStart hook: melde, wie viele Commits der ausgecheckte Stand hinter
# origin/<default-branch> liegt.
#
# WARUM (3.8.2026, zweimal): Ein veralteter Klon erzeugte eine rote CI, deren
# Ursache nicht im Diff stand -- die fehlenden Commits waren jeweils genau die,
# die das Gate einfuehrten, an dem der Branch scheiterte. Die Suche lief in den
# falschen Dateien. Diese Pruefung kostet eine Sekunde und ersetzt sie.
#
# OBERSTE REGEL: Der Hook blockiert die Session NIEMALS. Kein Netz, kein Remote,
# detached HEAD, flatterndes DNS, kein git, fremdes Verzeichnis -- jeder dieser
# Faelle geht still durch (exit 0, keine Ausgabe). Ein Hook, der bei
# Netzproblemen die Arbeit anhaelt, wird nach dem zweiten Mal abgeschaltet und
# schuetzt danach gar nichts. Darum: kein `set -e`, jeder Pfad endet in exit 0,
# und jeder Netzaufruf laeuft unter einem kurzen Timeout.
#
# Der Default-Branch wird ermittelt, nicht als "main" angenommen: drei Server im
# Portfolio (openlex-mcp, swiss-courts-mcp, swisstopo-mcp) heissen ihn "master".
# Genau diese Annahme hat einen Branch schon einmal 15 Commits alt werden lassen.

# Kein `set -e`: ein fehlgeschlagenes Kommando darf hier nichts abbrechen.
set -u
set -o pipefail 2>/dev/null || true

# Sekunden pro Netzaufruf. Ueberschreibbar, damit Tests nicht warten muessen.
NET_TIMEOUT="${CLAUDE_FRESHNESS_TIMEOUT:-5}"

# Nie nach Credentials fragen -- ein Prompt auf einem geschlossenen TTY ist
# genau die Art Haenger, die dieser Hook vermeiden soll.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=/bin/true
export SSH_ASKPASS=/bin/true
export SSH_ASKPASS_REQUIRE=never
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes -oConnectTimeout=3 -oStrictHostKeyChecking=accept-new}"
export GIT_CONFIG_PARAMETERS="'http.lowSpeedLimit=1000' 'http.lowSpeedTime=${NET_TIMEOUT}'"

# `timeout` gibt es nicht ueberall (macOS ohne coreutils). Fallback: Hintergrund
# starten und nach Ablauf abschiessen.
run_limited() {
  local secs="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout -k 1 "$secs" "$@"
    return $?
  fi
  "$@" &
  local pid=$! waited=0 limit=$((secs * 10))
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$waited" -ge "$limit" ]; then
      kill -TERM "$pid" 2>/dev/null
      kill -KILL "$pid" 2>/dev/null
      wait "$pid" 2>/dev/null
      return 124
    fi
    sleep 0.1
    waited=$((waited + 1))
  done
  wait "$pid"
}

# Default-Branch: erst der lokale Cache (kein Netz), dann der Remote.
resolve_default_branch() {
  local ref name
  ref="$(git symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null)"
  name="${ref#refs/remotes/origin/}"
  if [ -n "$name" ] && [ "$name" != "$ref" ]; then
    printf '%s\n' "$name"
    return 0
  fi
  name="$(run_limited "$NET_TIMEOUT" git ls-remote --symref origin HEAD 2>/dev/null |
    sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p' | head -n 1)"
  [ -n "$name" ] || return 1
  printf '%s\n' "$name"
}

emit() {
  local branch="$1" behind="$2"
  # SessionStart: stdout landet als Kontext in der Session.
  cat <<MSG
Klon-Aktualitaet: der ausgecheckte Stand liegt ${behind} Commit(s) hinter origin/${branch}.

    git fetch origin ${branch} && git merge --ff-only FETCH_HEAD   # oder rebase

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht:
Es fehlen dann genau die Commits, die das Gate einfuehrten, an dem der Branch
scheitert -- und die Fehlersuche laeuft in den falschen Dateien.
MSG
}

main() {
  # stdin (das SessionStart-JSON) konsumieren, aber nur wenn es eines gibt --
  # sonst wuerde ein Aufruf von Hand am `cat` haengen.
  local payload=""
  if [ ! -t 0 ]; then
    payload="$(run_limited 2 cat 2>/dev/null)"
  fi
  # Bei `clear`/`compact` ist der Klon seit dem Sessionstart unveraendert;
  # ein zweiter Netzaufruf brauchte dort niemand.
  case "$payload" in
    *'"source"'*'"clear"'* | *'"source"'*'"compact"'*) return 0 ;;
  esac

  command -v git >/dev/null 2>&1 || return 0
  cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || return 0
  git rev-parse --git-dir >/dev/null 2>&1 || return 0
  git rev-parse --verify --quiet HEAD >/dev/null 2>&1 || return 0
  git remote get-url origin >/dev/null 2>&1 || return 0

  local branch
  branch="$(resolve_default_branch)" || return 0
  [ -n "$branch" ] || return 0

  run_limited "$NET_TIMEOUT" git fetch --quiet --no-tags origin "refs/heads/${branch}" \
    >/dev/null 2>&1 || return 0

  local behind
  behind="$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null)"
  case "$behind" in
    '' | *[!0-9]*) return 0 ;;  # kein Zaehlergebnis -> schweigen
    0) return 0 ;;              # aktuell -> schweigen
  esac

  emit "$branch" "$behind"
}

main "$@"
exit 0

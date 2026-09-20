"""
Prüfen, ob für den aktuellen Head eines PR ein Codex-Verdikt vorliegt.

Warum es das gibt: Der Codex-Review ist im Portfolio eine Checkbox im
PR-Text — also Ehrensache. Zwischen dem 18. und 20.9.2026 ist sie in
`zurich-opendata-mcp` viermal in Folge formal gesetzt und faktisch leer
geblieben. Gemessen, nicht geschätzt (alle Zeiten UTC):

    PR    ready       gemergt     Review begann   Verdikt
    #115  18:26:16    18:33:27    18:30:55        ja, 1 s vor dem Merge
    #116  17:11:25    17:11:29    17:11:31        nein
    #117  19:21:27    19:21:31    19:21:33        nein
    #118  08:47:59    08:48:03    08:48:07        nein

Dreimal begann der Review NACH dem Merge. Der Review braucht zwei bis drei
Minuten ab «ready»; dazwischen hindert nichts am Mergen. Ein Text, den man
zum Merge-Zeitpunkt lesen müsste, wird zum Merge-Zeitpunkt nicht gelesen —
das ist keine Nachlässigkeit, sondern eine Eigenschaft des Ablaufs. Deshalb
hier eine Mechanik statt einer weiteren Zeile Dokumentation.

**Was dieses Skript beantwortet:** Liegt für GENAU diesen Head ein Verdikt
vor? Nicht: ist das Verdikt gut. Ein Befund ist ein Verdikt — ihn zu
beantworten bleibt Menschenarbeit, das steht in CLAUDE.md.

**Was als Verdikt zählt** (und was ausdrücklich nicht):

| Beobachtung | zählt? |
|---|---|
| Review-Objekt des Bots auf dem Head | ja — Befund liegt vor |
| «Didn't find any major issues» mit passendem Commit | ja — befundlos |
| Summary-Tabelle `Completed`, sonst nichts | **nein** |
| Summary-Tabelle `Running` | nein, noch am Laufen |
| Kontingent- oder Environment-Meldung | nein, Review fand nicht statt |
| gar nichts | nein |

Die dritte Zeile ist die wichtige und stammt aus derselben Messung: Läuft
ein Review auf einem schon geschlossenen PR zu Ende, steht die Tabelle auf
`Completed`, ohne dass je ein Verdikt kommt. «Completed» sagt, dass der Lauf
fertig ist, nicht wie er ausging. Wer darauf grün schaltet, hat die Lücke
nur verschoben.

**Der Commit-Vergleich ist der Kern.** Ein Push löst keinen neuen Review
aus; die Trigger sind «open for review», «draft marked ready» und ein
`@codex review`-Kommentar. Ein Verdikt zu einem älteren Commit ist deshalb
kein Verdikt zum aktuellen. Die Befundlos-Zeile nennt den Commit abgekürzt
(`Reviewed commit: 65fd46b4bc`), die Tabelle in wieder anderer Länge —
verglichen wird darum über ein gemeinsames Präfix.

**Notausgang, sichtbar statt still:** Das Label aus `--waiver-label`
(Vorgabe `codex-review-waived`) lässt den Check durch und schreibt in die
Begründung, dass gewaivert wurde. Ein Notausgang, den man im Protokoll
sieht, ist einem stillen Vorbeigehen vorzuziehen.

Verwendung:
    python scripts/check_codex_verdict.py --event event.json
    python scripts/check_codex_verdict.py --event -   # von stdin

`event.json` ist ein Objekt mit `head_sha`, `reviews`, `comments` und
`labels`; die Felder folgen der GitHub-REST-Form. Exit 0 = Verdikt liegt
vor, Exit 1 = nicht.

Bewusst nur Standardbibliothek und ohne Netz: die Abfragen macht der
Workflow, dieses Skript entscheidet nur — so ist es lokal und im Test
gegen aufgezeichnete Antworten fahrbar.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Any

CODEX_LOGIN = "chatgpt-codex-connector[bot]"
DEFAULT_WAIVER_LABEL = "codex-review-waived"

# Kürzeste Commit-Angabe, die in den beobachteten Texten vorkommt, ist sieben
# Zeichen. Darunter wird ein Präfixvergleich mehrdeutig.
MIN_SHA_PREFIX = 7

_NO_FINDINGS = re.compile(r"Didn't find any major issues", re.IGNORECASE)
_QUOTA = re.compile(r"reached your Codex usage limits", re.IGNORECASE)
_ENVIRONMENT = re.compile(r"create an environment for this repo", re.IGNORECASE)
_SUMMARY_MARKER = "codex-pull-request-review-summary"
# Ueberschrift eines echten Review-Objekts — eine Thread-Antwort hat keine.
_REVIEW_MARKER = re.compile(r"Codex Review", re.IGNORECASE)
_REVIEWED_COMMIT = re.compile(r"Reviewed commit:\*{0,2}\s*`([0-9a-f]{7,40})`", re.IGNORECASE)
# Zelle der Summary-Tabelle: | 📝 **Code Review** | ✅ **Completed** … | `sha` | … |
_TABLE_STATUS = re.compile(r"\*\*(Completed|Running|Failed)\*\*", re.IGNORECASE)
_TABLE_COMMIT = re.compile(r"\|\s*`([0-9a-f]{7,40})`\s*\|")


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str


def _same_commit(a: str, b: str) -> bool:
    """Gleicher Commit, über ein gemeinsames Präfix verglichen.

    Die Texte nennen den Commit in unterschiedlicher Länge; ein wörtlicher
    Vergleich wäre deshalb immer falsch.
    """
    a, b = a.strip().lower(), b.strip().lower()
    n = min(len(a), len(b))
    return n >= MIN_SHA_PREFIX and a[:n] == b[:n]


def _codex_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [i for i in items if (i.get("user") or {}).get("login") == CODEX_LOGIN]


_OUTAGE_LABEL = {
    "quota": "eine Kontingent-Meldung",
    "environment": "eine Environment-Meldung",
}


def _also_seen(outage: str | None, unknown: list[str]) -> str:
    """Nebenbeobachtungen anhaengen, statt sie zu verschweigen.

    Sie entscheiden nichts mehr, sollen aber im Check-Text sichtbar bleiben:
    eine aeltere Ausfallmeldung erklaert oft, warum ein Verdikt fehlt.
    """
    rest = ([_OUTAGE_LABEL[outage]] if outage else []) + list(unknown)
    return "\nAusserdem gesehen: " + "; ".join(rest) if rest else ""


def evaluate(event: dict[str, Any], waiver_label: str = DEFAULT_WAIVER_LABEL) -> Verdict:
    """Das ganze Urteil, als reine Funktion — damit es testbar ist."""
    head = str(event.get("head_sha") or "").strip()
    if len(head) < MIN_SHA_PREFIX:
        return Verdict(False, f"kein brauchbarer head_sha im Ereignis: {head!r}")

    labels = {str(name).strip() for name in event.get("labels") or []}
    if waiver_label in labels:
        return Verdict(
            True,
            f"Gewaivert über das Label «{waiver_label}». Kein Codex-Verdikt verlangt — "
            "diese Zeile ist der Beleg, dass jemand das bewusst entschieden hat.",
        )

    # 1. Review-Objekt auf dem Head: ein Befund liegt vor.
    #
    # `commit_id` allein genuegt hier NICHT. GitHub verpackt jede Antwort auf
    # einen Inline-Kommentar als Review-Objekt, und es traegt den aktuellen
    # Head. Am 20.9.2026 auf PR #119 gemessen: Codex antwortete um 13:03:12 in
    # einem Thread mit seiner Environment-Meldung, das dabei entstandene
    # Review-Objekt trug `b64b96d` — einen Commit, den Codex nie geprueft hat.
    # Der Gate schaltete darauf gruen. Ein blosser Wortwechsel haette also
    # genau die Luecke geoeffnet, gegen die dieses Skript geschrieben ist.
    #
    # Unterscheidbar sind die beiden am Body: ein echtes Review fuehrt die
    # Ueberschrift «Codex Review» und nennt den geprueften Commit im Text;
    # eine Thread-Antwort hat gar keinen Body. Der Text schlaegt `commit_id`,
    # weil er sagt, was geprueft wurde, und nicht bloss, woran der Kommentar
    # haengt.
    for review in _codex_items(event.get("reviews") or []):
        body = str(review.get("body") or "")
        if not _REVIEW_MARKER.search(body):
            continue
        reviewed = _REVIEWED_COMMIT.search(body)
        commit = reviewed.group(1) if reviewed else str(review.get("commit_id") or "")
        if commit and _same_commit(commit, head):
            return Verdict(
                True,
                f"Codex hat {head[:10]} geprüft und einen Befund als Review-Objekt "
                "hinterlegt. Der Gate ist damit erfüllt — der Befund selbst ist "
                "beantwortet oder behoben, nie ignoriert (CLAUDE.md).",
            )

    comments = _codex_items(event.get("comments") or [])
    table_status: str | None = None
    table_commit: str | None = None
    unknown: list[str] = []
    # Juengste Ausfallmeldung, nicht die erste: Kommentare kommen chronologisch,
    # eine spaetere ueberschreibt eine fruehere.
    outage: str | None = None

    # In dieser Schleife wird NUR positiv zurueckgekehrt. Eine Ausfallmeldung
    # bleibt fuer immer in der Kommentarliste stehen; kehrte man auf ihr
    # negativ zurueck, wuerde eine spaetere, gueltige Befundlos-Meldung nie
    # mehr erreicht — der Rat «per @codex review erneut ausloesen», den die
    # Ausfallmeldung selbst erteilt, waere mechanisch unbefolgbar.
    for comment in comments:
        body = str(comment.get("body") or "")

        if _SUMMARY_MARKER in body:
            status = _TABLE_STATUS.search(body)
            commit = _TABLE_COMMIT.search(body)
            table_status = status.group(1).lower() if status else None
            table_commit = commit.group(1) if commit else None
            continue

        if _QUOTA.search(body):
            outage = "quota"
            continue

        if _ENVIRONMENT.search(body):
            outage = "environment"
            continue

        if _NO_FINDINGS.search(body):
            reviewed = _REVIEWED_COMMIT.search(body)
            if reviewed and _same_commit(reviewed.group(1), head):
                return Verdict(
                    True,
                    f"Codex hat {head[:10]} geprüft und keinen Befund gemeldet.",
                )
            if reviewed:
                unknown.append(
                    f"Befundlos-Meldung, aber zu Commit {reviewed.group(1)} statt "
                    f"{head[:10]} — seither wurde gepusht, und ein Push loest keinen "
                    "neuen Review aus."
                )
            else:
                unknown.append("Befundlos-Meldung ohne Commit-Angabe")
            continue

        unknown.append(f"unbekannter Codex-Text: {body.strip()[:200]!r}")

    if table_status == "running":
        return Verdict(
            False,
            f"Codex prüft {(table_commit or head)[:10]} noch (Tabelle: «Running»). "
            "Der Review braucht zwei bis drei Minuten ab «ready» — das ist kein "
            "Fehler, sondern der Grund, warum es diesen Check gibt." + _also_seen(outage, unknown),
        )

    if table_status == "completed" and table_commit and _same_commit(table_commit, head):
        return Verdict(
            False,
            f"Die Summary-Tabelle steht auf «Completed» für {table_commit[:10]}, aber "
            "es liegt weder ein Review-Objekt noch eine Befundlos-Meldung vor. "
            "«Completed» sagt, dass der Lauf fertig ist, nicht wie er ausging — "
            "gemessen an #116 und #117 ist das der Zustand, in dem ein Review auf "
            "einem bereits geschlossenen PR endete. Per «@codex review» erneut "
            "auslösen." + _also_seen(outage, unknown),
        )

    if outage == "quota":
        return Verdict(
            False,
            "Codex meldet ein erschöpftes Kontingent — der Review hat NICHT "
            "stattgefunden. Warten, bis das Fenster wieder offen ist, dann per "
            "«@codex review» erneut auslösen. Kein Grund zu mergen." + _also_seen(None, unknown),
        )

    if outage == "environment":
        return Verdict(
            False,
            "Codex meldet eine fehlende Environment für dieses Repo — der Review "
            "hat NICHT stattgefunden. Environment unter "
            "chatgpt.com/codex/cloud/settings/environments anlegen (je Repo), "
            "dann per «@codex review» erneut auslösen." + _also_seen(None, unknown),
        )

    if unknown:
        return Verdict(
            False,
            "Kein verwertbares Verdikt für " + head[:10] + ". Gesehen: " + "; ".join(unknown),
        )

    return Verdict(
        False,
        f"Für {head[:10]} liegt noch kein Codex-Verdikt vor. Warten, bis die "
        "Befundlos-Meldung oder ein Review-Objekt erscheint (zwei bis drei Minuten "
        f"ab «ready»), oder bewusst über das Label «{waiver_label}» waivern.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_codex_verdict.py",
        description="Liegt fuer den aktuellen PR-Head ein Codex-Verdikt vor?",
    )
    parser.add_argument("--event", required=True, help="JSON-Datei oder '-' fuer stdin")
    parser.add_argument("--waiver-label", default=DEFAULT_WAIVER_LABEL)
    args = parser.parse_args(argv)

    raw = sys.stdin.read() if args.event == "-" else open(args.event, encoding="utf-8").read()
    verdict = evaluate(json.loads(raw), args.waiver_label)

    print(("OK: " if verdict.ok else "BLOCKIERT: ") + verdict.reason)
    return 0 if verdict.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

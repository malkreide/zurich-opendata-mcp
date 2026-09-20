"""Zusicherungen für `scripts/check_codex_verdict.py`.

Der Check ist eine Mechanik gegen einen Ablauf-Fehler, nicht gegen einen
Code-Fehler: Zwischen dem 18. und 20.9.2026 wurde die Checkbox
«Codex-Review beantwortet» viermal in Folge formal gesetzt und faktisch
leer gelassen, dreimal begann der Review sogar erst nach dem Merge.

Geprüft wird gegen aufgezeichnete Ereignisse in `tests/fixtures/codex/`
(Herkunft und Datum stehen dort in `PROVENANCE.md`). Handgeschriebene
Beispiele könnten nur die Annahme des Autors bestätigen — drei dieser
Dateien sind darum wörtliche Mitschriften der Kommentare aus #115, #116
und #118.

Die tragende Zusicherung ist nicht «erkennt ein Verdikt», sondern
**«hält die drei Beinahe-Verdikte für keines»**: die Tabelle auf
`Completed` ohne Verdikt, ein Verdikt zu einem älteren Commit, und die
beiden Ausfallmeldungen. Ein Gate, das dort grün wird, verschiebt die
Lücke bloss.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "codex"


def _load_module():
    """Das Skript liegt in `scripts/`, ist also kein importierbares Paket.

    Das Modul muss vor `exec_module` in `sys.modules` stehen: `dataclasses`
    schlaegt beim Aufloesen von Typ-Annotationen `sys.modules[cls.__module__]`
    nach und faellt sonst mit einem `AttributeError` auf `None` um.
    """
    path = ROOT / "scripts" / "check_codex_verdict.py"
    spec = importlib.util.spec_from_file_location("check_codex_verdict", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_module()


def event(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ── Was ein Verdikt ist ──────────────────────────────────────────────────


def test_befundlos_auf_dem_head_ist_ein_verdikt() -> None:
    """PR #115, wörtlich mitgeschrieben: Tabelle plus «Didn't find any major issues»."""
    verdict = gate.evaluate(event("pr115_befundlos.json"))
    assert verdict.ok, verdict.reason
    assert "keinen Befund" in verdict.reason


def test_ein_review_objekt_auf_dem_head_ist_ein_verdikt() -> None:
    """Ein Befund ist ein Verdikt. Ihn zu beantworten bleibt Menschenarbeit —
    der Gate fragt, OB geprüft wurde, nicht wie es ausging."""
    verdict = gate.evaluate(event("befund_review_objekt.json"))
    assert verdict.ok, verdict.reason
    assert "Befund" in verdict.reason


# ── Was keines ist: die drei Beinahe-Faelle ──────────────────────────────


def test_eine_thread_antwort_von_codex_ist_kein_review() -> None:
    """Der gefährlichste Fall, weil er GRÜN schaltete statt rot.

    GitHub verpackt jede Antwort auf einen Inline-Kommentar als Review-Objekt,
    und dieses trägt den aktuellen Head. Am 20.9.2026 auf PR #119 mitgeschrieben:
    Codex antwortete um 13:03:12 in einem Thread, das Objekt trug `b64b96d` —
    einen Commit, den Codex nie geprüft hat. Ein blosser Wortwechsel hätte den
    Gate erfüllt.
    """
    verdict = gate.evaluate(event("pr119_thread_antwort_kein_review.json"))
    assert not verdict.ok, verdict.reason


def test_positivkontrolle_dasselbe_ereignis_auf_dem_geprueften_commit() -> None:
    """Gegenprobe zum Test davor: dieselben Objekte, nur der Head passt.

    Ohne sie hiesse «nicht grün» womöglich nur, dass die Regel alles ablehnt.
    """
    ereignis = event("pr119_thread_antwort_kein_review.json")
    ereignis["head_sha"] = "6dc81d17ccf8f4aee8cddf58ae127b1281bb683f"
    verdict = gate.evaluate(ereignis)
    assert verdict.ok, verdict.reason
    assert "Review-Objekt" in verdict.reason


def test_der_text_des_reviews_schlaegt_die_commit_id() -> None:
    """`commit_id` sagt, woran das Objekt hängt; der Text, was geprüft wurde."""
    ereignis = {
        "head_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "labels": [],
        "comments": [],
        "reviews": [
            {
                "user": {"login": gate.CODEX_LOGIN},
                "commit_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "body": "### 💡 Codex Review\n\n**Reviewed commit:** `bbbbbbbbbb`\n",
            }
        ],
    }
    verdict = gate.evaluate(ereignis)
    assert not verdict.ok, verdict.reason


def test_completed_ohne_verdikt_zaehlt_nicht() -> None:
    """Der Kern. PR #116: Der Review lief auf dem geschlossenen PR zu Ende,
    die Tabelle stand auf «Completed», ein Verdikt kam nie. Wer hier grün
    schaltet, baut genau die Lücke nach, die der Check schliessen soll."""
    verdict = gate.evaluate(event("pr116_completed_ohne_verdikt.json"))
    assert not verdict.ok
    assert "Completed" in verdict.reason
    assert "nicht wie er ausging" in verdict.reason


def test_verdikt_zu_einem_aelteren_commit_zaehlt_nicht() -> None:
    """Ein Push löst keinen neuen Review aus — ein Verdikt zu `3fdce1b` sagt
    nichts über `cd90442`."""
    verdict = gate.evaluate(event("verdikt_zu_altem_commit.json"))
    assert not verdict.ok
    assert "3fdce1b" in verdict.reason


def test_running_ist_noch_kein_verdikt() -> None:
    """PR #118, der Zustand im Moment des Merges."""
    verdict = gate.evaluate(event("pr118_running.json"))
    assert not verdict.ok
    assert "Running" in verdict.reason


# ── Ausfallmeldungen: der Review hat nicht stattgefunden ─────────────────


def test_kontingent_ist_kein_verdikt_und_nennt_den_weg() -> None:
    verdict = gate.evaluate(event("kontingent.json"))
    assert not verdict.ok
    assert "Kontingent" in verdict.reason
    assert "@codex review" in verdict.reason


def test_fehlende_environment_ist_kein_verdikt_und_nennt_den_weg() -> None:
    verdict = gate.evaluate(event("environment.json"))
    assert not verdict.ok
    assert "Environment" in verdict.reason
    assert "settings/environments" in verdict.reason


def test_ein_spaeterer_erfolg_schlaegt_eine_aeltere_kontingent_meldung() -> None:
    """Die Ausfallmeldung bleibt für immer in der Kommentarliste stehen.

    Sie rät, per «@codex review» erneut auszulösen. Bewertete das Skript sie
    weiterhin als Absage, wäre genau dieser Rat unbefolgbar: der Gate käme nach
    einem erschöpften Kontingent nie mehr auf Grün. Befund eines Codex-Reviews
    auf PR #119.
    """
    verdict = gate.evaluate(event("kontingent_dann_verdikt.json"))
    assert verdict.ok, verdict.reason
    assert "keinen Befund" in verdict.reason


def test_ein_spaeterer_erfolg_schlaegt_eine_aeltere_environment_meldung() -> None:
    verdict = gate.evaluate(event("environment_dann_verdikt.json"))
    assert verdict.ok, verdict.reason


def test_eine_aeltere_ausfallmeldung_bleibt_sichtbar_wenn_sie_nichts_entscheidet() -> None:
    """Sie entscheidet nichts mehr — verschwiegen wird sie deshalb nicht.

    Ohne Verdikt erklärt eine Kontingent-Meldung oft genau, warum keines da
    ist; sie aus dem Text zu streichen wäre der gegenteilige Fehler.
    """
    ereignis = event("kontingent_dann_verdikt.json")
    # Das Verdikt entfernen, die Ausfallmeldung stehen lassen.
    ereignis["comments"] = [
        k for k in ereignis["comments"] if "Didn't find any major issues" not in k["body"]
    ]
    verdict = gate.evaluate(ereignis)
    assert not verdict.ok
    assert "Kontingent" in verdict.reason


def test_ein_laufender_review_schlaegt_eine_aeltere_ausfallmeldung() -> None:
    """«Running» ist die jüngere Auskunft und gewinnt — die ältere bleibt im Text."""
    ereignis = event("pr118_running.json")
    ereignis["comments"].insert(
        0,
        {
            "user": {"login": "chatgpt-codex-connector[bot]"},
            "body": "You have reached your Codex usage limits for code reviews.",
        },
    )
    verdict = gate.evaluate(ereignis)
    assert not verdict.ok
    assert "Running" in verdict.reason
    assert "Kontingent-Meldung" in verdict.reason


def test_gar_nichts_ist_kein_verdikt() -> None:
    verdict = gate.evaluate(event("leer.json"))
    assert not verdict.ok
    assert "noch kein Codex-Verdikt" in verdict.reason


# ── Notausgang und Randfaelle ────────────────────────────────────────────


def test_das_waiver_label_laesst_durch_und_sagt_es() -> None:
    """Ein Notausgang, den man im Protokoll sieht, ist einem stillen
    Vorbeigehen vorzuziehen."""
    payload = event("leer.json") | {"labels": ["codex-review-waived"]}
    verdict = gate.evaluate(payload)
    assert verdict.ok
    assert "Gewaivert" in verdict.reason


def test_ein_fremdes_label_laesst_nicht_durch() -> None:
    """Gegenprobe zum Notausgang: sonst öffnete ihn jedes beliebige Label."""
    payload = event("leer.json") | {"labels": ["dependencies", "bug"]}
    assert not gate.evaluate(payload).ok


def test_der_waiver_label_name_ist_konfigurierbar() -> None:
    payload = event("leer.json") | {"labels": ["freigabe-ohne-review"]}
    assert not gate.evaluate(payload).ok
    assert gate.evaluate(payload, waiver_label="freigabe-ohne-review").ok


def test_ein_fremder_bot_zaehlt_nicht() -> None:
    """Sonst genügte ein beliebiger Kommentar mit dem richtigen Satz."""
    payload = event("leer.json")
    payload["comments"] = [
        {
            "user": {"login": "irgendein-bot[bot]"},
            "body": "Codex Review: Didn't find any major issues.\n\n"
            "**Reviewed commit:** `cd90442724`\n",
        }
    ]
    assert not gate.evaluate(payload).ok


def test_ein_unbekannter_text_wird_woertlich_zitiert_statt_eingeordnet() -> None:
    """Der Abschnitt in CLAUDE.md musste schon zweimal wachsen. Ein Text, den
    dieses Skript nicht kennt, gehört sichtbar in die Begründung — nicht in
    eine der bekannten Schubladen gezwungen."""
    payload = event("leer.json")
    payload["comments"] = [{"user": {"login": gate.CODEX_LOGIN}, "body": "Etwas ganz Neues."}]
    verdict = gate.evaluate(payload)
    assert not verdict.ok
    assert "Etwas ganz Neues." in verdict.reason


def test_ein_unbrauchbarer_head_sha_faellt_auf() -> None:
    """Lieber blockieren als auf einem leeren Vergleich grün werden."""
    assert not gate.evaluate({"head_sha": "", "comments": [], "reviews": []}).ok


@pytest.mark.parametrize(
    ("a", "b", "gleich"),
    [
        ("cd90442724fac5167450175d93e6631de3702b75", "cd90442", True),
        ("cd90442724fac5167450175d93e6631de3702b75", "cd90442724", True),
        ("cd90442724fac5167450175d93e6631de3702b75", "3fdce1b", False),
        ("cd90442", "cd904", False),  # zu kurz: waere mehrdeutig
    ],
)
def test_commits_werden_ueber_ein_gemeinsames_praefix_verglichen(
    a: str, b: str, gleich: bool
) -> None:
    """Die Texte nennen den Commit in unterschiedlicher Länge — sieben Zeichen
    in der Tabelle, zehn in der Befundlos-Zeile. Ein wörtlicher Vergleich wäre
    deshalb immer falsch, ein zu kurzer mehrdeutig."""
    assert gate._same_commit(a, b) is gleich


# ── Der Weg durch das CLI, nicht nur durch die Funktion ──────────────────


def test_die_concurrency_gruppe_steht_auf_job_ebene() -> None:
    """Drift-Wache für eine Eigenschaft, die kein Unit-Test sonst erreicht.

    `pull_request_target` feuert für JEDEN PR, nicht nur für Forks; für
    dieselbe Aktion entstehen also immer zwei Läufe. Stünde die
    `concurrency`-Gruppe auf Workflow-Ebene, träten beide ihr bei — sie wird
    ausgewertet, bevor der Job-`if` je gelesen wird. Mit `cancel-in-progress`
    könnte dann der Lauf gewinnen, dessen Job der Filter gleich darauf
    überspringt: kein Job, kein POST, gar kein Check.

    Geprüft wird die Einrückung und nicht der geparste Baum: pyyaml ist keine
    Abhängigkeit dieses Projekts, und für genau diese Eigenschaft — steht der
    Schlüssel auf Spalte 0 oder eingerückt — reicht der Text.
    """
    zeilen = (
        (ROOT / ".github" / "workflows" / "codex-gate.yml").read_text(encoding="utf-8").splitlines()
    )
    auf_spalte_null = [z for z in zeilen if z.startswith("concurrency:")]
    eingerueckt = [z for z in zeilen if z.strip() == "concurrency:" and z != z.lstrip()]

    assert not auf_spalte_null, (
        "concurrency steht wieder auf Workflow-Ebene — damit tritt auch der "
        "Lauf der Gruppe bei, dessen Job uebersprungen wird."
    )
    assert len(eingerueckt) == 1, "genau eine concurrency-Gruppe, auf Job-Ebene"


def test_der_checkout_pinnt_einen_ref() -> None:
    """Zweite Drift-Wache, und die sicherheitsrelevante.

    Ohne `ref` richtet sich `actions/checkout` nach dem Ereignis. Bei
    `pull_request_review` ist die Vorgabe `refs/pull/<n>/merge` — am
    20.9.2026 an Lauf 35514764426 im Log abgelesen —, und dieses Ereignis
    trägt auch bei einem Fork-PR einen Token mit `checks: write`. Ein Fork
    könnte `check_codex_verdict.py` dann in eigener Fassung ausführen lassen
    und sich ein grünes `Codex-Verdikt` selbst schreiben.

    Wer die `ref:`-Zeile entfernt, öffnet genau das wieder.
    """
    text = (ROOT / ".github" / "workflows" / "codex-gate.yml").read_text(encoding="utf-8")
    checkout = text.split("actions/checkout@", 1)[1]
    # Nur der Block bis zum naechsten Schritt derselben Ebene.
    block = checkout.split("\n      - ", 1)[0]

    assert "ref:" in block, "der Checkout pinnt keinen Ref mehr"
    assert "github.event.pull_request.base.sha" in block, (
        "der Fork-Fall faellt nicht mehr auf die Basis zurueck"
    )
    assert "persist-credentials: false" in block


def test_dependabot_laeuft_ueber_den_privilegierten_pfad() -> None:
    """Dritte Drift-Wache: der unscheinbarste der drei Faelle.

    Ein Dependabot-Branch liegt in diesem Repo, eine blosse Herkunftspruefung
    schickt ihn also auf den `pull_request`-Pfad. GitHub behandelt von
    Dependabot ausgeloeste Ereignisse aber wie Fork-Ereignisse und gibt einen
    Nur-Lese-Token; der POST endet mit 403. Unter einem Required Check waere
    jeder woechentliche Dependabot-PR dauerhaft blockiert — der Notausgang
    eingeschlossen. `.github/dependabot.yml` erzeugt zwei davon pro Woche.
    """
    text = (ROOT / ".github" / "workflows" / "codex-gate.yml").read_text(encoding="utf-8")
    bedingung = text.split("if: >-", 1)[1].split("env:", 1)[0]

    # Beide Zweige muessen Dependabot kennen, sonst faellt er durch oder
    # laeuft doppelt.
    assert bedingung.count("dependabot[bot]") == 2, (
        "beide PR-Zweige muessen Dependabot benennen — einmal ausschliessend, einmal einschliessend"
    )
    # Am PR-Autor, nicht am Ausloeser: wer das Label setzt, wechselt.
    assert "github.event.pull_request.user.login" in bedingung
    assert "github.actor" not in bedingung


def test_das_cli_endet_mit_0_bei_verdikt_und_1_ohne(capsys, tmp_path) -> None:
    ok = tmp_path / "ok.json"
    ok.write_text((FIXTURES / "pr115_befundlos.json").read_text(encoding="utf-8"), "utf-8")
    assert gate.main(["--event", str(ok)]) == 0
    assert capsys.readouterr().out.startswith("OK: ")

    nein = tmp_path / "nein.json"
    nein.write_text((FIXTURES / "pr118_running.json").read_text(encoding="utf-8"), "utf-8")
    assert gate.main(["--event", str(nein)]) == 1
    assert capsys.readouterr().out.startswith("BLOCKIERT: ")

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


def test_das_cli_endet_mit_0_bei_verdikt_und_1_ohne(capsys, tmp_path) -> None:
    ok = tmp_path / "ok.json"
    ok.write_text((FIXTURES / "pr115_befundlos.json").read_text(encoding="utf-8"), "utf-8")
    assert gate.main(["--event", str(ok)]) == 0
    assert capsys.readouterr().out.startswith("OK: ")

    nein = tmp_path / "nein.json"
    nein.write_text((FIXTURES / "pr118_running.json").read_text(encoding="utf-8"), "utf-8")
    assert gate.main(["--event", str(nein)]) == 1
    assert capsys.readouterr().out.startswith("BLOCKIERT: ")

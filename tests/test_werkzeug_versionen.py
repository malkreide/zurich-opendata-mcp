"""`uv.lock` ist die einzige Quelle der Gate-Werkzeug-Versionen — und bleibt es.

Dieses Repo installiert per `uv sync` aus dem committeten Lock; der schreibt
ruff und mypy fest, und `pyproject.toml` nennt nur die zulaessige Spanne. Das
ist die richtige Aufteilung, und sie ist bereits hergestellt.

Sie war es nicht immer. Die CLAUDE.md haelt den Vorfall fest: `ci.yml` rief ruff
per `uv run --with ruff==0.16.1` auf, waehrend der Lock auf 0.15.18 stand. Der
Aufruf ueberschrieb genau diesen einen Schritt — wer lokal `uv run ruff check`
fuhr, lintete mit 0.15.18 gegen ein Gate, das 0.16.1 fuhr. Nichts daran war rot;
die beiden Laeufe waren sich nur ueber die Regeln uneinig.

Diese Tests halten fest, dass kein Workflow ein Gate-Werkzeug an `uv.lock`
vorbei installiert. `--with` an sich ist erlaubt: `pip-audit` steht bewusst
nicht im dev-Extra, ist kein Gate-Werkzeug und traegt keine Version.
"""

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"
_LOCK = _ROOT / "uv.lock"
# Werkzeuge, deren Version einen Gate-Ausgang veraendert. pip-audit gehoert
# nicht dazu: es meldet Verwundbarkeiten, nicht Regelverstoesse an unserem Code.
_GATE_WERKZEUGE = ("ruff", "mypy")


def _lock_version(paket: str) -> str | None:
    """Die im Lock festgeschriebene Version, oder None."""
    treffer = re.search(
        rf'name = "{paket}"\nversion = "([^"]+)"', _LOCK.read_text(encoding="utf-8")
    )
    return treffer.group(1) if treffer else None


def test_der_lock_schreibt_die_gate_werkzeuge_fest() -> None:
    """Ohne Eintrag im Lock waere die Version wieder Aufloesungssache.

    Geprueft wird nur die Anwesenheit, nicht die Form der Versionsangabe: uv
    weigert sich, einen Lock mit einer nicht-numerischen Version ueberhaupt zu
    parsen ("expected version to start with a number"), der Testlauf kaeme also
    nie so weit. Eine Zusicherung, die sich nicht zum Fallen bringen laesst,
    prueft nichts — sie stand hier und ist wieder raus.
    """
    assert _LOCK.exists(), "uv.lock fehlt — dann pinnt nichts die Gate-Werkzeuge"
    for werkzeug in _GATE_WERKZEUGE:
        assert _lock_version(werkzeug) is not None, (
            f"{werkzeug} steht nicht in uv.lock — dann entscheidet wieder die "
            "Aufloesung, welche Version das Gate faehrt"
        )


def test_kein_workflow_installiert_ein_gate_werkzeug_am_lock_vorbei() -> None:
    """Ein Inline-Pin ueberschreibt den Lock fuer genau einen Schritt.

    Das ist der Vorfall aus der CLAUDE.md, und er ist still: der Schritt laeuft
    gruen, nur eben mit einer anderen ruff-Version als jeder lokale Lauf.
    """
    muster = re.compile(rf"(--with|pip install)\s+({'|'.join(_GATE_WERKZEUGE)})\b")
    for workflow in sorted(_WORKFLOWS.glob("*.yml")):
        # Kommentare ausgenommen, damit ein erklaerender Hinweis auf den
        # frueheren Aufruf den Test nicht selbst ausloest.
        zeilen = [z for z in workflow.read_text().splitlines() if not z.lstrip().startswith("#")]
        treffer = [z.strip() for z in zeilen if muster.search(z)]
        assert not treffer, (
            f"{workflow.name} installiert ein Gate-Werkzeug an uv.lock vorbei ({treffer}). "
            "Ein solcher Aufruf gilt nur fuer diesen Schritt — lokaler Lauf und Gate "
            "fahren dann verschiedene Versionen."
        )


def test_der_scan_findet_ueberhaupt_etwas() -> None:
    """Sichert die Pruefung oben gegen leere Eingaben ab.

    Faende der Glob nichts, waere die Schleife leer und die Zusicherung
    trivialerweise wahr — gruen, ohne irgendetwas geprueft zu haben.
    """
    workflows = list(_WORKFLOWS.glob("*.yml"))
    assert len(workflows) >= 2, f"Workflow-Scan findet fast nichts: {workflows}"
    assert any("ruff check" in w.read_text() for w in workflows), (
        "kein Workflow ruft ruff auf — der Scan sucht am falschen Ort"
    )

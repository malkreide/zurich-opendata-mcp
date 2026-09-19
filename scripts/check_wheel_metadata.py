"""
Prüfen, dass das gebaute Wheel eine Kernmetadaten-Version trägt, welche die
in `publish.yml` gepinnte Publish-Action auch akzeptiert.

Der Fehlschlag, für den dieser Check existiert: Am 19.9.2026 scheiterte der
Release-Lauf von `v0.8.0` nicht an PyPI, sondern an der Vorabprüfung *in* der
Action:

    InvalidDistribution: Invalid distribution metadata:
    '2.5' is not a valid metadata version

Im Repo hatte sich nichts geändert. `[build-system] requires` nennt
`hatchling` ohne Obergrenze, `python -m build` holt beim Release also die
jeweils neuste — und `hatchling 1.32.3` schreibt `Metadata-Version: 2.5`, wo
`1.31.0` noch `2.4` schrieb (beides nachgebaut und abgelesen). Die gepinnte
Action `v1.14.1` bringt twine 6.1.0 mit und kennt 2.5 nicht. PyPI selbst
akzeptiert 2.5 sehr wohl: `hatchling 1.32.3` liegt dort genau damit.

Das ist dieselbe Klasse wie der 0.5.1-Defekt: Der Auslöser ist keine
Änderung hier, sondern eine Veröffentlichung von jemand anderem, und der
einzige Ort, an dem er sich zeigt, wird genau einmal pro Release betreten —
also zu spät. Deshalb läuft dieser Check im `fresh-install`-Job, der schon
ein Wheel mit freiem Resolve baut, auf jedem PR **und** wöchentlich.

Was er prüft: die Metadaten-Version des gebauten Wheels gegen das, was die in
`publish.yml` gepinnte Action-Fassung verträgt. Was er *nicht* prüft: ob die
Action-Fassung überhaupt noch aktuell ist — dafür gibt es Dependabot.

Fällt er, gibt es genau zwei richtige Antworten, und «das Backend
zurückpinnen» ist keine davon:

  1. Die Action auf eine Fassung heben, die die neue Metadaten-Version kennt,
     und die Tabelle unten ergänzen.
  2. Ist noch keine solche Fassung veröffentlicht: warten und das Release
     zurückhalten, statt ein Artefakt zu bauen, das am Upload scheitert.

Verwendung:
    python scripts/check_wheel_metadata.py [dist-Verzeichnis]   # exit 1 bei Drift

Bewusst nur Standardbibliothek: der Check läuft direkt nach `python -m build`,
bevor irgendetwas installiert ist.
"""

import email.parser
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUBLISH_WORKFLOW = ROOT / ".github/workflows/publish.yml"

# Welche Kernmetadaten-Version die jeweilige Action-Fassung akzeptiert —
# bestimmt durch die twine, die sie mitbringt, nicht durch PyPI.
#
# Diese Tabelle wird von Hand gepflegt, und das ist Absicht: Ein Eintrag ist
# eine Behauptung über fremde Software und gehört belegt, nicht geraten. Beim
# Anheben der Action die Release Notes lesen und die Zeile dazuschreiben.
ACTION_MAX_METADATA = {
    # twine 6.1.0 / packaging 25.0 — kennt Metadaten bis 2.4.
    "v1.14.1": (2, 4),
    # twine 7.0.0 — Release Notes: «This version will let them upload their
    # sdists and wheels containing core packaging metadata v2.5 to (Test)PyPI».
    "v1.14.2": (2, 5),
}

_PIN = re.compile(r"^\s*uses:\s*pypa/gh-action-pypi-publish@(\S+)\s*$", re.MULTILINE)


def pinned_action_version() -> str:
    """Die in `publish.yml` gepinnte Fassung der Publish-Action."""
    matches = _PIN.findall(PUBLISH_WORKFLOW.read_text(encoding="utf-8"))
    if not matches:
        raise SystemExit(
            f"{PUBLISH_WORKFLOW.relative_to(ROOT)} nennt kein "
            "`pypa/gh-action-pypi-publish@…` — wurde der Publish-Schritt umgebaut?"
        )
    if len(set(matches)) > 1:
        raise SystemExit(
            f"mehrere widersprüchliche Pins der Publish-Action: {sorted(set(matches))}"
        )
    return matches[0]


def wheel_metadata_version(wheel: pathlib.Path) -> str:
    """`Metadata-Version` aus dem `.dist-info/METADATA` des Wheels."""
    with zipfile.ZipFile(wheel) as archive:
        names = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise SystemExit(
                f"{wheel.name}: erwartet genau ein .dist-info/METADATA, gefunden {names}"
            )
        headers = email.parser.BytesParser().parsebytes(archive.read(names[0]), headersonly=True)
    value = headers.get("Metadata-Version")
    if not value:
        raise SystemExit(f"{wheel.name}: METADATA trägt keine `Metadata-Version`")
    return value.strip()


def as_tuple(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        raise SystemExit(f"unlesbare Metadaten-Version: {version!r}") from None


def main() -> None:
    dist = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist"
    wheels = sorted(dist.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"kein Wheel in {dist} — läuft dieser Check vor `python -m build`?")

    pin = pinned_action_version()
    supported = ACTION_MAX_METADATA.get(pin)
    if supported is None:
        raise SystemExit(
            f"pypa/gh-action-pypi-publish ist auf {pin} gepinnt, und diese Fassung steht "
            f"nicht in ACTION_MAX_METADATA ({', '.join(sorted(ACTION_MAX_METADATA))}).\n"
            "Nicht raten: die Release Notes der Action lesen, welche Kernmetadaten-Version "
            "ihre twine akzeptiert, und die Zeile hier ergaenzen."
        )

    for wheel in wheels:
        found = wheel_metadata_version(wheel)
        if as_tuple(found) > supported:
            raise SystemExit(
                f"DRIFT: {wheel.name} traegt Metadata-Version {found}, aber die gepinnte "
                f"Publish-Action {pin} akzeptiert hoechstens "
                f"{'.'.join(str(p) for p in supported)}.\n\n"
                "Das Release wuerde an der Vorabpruefung der Action scheitern, nicht an PyPI:\n"
                f"    InvalidDistribution: Invalid distribution metadata: '{found}' is not a "
                "valid metadata version\n\n"
                "Ausloeser ist fast immer ein neues Build-Backend, nicht eine Aenderung hier: "
                "`[build-system] requires` nennt `hatchling` ohne Obergrenze. Richtig ist, die "
                "Action zu heben und ACTION_MAX_METADATA zu ergaenzen — nicht, das Backend "
                "zurueckzupinnen."
            )
        print(
            f"OK: {wheel.name} — Metadata-Version {found}, Action {pin} akzeptiert bis "
            f"{'.'.join(str(p) for p in supported)}"
        )


if __name__ == "__main__":
    main()

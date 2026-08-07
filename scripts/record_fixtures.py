#!/usr/bin/env python3
"""Zeichnet die Unit-Test-Fixtures von der echten CKAN-Instanz auf.

    python scripts/record_fixtures.py

WARUM ES DIESES SKRIPT GIBT. Ein handgeschriebener Mock kodiert die Annahme
seines Autors und kann sie deshalb prinzipiell nicht widerlegen: Produktivcode
und Fixture stammen aus demselben Kopf, derselben Stunde, derselben Lektuere
der Doku. Wo beide irren, irren beide gleich, und die Suite bleibt gruen.

Aufgezeichnet werden die drei CKAN-Antworten, auf denen die Katalog-Tools
stehen: `group_list`, `group_show` und `package_search`. Die Auswahlregel je
Datei steht in `tests/fixtures/PROVENANCE.md` neben dem Abrufdatum — ohne Datum
ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht mehr zu
unterscheiden, weil die Datei gleich aussieht.

**Es sind Ausschnitte, keine Vollabzuege.** Eine Fixture belegt die Form der
Antwort und einen datierten Ausschnitt ihres Inhalts, nicht den Bestand.

`package_search` wird bewusst MIT explizitem `rows` aufgezeichnet und der
`count` daneben festgehalten: CKAN liefert ohne `rows` genau 10 Treffer,
unabhaengig davon, wie viele es gibt (gemessen: `q=verkehr` -> count 102,
results 10). Das ist der Gruendungsfall von Regel 1 des Skills
`mcp-data-fidelity`, und die Fixture soll beide Zahlen tragen, damit ein Test
sie auseinanderhalten kann.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

CKAN = "https://data.stadt-zuerich.ch/api/3/action"
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

SEARCH_TERM = "verkehr"
SEARCH_ROWS = 3
GROUP = "mobilitat"


def record() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(UTC).strftime("%Y-%m-%d")
    entries: list[dict] = []

    def write(name: str, payload: object, url: str, rule: str) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        (FIXTURES / name).write_text(text, encoding="utf-8")
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": rule,
                "bytes": len(text.encode("utf-8")),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
        print(f"ok  {name:<26} {len(text.encode('utf-8')):>7} B")

    def unwrap(resp: httpx.Response) -> object:
        body = resp.json()
        if not body.get("success"):
            raise SystemExit(f"{resp.request.url}: CKAN meldet success=false")
        return body["result"]

    with httpx.Client(timeout=90.0, follow_redirects=True) as c:
        # 1) Kategorien. Die Tools lesen name/title/package_count.
        r = c.get(f"{CKAN}/group_list", params={"all_fields": "true"})
        r.raise_for_status()
        groups = unwrap(r)
        if not isinstance(groups, list) or not groups:
            raise SystemExit("group_list: keine Gruppen — Antwortform geaendert?")
        write(
            "ckan_group_list.json",
            groups,
            f"{CKAN}/group_list?all_fields=true",
            f"vollstaendig, {len(groups)} Kategorien",
        )

        # 2) Eine einzelne Kategorie samt ihrer Pakete.
        r = c.get(f"{CKAN}/group_show", params={"id": GROUP, "include_datasets": "true"})
        r.raise_for_status()
        group = unwrap(r)
        packages = group.get("packages") or []
        # Auf drei Pakete kuerzen: eine Fixture muss lesbar bleiben, und die
        # Zahl steht in PROVENANCE.md. `package_count` bleibt der echte Wert —
        # sonst wuerde die Fixture stillschweigend behaupten, die Kategorie sei
        # kleiner, als sie ist.
        group["packages"] = packages[:3]
        write(
            "ckan_group_show.json",
            group,
            f"{CKAN}/group_show?id={GROUP}&include_datasets=true",
            f"Kategorie «{GROUP}»; `packages` auf die ersten 3 von "
            f"{len(packages)} gekuerzt, `package_count` unveraendert",
        )

        # 3) Volltextsuche MIT explizitem rows.
        params = {"q": SEARCH_TERM, "rows": str(SEARCH_ROWS), "sort": "score desc"}
        r = c.get(f"{CKAN}/package_search", params=params)
        r.raise_for_status()
        search = unwrap(r)
        if len(search.get("results", [])) > SEARCH_ROWS:
            raise SystemExit(
                f"package_search: {len(search['results'])} Treffer trotz "
                f"rows={SEARCH_ROWS} — der Parameter wirkt nicht mehr"
            )
        write(
            "ckan_package_search.json",
            search,
            f"{CKAN}/package_search?q={SEARCH_TERM}&rows={SEARCH_ROWS}",
            f"Suche «{SEARCH_TERM}» mit explizitem rows={SEARCH_ROWS}; "
            f"`count` ist der echte Gesamtbestand der Suche "
            f"({search.get('count')}), `results` sind {len(search.get('results', []))}",
        )

        # 4) Dieselbe Suche OHNE rows — der Gruendungsfall von Regel 1.
        r = c.get(f"{CKAN}/package_search", params={"q": SEARCH_TERM})
        r.raise_for_status()
        unfiltered = unwrap(r)
        write(
            "ckan_package_search_no_rows.json",
            {
                "count": unfiltered.get("count"),
                "returned": len(unfiltered.get("results", [])),
            },
            f"{CKAN}/package_search?q={SEARCH_TERM} (ohne rows)",
            "nur die beiden Zahlen: wie viele es gibt und wie viele ohne "
            "`rows` kommen. Der Beleg dafuer, dass das Weglassen des Parameters "
            "eine willkuerliche Teilmenge liefert und keine Vollmenge",
        )

    _write_provenance(recorded_at, entries)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return 0


def _write_provenance(recorded_at: str, entries: list[dict]) -> None:
    lines = [
        "# Herkunft der Fixtures",
        "",
        "**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{recorded_at}** von `{CKAN}`.",
        "",
        "Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht",
        "mehr zu unterscheiden — die Datei sieht gleich aus, und niemand weiss,",
        "ob sie den Stand von gestern zeigt oder den von vor drei",
        "Schema-Wechseln.",
        "",
        "**Es sind Ausschnitte, keine Vollabzuege.** Die Auswahlregel steht je",
        "Datei dabei. Wo gekuerzt wurde, bleiben die Zaehlfelder (`count`,",
        "`package_count`) auf dem echten Wert — eine Fixture, die stillschweigend",
        "behauptet, der Bestand sei kleiner, waere genau der Fehler, gegen den",
        "diese Aufzeichnung angeht.",
        "",
    ]
    for e in entries:
        lines += [
            f"## `{e['name']}`",
            "",
            f"- **Quelle:** `{e['url']}`",
            f"- **Aufgezeichnet:** {recorded_at}",
            f"- **Auswahl:** {e['rule']}",
            f"- **Groesse:** {e['bytes']} B",
            f"- **SHA-256:** `{e['sha256']}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(record())
    except httpx.HTTPError as exc:
        print(f"FEHLER: Quelle nicht erreichbar: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

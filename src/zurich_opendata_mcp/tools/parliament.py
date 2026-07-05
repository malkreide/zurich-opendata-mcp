"""Paris API tools: Gemeinderat business and members."""

from __future__ import annotations

from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..clients.paris import (
    cql_escape,
    paris_extract_text,
    paris_get_num_hits,
    paris_search,
)
from ..config import PARIS_NAMESPACES, OutputFormat
from ..formatters import FORMAT_FIELD_DESC, handle_api_error, json_out


def _build_geschaeft_cql(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    department: str | None = None,
) -> str:
    # year_* are int-validated by Pydantic and cannot inject; the string
    # fields go through cql_escape() to neutralise quote-closing payloads.
    cql_parts = [f'Titel any "{cql_escape(query)}"']
    if year_from:
        cql_parts.append(f'beginn_start > "{year_from}-01-01 00:00:00"')
    if year_to:
        cql_parts.append(f'beginn_start < "{year_to + 1}-01-01 00:00:00"')
    if department:
        cql_parts.append(f'Departement any "{cql_escape(department)}"')
    return " AND ".join(cql_parts) + " sortBy beginn_start/sort.descending"


def _build_behoerdenmandat_cql(
    commission: str,
    active_only: bool = True,
    name: str | None = None,
) -> str:
    cql_parts = [f'gremium any "{cql_escape(commission)}"']
    if active_only:
        # Paris-API idiom for "no end date set" — sentinel literal, no escape needed.
        cql_parts.append('Dauer_end > "9999-12-31 00:00:00"')
    if name:
        cql_parts.append(f'Name any "{cql_escape(name)}"')
    return " AND ".join(cql_parts)


def _geschaeft_record(geschaeft, ns) -> dict:
    """Normalise one Paris Geschaeft XML element into a plain record."""
    gr_nr = paris_extract_text(geschaeft.find("g:GRNr", ns), "?")
    erst_el = geschaeft.find("g:Erstunterzeichner/g:KontaktGremium", ns)
    if erst_el is not None:
        erst_name = paris_extract_text(erst_el.find("g:n", ns), "")
        erst_partei = paris_extract_text(erst_el.find("g:Partei", ns), "")
        erstunterzeichner = f"{erst_name} ({erst_partei})" if erst_partei else erst_name
    else:
        erstunterzeichner = ""
    return {
        "gr_nr": gr_nr,
        "titel": paris_extract_text(geschaeft.find("g:Titel", ns), "Ohne Titel"),
        "art": paris_extract_text(geschaeft.find("g:Geschaeftsart", ns), "?"),
        "status": paris_extract_text(geschaeft.find("g:Geschaeftsstatus", ns), "?"),
        "datum": paris_extract_text(geschaeft.find("g:Beginn/g:Text", ns), "?"),
        "departement": paris_extract_text(
            geschaeft.find("g:FederfuehrendesDepartement/g:Departement/g:n", ns), ""
        ),
        "erstunterzeichner": erstunterzeichner,
        "link": f"https://www.gemeinderat-zuerich.ch/geschaefte/{gr_nr.replace('/', '-')}",
    }


def _behoerdenmandat_record(bm, ns) -> dict:
    """Normalise one Behoerdenmandat XML element into a plain record."""
    return {
        "name": paris_extract_text(bm.find("b:n", ns), "?"),
        "vorname": paris_extract_text(bm.find("b:Vorname", ns), ""),
        "gremium": paris_extract_text(bm.find("b:Gremium", ns), "?"),
        "funktion": paris_extract_text(bm.find("b:Funktion", ns), "Mitglied"),
        "partei": paris_extract_text(bm.find("b:Partei", ns), ""),
        "dauer": paris_extract_text(bm.find("b:Dauer/b:Text", ns), "?"),
    }


def _kontakt_record(kontakt, ns) -> dict:
    """Normalise one Kontakt XML element into a plain record."""
    return {
        "name_vorname": paris_extract_text(kontakt.find("k:NameVorname", ns), "?"),
        "partei": paris_extract_text(kontakt.find("k:Partei", ns), ""),
        "wahlkreis": paris_extract_text(kontakt.find("k:Wahlkreis", ns), ""),
        "mandate": [
            {
                "gremium": paris_extract_text(m.find("k:GremiumName", ns), "?"),
                "funktion": paris_extract_text(m.find("k:Funktion", ns), ""),
            }
            for m in kontakt.findall("k:Behoerdenmandat/k:Behoerdenmandat", ns)
        ],
    }


def _build_kontakt_cql(
    name: str | None = None,
    party: str | None = None,
    active_only: bool = True,
) -> str:
    cql_parts: list[str] = []
    if name:
        cql_parts.append(f'NameVorname any "{cql_escape(name)}"')
    if party:
        cql_parts.append(f'Partei any "{cql_escape(party)}"')
    if active_only:
        cql_parts.append('AktivesRatsmitglied = "true"')
    if not cql_parts:
        cql_parts.append('AktivesRatsmitglied = "true"')
    return " AND ".join(cql_parts)


class ParliamentSearchInput(BaseModel):
    """Input für die Geschäftssuche im Gemeinderat."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description=(
            "Suchbegriff für Gemeinderatsgeschäfte. Wird im Titel gesucht. "
            "Beispiele: 'Schule', 'Digitalisierung', 'Klimaschutz', 'Budget'"
        ),
        min_length=1,
        max_length=500,
    )
    year_from: int | None = Field(
        default=None,
        description="Geschäfte ab diesem Jahr filtern, z.B. 2020",
        ge=1990,
        le=2030,
    )
    year_to: int | None = Field(
        default=None,
        description="Geschäfte bis zu diesem Jahr filtern, z.B. 2025",
        ge=1990,
        le=2030,
    )
    department: str | None = Field(
        default=None,
        description=(
            "Nach zuständigem Departement filtern. Beispiele: 'Schul- und Sportdepartement', 'Finanzdepartement'"
        ),
    )
    max_results: int = Field(default=10, description="Maximale Anzahl Ergebnisse", ge=1, le=50)
    format: OutputFormat = Field(default="markdown", description=FORMAT_FIELD_DESC)


@mcp.tool(
    name="zurich_parliament_search",
    annotations=ToolAnnotations(
        title="Gemeinderatsgeschäfte suchen",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def zurich_parliament_search(params: ParliamentSearchInput) -> str:
    """Durchsucht die Geschäfte des Gemeinderats der Stadt Zürich (Paris API).

    Findet Interpellationen, Motionen, Postulate, Anfragen und weitere
    parlamentarische Vorstösse. Besonders nützlich für Schulthemen, da viele
    Geschäfte das SSD (Schul- und Sportdepartement) betreffen.

    Returns:
        Markdown-Liste der gefundenen Gemeinderatsgeschäfte
    """
    try:
        cql = _build_geschaeft_cql(
            query=params.query,
            year_from=params.year_from,
            year_to=params.year_to,
            department=params.department,
        )

        root = await paris_search("geschaeft", cql, max_results=params.max_results)
        num_hits = paris_get_num_hits(root)

        ns = PARIS_NAMESPACES
        hits = root.findall("sr:Hit", ns)

        if not hits:
            return f"Keine Gemeinderatsgeschäfte gefunden für '{params.query}'."

        records = []
        for hit in hits:
            geschaeft = hit.find("g:Geschaeft", ns)
            if geschaeft is None:
                continue
            records.append(_geschaeft_record(geschaeft, ns))

        if params.format == "json":
            return json_out(
                {
                    "query": params.query,
                    "total": num_hits,
                    "count": len(records),
                    "geschaefte": records,
                }
            )

        lines = [
            f"## Gemeinderatsgeschäfte: '{params.query}'",
            f"**{num_hits} Treffer** (zeige {len(hits)})\n",
        ]

        for rec in records:
            lines.append(f"### {rec['gr_nr']}: {rec['titel']}")
            lines.append(f"- **Art**: {rec['art']}")
            lines.append(f"- **Status**: {rec['status']}")
            lines.append(f"- **Datum**: {rec['datum']}")
            if rec["departement"]:
                lines.append(f"- **Departement**: {rec['departement']}")
            if rec["erstunterzeichner"]:
                lines.append(f"- **Eingereicht von**: {rec['erstunterzeichner']}")
            lines.append(f"- **Link**: {rec['link']}")
            lines.append("")

        if num_hits > len(hits):
            lines.append(f"*→ {num_hits - len(hits)} weitere Treffer vorhanden*")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Geschäftssuche Gemeinderat")


class ParliamentMembersInput(BaseModel):
    """Input für die Mitgliedersuche im Gemeinderat."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(
        default=None,
        description="Name oder Teilname des Ratsmitglieds, z.B. 'Marti' oder 'Peter'",
    )
    party: str | None = Field(
        default=None,
        description="Parteiname, z.B. 'SP', 'SVP', 'Grüne', 'FDP', 'GLP', 'AL', 'Mitte'",
    )
    commission: str | None = Field(
        default=None,
        description=(
            "Kommissionsname, z.B. 'GPK', 'RPK', 'Bildungsrat'. Sucht aktive Mitglieder der genannten Kommission."
        ),
    )
    active_only: bool = Field(
        default=True,
        description="Nur aktive Ratsmitglieder anzeigen",
    )
    max_results: int = Field(default=20, description="Maximale Anzahl Ergebnisse", ge=1, le=100)
    format: OutputFormat = Field(default="markdown", description=FORMAT_FIELD_DESC)


@mcp.tool(
    name="zurich_parliament_members",
    annotations=ToolAnnotations(
        title="Gemeinderatsmitglieder suchen",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def zurich_parliament_members(params: ParliamentMembersInput) -> str:
    """Sucht Mitglieder des Gemeinderats der Stadt Zürich.

    Ermöglicht die Suche nach Name, Partei und Kommissionszugehörigkeit.
    Zeigt aktuelle Mandate und Funktionen.

    Returns:
        Markdown-Liste der gefundenen Ratsmitglieder
    """
    try:
        ns = PARIS_NAMESPACES

        if params.commission:
            # Search via Behoerdenmandat index for commission members
            cql = _build_behoerdenmandat_cql(
                commission=params.commission,
                active_only=params.active_only,
                name=params.name,
            )

            root = await paris_search("behoerdenmandat", cql, max_results=params.max_results)
            num_hits = paris_get_num_hits(root)
            hits = root.findall("sr:Hit", ns)

            if not hits:
                return f"Keine Mitglieder gefunden für Kommission '{params.commission}'."

            records = []
            for hit in hits:
                bm = hit.find("b:Behordenmandat", ns)
                if bm is None:
                    continue
                records.append(_behoerdenmandat_record(bm, ns))

            if params.format == "json":
                return json_out(
                    {
                        "commission": params.commission,
                        "total": num_hits,
                        "count": len(records),
                        "members": records,
                    }
                )

            lines = [
                f"## Kommission: {params.commission}",
                f"**{num_hits} Mitglieder**\n",
            ]

            for rec in records:
                name, vorname, partei = rec["name"], rec["vorname"], rec["partei"]
                dauer_text = rec["dauer"]

                display = f"**{vorname} {name}**" if vorname else f"**{name}**"
                if partei:
                    display += f" ({partei})"
                display += f" – {rec['funktion']}, {rec['gremium']}"
                display += f" (seit {dauer_text.split(' -')[0].strip()})" if " -" in dauer_text else ""

                lines.append(f"- {display}")

            return "\n".join(lines)

        else:
            # Search via Kontakt index
            cql = _build_kontakt_cql(
                name=params.name,
                party=params.party,
                active_only=params.active_only,
            )

            root = await paris_search("kontakt", cql, max_results=params.max_results)
            num_hits = paris_get_num_hits(root)
            hits = root.findall("sr:Hit", ns)

            if not hits:
                return "Keine Ratsmitglieder gefunden."

            records = []
            for hit in hits:
                kontakt = hit.find("k:Kontakt", ns)
                if kontakt is None:
                    continue
                records.append(_kontakt_record(kontakt, ns))

            if params.format == "json":
                return json_out(
                    {"total": num_hits, "count": len(records), "members": records}
                )

            lines = [
                "## Gemeinderatsmitglieder",
                f"**{num_hits} Treffer** (zeige {len(hits)})\n",
            ]

            for rec in records:
                display = f"**{rec['name_vorname']}**"
                if rec["partei"]:
                    display += f" ({rec['partei']})"
                if rec["wahlkreis"]:
                    display += f" – Wahlkreis {rec['wahlkreis']}"

                if rec["mandate"]:
                    mandate_list = [
                        m["gremium"] + (f" ({m['funktion']})" if m["funktion"] else "")
                        for m in rec["mandate"][:5]
                    ]
                    display += f"\n  - Mandate: {', '.join(mandate_list)}"

                lines.append(f"- {display}")
                lines.append("")

            return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Mitgliedersuche Gemeinderat")

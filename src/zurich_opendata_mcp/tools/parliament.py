"""Paris API tools: Gemeinderat business and members."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..clients.paris import (
    cql_escape,
    paris_extract_text,
    paris_get_num_hits,
    paris_search,
)
from ..config import PARIS_NAMESPACES
from ..formatters import handle_api_error


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


@mcp.tool(
    name="zurich_parliament_search",
    annotations={
        "title": "Gemeinderatsgeschäfte suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
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

        lines = [
            f"## Gemeinderatsgeschäfte: '{params.query}'",
            f"**{num_hits} Treffer** (zeige {len(hits)})\n",
        ]

        for hit in hits:
            geschaeft = hit.find("g:Geschaeft", ns)
            if geschaeft is None:
                continue

            gr_nr = paris_extract_text(geschaeft.find("g:GRNr", ns), "?")
            titel = paris_extract_text(geschaeft.find("g:Titel", ns), "Ohne Titel")
            art = paris_extract_text(geschaeft.find("g:Geschaeftsart", ns), "?")
            status = paris_extract_text(geschaeft.find("g:Geschaeftsstatus", ns), "?")
            dept_el = geschaeft.find("g:FederfuehrendesDepartement/g:Departement/g:n", ns)
            dept = paris_extract_text(dept_el, "")

            beginn_el = geschaeft.find("g:Beginn/g:Text", ns)
            datum = paris_extract_text(beginn_el, "?")

            # Erstunterzeichner
            erst_el = geschaeft.find("g:Erstunterzeichner/g:KontaktGremium", ns)
            if erst_el is not None:
                erst_name = paris_extract_text(erst_el.find("g:n", ns), "")
                erst_partei = paris_extract_text(erst_el.find("g:Partei", ns), "")
                erstunterzeichner = f"{erst_name} ({erst_partei})" if erst_partei else erst_name
            else:
                erstunterzeichner = ""

            lines.append(f"### {gr_nr}: {titel}")
            lines.append(f"- **Art**: {art}")
            lines.append(f"- **Status**: {status}")
            lines.append(f"- **Datum**: {datum}")
            if dept:
                lines.append(f"- **Departement**: {dept}")
            if erstunterzeichner:
                lines.append(f"- **Eingereicht von**: {erstunterzeichner}")
            lines.append(f"- **Link**: https://www.gemeinderat-zuerich.ch/geschaefte/{gr_nr.replace('/', '-')}")
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


@mcp.tool(
    name="zurich_parliament_members",
    annotations={
        "title": "Gemeinderatsmitglieder suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
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

            lines = [
                f"## Kommission: {params.commission}",
                f"**{num_hits} Mitglieder**\n",
            ]

            for hit in hits:
                bm = hit.find("b:Behordenmandat", ns)
                if bm is None:
                    continue
                name = paris_extract_text(bm.find("b:n", ns), "?")
                vorname = paris_extract_text(bm.find("b:Vorname", ns), "")
                gremium = paris_extract_text(bm.find("b:Gremium", ns), "?")
                funktion = paris_extract_text(bm.find("b:Funktion", ns), "Mitglied")
                partei = paris_extract_text(bm.find("b:Partei", ns), "")
                dauer_text = paris_extract_text(bm.find("b:Dauer/b:Text", ns), "?")

                display = f"**{vorname} {name}**" if vorname else f"**{name}**"
                if partei:
                    display += f" ({partei})"
                display += f" – {funktion}, {gremium}"
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

            lines = [
                "## Gemeinderatsmitglieder",
                f"**{num_hits} Treffer** (zeige {len(hits)})\n",
            ]

            for hit in hits:
                kontakt = hit.find("k:Kontakt", ns)
                if kontakt is None:
                    continue

                name_vn = paris_extract_text(kontakt.find("k:NameVorname", ns), "?")
                partei = paris_extract_text(kontakt.find("k:Partei", ns), "")
                wahlkreis = paris_extract_text(kontakt.find("k:Wahlkreis", ns), "")

                display = f"**{name_vn}**"
                if partei:
                    display += f" ({partei})"
                if wahlkreis:
                    display += f" – Wahlkreis {wahlkreis}"

                # Mandate
                mandate = kontakt.findall("k:Behoerdenmandat/k:Behoerdenmandat", ns)
                if mandate:
                    mandate_list = []
                    for m in mandate[:5]:
                        gremium = paris_extract_text(m.find("k:GremiumName", ns), "?")
                        funktion = paris_extract_text(m.find("k:Funktion", ns), "")
                        mandate_list.append(f"{gremium}" + (f" ({funktion})" if funktion else ""))
                    display += f"\n  - Mandate: {', '.join(mandate_list)}"

                lines.append(f"- {display}")
                lines.append("")

            return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Mitgliedersuche Gemeinderat")

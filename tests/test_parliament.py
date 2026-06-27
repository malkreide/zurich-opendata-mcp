"""respx-backed unit tests for tools/parliament.py (audit M-7 continuation).

These exercise the full HTTP round-trip — CQL build → Paris XML response →
Markdown rendering — without touching the network. They complement the
CQL-injection builder tests in test_server.py by covering the rendering and
error branches end-to-end (audit rerun fix-order #2, immediately after H-2).
"""

from __future__ import annotations

import httpx
import respx

from zurich_opendata_mcp.config import PARIS_API_URL
from zurich_opendata_mcp.tools.parliament import (
    ParliamentMembersInput,
    ParliamentSearchInput,
    zurich_parliament_members,
    zurich_parliament_search,
)

_NS_DECL = (
    'xmlns:sr="http://www.cmiag.ch/cdws/searchDetailResponse" '
    'xmlns:g="http://www.cmiag.ch/cdws/Geschaeft" '
    'xmlns:k="http://www.cmiag.ch/cdws/Kontakt" '
    'xmlns:b="http://www.cmiag.ch/cdws/Behoerdenmandat"'
)


def _response(num_hits: int, hits_xml: str) -> httpx.Response:
    body = (
        f'<sr:searchDetailResponse {_NS_DECL} numHits="{num_hits}">'
        f"{hits_xml}"
        "</sr:searchDetailResponse>"
    )
    return httpx.Response(200, content=body.encode("utf-8"))


def _url(index: str) -> str:
    return f"{PARIS_API_URL}/{index}/searchdetails"


# ─── Geschäftssuche ──────────────────────────────────────────────────────────

_GESCHAEFT_HIT = """
<sr:Hit>
  <g:Geschaeft>
    <g:GRNr>2023/123</g:GRNr>
    <g:Titel>Schulraumplanung Test</g:Titel>
    <g:Geschaeftsart>Motion</g:Geschaeftsart>
    <g:Geschaeftsstatus>hängig</g:Geschaeftsstatus>
    <g:FederfuehrendesDepartement><g:Departement>
      <g:n>Schul- und Sportdepartement</g:n>
    </g:Departement></g:FederfuehrendesDepartement>
    <g:Beginn><g:Text>2023-05-01</g:Text></g:Beginn>
    <g:Erstunterzeichner><g:KontaktGremium>
      <g:n>Anna Muster</g:n>
      <g:Partei>SP</g:Partei>
    </g:KontaktGremium></g:Erstunterzeichner>
  </g:Geschaeft>
</sr:Hit>
"""


@respx.mock
async def test_parliament_search_renders_hit():
    route = respx.get(_url("geschaeft")).mock(
        return_value=_response(3, _GESCHAEFT_HIT)
    )

    result = await zurich_parliament_search(
        ParliamentSearchInput(query="Schule", max_results=10)
    )

    assert route.called
    assert "## Gemeinderatsgeschäfte: 'Schule'" in result
    assert "2023/123: Schulraumplanung Test" in result
    assert "**Art**: Motion" in result
    assert "**Status**: hängig" in result
    assert "Schul- und Sportdepartement" in result
    assert "Anna Muster (SP)" in result
    # GRNr slashes become dashes in the deep-link.
    assert "/geschaefte/2023-123" in result
    # numHits (3) > shown (1) → pagination hint.
    assert "2 weitere Treffer" in result


@respx.mock
async def test_parliament_search_empty():
    respx.get(_url("geschaeft")).mock(return_value=_response(0, ""))

    result = await zurich_parliament_search(ParliamentSearchInput(query="xyzzy"))

    assert "Keine Gemeinderatsgeschäfte gefunden für 'xyzzy'." == result


@respx.mock
async def test_parliament_search_http_error():
    respx.get(_url("geschaeft")).mock(return_value=httpx.Response(500))

    result = await zurich_parliament_search(ParliamentSearchInput(query="Schule"))

    assert "Fehler bei Geschäftssuche Gemeinderat" in result
    assert "500" in result


# ─── Mitglieder via Kontakt-Index ────────────────────────────────────────────

_KONTAKT_HIT = """
<sr:Hit>
  <k:Kontakt>
    <k:NameVorname>Muster Anna</k:NameVorname>
    <k:Partei>SP</k:Partei>
    <k:Wahlkreis>1+2</k:Wahlkreis>
    <k:Behoerdenmandat><k:Behoerdenmandat>
      <k:GremiumName>GPK</k:GremiumName>
      <k:Funktion>Mitglied</k:Funktion>
    </k:Behoerdenmandat></k:Behoerdenmandat>
  </k:Kontakt>
</sr:Hit>
"""


@respx.mock
async def test_parliament_members_kontakt_index():
    kontakt = respx.get(_url("kontakt")).mock(return_value=_response(1, _KONTAKT_HIT))
    behoerden = respx.get(_url("behoerdenmandat")).mock(return_value=_response(0, ""))

    result = await zurich_parliament_members(
        ParliamentMembersInput(party="SP", active_only=True)
    )

    # No commission → goes through the Kontakt index, not Behoerdenmandat.
    assert kontakt.called
    assert not behoerden.called
    assert "## Gemeinderatsmitglieder" in result
    assert "**Muster Anna** (SP)" in result
    assert "Wahlkreis 1+2" in result
    assert "Mandate: GPK (Mitglied)" in result


# ─── Mitglieder via Behoerdenmandat-Index (commission) ───────────────────────

_BEHOERDEN_HIT = """
<sr:Hit>
  <b:Behordenmandat>
    <b:n>Muster</b:n>
    <b:Vorname>Anna</b:Vorname>
    <b:Gremium>GPK</b:Gremium>
    <b:Funktion>Präsidentin</b:Funktion>
    <b:Partei>SP</b:Partei>
    <b:Dauer><b:Text>2022-05-01 - </b:Text></b:Dauer>
  </b:Behordenmandat>
</sr:Hit>
"""


@respx.mock
async def test_parliament_members_commission_index():
    kontakt = respx.get(_url("kontakt")).mock(return_value=_response(0, ""))
    behoerden = respx.get(_url("behoerdenmandat")).mock(
        return_value=_response(1, _BEHOERDEN_HIT)
    )

    result = await zurich_parliament_members(
        ParliamentMembersInput(commission="GPK")
    )

    # commission set → Behoerdenmandat index, not Kontakt.
    assert behoerden.called
    assert not kontakt.called
    assert "## Kommission: GPK" in result
    assert "**Anna Muster** (SP)" in result
    assert "Präsidentin, GPK" in result
    assert "(seit 2022-05-01)" in result


@respx.mock
async def test_parliament_members_empty():
    respx.get(_url("kontakt")).mock(return_value=_response(0, ""))

    result = await zurich_parliament_members(ParliamentMembersInput())

    assert "Keine Ratsmitglieder gefunden." == result


# ─── Coverage: branch + error paths ──────────────────────────────────────────

from zurich_opendata_mcp.tools.parliament import _build_kontakt_cql  # noqa: E402

# A Geschaeft hit with no Erstunterzeichner element (else-branch), plus an
# empty Hit with no g:Geschaeft (continue-branch).
_GESCHAEFT_NO_ERST = """
<sr:Hit></sr:Hit>
<sr:Hit>
  <g:Geschaeft>
    <g:GRNr>2024/9</g:GRNr>
    <g:Titel>Ohne Erstunterzeichner</g:Titel>
    <g:Geschaeftsart>Postulat</g:Geschaeftsart>
    <g:Geschaeftsstatus>erledigt</g:Geschaeftsstatus>
  </g:Geschaeft>
</sr:Hit>
"""


def test_build_kontakt_cql_empty_falls_back_to_active_filter():
    # No name/party and active_only=False → still emits the active sentinel.
    assert _build_kontakt_cql(active_only=False) == 'AktivesRatsmitglied = "true"'


@respx.mock
async def test_parliament_search_skips_empty_hit_and_missing_signer():
    respx.get(_url("geschaeft")).mock(return_value=_response(2, _GESCHAEFT_NO_ERST))

    result = await zurich_parliament_search(ParliamentSearchInput(query="x"))

    assert "2024/9: Ohne Erstunterzeichner" in result
    # The signer line is omitted when Erstunterzeichner is absent.
    assert "Eingereicht von" not in result


@respx.mock
async def test_parliament_members_commission_empty():
    respx.get(_url("behoerdenmandat")).mock(return_value=_response(0, ""))

    result = await zurich_parliament_members(
        ParliamentMembersInput(commission="GPK")
    )

    assert "Keine Mitglieder gefunden für Kommission 'GPK'." == result


@respx.mock
async def test_parliament_members_commission_skips_empty_hit():
    # Hit without b:Behordenmandat → continue; numHits keeps the section header.
    respx.get(_url("behoerdenmandat")).mock(
        return_value=_response(1, "<sr:Hit></sr:Hit>")
    )

    result = await zurich_parliament_members(
        ParliamentMembersInput(commission="GPK")
    )

    assert "## Kommission: GPK" in result


@respx.mock
async def test_parliament_members_kontakt_skips_empty_hit():
    # Hit without k:Kontakt → continue.
    respx.get(_url("kontakt")).mock(return_value=_response(1, "<sr:Hit></sr:Hit>"))

    result = await zurich_parliament_members(ParliamentMembersInput(party="SP"))

    assert "## Gemeinderatsmitglieder" in result


@respx.mock
async def test_parliament_members_error_path():
    respx.get(_url("kontakt")).mock(return_value=httpx.Response(500))

    result = await zurich_parliament_members(ParliamentMembersInput())

    assert "Fehler bei Mitgliedersuche Gemeinderat" in result

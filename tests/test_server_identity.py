"""SEP-2575: was der Server ueber sich selbst sagt, und wo.

Spec `2026-07-28` streicht `initialize`. Damit faellt die eine Stelle weg, an
der eine Verbindung bisher einmalig `serverInfo` und `instructions` bekam, und
beides wandert an zwei neue Orte:

* **Identitaet** in das `_meta` JEDES Resultats, unter dem Schluessel
  `io.modelcontextprotocol/serverInfo`. Nicht mehr pro Verbindung, sondern pro
  Antwort — weil es in der modernen Aera keine Verbindung mehr gibt, die etwas
  tragen koennte.
* **Anleitung** in `server/discover`, die einzige Stelle, an der ein
  zustandsloser Client sie noch abholen kann.

Gemessen ueber eine echte `Client`-Verbindung, nicht durch Ruecklesen der
Konstanten aus `app.py`: ein Blick ins Modul waere auch dann gruen, wenn das
Argument am `MCPServer`-Konstruktor verlorenginge. Genau das war der Zustand
vorher — `name` kam an, `version` war nie gesetzt.

Beide Aeren werden geprueft. Die Felder sind kein Novum von `2026-07-28`, der
Handshake trug sie auch schon; was neu ist, ist ihr Gewicht. Ein Server, der
sie nur in einer Aera fuellt, waere trotzdem falsch.
"""

from __future__ import annotations

import re

from mcp import Client
from mcp.server.mcpserver import MCPServer

from zurich_opendata_mcp.app import (
    SERVER_DESCRIPTION,
    SERVER_INSTRUCTIONS,
    SERVER_TITLE,
)
from zurich_opendata_mcp.config import PACKAGE_VERSION, REPO_URL

# Der `_meta`-Schluessel aus der Spec. Woertlich hier, nicht aus dem SDK
# importiert: faellt der Test, weil das SDK die Konstante umbenennt, ist das
# eine Spec-Frage und keine Importfrage.
SERVER_INFO_META_KEY = "io.modelcontextprotocol/serverInfo"


def mcp_server() -> MCPServer:
    """Die Serverinstanz, wie `server.py` sie ausliefert.

    Import in der Funktion, damit die Tool-Registrierung als Seiteneffekt des
    `server`-Imports nicht an der Sammelreihenfolge der Suite haengt.
    """
    from zurich_opendata_mcp.server import mcp

    return mcp


async def test_die_identitaet_traegt_eine_version() -> None:
    """Der lasttragende Teil: `version` war leer und ist es nicht mehr.

    `MCPServer` ohne `version=` meldet `""` — das SDK setzt nichts ein. Auf
    dem Draht ist das keine Auskunft, sondern eine halbe.
    """
    async with Client(mcp_server()) as client:
        info = client.server_info

    assert info is not None
    assert info.version == PACKAGE_VERSION
    assert info.version, "leere Version: der Aufrufer erfaehrt nicht, welche Fassung antwortet"


async def test_ein_server_ohne_identitaet_meldet_eine_leere_version() -> None:
    """Negativkontrolle: gleiches SDK, gleicher Client, kein `version=`.

    Faengt den Tag ab, an dem das SDK selbst eine Version einsetzt — dann
    prueft der Test oben naemlich nicht mehr, dass wir sie setzen.
    """
    async with Client(MCPServer("kontrolle")) as client:
        info = client.server_info

    assert info is not None
    assert info.version == ""
    assert info.title is None
    assert info.website_url is None


async def test_die_identitaet_steht_im_meta_eines_gewoehnlichen_resultats() -> None:
    """Der Stempel, nicht das Handshake-Feld.

    `server/discover` liefert `supportedVersions`, `capabilities` und
    `instructions` — aber kein `serverInfo`. In der modernen Aera erfaehrt ein
    Client die Identitaet ausschliesslich ueber diesen `_meta`-Stempel, den
    jedes Resultat traegt. Deshalb wird er an `tools/list` gemessen und nicht
    am Verbindungsaufbau.
    """
    async with Client(mcp_server()) as client:
        assert client.protocol_version == "2026-07-28"
        result = await client.list_tools()

    stamp = (result.meta or {}).get(SERVER_INFO_META_KEY)
    assert stamp is not None, f"kein {SERVER_INFO_META_KEY} im _meta von tools/list"
    assert stamp["name"] == "zurich_opendata_mcp"
    assert stamp["version"] == PACKAGE_VERSION
    assert stamp["title"] == SERVER_TITLE
    assert stamp["description"] == SERVER_DESCRIPTION
    # Wire-Schreibweise, camelCase — nicht `website_url`.
    assert stamp["websiteUrl"] == REPO_URL


async def test_die_handshake_aera_bekommt_dieselbe_identitaet() -> None:
    """Ein Server, der sich nur einer der beiden Aeren vorstellt, ist falsch."""
    async with Client(mcp_server(), mode="legacy") as client:
        assert client.protocol_version == "2025-11-25"
        info = client.server_info

    assert info is not None
    assert (info.name, info.version, info.title) == (
        "zurich_opendata_mcp",
        PACKAGE_VERSION,
        SERVER_TITLE,
    )
    assert info.website_url == REPO_URL


async def test_die_anleitung_erreicht_den_client() -> None:
    """`instructions` war `None` — in der modernen Aera heisst das: nichts.

    Ohne `initialize` ist `server/discover` die einzige Stelle, an der ein
    Client sie noch bekommt.
    """
    async with Client(mcp_server()) as client:
        assert client.instructions == SERVER_INSTRUCTIONS

    async with Client(MCPServer("kontrolle")) as client:
        assert client.instructions is None


def test_die_anleitung_nennt_nur_tools_die_es_gibt() -> None:
    """Drift-Wache auf dem Text selbst.

    Die Anleitung nennt Tools beim Namen — den dreistufigen Einstieg und die
    drei veralteten Aliase. Wird eines davon umbenannt oder entfernt, schickt
    der Server jedem Client eine Anleitung auf nicht existierende Werkzeuge.
    Das faellt sonst nirgends auf: kein Test ruft die Anleitung auf, und die
    Tool-Zahl bliebe gleich.
    """
    from zurich_opendata_mcp.server import mcp

    registriert = {tool.name for tool in mcp._tool_manager.list_tools()}
    # Alles in Backticks, das wie ein Tool-Name aussieht — Suffix-Muster wie
    # `zurich_strb_*` sind ausgenommen, sie benennen eine Familie.
    genannt = {
        name
        for name in re.findall(r"`([a-z][a-z0-9_]+)`", SERVER_INSTRUCTIONS)
        if not name.endswith("_")
    }
    assert genannt, "die Anleitung nennt gar kein Tool — dann prueft dieser Test nichts"
    fehlend = sorted(genannt - registriert)
    assert not fehlend, f"die Anleitung nennt nicht registrierte Tools: {fehlend}"


def test_die_anleitung_bleibt_kurz() -> None:
    """Sichert die Richtung, nicht die Zahl.

    Der Text landet im Kontextfenster jedes Clients, der `server/discover`
    aufruft. Waechst er zur zweiten README, ist der Zweck verfehlt.
    """
    assert len(SERVER_INSTRUCTIONS) < 1200, len(SERVER_INSTRUCTIONS)


async def test_die_werkzeugreihenfolge_ist_die_registrierungsreihenfolge() -> None:
    """Spec `2026-07-28`, Minor #3: `tools/list` SOLL deterministisch sortieren.

    Erfuellt ueber die Einfuegereihenfolge des `ToolManager`-Dicts, die aus der
    Importreihenfolge in `server.py` folgt und damit im Quelltext festliegt.

    Was dieser Test faengt: eine SDK-Aenderung, die auf der Handler-Ebene
    umsortiert oder aus einem Set liefert. Was er NICHT zeigt: Stabilitaet
    ueber Prozessgrenzen — dafuer muesste er zweimal starten. Die zweite
    Zusicherung haelt fest, dass die Reihenfolge nicht zufaellig alphabetisch
    ist; sonst waere der Test auch gegen ein sortierendes SDK gruen.
    """
    from zurich_opendata_mcp.server import mcp

    registrierung = list(mcp._tool_manager._tools)
    async with Client(mcp) as client:
        result = await client.list_tools()

    assert [tool.name for tool in result.tools] == registrierung
    assert registrierung != sorted(registrierung), (
        "die Registrierungsreihenfolge ist zufaellig alphabetisch — dann kann "
        "dieser Test ein sortierendes SDK nicht mehr von einem "
        "reihenfolgetreuen unterscheiden"
    )

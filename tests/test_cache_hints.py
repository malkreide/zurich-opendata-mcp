"""SEP-2549: die auflistenden Methoden muessen einen Frischehinweis tragen.

Spec `2026-07-28` gibt jedem cachebaren Resultat `ttlMs` und `cacheScope`. Das
SDK fuellt keines von beiden — `CacheHint()` defaultet auf `ttl_ms=0`,
`scope="private"`, die Drahtform von «schon veraltet, nie teilen». Ein Server
ohne `cache_hints` verhaelt sich also nicht neutral: er laesst jeden Client bei
jeder Verbindung neu auflisten, fuer Verzeichnisse, die beim Import feststehen.

Geprueft ueber eine echte `ClientSession` statt durch Ruecklesen von
`CACHE_HINTS`: `MCPServer` fuellt den Hinweis feldweise und nur, wo der Handler
nichts gesetzt hat — ein Blick ins Dict waere auch dann gruen, wenn das Argument
am Konstruktor verlorenginge.
"""

from __future__ import annotations

from mcp import Client
from mcp.server.caching import CACHEABLE_METHODS
from mcp.server.mcpserver import MCPServer

from zurich_opendata_mcp.app import CACHE_HINTS, LIST_CACHE_TTL_MS, mcp


async def test_die_werkzeugliste_traegt_die_ttl() -> None:
    async with Client(mcp) as client:
        result = await client.list_tools()

    assert result.ttl_ms == LIST_CACHE_TTL_MS, (
        f"tools/list antwortete mit ttlMs={result.ttl_ms}; bei 0 listet jeder Client "
        "bei jeder Verbindung neu auf"
    )
    assert result.cache_scope == "public"


async def test_ein_server_ohne_hinweise_sagt_nichts() -> None:
    """Negativkontrolle: gleiches SDK, gleicher Client, kein `cache_hints`.
    Faengt den Tag ab, an dem das SDK selbst einen Default bekommt — dann
    pruefen die Tests oben naemlich nicht mehr, dass wir ihn setzen."""
    async with Client(MCPServer("kontrolle")) as client:
        result = await client.list_tools()

    assert result.ttl_ms == 0
    assert result.cache_scope == "private"


def test_die_ttl_ist_lang_genug_um_etwas_zu_sagen() -> None:
    """Sichert die Richtung einer kuenftigen Aenderung, nicht die Zahl: eine
    TTL von wenigen Sekunden ist in der Praxis von keiner zu unterscheiden."""
    assert LIST_CACHE_TTL_MS >= 60_000


def test_jede_gehinweiste_methode_ist_nach_spec_cachebar() -> None:
    """`MCPServer` lehnt einen unbekannten Schluessel schon im Konstruktor ab;
    ein Tippfehler taeuchte sonst als Collection-Error an ganz anderer Stelle
    auf. Hier steht er benannt."""
    unknown = sorted(set(CACHE_HINTS) - set(CACHEABLE_METHODS))
    assert not unknown, f"nach Spec 2026-07-28 nicht cachebar: {unknown}"


def test_kein_hinweis_auf_einer_inhalts_methode() -> None:
    """Dieselbe Absicht wie oben, an der Konfiguration statt an der Antwort —
    damit sie sichtbar bleibt, wenn die geprueften Objekte einmal verschwinden.
    `resources/read` und `prompts/get` liefern Inhalt, kein Verzeichnis."""
    assert "resources/read" not in CACHE_HINTS
    assert "prompts/get" not in CACHE_HINTS

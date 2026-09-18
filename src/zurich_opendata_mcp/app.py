"""Shared MCPServer instance.

Lives in its own module so tool/resource modules can import it without
creating a cycle through ``server.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.caching import CacheableMethod, CacheHint
from mcp.server.mcpserver import MCPServer

from .config import PACKAGE_VERSION, REPO_URL
from .http_client import close_client


@asynccontextmanager
async def _lifespan(_server: MCPServer) -> AsyncIterator[None]:
    """Close the shared HTTP client's connection pool on server shutdown."""
    try:
        yield
    finally:
        await close_client()


# SEP-2549, Spec 2026-07-28: die auflistenden Methoden tragen `ttlMs` und
# `cacheScope`. Das SDK setzt beides auf «sofort veraltet, nie geteilt» — ein
# Server ohne `cache_hints` verhaelt sich also nicht neutral, sondern laesst
# jeden Client bei jeder Verbindung neu auflisten, fuer Verzeichnisse, die beim
# Import feststehen und sich zur Laufzeit des Prozesses nicht aendern koennen.
#
# `public` folgt aus der Sache, nicht aus Bequemlichkeit: die Tools werden per
# Dekorator beim Import registriert, es gibt keine Filterung nach Aufrufer.
# Sobald eine Liste vom Aufrufer abhaengt, muss der Scope im selben Commit auf
# `private` wechseln.
#
# `resources/read` und `prompts/get` stehen bewusst nicht dabei: das waere eine
# Zusicherung ueber den INHALT statt ueber das Verzeichnis.
LIST_CACHE_TTL_MS = 300_000

# Annotiert, nicht inferiert: `MCPServer` nimmt
# `Mapping[CacheableMethod, CacheHint]`, und ein Dict-Literal ohne Annotation
# inferiert mypy als `str`. Zur Laufzeit stimmt beides — ein `mypy src/`-Gate
# meldet den Unterschied, die Tests nicht.
CACHE_HINTS: dict[CacheableMethod, CacheHint] = {
    "tools/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "resources/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "resources/templates/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "server/discover": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
}

# SEP-2575, Spec 2026-07-28: Identitaet ist keine Verbindungseigenschaft mehr.
#
# In der Handshake-Aera kam `serverInfo` genau einmal, im `initialize`-Resultat,
# und eine Verbindung trug es danach implizit weiter. Die moderne Aera hat
# weder `initialize` noch eine Session: jede Anfrage steht fuer sich, und der
# Server stempelt seine Identitaet deshalb in das `_meta` JEDES Resultats
# (`io.modelcontextprotocol/serverInfo`). Damit ist das hier keine Kosmetik
# mehr — es ist das Einzige, woran ein zustandsloser Aufrufer erkennt, mit
# welchem Server und welcher Version er gerade gesprochen hat.
#
# Nachgemessen, nicht angenommen: `MCPServer` ohne `version=` meldet
# `{"name": "...", "version": ""}`. Das SDK setzt nichts ein — «An unversioned
# server reports an empty `version`; the SDK never substitutes its own»
# (`mcp/server/lowlevel/server.py`). Ein leerer String ist auf dem Draht keine
# Auskunft, sondern eine halbe: der Name ist da, die Frage «welche Fassung»
# bleibt offen, und zwar bei jeder einzelnen Antwort.
#
# Beschreibung und Anleitung unten fuehren bewusst keine Anzahlen: «6 APIs»,
# «23 Tools» veralten beim naechsten Tool, und kein Drift-Gate greift in einen
# Fliesstext hinein. Der Kommentar direkt darueber trug selbst so eine Zahl.
SERVER_TITLE = "Stadt Zürich Open Data"
SERVER_DESCRIPTION = (
    "Offene Daten der Stadt Zürich: Datenkatalog, Geodaten, Gemeinderat, "
    "Stadtratsbeschlüsse, Tourismus und Echtzeitmessungen."
)

# Die Anleitung, die `server/discover` mitgibt.
#
# In der Handshake-Aera reiste sie im `initialize`-Resultat. Die moderne Aera
# hat kein `initialize`: `server/discover` ist die EINZIGE Stelle, an der ein
# Client sie noch bekommt — und der Aufruf ist fuer ihn optional. Was hier
# fehlt, fehlt einem zustandslosen Aufrufer vollstaendig; er sieht dann nur
# noch die Tool-Liste.
#
# Absichtlich kurz: der Text landet im Kontextfenster jedes Clients, der
# `server/discover` aufruft. Er sagt, was aus der Tool-Liste allein nicht
# hervorgeht — die Reihenfolge Katalog → Resource-UUID → DataStore, die
# Haltbarkeit der Echtzeitwerte, und dass drei Namen nur noch Altlast sind.
SERVER_INSTRUCTIONS = """\
Offene Daten der Stadt Zürich aus öffentlichen APIs, ohne API-Schlüssel.

Einstieg in tabellarische Daten ist immer dreistufig: `zurich_search_datasets`
findet den Datensatz, `zurich_get_dataset` liefert dessen Resource-UUIDs, und
erst mit einer solchen UUID arbeiten `zurich_datastore_query` und
`zurich_datastore_sql` (nur SELECT). Eine UUID zu raten führt zu nichts.

Die Echtzeit-Tools (Parkhäuser, Wetter, Luftqualität, Seewasser, Fussgänger,
VBZ) liefern Messwerte mit Zeitstempel. Sie sind eine Momentaufnahme — den
Zeitstempel mitzitieren und die Werte nicht über die Anfrage hinaus als
aktuell behandeln.

Alle Tools heissen `zurich_*`. Die drei präfixlosen Namen
(`search_stadtratsbeschluesse`, `get_beschluesse_by_departement`,
`get_stadtratsbeschluss_detail`) sind veraltete Aliase für die
`zurich_strb_*`-Tools und existieren nur für bestehende Konfigurationen.
"""

mcp = MCPServer(
    "zurich_opendata_mcp",
    title=SERVER_TITLE,
    description=SERVER_DESCRIPTION,
    instructions=SERVER_INSTRUCTIONS,
    website_url=REPO_URL,
    version=PACKAGE_VERSION,
    lifespan=_lifespan,
    cache_hints=CACHE_HINTS,
)

# Sicherheitsrichtlinie & Sicherheitsstatus

🌐 **[English](SECURITY.md)** | **Deutsch**

`zurich-opendata-mcp` wurde gegen den internen MCP-Best-Practice-Audit-Katalog
gehärtet. Dieses Dokument fasst den Sicherheitsstatus zusammen und hält die
**akzeptierten Restrisiken** für jene Kontrollen fest, die bewusst auf der
Portfolio-/Gateway-Ebene statt in diesem einzelnen Server behandelt werden.

## Eine Schwachstelle melden

Bitte eröffnen Sie ein privates Security Advisory im GitHub-Repository oder
kontaktieren Sie die in `README.md` genannte Maintainerin. Melden Sie
ausnutzbare Schwachstellen nicht über öffentliche Issues.

## Statusübersicht

Dies ist ein **Nur-Lese-**, **PII-freier**, **Public-Open-Data**-MCP-Server.
Alle 23 Tools (plus drei deprecated STRB-Aliase) stellen ausschliesslich HTTP-GET-Anfragen an
eine feste Menge von Open-Data-Endpunkten der Stadt Zürich und ihrer Partner
(CKAN, Geoportal WFS, Paris, Zürich Tourismus, SPARQL, ParkenDD — siehe
`README.md`). Bereits umgesetzte Härtung:

| Bereich | Kontrolle |
|---|---|
| Egress | HTTPS zu einer festen Allow-List von Hosts der Stadt Zürich / Partner; keine benutzergesteuerten URLs (SEC-004/021) |
| TLS | Zertifikatsprüfung standardmässig aktiv (httpx-Default); nie deaktiviert (SEC-005) |
| Binding | Standardmässig stdio-Transport; der optionale `--http`-Transport bindet an den SDK-Default `127.0.0.1` (SEC-016 / SDK-004) |
| Eingaben | Strikte Pydantic-v2-Validierung (`extra="forbid"`, Whitespace-Trimming) auf jedem Tool-Eingabemodell (SEC-008/018) |
| Injection | SQL-String-Literal- und ILIKE-Wildcard-Escaping in `tools/strb.py` (H-1, Rerun §2.3) und CQL-Escaping in `clients/paris.py` (H-2); Datums-/ID-Felder werden upstream per Regex validiert (SEC-018) |
| Tools | Jedes Tool setzt `readOnlyHint: True`; es existieren keine Schreib-, Mutations- oder Löschpfade (ARCH) |
| Secrets | Keine erforderlich — der Server nutzt keinen API-Key und keine Credentials; nichts Geheimes wird gespeichert oder geloggt (ARCH-005/SEC-013) |
| XML | Paris-API-Antworten werden via `defusedxml` geparst — DTDs, Entity-Expansion und externe Entities werden abgelehnt (F-9) |
| Fehler | Upstream-Fehlerbodies werden nur nach stderr geloggt; das Modell erhält eine generische, nicht-leckende Meldung (OBS-002) |
| Stdout | Reserviert für den JSON-RPC-Stream; sämtliches Logging auf stderr gepinnt (OBS-004) |
| Resilienz | Ein 30s-Timeout pro Anfrage (`REQUEST_TIMEOUT`) begrenzt jeden Upstream-Aufruf (SCALE-002/003) |

Das Audit (`audits/zurich-opendata-mcp-audit.md`) und sein Rerun
(`audits/zurich-opendata-mcp-audit-rerun.md`) — 2 High, 8 Medium und 14 Low —
sind seit `0.3.0` **vollständig geschlossen**. Die Härtungshistorie steht in
`CHANGELOG.md`.

## Akzeptierte Restrisiken (Kontrollen auf Portfolio-Ebene)

Die folgenden Audit-Checks sind bewusst **nicht** innerhalb dieses Servers
umgesetzt. Es handelt sich um portfolioweite Belange, die am besten auf einer
MCP-Gateway-/Host-Ebene durchgesetzt werden; das Restrisiko ist hier gering,
weil der Server nur lesend arbeitet und nur eine kleine Menge vertrauenswürdiger
Public-Data-Anbieter erreicht.

### SEC-014 — Tool-Allow-Listing über ein MCP-Gateway

**Status:** akzeptiertes Risiko (Portfolio-Ebene).
Eine Tool-bezogene Allow-List gehört zum MCP-Host/-Gateway, das mehrere Server
aggregiert, nicht zu einem einzelnen Server mit festem, nur lesendem Tool-Set.
Sobald ein zentrales Gateway für das Portfolio eingeführt wird, sollte das
Tool-Allow-Listing dort konfiguriert werden. Bis dahin ist das Risiko begrenzt:
Jedes Tool ist nur lesend und auf die obigen festen Endpunkte beschränkt.

### SEC-015 — Pre-Flight-Erkennung von Tool-Poisoning

**Status:** akzeptiertes Risiko (Portfolio-Ebene) — mit lokaler Absicherung.
Tool-Poisoning (bösartige Tool-Beschreibungen / Rug-Pulls) ist ein
Supply-Chain- und Host-seitiges Thema. Die Tool-Definitionen dieses Servers sind
versionskontrolliert, im Repo verfasst und via PR reviewt; es gibt keine
dynamische oder entfernte Tool-Registrierung. Server-übergreifende
Poisoning-Erkennung bleibt eine Gateway-/Host-Verantwortung auf Portfolio-Ebene.

### WFS-`property_filter` (CQL) — Durchreichung ohne Escaping

**Status:** akzeptiertes Risiko (durch Design begrenzt).
`zurich_geo_features` reicht den `property_filter`-String unescaped als
`CQL_FILTER`-Query-Parameter an den Geoserver der Stadt Zürich weiter. Der
Wirkungsradius ist begrenzt: Layer und Typename sind serverseitig fixiert
(`Literal`-validiert gegen `GEOPORTAL_LAYERS`), der Geoserver ist nur lesend
und liefert öffentliche Daten, und der Parameter kann das Anfrageziel nicht
ändern. Ein bösartiger Filter kann höchstens einen WFS-Fehler oder ein leeres
Ergebnis für die eigene Abfrage erzeugen. Sinnvolles Escaping würde einen
vollständigen CQL-Parser erfordern — unverhältnismässig für dieses
Risikoprofil. Neu bewerten, falls die WFS-Fläche je Layer mit
nicht-öffentlichen Daten erhält.

### `--http`-Transport ohne Authentifizierung

**Status:** dokumentierte Deployment-Einschränkung.
Der optionale Streamable-HTTP-Transport (`--http`) bindet an den SDK-Default
`127.0.0.1` und ist nur für lokale Clients gedacht. Der Server implementiert
selbst keine Authentifizierung. Wer ihn über localhost hinaus exponiert
(Reverse Proxy, Container-Netzwerk, Tunnel), muss Authentifizierung und TLS
auf dieser Proxy-Ebene erzwingen — den Port niemals unauthentifiziert
weiterleiten.

## Trigger für eine Neubewertung

Diese Akzeptanzen sollten neu bewertet werden, falls der Server jemals:

- **Schreib**-Fähigkeit erhält oder **PII** verarbeitet, oder
- ein **Authentifizierungs**-Modell erhält (dann gebundene, TTL-versehene,
  serverseitig invalidierbare Session-IDs implementieren und vor dem Merge neu
  auditieren), oder
- Tools **dynamisch** / aus entfernten Quellen registriert, oder
- hinter einem gemeinsamen MCP-Gateway aggregiert wird (dann das
  Tool-Allow-Listing und die Tool-Poisoning-Erkennung des Gateways aktivieren).

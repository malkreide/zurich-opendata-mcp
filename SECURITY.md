# Security Policy & Posture

🌐 **English** | **[Deutsch](SECURITY.de.md)**

`zurich-opendata-mcp` was hardened against the internal MCP best-practice audit
catalogue. This document summarises the security posture and records the
**accepted-risk** decisions for controls that are deliberately handled at the
portfolio/gateway layer rather than inside this single server.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository, or contact the
maintainer listed in `README.md`. Do not file public issues for exploitable
vulnerabilities.

## Posture summary

This is a **read-only**, **no-PII**, **public-open-data** MCP server. All 23
tools (plus three deprecated STRB aliases) only issue HTTP GET requests against a fixed set of
City-of-Zurich and partner open-data endpoints (CKAN, Geoportal WFS, Paris,
Zürich Tourism, SPARQL, ParkenDD — see `README.md`). Hardening already in place:

| Area | Control |
|---|---|
| Egress | HTTPS to a fixed allow-list of City-of-Zurich / partner hosts; no user-controlled URLs are constructed (SEC-004/021) |
| TLS | Certificate verification on by default (httpx default); never disabled (SEC-005) |
| Binding | stdio transport by default; the optional `--http` transport binds to the SDK default of `127.0.0.1` (SEC-016 / SDK-004) |
| Input | Pydantic v2 strict validation (`extra="forbid"`, whitespace stripping) on every tool input model (SEC-008/018) |
| Injection | SQL string-literal + ILIKE-wildcard escaping in `tools/strb.py` (H-1, rerun §2.3) and CQL escaping in `clients/paris.py` (H-2); date/ID fields are regex-validated upstream (SEC-018) |
| Tools | Every tool sets `readOnlyHint: True`; no write, mutate, or delete paths exist (ARCH) |
| Secrets | None required — the server uses no API key or credentials; nothing secret is stored or logged (ARCH-005/SEC-013) |
| XML | Paris-API responses parsed via `defusedxml` — DTDs, entity expansion and external entities rejected (F-9) |
| Errors | Upstream error bodies are logged to stderr only; the model receives a generic, non-leaking message (OBS-002) |
| Stdout | Reserved for the JSON-RPC stream; all logging pinned to stderr (OBS-004) |
| Resilience | A 30s per-request timeout (`REQUEST_TIMEOUT`) bounds every upstream call (SCALE-002/003) |

The audit (`audits/zurich-opendata-mcp-audit.md`) and its rerun
(`audits/zurich-opendata-mcp-audit-rerun.md`) — 2 High, 8 Medium and 14 Low —
are **fully closed** as of `0.3.0`. See `CHANGELOG.md` for the hardening history.

## Accepted risks (portfolio-level controls)

The following audit checks are **not** implemented inside this server by design.
They are portfolio-wide concerns best enforced at an MCP gateway / host layer,
and the residual risk here is low because the server is read-only and only
reaches a small set of trusted public-data providers.

### SEC-014 — Tool allow-listing via an MCP gateway

**Status:** accepted risk (portfolio-level).
A per-tool allow-list belongs to the MCP host/gateway that aggregates multiple
servers, not to an individual server that exposes a fixed, read-only tool set.
If/when a central gateway is introduced for the portfolio, tool allow-listing
should be configured there. Until then, the risk is bounded: every tool is
read-only and constrained to the fixed endpoints above.

### SEC-015 — Pre-flight tool-poisoning detection

**Status:** accepted risk (portfolio-level) — with a local guard in place.
Tool-poisoning (malicious tool descriptions / rug-pulls) is a supply-chain and
host-side concern. This server's tool definitions are version-controlled,
authored in-repo, and reviewed via PR; there is no dynamic or remote tool
registration. Cross-server poisoning detection remains a gateway/host
responsibility tracked at the portfolio level.

### WFS `property_filter` (CQL) passthrough

**Status:** accepted risk (bounded by design).
`zurich_geo_features` forwards its `property_filter` string unescaped as the
`CQL_FILTER` query parameter to the Stadt Zürich Geoserver. The blast radius
is bounded: layer and typename are fixed server-side (`Literal`-validated
against `GEOPORTAL_LAYERS`), the Geoserver is read-only and serves public
data, and the parameter cannot change the request target. A malicious filter
can at most produce a WFS error or an empty result for the caller's own
query. Meaningful escaping would require a full CQL parser, which is not
proportionate to this risk profile. Revisit if the WFS surface ever gains
layers with non-public data.

### `--http` transport has no authentication

**Status:** documented deployment constraint.
The optional Streamable-HTTP transport (`--http`) binds to the SDK default
`127.0.0.1` and is intended for local clients only. The server implements no
authentication of its own. If you expose it beyond localhost (reverse proxy,
container network, tunnel), enforce authentication and TLS at that proxy
layer — never forward the port unauthenticated.

## Re-evaluation triggers

These acceptances should be revisited if the server ever:

- gains **write** capability or starts processing **PII**, or
- adds an **authentication** model (then implement bound, TTL'd,
  server-side-invalidated session IDs and re-audit before merge), or
- registers tools **dynamically** / from remote sources, or
- is aggregated behind a shared MCP gateway (then enable the gateway's tool
  allow-listing and tool-poisoning detection).

"""Unit tests for shared helpers and the CLI entry point (coverage to 100%)."""

from __future__ import annotations

import sys

import httpx
import pytest
import respx

from zurich_opendata_mcp.config import CKAN_API_URL

# ─── formatters.render_dataset_summary optional branches ─────────────────────


def test_format_dataset_summary_renders_all_optional_fields():
    from zurich_opendata_mcp.formatters import format_dataset_summary

    md = format_dataset_summary(
        {
            "name": "ds",
            "title": "Titel",
            "updateInterval": ["jährlich"],
            "groups": [{"title": "Bildung"}],
            "tags": [{"display_name": "schule"}],
            "notes": "Eine Beschreibung",
            "resources": [{"id": "r1", "name": "CSV", "format": "CSV", "datastore_active": True}],
        }
    )

    assert "- **Aktualisierung**: jährlich" in md
    assert "- **Kategorien**: Bildung" in md
    assert "- **Tags**: schule" in md
    assert "- **Beschreibung**: Eine Beschreibung..." in md
    assert "✔ DataStore" in md


# ─── formatters.handle_api_error branches ────────────────────────────────────


def _http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://x.test")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


@pytest.mark.parametrize(
    "exc, needle",
    [
        (_http_error(403), "Zugriff verweigert"),
        (_http_error(429), "Zu viele Anfragen"),
        (httpx.TimeoutException("slow"), "Zeitüberschreitung"),
    ],
)
def test_handle_api_error_branches(exc, needle):
    from zurich_opendata_mcp.formatters import handle_api_error

    assert needle in handle_api_error(exc, "Test")


# ─── http_client.ckan_request unsuccessful response ──────────────────────────


@respx.mock
async def test_ckan_request_raises_on_unsuccessful_response():
    from zurich_opendata_mcp.http_client import ckan_request

    respx.get(f"{CKAN_API_URL}/package_show").mock(
        return_value=httpx.Response(200, json={"success": False, "error": {"message": "Not found"}})
    )

    with pytest.raises(RuntimeError, match="Not found"):
        await ckan_request("package_show", {"id": "x"})


# ─── clients/paris.paris_extract_text default ────────────────────────────────


def test_paris_extract_text_defaults():
    import xml.etree.ElementTree as ET

    from zurich_opendata_mcp.clients.paris import paris_extract_text

    assert paris_extract_text(None, "fallback") == "fallback"
    # Element present but empty → default.
    assert paris_extract_text(ET.Element("x"), "fallback") == "fallback"


# ─── server.main() CLI wiring ────────────────────────────────────────────────


def test_main_runs_stdio_by_default(monkeypatch):
    import zurich_opendata_mcp.server as srv

    calls: list[tuple] = []
    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(sys, "argv", ["zurich-opendata-mcp"])

    srv.main()

    assert calls == [((), {})]


def test_main_runs_http_with_host_port_and_security(monkeypatch):
    import zurich_opendata_mcp.server as srv

    # An inherited allow-list would change which branch the security builder
    # takes, and with it the assertion below.
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    calls: list[tuple] = []
    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(sys, "argv", ["zurich-opendata-mcp", "--http", "--port", "9001"])

    srv.main()

    # mcp 2.x: MCPServer.settings carries no host/port, so the bind travels as
    # run() kwargs instead of being assigned beforehand. Asserting the whole
    # call keeps them in one place — dropping any of them fails here.
    #
    # `host` in particular: without it the server binds loopback whatever
    # --host said, and the SDK derives its Host allow-list from the default it
    # then sees. `transport_security` is asserted separately because it is an
    # object, not a literal; see tests/test_transport_security.py for what it
    # contains.
    ((args, kwargs),) = calls
    assert args == ()
    assert kwargs["transport"] == "streamable-http"
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 9001
    assert set(kwargs) == {"transport", "host", "port", "transport_security"}
    assert "127.0.0.1:9001" in kwargs["transport_security"].allowed_hosts

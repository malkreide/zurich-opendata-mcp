"""Inbound Host/Origin allow-list for the HTTP transport.

The counterpart to the outbound hardening elsewhere in the suite: that side
covers where this server may talk *to*, this one under *which name* it may be
addressed.

The threat is DNS rebinding — a page on the operator's network resolves its own
hostname to this server's address and then talks to it from the browser. From
the browser's point of view the request is same-origin, so no origin rule stops
it, and a token would not either: the attacking page runs in a context that
holds one. Only the Host check does.

The load-bearing test is **right hostname, wrong port**. `evil.invalid` alone
proves little, because a fallback loopback-only policy rejects that too; only
the wrong-port case tells a port-exact allow-list apart from one that lets
everything through.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from zurich_opendata_mcp import server

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


@pytest.fixture(autouse=True)
def _no_inherited_allowlist(monkeypatch):
    """A real MCP_ALLOWED_HOSTS in the environment would silently change what
    the `env=None` paths below resolve."""
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)


# ─── Allow-list resolution ───────────────────────────────────────────────────


def test_allowed_hosts_default_is_empty():
    assert server._resolve_allowed_hosts(env={}) == []


def test_allowed_hosts_parsed_comma_separated_and_stripped():
    assert server._resolve_allowed_hosts(
        env={"MCP_ALLOWED_HOSTS": " zurich.example.ch:8000 , alt.example.ch , "}
    ) == ["zurich.example.ch:8000", "alt.example.ch"]


def test_allowed_hosts_reads_the_real_environment(monkeypatch):
    """The `env=None` default path — the one main() actually takes."""
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "zurich.example.ch:8000")
    assert server._resolve_allowed_hosts() == ["zurich.example.ch:8000"]


def test_loopback_bind_gets_an_explicit_allowlist():
    """The SDK infers this from a loopback `host`; stating it explicitly means
    the protection no longer depends on that inference."""
    sec = server._build_transport_security("127.0.0.1", 8000, env={})
    assert sec is not None
    assert sec.enable_dns_rebinding_protection is True
    assert "127.0.0.1:8000" in sec.allowed_hosts
    assert "http://127.0.0.1:8000" in sec.allowed_origins


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_every_loopback_spelling_counts_as_local(host):
    assert server._build_transport_security(host, 8000, env={}) is not None


def test_non_loopback_bind_without_allowlist_stays_off():
    """Unchanged behaviour, and deliberately not a guess: on 0.0.0.0 the
    reachable name is unknowable here, and a guessed list would reject the very
    deployment it is meant to protect."""
    assert server._build_transport_security("0.0.0.0", 8000, env={}) is None


def test_non_loopback_bind_with_allowlist_is_enforced():
    sec = server._build_transport_security(
        "0.0.0.0", 8000, env={"MCP_ALLOWED_HOSTS": "zurich.example.ch:8000"}
    )
    assert sec is not None
    assert "zurich.example.ch:8000" in sec.allowed_hosts
    # Loopback stays reachable so container health checks keep working.
    assert "127.0.0.1:8000" in sec.allowed_hosts


def test_the_allowlist_names_the_port_actually_served():
    """A port mismatch here would name a port nobody listens on, silently
    breaking container health checks."""
    sec = server._build_transport_security("127.0.0.1", 9101, env={})
    assert sec is not None
    assert "127.0.0.1:9101" in sec.allowed_hosts
    assert "127.0.0.1:8000" not in sec.allowed_hosts


# ─── Through the real ASGI stack ─────────────────────────────────────────────


def _post_init(app, host_header: str) -> int:
    """POST an initialize request under `host_header` and return the status.

    Via `TestClient` rather than a bare ASGI transport: streamable-HTTP starts
    its session manager in the app lifespan, and without that every request
    answers 500 instead of exercising the Host check.
    `raise_server_exceptions=False` because a rejection surfaces as an
    exception here, while a real client sees the status — which is what is
    being asserted.
    """
    with TestClient(app, raise_server_exceptions=False) as client:
        return client.post(
            "/mcp", headers={**_HEADERS, "Host": host_header}, json=_INIT
        ).status_code


def _app(host: str, port: int, env: dict[str, str] | None = None):
    return server.mcp.streamable_http_app(
        host=host,
        transport_security=server._build_transport_security(host, port, env=env or {}),
    )


def test_an_allowlisted_host_is_admitted():
    app = _app("0.0.0.0", 8000, {"MCP_ALLOWED_HOSTS": "zurich.example.ch:8000"})
    assert _post_init(app, "zurich.example.ch:8000") == 200


def test_a_foreign_host_is_rejected():
    app = _app("0.0.0.0", 8000, {"MCP_ALLOWED_HOSTS": "zurich.example.ch:8000"})
    assert _post_init(app, "evil.invalid") == 421


def test_right_host_wrong_port_is_rejected():
    """The load-bearing case — see the module docstring."""
    app = _app("0.0.0.0", 8000, {"MCP_ALLOWED_HOSTS": "zurich.example.ch:8000"})
    assert _post_init(app, "zurich.example.ch:9999") == 421


def test_the_gateway_fronted_deployment_keeps_working():
    """No allow-list means no behaviour change: a real hostname on a 0.0.0.0
    bind is still served, exactly as it would have been before this existed."""
    app = _app("0.0.0.0", 8000)
    assert _post_init(app, "zurich.example.ch:8000") == 200


def test_a_loopback_bind_rejects_a_foreign_host():
    """The default deployment is protected without any configuration."""
    app = _app("127.0.0.1", 8000)
    assert _post_init(app, "evil.invalid") == 421


# ─── CLI wiring ──────────────────────────────────────────────────────────────


def test_host_defaults_to_loopback():
    """A server that starts listening on every interface after an update is a
    security regression, not a feature."""
    assert server._parse_args([]).host == "127.0.0.1"
    assert server._parse_args(["--http"]).host == "127.0.0.1"


def test_host_is_configurable():
    assert server._parse_args(["--http", "--host", "0.0.0.0"]).host == "0.0.0.0"


def test_main_forwards_host_port_and_security_to_run(monkeypatch):
    """The regression guard for the reported defect: without `host=` reaching
    `run()`, the server binds loopback whatever `--host` said."""
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.setattr(
        "sys.argv", ["zurich-opendata-mcp", "--http", "--host", "127.0.0.1", "--port", "9001"]
    )
    captured: dict = {}
    monkeypatch.setattr(server.mcp, "run", lambda **kw: captured.update(kw))

    server.main()

    assert captured["transport"] == "streamable-http"
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 9001
    assert "127.0.0.1:9001" in captured["transport_security"].allowed_hosts


def test_main_warns_when_binding_wide_without_an_allowlist(monkeypatch, caplog):
    """The check being off is a real posture change, so it is said out loud
    rather than left to be inferred from silence."""
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.setattr(
        "sys.argv", ["zurich-opendata-mcp", "--http", "--host", "0.0.0.0", "--port", "9002"]
    )
    captured: dict = {}
    monkeypatch.setattr(server.mcp, "run", lambda **kw: captured.update(kw))

    with caplog.at_level("WARNING"):
        server.main()

    assert captured["host"] == "0.0.0.0"
    assert captured["transport_security"] is None
    assert any("MCP_ALLOWED_HOSTS" in r.getMessage() for r in caplog.records)


def test_main_does_not_warn_when_the_allowlist_is_set(monkeypatch, caplog):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "zurich.example.ch:9003")
    monkeypatch.setattr(
        "sys.argv", ["zurich-opendata-mcp", "--http", "--host", "0.0.0.0", "--port", "9003"]
    )
    captured: dict = {}
    monkeypatch.setattr(server.mcp, "run", lambda **kw: captured.update(kw))

    with caplog.at_level("WARNING"):
        server.main()

    assert "zurich.example.ch:9003" in captured["transport_security"].allowed_hosts
    assert not any("MCP_ALLOWED_HOSTS" in r.getMessage() for r in caplog.records)


def test_stdio_is_untouched_by_any_of_this(monkeypatch):
    """The default transport takes no host, port or security kwargs."""
    monkeypatch.setattr("sys.argv", ["zurich-opendata-mcp"])
    calls: list = []
    monkeypatch.setattr(server.mcp, "run", lambda *a, **kw: calls.append((a, kw)))

    server.main()

    assert calls == [((), {})]


# ─── Auditor boot commands ───────────────────────────────────────────────────


def test_auditor_boot_commands_are_declared():
    """An external auditor cannot boot the HTTP path by setting an env var,
    because the transport is chosen by CLI flag — so the commands are declared."""
    import tomllib
    from pathlib import Path

    cfg = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    commands = cfg["tool"]["mcp_auditor"]["boot"]["commands"]
    entry = cfg["project"]["scripts"]
    assert commands["stdio"] == ["zurich-opendata-mcp"]
    assert commands["streamable-http"] == [
        "zurich-opendata-mcp",
        "--http",
        "--port",
        "{port}",
    ]
    # The commands invoke the console script, so they are only bootable if that
    # script exists — pin them together rather than let one drift.
    assert set(commands) == {"stdio", "streamable-http"}
    assert "zurich-opendata-mcp" in entry

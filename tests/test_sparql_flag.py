"""Tests for the ZURICH_OPENDATA_ENABLE_SPARQL opt-in flag (F-6)."""

from __future__ import annotations

from zurich_opendata_mcp.app import mcp
from zurich_opendata_mcp.tools import sparql


def _registered() -> bool:
    return any(t.name == "zurich_sparql" for t in mcp._tool_manager.list_tools())


def test_sparql_not_registered_by_default(monkeypatch):
    monkeypatch.delenv("ZURICH_OPENDATA_ENABLE_SPARQL", raising=False)
    mcp._tool_manager._tools.pop("zurich_sparql", None)  # isolate from other tests

    assert sparql.sparql_enabled() is False
    assert sparql.register_sparql_tool() is False
    assert not _registered()


def test_sparql_registers_with_flag(monkeypatch):
    monkeypatch.setenv("ZURICH_OPENDATA_ENABLE_SPARQL", "1")

    assert sparql.sparql_enabled() is True
    try:
        assert sparql.register_sparql_tool() is True
        assert _registered()
    finally:
        mcp._tool_manager._tools.pop("zurich_sparql", None)
    assert not _registered()


async def test_sparql_function_still_returns_notice():
    # The implementation stays importable and callable (server.py re-export)
    # even when the tool is not registered.
    result = await sparql.zurich_sparql(
        sparql.SparqlQueryInput(query="SELECT * WHERE { ?s ?p ?o } LIMIT 1")
    )
    assert "SPARQL-Endpunkt nicht produktiv" in result

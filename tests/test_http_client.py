"""Tests for the shared HTTP client lifecycle (connection reuse + lifespan)
and the http_get retry behaviour."""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from zurich_opendata_mcp import http_client


@pytest.fixture(autouse=True)
async def _reset_shared_client():
    await http_client.close_client()
    yield
    await http_client.close_client()


async def test_get_client_reuses_instance_within_loop():
    first = http_client.get_client()
    second = http_client.get_client()

    assert first is second
    assert not first.is_closed


async def test_close_client_closes_and_resets():
    client = http_client.get_client()

    await http_client.close_client()

    assert client.is_closed
    # Closing again with no client around is a no-op.
    await http_client.close_client()
    # The next access transparently creates a fresh client.
    fresh = http_client.get_client()
    assert fresh is not client
    assert not fresh.is_closed


async def test_get_client_replaces_externally_closed_client():
    client = http_client.get_client()
    await client.aclose()

    fresh = http_client.get_client()

    assert fresh is not client
    assert not fresh.is_closed


def test_get_client_recreates_after_loop_change():
    """Each new event loop gets its own client — pooled connections are bound
    to the loop they were opened on and must not leak across loops."""

    async def grab():
        return http_client.get_client()

    first = asyncio.run(grab())
    second = asyncio.run(grab())

    assert first is not second


async def test_lifespan_closes_shared_client():
    from zurich_opendata_mcp.app import _lifespan, mcp

    assert mcp.settings.lifespan is _lifespan

    async with _lifespan(mcp):
        client = http_client.get_client()
        assert not client.is_closed

    assert client.is_closed


# ─── http_get retry behaviour ────────────────────────────────────────────────


@respx.mock
async def test_http_get_retries_once_on_503_then_succeeds():
    route = respx.get("https://example.test/x").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"ok": True})]
    )

    response = await http_client.http_get("https://example.test/x")

    assert response.status_code == 200
    assert route.call_count == 2


@respx.mock
async def test_http_get_gives_up_after_one_retry():
    route = respx.get("https://example.test/x").mock(return_value=httpx.Response(503))

    with pytest.raises(httpx.HTTPStatusError):
        await http_client.http_get("https://example.test/x")

    assert route.call_count == 2


@respx.mock
async def test_http_get_does_not_retry_deterministic_errors():
    # 4xx and plain 500 are answers, not transient gateway hiccups.
    route = respx.get("https://example.test/x").mock(return_value=httpx.Response(404))

    with pytest.raises(httpx.HTTPStatusError):
        await http_client.http_get("https://example.test/x")

    assert route.call_count == 1

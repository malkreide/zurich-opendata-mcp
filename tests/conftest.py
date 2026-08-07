"""Shared test fixtures."""

from __future__ import annotations

import pytest

from zurich_opendata_mcp import retry


@pytest.fixture(autouse=True)
def _no_retry_backoff(monkeypatch):
    """Zero the retry backoff so retrying code paths don't slow the suite.

    Patched on `retry._sleep`, deliberately, and NOT via
    `monkeypatch.setattr(retry.asyncio, "sleep", ...)`. The latter looks local
    and is not: `retry.asyncio` *is* the stdlib module, so the patch takes the
    real `asyncio.sleep` out for the whole process — including any test that
    uses it to yield to the event loop, which then measures nothing and stays
    green. `test_retry.py` keeps a test that guards this seam.
    """

    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr(retry, "_sleep", _instant)

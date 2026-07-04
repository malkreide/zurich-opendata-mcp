"""Shared test fixtures."""

from __future__ import annotations

import pytest

from zurich_opendata_mcp import http_client


@pytest.fixture(autouse=True)
def _no_retry_backoff(monkeypatch):
    """Zero the 5xx retry backoff so retrying code paths don't slow the suite."""
    monkeypatch.setattr(http_client, "RETRY_BACKOFF_SECONDS", 0)

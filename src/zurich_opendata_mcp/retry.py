"""Retry policy against the upstream: bounded, spread, obedient.

Adopted from the ``mcp-data-source-probe`` reference template
(``reference/retry_backoff.py``, repaired 2026-08-07). Copied, not imported —
a change here is a change to this server only, and the template's adoption
manifest names this file.

Three questions, and the previous implementation answered none of them:

* **What** is retried. 5xx, 429, timeouts and connection errors. Everything
  else in the 4xx range is a statement about the request, not about the
  moment, and a fourth attempt does not turn a 404 into a 200.
* **How fast.** Every wait is jittered. Without it, every client that hit the
  same outage retries in lockstep and the load returns as a wave exactly when
  the source recovers — the retry storm extends the outage it was meant to
  bridge. And when the source sends ``Retry-After``, that beats our curve: it
  answers the very question the curve is guessing at.
* **How long.** A wall-clock budget in seconds, not a number of attempts. An
  attempt count is not a bound — the previous code could sit through two full
  30s ``REQUEST_TIMEOUT`` operations and never say so.

The old policy also retried on *two* levels at once: this module's loop and
``AsyncHTTPTransport(retries=2)`` underneath it. Those multiply rather than
add. Exactly one level may retry, and it is this one.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 4
BASE_DELAY_SECONDS = 2.0  # ladder before jitter: 2, 4, 8

# Ceiling on the WHOLE call — every attempt and every wait together. The
# anchor is measured, not guessed: the Python MCP SDK ships
# MCP_DEFAULT_TIMEOUT = 30.0, so 25s leaves headroom for framing and parsing.
# Note this is *below* REQUEST_TIMEOUT (30s): that value bounds one operation,
# this one bounds the call, and only the second is what the caller waits on.
TOTAL_BUDGET_SECONDS = 25.0

# Ceiling for a single wait. Bounds the exponential ladder, and bounds a
# `Retry-After` the source may send but we are not obliged to sit through.
MAX_DELAY_SECONDS = 20.0

JITTER_SPREAD = 0.5  # exponential delays land in [0.5x, 1.5x]

# One-sided on purpose: the source said *when* to come back, so later is
# polite and earlier ignores the very value being read.
RETRY_AFTER_JITTER = 0.25  # lands in [1.0x, 1.25x]

# Statuses that carry a meaningful `Retry-After` (RFC 9110 §10.2.3).
RETRY_AFTER_STATUSES = frozenset({429, 503})


class UpstreamUnavailableError(RuntimeError):
    """No request was attempted — the budget was gone before the first try.

    A named type and not a bare ``RuntimeError``: a caller can branch on this,
    and cannot tell a bare ``RuntimeError`` apart from a bug in the server's
    own code. Raised only when there is no upstream exception to re-raise;
    whenever there is one, the original travels out untouched.
    """


def parse_retry_after(resp: httpx.Response | None) -> float | None:
    """Seconds to wait per the response's ``Retry-After``, or ``None``.

    RFC 9110 §10.2.3 allows two forms — delta-seconds (``120``) and an
    HTTP-date (``Wed, 21 Oct 2026 07:28:00 GMT``). Both appear in the wild, so
    both are read. Anything unparseable yields ``None`` and the caller falls
    back to its own curve: a malformed header must not become a crash on the
    error path, which is the one path already going badly.
    """
    if resp is None or resp.status_code not in RETRY_AFTER_STATUSES:
        return None
    raw = (resp.headers.get("retry-after") or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return float(raw)
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:  # RFC 9110 dates are GMT; a naive one means UTC
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())  # past date -> now


def compute_delay(attempt: int, last_error: Exception | None) -> float:
    """Seconds to wait before ``attempt`` (1-based for the first retry).

    The cap wraps the jitter and not the other way round. ``min(cap, base) *
    jitter`` and ``min(cap, base * jitter)`` both contain a cap and a jitter;
    only the second is bounded — a value capped at 20s and then multiplied by
    up to 1.5 lands at 30s, and the constant would claim a ceiling it does not
    hold. That ordering shipped in six portfolio servers.
    """
    hinted = parse_retry_after(getattr(last_error, "response", None))
    if hinted is not None:
        return min(hinted * (1.0 + random.random() * RETRY_AFTER_JITTER), MAX_DELAY_SECONDS)
    return min(
        BASE_DELAY_SECONDS
        * 2 ** (attempt - 1)
        * (1.0 - JITTER_SPREAD + random.random() * 2 * JITTER_SPREAD),
        MAX_DELAY_SECONDS,
    )


# Indirection so tests can zero the wait without patching `asyncio.sleep`
# itself. Patching `retry.asyncio` would reach the stdlib module and take the
# real `asyncio.sleep` out for the whole process, including tests that use it
# to yield to the event loop — those then measure nothing and stay green.
_sleep = asyncio.sleep


async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    total_budget: float = TOTAL_BUDGET_SECONDS,
) -> httpx.Response:
    """GET ``url`` with jittered backoff, ``Retry-After`` and a time budget.

    Retries 5xx, 429 and network errors; fails fast on any other 4xx.

    Raises the last upstream exception **unwrapped** — ``httpx.HTTPStatusError``
    or ``httpx.RequestError``. Callers branch on the type and read
    ``.response`` where it exists; a wrapper takes both away, and for the
    errors a real outage produces (``ConnectTimeout``, ``ReadTimeout``,
    ``ConnectError``) it would interpolate an empty ``str()``.
    """
    deadline = time.monotonic() + total_budget
    last_error: Exception | None = None

    for attempt in range(MAX_ATTEMPTS):
        if attempt > 0:
            delay = compute_delay(attempt, last_error)
            # A wait that outlasts the budget is a wait for nobody: the caller
            # has given up by the time it ends. Stop instead of sleeping.
            if delay >= deadline - time.monotonic():
                break
            logger.warning(
                "GET %s failed (%s); retrying in %.1fs",
                url,
                type(last_error).__name__,
                delay,
            )
            await _sleep(delay)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            # httpx bounds each operation and its read timeout restarts with
            # every chunk, so a slowly trickling response outlives the budget
            # without a single read expiring. `asyncio.timeout` is the
            # wall-clock deadline the budget actually promises.
            async with asyncio.timeout(remaining):
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response
        except TimeoutError as exc:  # the budget is gone, not just this try
            last_error = exc
            break
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status = exc.response.status_code
            if 400 <= status < 500 and status != 429:
                raise  # a statement about the request, not about the moment
        except httpx.RequestError as exc:
            last_error = exc  # network or timeout: retry

    host = urlsplit(url).hostname
    if last_error is None:
        # Budget gone before a single request went out. Nothing to re-raise,
        # so this is the one place that constructs its own error.
        raise UpstreamUnavailableError(
            f"no attempt made: the {total_budget:g}s budget was already spent (host={host})"
        )

    # Logged, not wrapped. `str(last_error)` is empty for exactly the errors an
    # outage produces — ConnectTimeout, ReadTimeout, ConnectError — so the type
    # is what carries the diagnosis.
    logger.warning(
        "Upstream unreachable: %s: %s (host=%s)",
        type(last_error).__name__,
        str(last_error) or "no further detail",
        host,
    )
    raise last_error

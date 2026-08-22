"""Tests for the retry policy (ARCH-014).

Every assertion here has a counter-check somewhere in the file: a test that
shows the property would be *missed* if the implementation were the previous
one. A test that stays green when the implementation is removed measures
nothing, and the previous implementation is the honest thing to measure
against — it was in production until this branch.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest
import respx

from zurich_opendata_mcp import http_client, retry

URL = "https://example.test/x"

# Wall-clock numbers for the deadline test below, spread far enough apart that
# scheduler jitter cannot move the outcome. Measured on 3.11 over 15 runs of
# that test's own body, through pytest so every fixture is in place:
# 0.088-0.101s against a 0.05s budget. Setup — the first call through a fresh
# shared client — accounted for about 0.039s of that, nearly the whole budget,
# so most of what the test used to measure was not the deadline. The old bound
# of 0.25s left only 0.16s of absolute headroom, the thinnest in the portfolio,
# and CI jitter is absolute, not proportional: in swiss-efv-mcp a loaded runner
# turned 0.105s into 0.55s on 2026-08-21 and tore the same assertion there,
# with more room to spare than this one had. Raising the budget does not shrink
# that stall, it makes the stall small *relative to* what is measured.
_BUDGET = 0.5
_CUT_BY = 2.5
_SLOW_RESPONSE = 8.0


@pytest.fixture(autouse=True)
async def _reset_shared_client():
    await http_client.close_client()
    yield
    await http_client.close_client()


# ─── Retry-After: read at all, and both RFC 9110 forms ───────────────────────


def _resp(status: int, retry_after: str | None = None) -> httpx.Response:
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    return httpx.Response(status, headers=headers)


def test_retry_after_reads_delta_seconds():
    assert retry.parse_retry_after(_resp(429, "120")) == 120.0


def test_retry_after_reads_an_http_date():
    when = datetime.now(UTC) + timedelta(seconds=60)
    got = retry.parse_retry_after(_resp(503, format_datetime(when, usegmt=True)))
    assert got is not None
    assert 55 <= got <= 61


def test_retry_after_treats_a_past_date_as_now():
    when = datetime.now(UTC) - timedelta(hours=1)
    assert retry.parse_retry_after(_resp(503, format_datetime(when, usegmt=True))) == 0.0


def test_retry_after_ignores_a_naive_date_timezone():
    # RFC 9110 dates are GMT; a header without a zone must not be read as local.
    when = datetime.now(UTC) + timedelta(seconds=30)
    got = retry.parse_retry_after(_resp(503, when.strftime("%a, %d %b %Y %H:%M:%S")))
    assert got is not None
    assert 25 <= got <= 31


@pytest.mark.parametrize("raw", ["", "   ", "soon", "not-a-date"])
def test_an_unreadable_retry_after_falls_back_instead_of_crashing(raw):
    # The error path is the one already going badly; a malformed header there
    # must not become a second failure.
    assert retry.parse_retry_after(_resp(429, raw)) is None


def test_retry_after_is_ignored_on_statuses_where_it_means_nothing():
    # A 500 does not answer "when should I come back"; honouring a header
    # there means sitting through a number that was never about waiting.
    assert retry.parse_retry_after(_resp(500, "120")) is None
    assert retry.parse_retry_after(None) is None


# ─── Jitter, and the cap that has to come after it ───────────────────────────


def test_the_exponential_delay_is_spread_not_deterministic():
    draws = {retry.compute_delay(1, None) for _ in range(50)}
    assert len(draws) > 1, "a deterministic backoff retries in lockstep with every other client"


def test_a_retry_after_delay_is_spread_one_sided():
    # Later than the source said is polite; earlier ignores the value read.
    draws = [retry.compute_delay(1, _err(429, "10")) for _ in range(50)]
    assert len(set(draws)) > 1
    assert all(10.0 <= d <= 12.5 for d in draws), sorted(draws)[:3]


def test_the_cap_is_a_real_bound_not_a_midpoint():
    # Jitter is random — one draw proves nothing.
    for attempt in range(1, 9):
        for _ in range(25):
            assert retry.compute_delay(attempt, None) <= retry.MAX_DELAY_SECONDS
            assert retry.compute_delay(attempt, _err(429, "86400")) <= retry.MAX_DELAY_SECONDS


def test_capping_before_the_jitter_would_have_been_missed_by_a_single_draw():
    """Counter-check for the cap ordering.

    `min(cap, base) * jitter` and `min(cap, base * jitter)` both contain a cap
    and a jitter. Only the second is bounded: the first multiplies an already
    capped value by up to 1.5. That ordering shipped in six portfolio servers
    because it reads correctly. Reproduced here so the test above is known to
    be able to fail.
    """
    broken = [min(retry.BASE_DELAY_SECONDS * 2**7, retry.MAX_DELAY_SECONDS) * 1.5 for _ in range(5)]
    assert all(d > retry.MAX_DELAY_SECONDS for d in broken)


def _err(status: int, retry_after: str | None = None) -> httpx.HTTPStatusError:
    resp = _resp(status, retry_after)
    return httpx.HTTPStatusError("x", request=httpx.Request("GET", URL), response=resp)


# ─── What is retried ─────────────────────────────────────────────────────────


@respx.mock
async def test_a_500_is_retried():
    # The previous implementation retried only 502/503/504 and called a 500 a
    # deterministic answer. ARCH-014 says otherwise: 5xx is retryable.
    route = respx.get(URL).mock(
        side_effect=[httpx.Response(500), httpx.Response(200, json={"ok": True})]
    )
    assert (await http_client.http_get(URL)).status_code == 200
    assert route.call_count == 2


@respx.mock
async def test_a_429_is_retried():
    route = respx.get(URL).mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json={"ok": True})]
    )
    assert (await http_client.http_get(URL)).status_code == 200
    assert route.call_count == 2


@respx.mock
async def test_a_404_fails_fast():
    route = respx.get(URL).mock(return_value=httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        await http_client.http_get(URL)
    assert route.call_count == 1, "a fourth attempt does not turn a 404 into a 200"


@respx.mock
async def test_a_network_error_is_retried_not_surfaced_on_the_first_try():
    """The case the retry is built for, and the one a status-only loop misses.

    One portfolio server retried 503 three times and a refused connection from
    the same outage not once.
    """
    route = respx.get(URL).mock(
        side_effect=[httpx.ConnectError("refused"), httpx.Response(200, json={"ok": True})]
    )
    assert (await http_client.http_get(URL)).status_code == 200
    assert route.call_count == 2


@respx.mock
async def test_the_original_exception_travels_out_unwrapped():
    respx.get(URL).mock(side_effect=httpx.ConnectTimeout("boom"))
    with pytest.raises(httpx.ConnectTimeout):
        await http_client.http_get(URL)


@respx.mock
async def test_attempts_are_bounded():
    route = respx.get(URL).mock(return_value=httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        await http_client.http_get(URL)
    assert route.call_count == retry.MAX_ATTEMPTS


# ─── The budget, measured on the wall clock ──────────────────────────────────


@respx.mock
async def test_a_slow_response_is_cut_by_the_wall_clock_deadline():
    """The assertion a fake clock cannot refute.

    A clock that only advances when something sleeps cannot disprove a claim
    about *real* time: the code that ignores the wall clock never sleeps, so
    no time passes and the broken version stays green. This test therefore
    sleeps for real — deliberately, and it is the only one here that does.

    The margins are wide on purpose — see `_BUDGET` above for the measurement
    that set them. The first call through a fresh shared client happens before
    the clock starts, so the measured window holds the deadline and nothing
    else.
    """
    # Warm-up on the untouched default budget: pays whatever the first call
    # through a fresh shared client costs, outside the window measured below.
    route = respx.get(URL).mock(return_value=httpx.Response(200))
    await retry.fetch_with_retry(http_client.get_client(), URL)

    async def _slow(request):
        await asyncio.sleep(_SLOW_RESPONSE)
        return httpx.Response(200)

    route.mock(side_effect=_slow)
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        await retry.fetch_with_retry(http_client.get_client(), URL, total_budget=_BUDGET)
    elapsed = time.monotonic() - started

    # Two-sided on purpose. The upper bound is the guarantee: a response that
    # would have taken _SLOW_RESPONSE was cut. The lower bound says the cut came
    # from the budget rather than from something failing straight away — a
    # deadline computed wrong sails through an upper bound alone.
    assert elapsed >= _BUDGET / 2, f"cut too early to be the budget: {elapsed:.3f}s"
    assert elapsed < _CUT_BY, f"the per-operation timeout is not a budget: {elapsed:.2f}s"


@respx.mock
async def test_a_wait_that_would_outlast_the_budget_is_not_taken(monkeypatch):
    # Sleeping past the caller's deadline buys nothing and costs the source a
    # request. The loop stops instead.
    monkeypatch.setattr(retry, "compute_delay", lambda *_a, **_k: 999.0)
    route = respx.get(URL).mock(return_value=httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        await retry.fetch_with_retry(http_client.get_client(), URL, total_budget=1.0)
    assert route.call_count == 1


# ─── The seam, and why it is not `asyncio.sleep` ─────────────────────────────


async def test_the_no_backoff_fixture_leaves_the_global_asyncio_sleep_alone():
    """Guards the seam the conftest fixture patches.

    `monkeypatch.setattr(retry.asyncio, "sleep", ...)` would look local and
    reach the stdlib module, disabling `asyncio.sleep` for the whole process —
    including foreign tests that use it to yield to the event loop, which then
    measure nothing and stay green. That is how a concurrency check broke in
    `srgssr-mcp` without turning red. The fixture patches `retry._sleep`
    instead; this test fails if it ever moves.
    """
    started = time.monotonic()
    await asyncio.sleep(0.05)
    assert time.monotonic() - started >= 0.04, "asyncio.sleep is disabled process-wide"


# ─── The transport must not retry underneath us ──────────────────────────────


async def test_exactly_one_level_retries():
    """Counter-check for the stacking the previous version shipped.

    `AsyncHTTPTransport(retries=2)` under a loop of 4 is 3 x 4 attempts, not
    3 + 4 — and nothing in the code said so.
    """
    assert http_client.CONNECT_RETRIES == 0
    client = http_client.get_client()
    transport = client._transport
    assert getattr(transport, "_pool", None) is not None
    assert transport._pool._retries == 0


@respx.mock
async def test_no_attempt_is_made_when_the_budget_is_already_spent():
    """The one case with no upstream exception to re-raise.

    A bare `RuntimeError` here would be indistinguishable from a bug in this
    server's own code, so it gets a named type the caller can branch on.
    """
    route = respx.get(URL).mock(return_value=httpx.Response(200))
    with pytest.raises(retry.UpstreamUnavailableError, match="no attempt made"):
        await retry.fetch_with_retry(http_client.get_client(), URL, total_budget=0.0)
    assert route.call_count == 0, "the source must not be touched at all"

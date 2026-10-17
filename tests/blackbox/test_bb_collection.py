"""FR-05 retry count and exponential back-off, and the per-source rate limit built from RunConfig.

EP on the response class (2xx accepted, 429/5xx retried, other codes not retried) and BVA on the status-code
edges, on max_retries (attempts = max_retries + 1) and on success at the last allowed attempt.
Already covered elsewhere (referenced, not repeated): max_retries 0 and 3, 503, 429-then-200, 403, 404,
TIMEOUT/NETWORK, malformed body in tests/unit/collection/test_collector_retry.py.
"""

import pytest

from pipeline.adapters.fakes import FakeHttpClient, json_response
from pipeline.core.collection.collector import Collector
from pipeline.core.collection.factory import CollectorFactory
from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.errors import CollectionError
from pipeline.core.inputs import RunConfig
from pipeline.core.ports import HttpResponse

URL = "https://api.example.test/item"


class Probe(Collector):
    """Smallest concrete collector: one logical request through the shared retry logic."""

    source_name = "probe"

    async def _collect(self, handle):
        fetch, _ = await self._fetch(handle, "probe/item", URL)
        return [fetch]


def status(code: int, body: bytes = b"{}") -> HttpResponse:
    return HttpResponse(code, body, URL)


async def outcome(route, sleep, max_retries=3) -> tuple[str, int]:
    """Returns (result code or 'OK', number of HTTP attempts)."""
    http = FakeHttpClient({URL: route})
    probe = Probe(http, RateLimiter(1, 0.0), RunConfig(min_interval_seconds=0.0, max_retries=max_retries), sleep=sleep)
    try:
        await probe.collect("octo-dev")
        return "OK", len(http.calls)
    except CollectionError as err:
        return err.code, len(http.calls)


# Attempts = max_retries + 1, back-off doubles from 0.5 s (interior values 1 and 2; 0 and 3 are referenced)
@pytest.mark.parametrize(
    ("max_retries", "delays"),
    [(1, [0.5]), (2, [0.5, 1.0])],
    ids=["BB-FR05-11", "BB-FR05-12"],
)
async def test_attempts_and_backoff_follow_max_retries(sleep, max_retries, delays):  # BB-FR05-11..12
    code, attempts = await outcome(status(503), sleep, max_retries)
    assert (code, attempts) == ("HTTP_503", max_retries + 1)
    assert sleep.delays == delays


# Retried class: 429 and 5xx (edges 500 and 599)
@pytest.mark.parametrize(
    "code", [429, 500, 502, 504, 599], ids=["BB-FR05-13", "BB-FR05-14", "BB-FR05-15", "BB-FR05-16", "BB-FR05-17"]
)
async def test_429_and_5xx_are_retried_until_exhausted(sleep, code):  # BB-FR05-13..17
    assert await outcome(status(code), sleep) == (f"HTTP_{code}", 4)
    assert sleep.delays == [0.5, 1.0, 2.0]


# Not-retried class: other 4xx (neighbours of 429 and the 499/500 edge), 3xx and 1xx edges of 2xx
@pytest.mark.parametrize(
    "code",
    [400, 401, 428, 430, 499, 300, 199],
    ids=["BB-FR05-18", "BB-FR05-19", "BB-FR05-20", "BB-FR05-21", "BB-FR05-22", "BB-FR05-23", "BB-FR05-24"],
)
async def test_other_status_codes_fail_without_retry(sleep, code):  # BB-FR05-18..24
    assert await outcome(status(code), sleep) == (f"HTTP_{code}", 1)
    assert sleep.delays == []


@pytest.mark.parametrize("code", [201, 299], ids=["BB-FR05-25", "BB-FR05-26"])
async def test_2xx_edges_are_accepted(sleep, code):  # BB-FR05-25..26
    assert await outcome(status(code), sleep) == ("OK", 1)


# BVA on the number of transient failures before success: 3 (last allowed attempt) vs 4 (one too many)
async def test_success_on_the_last_allowed_attempt(sleep):  # BB-FR05-27
    route = [status(503), status(500), status(429), json_response(URL, {})]
    assert await outcome(route, sleep) == ("OK", 4)


async def test_success_one_attempt_too_late_is_a_failure(sleep):  # BB-FR05-28
    route = [status(503)] * 4 + [json_response(URL, {})]
    assert await outcome(route, sleep) == ("HTTP_503", 4)


async def test_timeout_recovers_on_the_last_allowed_attempt(sleep):  # BB-FR05-29
    timeout = CollectionError("slow", code="TIMEOUT")
    assert await outcome([timeout, timeout, timeout, json_response(URL, {})], sleep) == ("OK", 4)


# Per-source rate limit built from RunConfig; Codeforces has a 2 s floor (source terms)
@pytest.mark.parametrize(
    ("source", "interval", "expected"),
    [("github", 0.0, 0.0), ("codeforces", 0.0, 2.0), ("codeforces", 1.99, 2.0), ("codeforces", 2.01, 2.01)],
    ids=["BB-FR05-30", "BB-FR05-31", "BB-FR05-32", "BB-FR05-33"],
)
def test_limiter_interval_respects_source_floor(source, interval, expected):  # BB-FR05-30..33
    limiter = CollectorFactory.create_limiter(source, RunConfig(min_interval_seconds=interval))
    assert limiter.min_interval == expected


def test_limiter_concurrency_comes_from_config():  # BB-FR05-34
    assert CollectorFactory.create_limiter("github", RunConfig(max_requests_per_source=1)).max_concurrent == 1

"""White-box basis-path tests for Collector._fetch (M1, FR-05, NFR-02).

Design, CFG and path list: docs/milestone2/whitebox-test-design.md, section 1.
Node numbers in the docstrings refer to that CFG. V(G) = 6; path P6 is infeasible (see the design).
"""

import pytest

from pipeline.adapters.fakes import FakeHttpClient, json_response
from pipeline.core.collection.collector import Collector
from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.errors import CollectionError
from pipeline.core.inputs import RunConfig
from pipeline.core.ports import HttpResponse

URL = "https://api.example.test/wb"


class WbCollector(Collector):
    source_name = "wb"

    async def _collect(self, handle):
        fetch, _ = await self._fetch(handle, "wb/item", URL)
        return [fetch]


class RecordingSleep:
    """Replaces asyncio.sleep so back-off delays are recorded instead of waited."""

    def __init__(self):
        self.delays = []

    async def __call__(self, delay):
        self.delays.append(delay)


def make(route, max_retries=3):
    sleep = RecordingSleep()
    http = FakeHttpClient({URL: route})
    config = RunConfig(min_interval_seconds=0.0, max_retries=max_retries)
    return WbCollector(http, RateLimiter(1, 0.0), config, sleep=sleep), http, sleep


async def test_wb_col_01_first_attempt_succeeds():
    """WB-COL-01, P1: 1-2-3-5-9-11-X. 200 on the first attempt returns the payload; no retry, no sleep."""
    collector, http, sleep = make(HttpResponse(200, b'{"login": "octo"}', URL))
    fetch, parsed = await collector._fetch("octo", "wb/item", URL)
    assert parsed == {"login": "octo"}
    assert fetch.payload == b'{"login": "octo"}'
    assert len(http.calls) == 1
    assert sleep.delays == []


async def test_wb_col_02_retryable_status_with_no_retries_left_raises_it():
    """WB-COL-02, P2: 1-2-3-5-9-10-2-12-X. max_retries=0 and HTTP 503: loop exits, last error raised."""
    collector, http, sleep = make(HttpResponse(503, b"{}", URL), max_retries=0)
    with pytest.raises(CollectionError) as err:
        await collector._fetch("octo", "wb/item", URL)
    assert err.value.code == "HTTP_503"
    assert err.value.context == {"source": "wb", "endpoint": "wb/item", "url": URL}
    assert len(http.calls) == 1
    assert sleep.delays == []


async def test_wb_col_03_non_transient_transport_error_is_reraised_at_once():
    """WB-COL-03, P3: 1-2-3-5-6-7-X. A CollectionError whose code is not TIMEOUT/NETWORK is not retried."""
    collector, http, sleep = make(CollectionError("offline", code="NETWORK_DISABLED"))
    with pytest.raises(CollectionError) as err:
        await collector._fetch("octo", "wb/item", URL)
    assert err.value.code == "NETWORK_DISABLED"
    assert len(http.calls) == 1
    assert sleep.delays == []


async def test_wb_col_04_transient_error_with_no_retries_left_raises_it():
    """WB-COL-04, P4: 1-2-3-5-6-8-2-12-X. max_retries=0 and a TIMEOUT: stored error is raised after the loop."""
    collector, http, sleep = make(CollectionError("slow", code="TIMEOUT"), max_retries=0)
    with pytest.raises(CollectionError) as err:
        await collector._fetch("octo", "wb/item", URL)
    assert err.value.code == "TIMEOUT"
    assert len(http.calls) == 1
    assert sleep.delays == []


async def test_wb_col_05_retry_after_503_backs_off_then_succeeds():
    """WB-COL-05, P5: 1-2-3-5-9-10-2-3-4-5-9-11-X. 503 then 200: one back-off of 0.5 s, then success."""
    collector, http, sleep = make([HttpResponse(503, b"{}", URL), json_response(URL, {"ok": True})])
    _, parsed = await collector._fetch("octo", "wb/item", URL)
    assert parsed == {"ok": True}
    assert len(http.calls) == 2
    assert sleep.delays == [0.5]


@pytest.mark.parametrize(
    "status, retried",
    [(429, True), (499, False), (500, True), (599, True)],
)
async def test_wb_col_06_compound_retry_condition(status, retried):
    """WB-COL-06 (condition coverage, node 9): `status == 429 or status >= 500`, each operand true/false."""
    collector, http, _ = make([HttpResponse(status, b"{}", URL), json_response(URL, {})], max_retries=1)
    if retried:
        await collector._fetch("octo", "wb/item", URL)
        assert len(http.calls) == 2
    else:
        with pytest.raises(CollectionError) as err:
            await collector._fetch("octo", "wb/item", URL)
        assert err.value.code == f"HTTP_{status}"
        assert len(http.calls) == 1


async def test_wb_col_07_loop_runs_its_maximum_number_of_times():
    """WB-COL-07 (loop coverage, node 2 at its upper bound): 503 forever, max_retries=3 -> 4 calls, 3 back-offs."""
    collector, http, sleep = make(HttpResponse(503, b"{}", URL), max_retries=3)
    with pytest.raises(CollectionError) as err:
        await collector._fetch("octo", "wb/item", URL)
    assert err.value.code == "HTTP_503"
    assert len(http.calls) == 4
    assert sleep.delays == [0.5, 1.0, 2.0]

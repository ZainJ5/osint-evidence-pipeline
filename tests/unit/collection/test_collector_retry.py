"""Collector._fetch: retry with exponential back-off, error codes and raw payload capture (FR-02, NFR-02)."""

from datetime import timezone

import pytest

from pipeline.adapters.fakes import FakeHttpClient, json_response
from pipeline.core.collection.collector import Collector
from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.errors import CollectionError
from pipeline.core.inputs import RunConfig
from pipeline.core.ports import HttpResponse

URL = "https://api.example.test/item"


class ProbeCollector(Collector):
    source_name = "probe"

    async def _collect(self, handle):
        fetch, _ = await self._fetch(handle, "probe/item", URL)
        return [fetch]


def status(code: int, body: bytes = b"{}") -> HttpResponse:
    return HttpResponse(code, body, URL)


def probe(routes, sleep, max_retries=3) -> tuple[ProbeCollector, FakeHttpClient]:
    http = FakeHttpClient({URL: routes})
    config = RunConfig(min_interval_seconds=0.0, max_retries=max_retries)
    return ProbeCollector(http, RateLimiter(1, 0.0), config, sleep=sleep), http


async def test_success_returns_raw_payload_and_parsed_body(sleep):
    collector, http = probe(HttpResponse(200, b'{"a": 1}', URL), sleep)
    fetch, parsed = await collector._fetch("octo-dev", "probe/item", URL)
    assert fetch.payload == b'{"a": 1}'
    assert parsed == {"a": 1}
    assert (fetch.source, fetch.handle, fetch.endpoint) == ("probe", "octo-dev", "probe/item")
    assert fetch.fetched_at.tzinfo == timezone.utc
    assert len(http.calls) == 1 and sleep.delays == []


async def test_succeeds_on_second_try_after_503(sleep):
    collector, http = probe([status(503), json_response(URL, {"ok": True})], sleep)
    fetches = await collector.collect("octo-dev")
    assert len(fetches) == 1
    assert len(http.calls) == 2
    assert sleep.delays == [0.5]


async def test_gives_up_after_max_retries_with_last_status_code(sleep):
    collector, http = probe(status(503), sleep, max_retries=3)
    with pytest.raises(CollectionError) as err:
        await collector.collect("octo-dev")
    assert err.value.code == "HTTP_503"
    assert len(http.calls) == 4  # 1 attempt + 3 retries
    assert sleep.delays == [0.5, 1.0, 2.0]


async def test_zero_retries_means_a_single_attempt(sleep):
    collector, http = probe(status(500), sleep, max_retries=0)
    with pytest.raises(CollectionError) as err:
        await collector.collect("octo-dev")
    assert err.value.code == "HTTP_500"
    assert len(http.calls) == 1 and sleep.delays == []


async def test_404_is_not_found_and_not_retried(sleep):
    collector, http = probe(status(404), sleep)
    with pytest.raises(CollectionError) as err:
        await collector.collect("octo-dev")
    assert err.value.code == "NOT_FOUND"
    assert len(http.calls) == 1 and sleep.delays == []


async def test_other_client_error_is_reported_with_its_status(sleep):
    collector, http = probe(status(403), sleep)
    with pytest.raises(CollectionError) as err:
        await collector.collect("octo-dev")
    assert err.value.code == "HTTP_403"
    assert len(http.calls) == 1


@pytest.mark.parametrize("code", ["TIMEOUT", "NETWORK"])
async def test_transport_failure_is_retried(sleep, code):
    collector, http = probe([CollectionError("transport", code=code), json_response(URL, [])], sleep)
    assert len(await collector.collect("octo-dev")) == 1
    assert len(http.calls) == 2


async def test_timeout_forever_keeps_timeout_code(sleep):
    collector, _ = probe(CollectionError("slow", code="TIMEOUT"), sleep)
    with pytest.raises(CollectionError) as err:
        await collector.collect("octo-dev")
    assert err.value.code == "TIMEOUT"


async def test_non_transient_transport_error_is_not_retried(sleep):
    collector, http = probe(CollectionError("offline", code="NETWORK_DISABLED"), sleep)
    with pytest.raises(CollectionError) as err:
        await collector.collect("octo-dev")
    assert err.value.code == "NETWORK_DISABLED"
    assert len(http.calls) == 1


async def test_429_is_retried(sleep):
    collector, http = probe([status(429), json_response(URL, {})], sleep)
    assert len(await collector.collect("octo-dev")) == 1
    assert sleep.delays == [0.5]


async def test_malformed_body_is_reported_and_not_retried(sleep):
    collector, http = probe(status(200, b"<html>rate limited</html>"), sleep)
    with pytest.raises(CollectionError) as err:
        await collector.collect("octo-dev")
    assert err.value.code == "MALFORMED_BODY"
    assert len(http.calls) == 1


async def test_json_body_is_sent_with_post(sleep):
    calls = []

    class PostOnly(FakeHttpClient):
        async def get(self, url, params=None):
            raise AssertionError("GET used for a POST request")

        async def post(self, url, json):
            calls.append(json)
            return json_response(url, {"data": {}})

    collector = ProbeCollector(PostOnly(), RateLimiter(1, 0.0), RunConfig(), sleep=sleep)
    await collector._fetch("octo-dev", "probe/item", URL, json_body={"query": "{ x }"})
    assert calls == [{"query": "{ x }"}]


class LimitedProbe(ProbeCollector):
    def _is_rate_limited(self, response):
        return response.status == 403


async def test_rate_limited_response_has_its_own_code_and_is_not_retried(sleep):
    http = FakeHttpClient({URL: status(403)})
    collector = LimitedProbe(http, RateLimiter(1, 0.0), RunConfig(min_interval_seconds=0.0), sleep=sleep)
    with pytest.raises(CollectionError) as err:
        await collector.collect("octo-dev")
    assert err.value.code == "RATE_LIMITED"
    assert len(http.calls) == 1 and sleep.delays == []


async def test_no_attempt_raises_a_collection_error_not_a_type_error(sleep):
    """WB-OBS-01: if the retry loop ever ran zero times, `raise None` would be a TypeError."""
    collector, http = probe(status(200), sleep)
    object.__setattr__(collector._config, "max_retries", -1)  # bypasses RunConfig validation on purpose
    with pytest.raises(CollectionError) as err:
        await collector.collect("octo-dev")
    assert err.value.code == "NO_ATTEMPT"
    assert http.calls == []

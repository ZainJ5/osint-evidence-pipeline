"""LSP contract shared by every registered collector: list[RawFetch] or CollectionError, nothing else."""

import pytest

from pipeline.adapters.fakes import FakeHttpClient
from pipeline.core.collection import CollectorFactory
from pipeline.core.errors import CollectionError
from pipeline.core.models import RawFetch
from pipeline.core.ports import HttpClient, HttpResponse

SOURCES = CollectorFactory.registered()


class ConstantHttpClient(HttpClient):
    """Answers every request with the same response, or raises the same exception."""

    def __init__(self, outcome):
        self.outcome = outcome

    async def get(self, url, params=None):
        return self._serve(url)

    async def post(self, url, json):
        return self._serve(url)

    def _serve(self, url):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return HttpResponse(self.outcome[0], self.outcome[1], url)


async def assert_contract(collector):
    try:
        fetches = await collector.collect("octo-dev")
    except CollectionError:
        return
    assert isinstance(fetches, list)
    assert all(isinstance(f, RawFetch) and f.source == collector.source_name for f in fetches)


@pytest.mark.parametrize("source", SOURCES)
async def test_happy_path_returns_non_empty_list_of_raw_fetches(source, make_collector, source_routes):
    fetches = await make_collector(source, FakeHttpClient(source_routes[source])).collect("octo-dev")
    assert isinstance(fetches, list) and fetches
    assert all(isinstance(f, RawFetch) for f in fetches)
    assert {f.source for f in fetches} == {source}


@pytest.mark.parametrize("source", SOURCES)
@pytest.mark.parametrize(
    "outcome",
    [
        (404, b'{"message": "Not Found"}'),
        (503, b""),
        (200, b"not json"),
        (200, b"null"),
        (200, b"[]"),
        (200, b"{}"),
        (200, b'"text"'),
        (200, b'{"status": "OK", "result": null, "data": {}}'),
        CollectionError("timed out", code="TIMEOUT"),
        CollectionError("refused", code="NETWORK"),
    ],
    ids=["404", "503", "garbage", "null", "list", "object", "string", "odd-shape", "timeout", "network"],
)
async def test_never_returns_none_nor_raises_a_library_exception(source, outcome, make_collector):
    await assert_contract(make_collector(source, ConstantHttpClient(outcome)))

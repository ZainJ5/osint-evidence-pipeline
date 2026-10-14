"""CollectionRunner: concurrent sources with fault isolation (FR-05, NFR-02)."""

import pytest

from pipeline.adapters.fakes import FakeHttpClient
from pipeline.core.collection import CollectionRunner, CollectorFactory
from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.errors import ValidationError
from pipeline.core.ports import HttpClient, HttpResponse

HANDLES = {"github": "octo-dev", "codeforces": "octo-dev", "leetcode": "octo-dev"}


def no_wait_limiters():
    return {source: RateLimiter(2, 0.0) for source in CollectorFactory.registered()}


def runner_for(http, config, sleep):
    return CollectionRunner(CollectorFactory, http, config, limiters=no_wait_limiters(), sleep=sleep)


def all_routes(source_routes):
    return {url: resp for routes in source_routes.values() for url, resp in routes.items()}


async def test_all_sources_succeed(source_routes, config, sleep):
    result = await runner_for(FakeHttpClient(all_routes(source_routes)), config, sleep).run(HANDLES)
    assert {f.source for f in result.fetches} == {"github", "codeforces", "leetcode"}
    assert len(result.fetches) == 6 + 3 + 1
    assert result.failures == () and not result.partial


async def test_one_source_failing_forever_yields_a_partial_result(source_routes, config, sleep):
    routes = all_routes(source_routes)
    for url in source_routes["github"]:
        routes[url] = HttpResponse(503, b"Service Unavailable", url)
    result = await runner_for(FakeHttpClient(routes), config, sleep).run(HANDLES)
    assert result.partial
    assert result.failures == (("github", "HTTP_503"),)
    assert {f.source for f in result.fetches} == {"codeforces", "leetcode"}


async def test_empty_handles_give_an_empty_result(config, sleep):
    result = await runner_for(FakeHttpClient(), config, sleep).run({})
    assert result.fetches == () and result.failures == ()


async def test_unknown_source_is_rejected(config, sleep):
    with pytest.raises(ValidationError):
        await runner_for(FakeHttpClient(), config, sleep).run({"gitlab": "octo-dev"})


async def test_unexpected_exception_is_a_bug_and_propagates(config, sleep):
    class BrokenHttpClient(HttpClient):
        async def get(self, url, params=None):
            raise RuntimeError("adapter bug")

        async def post(self, url, json):
            raise RuntimeError("adapter bug")

    with pytest.raises(RuntimeError):
        await runner_for(BrokenHttpClient(), config, sleep).run(HANDLES)


async def test_runner_reuses_one_limiter_per_source_across_runs(source_routes, config, sleep):
    runner = CollectionRunner(CollectorFactory, FakeHttpClient(all_routes(source_routes)), config, sleep=sleep)
    assert runner.limiter_for("leetcode") is runner.limiter_for("leetcode")
    assert runner.limiter_for("codeforces").min_interval == 2.0

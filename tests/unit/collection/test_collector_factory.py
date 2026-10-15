"""CollectorFactory: registry-based Factory Method, per-source rate limits and Open/Closed extension (QR-12)."""

from datetime import datetime, timezone

import pytest

from pipeline.adapters.fakes import FakeHttpClient
from pipeline.core.collection import CollectionRunner, Collector, CollectorFactory
from pipeline.core.collection.codeforces import CodeforcesCollector
from pipeline.core.collection.github import GitHubCollector
from pipeline.core.collection.leetcode import LeetCodeCollector
from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.errors import ValidationError
from pipeline.core.inputs import RunConfig
from pipeline.core.models import RawFetch


class StubCollector(Collector):
    """A fourth source added without editing any production file."""

    source_name = "stub"

    async def _collect(self, handle):
        return [RawFetch("stub", handle, "stub/profile", b"{}", datetime.now(timezone.utc))]


@pytest.fixture
def stub_registered():
    CollectorFactory.register("stub", StubCollector)
    yield
    CollectorFactory.unregister("stub")


def test_three_sources_are_registered_on_import():
    assert CollectorFactory.registered() == ("codeforces", "github", "leetcode")


@pytest.mark.parametrize(
    ("name", "cls"), [("github", GitHubCollector), ("codeforces", CodeforcesCollector), ("leetcode", LeetCodeCollector)]
)
def test_create_builds_the_registered_class(name, cls):
    assert isinstance(CollectorFactory.create(name, FakeHttpClient(), RunConfig()), cls)


def test_create_unknown_source_is_a_validation_error():
    with pytest.raises(ValidationError):
        CollectorFactory.create("gitlab", FakeHttpClient(), RunConfig())


def test_register_rejects_non_collector_classes():
    with pytest.raises(ValidationError):
        CollectorFactory.register("bad", dict)


def test_registry_is_not_a_public_mutable_attribute():
    assert not hasattr(CollectorFactory, "registry")
    assert isinstance(CollectorFactory.registered(), tuple)


def test_limiter_uses_run_config_by_default():
    limiter = CollectorFactory.create_limiter("github", RunConfig(max_requests_per_source=3, min_interval_seconds=0.25))
    assert (limiter.max_concurrent, limiter.min_interval) == (3, 0.25)


def test_codeforces_limiter_honours_api_terms_of_one_call_per_two_seconds():
    assert CollectorFactory.create_limiter("codeforces", RunConfig(min_interval_seconds=0.5)).min_interval == 2.0
    assert CollectorFactory.create_limiter("codeforces", RunConfig(min_interval_seconds=3.0)).min_interval == 3.0


def test_create_uses_a_given_limiter():
    limiter = RateLimiter(1, 0.0)
    collector = CollectorFactory.create("github", FakeHttpClient(), RunConfig(), limiter=limiter)
    assert collector.limiter is limiter


@pytest.mark.usefixtures("stub_registered")
async def test_new_source_plugs_in_without_editing_existing_code():
    assert "stub" in CollectorFactory.registered()
    runner = CollectionRunner(CollectorFactory, FakeHttpClient(), RunConfig())
    result = await runner.run({"stub": "octo-dev"})
    assert [f.endpoint for f in result.fetches] == ["stub/profile"]


def test_unregistered_stub_is_gone_after_the_test():
    assert "stub" not in CollectorFactory.registered()

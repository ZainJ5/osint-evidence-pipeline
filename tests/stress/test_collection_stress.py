"""NFR-01 stress: 20 candidates collected concurrently through one runner sharing a limiter per source."""

import asyncio
import time

import pytest

from pipeline.adapters.fakes import FakeHttpClient, json_response
from pipeline.core.collection import CollectionRunner, CollectorFactory, RateLimiter
from pipeline.core.inputs import RunConfig

CANDIDATES = 20
INTERVALS = {"github": 0.03, "codeforces": 0.04, "leetcode": 0.03}
# Real-time gaps can shrink by OS thread preemption (seen: 8.9 ms for a 10 ms interval on a busy Windows machine).
# The exact interval arithmetic is proven with a fake clock in tests/unit/collection/test_rate_limiter.py; here a
# violation means a gap clearly below the interval, i.e. two calls let through together.
TOLERANCE_SHARE = 0.25
HOSTS = {"api.github.com": "github", "codeforces.com": "codeforces", "leetcode.com": "leetcode"}


def routes_for(handle: str) -> dict:
    gh, cf = f"https://api.github.com/users/{handle}", "https://codeforces.com/api"
    repo = f"https://api.github.com/repos/{handle}/app"
    ok = {"status": "OK", "result": []}
    return {
        gh: json_response(gh, {"login": handle}),
        f"{gh}/repos": json_response(gh, [{"name": "app", "fork": False}]),
        f"{repo}/languages": json_response(repo, {"Python": 100}),
        f"{repo}/commits": json_response(repo, []),
        f"{cf}/user.info": json_response(cf, ok),
        f"{cf}/user.rating": json_response(cf, ok),
        f"{cf}/user.status": json_response(cf, ok),
    }


class RecordingLimiter(RateLimiter):
    """Records when each slot is granted. Timing the HTTP call instead would include event-loop jitter."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grants: list[float] = []

    async def __aenter__(self):
        entered = await super().__aenter__()
        self.grants.append(time.perf_counter())
        return entered


def source_of(url: str) -> str:
    return next(source for host, source in HOSTS.items() if host in url)


@pytest.mark.stress
async def test_twenty_candidates_overlap_across_sources_but_respect_per_source_intervals():
    handles = [f"cand-{i:02d}" for i in range(CANDIDATES)]
    lc = "https://leetcode.com/graphql"
    routes = {lc: json_response(lc, {"data": {"matchedUser": {"username": "x"}}})}
    for handle in handles:
        routes.update(routes_for(handle))
    http = FakeHttpClient(routes, clock=time.perf_counter, delay=0.01)
    limiters = {s: RecordingLimiter(2, interval, clock=time.perf_counter) for s, interval in INTERVALS.items()}
    runner = CollectionRunner(CollectorFactory, http, RunConfig(), limiters=limiters)

    results = await asyncio.gather(*(runner.run(dict.fromkeys(INTERVALS, h)) for h in handles))

    assert all(not r.partial and len(r.fetches) == 8 for r in results)
    for source, limiter in limiters.items():
        times = sorted(limiter.grants)
        gaps = [b - a for a, b in zip(times, times[1:], strict=False)]
        assert min(gaps) >= INTERVALS[source] * (1 - TOLERANCE_SHARE), source
    starts: dict[str, list[float]] = {s: [] for s in INTERVALS}
    for url, at in http.calls:
        starts[source_of(url)].append(at)
    spans = {s: (min(t), max(t)) for s, t in starts.items()}
    for a in spans:
        for b in spans:
            assert spans[a][0] < spans[b][1], f"{a} and {b} did not overlap"

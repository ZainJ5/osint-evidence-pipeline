"""Runs every source of a candidate concurrently; one failing source never stops the others (NFR-02)."""

import asyncio

from pipeline.core.collection.collector import Collector
from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.errors import CollectionError
from pipeline.core.inputs import RunConfig
from pipeline.core.models import CollectionResult
from pipeline.core.ports import HttpClient


class CollectionRunner:
    """Keeps one RateLimiter per source, shared by every run() on this runner."""

    def __init__(
        self,
        factory_cls,
        http: HttpClient,
        config: RunConfig,
        limiters: dict[str, RateLimiter] | None = None,
        sleep=asyncio.sleep,
    ):
        self._factory = factory_cls
        self._http = http
        self._config = config
        self._limiters = dict(limiters or {})
        self._sleep = sleep

    def limiter_for(self, source: str) -> RateLimiter:
        if source not in self._limiters:
            self._limiters[source] = self._factory.create_limiter(source, self._config)
        return self._limiters[source]

    async def run(self, handles: dict[str, str]) -> CollectionResult:
        jobs = [(source, self._collector(source), handle) for source, handle in handles.items()]
        outcomes = await asyncio.gather(*(c.collect(h) for _, c, h in jobs), return_exceptions=True)
        fetches, failures = [], []
        for (source, _, _), outcome in zip(jobs, outcomes, strict=True):
            if isinstance(outcome, CollectionError):
                failures.append((source, outcome.code))
            elif isinstance(outcome, BaseException):
                raise outcome  # anything else is a bug, not a source failure
            else:
                fetches.extend(outcome)
        return CollectionResult(tuple(fetches), tuple(failures))

    def _collector(self, source: str) -> Collector:
        return self._factory.create(
            source, self._http, self._config, limiter=self.limiter_for(source), sleep=self._sleep
        )

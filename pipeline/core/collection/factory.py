"""Factory Method with a registry: collectors register themselves, new sources need no edits here (QR-12)."""

import asyncio
from typing import ClassVar

from pipeline.core.collection.collector import Collector
from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.errors import ValidationError
from pipeline.core.inputs import RunConfig
from pipeline.core.ports import HttpClient

# Source terms that are stricter than the run configuration. Codeforces API: 1 call / 2 s.
SOURCE_LIMITS = {"codeforces": {"min_interval": 2.0}}


class CollectorFactory:
    """Registry that builds collectors by source name."""

    _registry: ClassVar[dict[str, type[Collector]]] = {}

    @classmethod
    def register(cls, name: str, collector_cls: type) -> None:
        if not (isinstance(collector_cls, type) and issubclass(collector_cls, Collector)):
            raise ValidationError(f"{collector_cls!r} is not a Collector", context={"field": "collector_cls"})
        cls._registry[name] = collector_cls

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._registry.pop(name, None)

    @classmethod
    def registered(cls) -> tuple[str, ...]:
        return tuple(sorted(cls._registry))

    @classmethod
    def create_limiter(cls, name: str, config: RunConfig) -> RateLimiter:
        floor = SOURCE_LIMITS.get(name, {}).get("min_interval", 0.0)
        return RateLimiter(config.max_requests_per_source, max(config.min_interval_seconds, floor))

    @classmethod
    def create(
        cls,
        name: str,
        http: HttpClient,
        config: RunConfig,
        limiter: RateLimiter | None = None,
        sleep=asyncio.sleep,
    ) -> Collector:
        if name not in cls._registry:
            raise ValidationError(f"unknown source '{name}'", context={"field": "source"})
        return cls._registry[name](http, limiter or cls.create_limiter(name, config), config, sleep=sleep)

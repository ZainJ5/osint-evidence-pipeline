"""M1 Source Collection. Importing this package registers the GitHub, Codeforces and LeetCode collectors."""

from pipeline.core.collection import codeforces, github, leetcode  # noqa: F401  (self-registration)
from pipeline.core.collection.collector import Collector
from pipeline.core.collection.factory import CollectorFactory
from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.collection.runner import CollectionRunner

__all__ = ["CollectionRunner", "Collector", "CollectorFactory", "RateLimiter"]

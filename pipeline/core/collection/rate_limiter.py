"""Per-source rate limiting: bounded concurrency plus a minimum gap between call starts (NFR-01)."""

import asyncio
import time

from pipeline.core.errors import ValidationError


class RateLimiter:
    """Use as `async with limiter:` around each request."""

    def __init__(self, max_concurrent: int, min_interval: float, clock=time.monotonic, sleep=asyncio.sleep):
        if max_concurrent < 1:
            raise ValidationError("max_concurrent must be >= 1", context={"field": "max_concurrent"})
        if min_interval < 0:
            raise ValidationError("min_interval must be >= 0", context={"field": "min_interval"})
        self._max_concurrent = max_concurrent
        self._min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()
        self._last_start: float | None = None

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @property
    def min_interval(self) -> float:
        return self._min_interval

    async def __aenter__(self):
        await self._semaphore.acquire()
        try:
            async with self._lock:
                await self._wait_for_turn()
        except BaseException:
            self._semaphore.release()
            raise
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._semaphore.release()

    async def _wait_for_turn(self) -> None:
        now = self._clock()
        if self._last_start is not None:
            ready_at = self._last_start + self._min_interval
            # Re-check after sleeping: timers may wake slightly early on coarse clocks.
            while now < ready_at:
                await self._sleep(ready_at - now)
                now = self._clock()
        self._last_start = now

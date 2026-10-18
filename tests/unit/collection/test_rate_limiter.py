"""RateLimiter: Boundary Value Analysis on the interval and on the concurrency bound (NFR-01)."""

import asyncio

import pytest

from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.errors import ValidationError


class FakeClock:
    """A clock whose sleep advances time instantly, so intervals are exact."""

    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.now += delay


def make_limiter(clock: FakeClock, interval: float = 0.5, max_concurrent: int = 1) -> RateLimiter:
    return RateLimiter(max_concurrent=max_concurrent, min_interval=interval, clock=clock, sleep=clock.sleep)


async def test_first_call_does_not_wait():
    clock = FakeClock()
    async with make_limiter(clock):
        pass
    assert clock.sleeps == []


async def test_back_to_back_calls_start_exactly_one_interval_apart():
    clock = FakeClock()
    limiter = make_limiter(clock)
    starts = []
    for _ in range(3):
        async with limiter:
            starts.append(clock.now)
    assert starts == [0.0, 0.5, 1.0]


async def test_no_wait_when_elapsed_equals_interval():
    clock = FakeClock()
    limiter = make_limiter(clock)
    async with limiter:
        pass
    clock.now += 0.5  # exactly on the boundary
    async with limiter:
        pass
    assert clock.sleeps == []


async def test_waits_remainder_when_elapsed_is_just_below_interval():
    clock = FakeClock()
    limiter = make_limiter(clock)
    async with limiter:
        pass
    clock.now += 0.49
    async with limiter:
        assert clock.now == pytest.approx(0.5)
    assert clock.sleeps == [pytest.approx(0.01)]


async def test_zero_interval_never_sleeps():
    clock = FakeClock()
    limiter = make_limiter(clock, interval=0.0)
    for _ in range(5):
        async with limiter:
            pass
    assert clock.sleeps == []


async def test_concurrent_callers_are_spaced_by_interval():
    clock = FakeClock()
    limiter = make_limiter(clock, interval=2.0, max_concurrent=4)
    starts = []

    async def call():
        async with limiter:
            starts.append(clock.now)

    await asyncio.gather(*(call() for _ in range(4)))
    assert sorted(starts) == [0.0, 2.0, 4.0, 6.0]


async def _peak_in_flight(limiter: RateLimiter, callers: int) -> int:
    in_flight = peak = 0

    async def call():
        nonlocal in_flight, peak
        async with limiter:
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1

    await asyncio.gather(*(call() for _ in range(callers)))
    return peak


@pytest.mark.parametrize("max_concurrent", [1, 3])
async def test_in_flight_requests_never_exceed_bound(max_concurrent):
    limiter = RateLimiter(max_concurrent=max_concurrent, min_interval=0.0)
    assert await _peak_in_flight(limiter, callers=6) == max_concurrent


async def test_slot_is_released_when_the_body_raises():
    limiter = RateLimiter(max_concurrent=1, min_interval=0.0)
    with pytest.raises(RuntimeError):
        async with limiter:
            raise RuntimeError("boom")
    await asyncio.wait_for(limiter.__aenter__(), timeout=1)
    await limiter.__aexit__(None, None, None)


@pytest.mark.parametrize(
    ("max_concurrent", "min_interval", "valid"),
    [(0, 0.5, False), (1, 0.5, True), (1, -0.01, False), (1, 0.0, True)],
)
def test_constructor_boundaries(max_concurrent, min_interval, valid):
    if valid:
        limiter = RateLimiter(max_concurrent=max_concurrent, min_interval=min_interval)
        assert (limiter.max_concurrent, limiter.min_interval) == (max_concurrent, min_interval)
    else:
        with pytest.raises(ValidationError):
            RateLimiter(max_concurrent=max_concurrent, min_interval=min_interval)

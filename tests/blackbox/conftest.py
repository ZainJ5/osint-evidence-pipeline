"""Black-box test fixtures. The whole-pipeline fixtures are reused from the system suite, not copied."""

import pytest

from pipeline.core.collection import factory

# Re-exported so pytest discovers them here as well.
from tests.system.conftest import candidate, job, system  # noqa: F401


@pytest.fixture(autouse=True)
def _no_codeforces_floor_for_pipeline_tests(request, monkeypatch):
    """Same speed-up as the system suite, applied only to whole-pipeline tests so FR-05 can test the floor."""
    if "system" in request.fixturenames:
        monkeypatch.setattr(factory, "SOURCE_LIMITS", {})


class RecordingSleep:
    """Stands in for asyncio.sleep: records each requested back-off delay and returns at once."""

    def __init__(self):
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


@pytest.fixture
def sleep():
    return RecordingSleep()

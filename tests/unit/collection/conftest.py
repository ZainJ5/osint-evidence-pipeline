"""Shared fixtures for M1 Source Collection tests."""

from pathlib import Path

import pytest

from pipeline.adapters.fakes import FakeHttpClient
from pipeline.core.collection.factory import CollectorFactory
from pipeline.core.collection.rate_limiter import RateLimiter
from pipeline.core.inputs import RunConfig
from pipeline.core.ports import HttpResponse

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "api"
HANDLE = "octo-dev"
GH = f"https://api.github.com/users/{HANDLE}"
GH_REPO = f"https://api.github.com/repos/{HANDLE}"
CF = "https://codeforces.com/api"
LEETCODE = "https://leetcode.com/graphql"


def _fixture(url: str, name: str) -> HttpResponse:
    return HttpResponse(200, (FIXTURES / name).read_bytes(), url)


class RecordingSleep:
    """Stands in for asyncio.sleep: records the requested delays and returns at once."""

    def __init__(self):
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class RecordingHttpClient(FakeHttpClient):
    """FakeHttpClient that also records the params and JSON bodies it was given."""

    def __init__(self, routes=None):
        super().__init__(routes)
        self.requests: list[tuple[str, str, dict | None]] = []

    async def get(self, url, params=None):
        self.requests.append(("GET", url, params))
        return await super().get(url, params)

    async def post(self, url, json):
        self.requests.append(("POST", url, json))
        return await super().post(url, json)


@pytest.fixture
def sleep():
    return RecordingSleep()


@pytest.fixture
def config():
    return RunConfig(min_interval_seconds=0.0)


@pytest.fixture
def source_routes():
    """Happy-path routes for octo-dev, per source."""
    github = {
        GH: _fixture(GH, "github_user.json"),
        f"{GH}/repos": _fixture(f"{GH}/repos", "github_repos.json"),
    }
    for repo in ("evidence-kit", "rust-playground"):
        github[f"{GH_REPO}/{repo}/languages"] = _fixture(GH_REPO, "github_languages.json")
        github[f"{GH_REPO}/{repo}/commits"] = _fixture(GH_REPO, "github_commits.json")
    codeforces = {
        f"{CF}/user.info": _fixture(f"{CF}/user.info", "codeforces_user_info.json"),
        f"{CF}/user.rating": _fixture(f"{CF}/user.rating", "codeforces_user_rating.json"),
        f"{CF}/user.status": _fixture(f"{CF}/user.status", "codeforces_user_status.json"),
    }
    leetcode = {LEETCODE: _fixture(LEETCODE, "leetcode_profile.json")}
    return {"github": github, "codeforces": codeforces, "leetcode": leetcode}


@pytest.fixture
def make_collector(config, sleep):
    """Build a registered collector with a no-wait limiter and the recording sleep."""

    def make(source, http, run_config=None):
        limiter = RateLimiter(max_concurrent=2, min_interval=0.0)
        return CollectorFactory.create(source, http, run_config or config, limiter=limiter, sleep=sleep)

    return make


@pytest.fixture
def recording_http():
    return RecordingHttpClient


@pytest.fixture
def fixture_bytes():
    return lambda name: (FIXTURES / name).read_bytes()

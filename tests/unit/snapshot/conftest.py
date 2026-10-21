"""Shared fixtures: the fictional user octo-dev frozen into an in-memory snapshot store."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from pipeline.adapters.fakes import InMemoryBlobStore, InMemoryRepository
from pipeline.core.models import RawFetch
from pipeline.core.snapshot.store import SnapshotStore

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "snapshots"
FETCHED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

# fixture file -> (source, endpoint)
OCTO_DEV = {
    "github_user.json": ("github", "github/user"),
    "github_repos.json": ("github", "github/repos"),
    "github_languages_hello-api.json": ("github", "github/languages/hello-api"),
    "github_languages_algo-notes.json": ("github", "github/languages/algo-notes"),
    "github_commits_hello-api.json": ("github", "github/commits/hello-api"),
    "github_commits_algo-notes.json": ("github", "github/commits/algo-notes"),
    "codeforces_user.info.json": ("codeforces", "codeforces/user.info"),
    "codeforces_user.rating.json": ("codeforces", "codeforces/user.rating"),
    "codeforces_user.status.json": ("codeforces", "codeforces/user.status"),
    "leetcode_profile.json": ("leetcode", "leetcode/profile"),
}


def raw(source: str, endpoint: str, payload: bytes) -> RawFetch:
    return RawFetch(source=source, handle="octo-dev", endpoint=endpoint, payload=payload, fetched_at=FETCHED_AT)


def fixture_fetches() -> list[RawFetch]:
    return [raw(source, endpoint, (FIXTURES / name).read_bytes()) for name, (source, endpoint) in OCTO_DEV.items()]


@pytest.fixture
def make_raw():
    return raw


@pytest.fixture
def blobs():
    return InMemoryBlobStore()


@pytest.fixture
def store(blobs):
    return SnapshotStore(blobs, InMemoryRepository())


@pytest.fixture
def frozen_store(store):
    for fetch in fixture_fetches():
        store.freeze(fetch, run_id="run-1", candidate_id="cand-1")
    return store

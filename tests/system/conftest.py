"""Shared builders for system tests: the whole pipeline wired with in-memory adapters and recorded fixtures."""

import pytest

from pipeline.adapters.fakes import (
    FakeHttpClient,
    HashingEmbedder,
    InMemoryBlobStore,
    in_memory_eraser,
    in_memory_repositories,
)
from pipeline.adapters.rule_claims import RuleBasedClaimProvider
from pipeline.core.collection import factory
from pipeline.core.inputs import CandidateInput, JobRequirementInput, RunConfig
from pipeline.core.pipeline import PipelineRun
from tests.helpers import fixture_routes


@pytest.fixture(autouse=True)
def no_codeforces_floor(monkeypatch):
    """The real 2 s Codeforces interval is covered by unit tests; system tests should not wait for it."""
    monkeypatch.setattr(factory, "SOURCE_LIMITS", {})


@pytest.fixture
def system():
    repos = in_memory_repositories()
    blobs = InMemoryBlobStore()
    http = FakeHttpClient(fixture_routes())
    config = RunConfig(min_interval_seconds=0.0)
    pipeline = PipelineRun(
        repos, blobs, http, RuleBasedClaimProvider(), in_memory_eraser(repos, blobs), HashingEmbedder(), config
    )
    return pipeline, repos, blobs, http


@pytest.fixture
def candidate():
    return CandidateInput(
        name="Octo Developer",
        email="octo@example.org",
        resume_text="Backend developer with 3 years of Python. Codeforces rating 1600. Skills: Rust, Docker",
        handles={"github": "octo-dev", "codeforces": "octo-dev", "leetcode": "octo-dev"},
    )


@pytest.fixture
def job():
    return JobRequirementInput("job-1", "Backend Engineer", "Python backend role", ("Python", "Rust", "Kubernetes"))

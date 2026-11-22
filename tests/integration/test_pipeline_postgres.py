import pytest

from pipeline.adapters.fakes import FakeHttpClient, HashingEmbedder
from pipeline.adapters.postgres import PostgresEraser
from pipeline.adapters.rule_claims import RuleBasedClaimProvider
from pipeline.core.collection import factory
from pipeline.core.inputs import CandidateInput, JobRequirementInput, RunConfig
from pipeline.core.pipeline import PipelineRun, Repositories
from pipeline.core.queries import RunProgress, RunQueries
from tests.helpers import fixture_routes

pytestmark = pytest.mark.integration


@pytest.fixture
def pipeline(database, repos, minio_store, monkeypatch):
    monkeypatch.setattr(factory, "SOURCE_LIMITS", {})
    return PipelineRun(
        Repositories(**repos),
        minio_store,
        FakeHttpClient(fixture_routes()),
        RuleBasedClaimProvider(),
        PostgresEraser(database, minio_store),
        HashingEmbedder(),
        RunConfig(min_interval_seconds=0.0),
    )


async def test_full_run_persists_replays_and_deletes_on_real_storage(pipeline, repos):
    candidate = CandidateInput(
        "Octo Developer",
        "octo@example.org",
        "3 years of Python. Codeforces rating 1600. Skills: Rust",
        {"github": "octo-dev", "codeforces": "octo-dev", "leetcode": "octo-dev"},
    )
    job = JobRequirementInput("job-integration", "Backend", "", ("Python", "Rust"))

    report = await pipeline.execute(candidate, job)

    stored = repos["score_reports"].get(report.run_id)
    assert stored.total == report.total
    assert repos["runs"].get(report.run_id).status == "done"
    assert repos["evidence_nodes"].list_by(run_id=report.run_id)

    replay = await pipeline.replay(report.run_id)
    assert replay.evidence_identical and replay.score_identical

    pipeline.delete_candidate(report.candidate_id)
    assert repos["candidates"].get(report.candidate_id) is None
    assert repos["snapshots"].list_by(candidate_id=report.candidate_id) == []


async def test_run_list_and_detail_read_from_real_storage(pipeline):
    candidate = CandidateInput("Octo Developer", "octo@example.org", "3 years of Python.", {"github": "octo-dev"})
    report = await pipeline.execute(candidate, JobRequirementInput("job-integration-ui", "Backend", "", ("Python",)))
    queries = RunQueries(pipeline.repos, pipeline.snapshot_store, RunProgress())

    assert report.run_id in {r["run_id"] for r in queries.list_runs(limit=500)}
    detail = queries.run_detail(report.run_id)
    assert detail["report"]["total"] == report.total
    assert [m["skill"] for m in detail["matches"]] == ["python"]
    assert detail["claims"][0]["verdict"]["label"]
    raw = queries.snapshot_raw(detail["snapshots"][0]["id"])
    assert raw["verified"] is True
    pipeline.delete_candidate(report.candidate_id)

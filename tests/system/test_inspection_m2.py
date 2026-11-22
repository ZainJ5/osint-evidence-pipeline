"""Regression tests for defects found in the SE431 M2 Fagan inspection (docs/milestone2/inspection-report.md).

Each test was written first and failed against the inspection baseline; the INS id names the defect it reproduces.
"""

import asyncio
import dataclasses
from urllib.parse import urlsplit

import pytest

from pipeline.adapters.fakes import FakeHttpClient, HashingEmbedder, in_memory_eraser
from pipeline.adapters.rule_claims import RuleBasedClaimProvider
from pipeline.core.errors import ValidationError
from pipeline.core.inputs import JobRequirementInput, RunConfig
from pipeline.core.pipeline import PipelineRun
from tests.helpers import fixture_routes

INTERVAL = 0.05
JITTER = 0.005  # the fake records the call a few microseconds after the limiter stamps its start


def _pipeline(repos, blobs, http, config):
    return PipelineRun(
        repos, blobs, http, RuleBasedClaimProvider(), in_memory_eraser(repos, blobs), HashingEmbedder(), config
    )


async def test_ins01_concurrent_runs_share_one_rate_limiter_per_source(system, candidate, job):
    _, repos, blobs, _ = system
    http = FakeHttpClient(fixture_routes())
    pipeline = _pipeline(repos, blobs, http, RunConfig(min_interval_seconds=INTERVAL))

    await asyncio.gather(pipeline.execute(candidate, job), pipeline.execute(candidate, job))  # NFR-01 / QR-08

    starts: dict[str, list[float]] = {}
    for url, at in http.calls:
        starts.setdefault(urlsplit(url).hostname, []).append(at)
    for host, times in starts.items():
        gaps = [b - a for a, b in zip(sorted(times), sorted(times)[1:], strict=False)]
        assert min(gaps) >= INTERVAL - JITTER, f"{host}: two runs called it {min(gaps):.4f}s apart"


async def test_ins02_reusing_a_job_id_with_different_requirements_is_rejected(system, candidate, job):
    pipeline, repos, _, _ = system
    await pipeline.execute(candidate, job)
    await pipeline.execute(candidate, job)  # the same job again is fine
    changed = JobRequirementInput(job.id, job.title, job.text, ("Go",))

    with pytest.raises(ValidationError) as err:  # FR-14: replay would score against the stored job, not this one
        await pipeline.execute(candidate, changed)

    assert err.value.code == "JOB_CONFLICT"
    assert repos.job_requirements.get(job.id) == job


async def test_ins03_replay_uses_the_configuration_recorded_with_the_run(system, candidate, job):
    pipeline, repos, blobs, http = system
    report = await pipeline.execute(candidate, job)
    assert report.total > 0
    restarted = _pipeline(repos, blobs, http, RunConfig(min_interval_seconds=0.0, link_threshold=1.0))

    result = await restarted.replay(report.run_id)  # FR-14 / NFR-07 after a configuration change

    assert result.score_identical
    assert result.report.total == report.total


async def test_ins04_unexpected_error_marks_the_run_failed(system, candidate, job):
    pipeline, repos, _, http = system
    http.routes["https://api.github.com/users/octo-dev"] = RuntimeError("bug in a collaborator")

    with pytest.raises(RuntimeError):
        await pipeline.execute(candidate, job)

    [run] = repos.runs.list_by()
    assert run.status == "failed"
    assert run.finished_at is not None


async def test_ins06_replay_compares_components_not_only_the_total(system, candidate, job):
    pipeline, repos, _, _ = system
    report = await pipeline.execute(candidate, job)
    altered = dataclasses.replace(report, components=tuple(reversed(report.components)) + report.components[:1])
    repos.score_reports.add(altered)  # same total, different explanation

    result = await pipeline.replay(report.run_id)

    assert result.report.total == altered.total
    assert result.score_identical is False

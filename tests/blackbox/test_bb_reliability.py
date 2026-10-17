"""NFR-02 / QR-04: one failure class per test case on the GitHub source; the run must finish `partial`, record the
failure with its error code, log it, and keep the other sources' evidence.

Referenced from tests/system/test_pipeline_system.py: 503 on GitHub
(test_one_source_failing_gives_partial_run_with_other_evidence). Zero failing sources gives `done`
(test_full_run_produces_bounded_explainable_report).
"""

import logging

import pytest

from pipeline.core.errors import CollectionError
from pipeline.core.ports import HttpResponse

GH_USER = "https://api.github.com/users/octo-dev"


@pytest.mark.parametrize(
    ("failure", "code"),
    [
        (CollectionError("request timed out", code="TIMEOUT"), "TIMEOUT"),
        (HttpResponse(500, b"server error", GH_USER), "HTTP_500"),
        (HttpResponse(200, b"<html>not json</html>", GH_USER), "MALFORMED_BODY"),
        (HttpResponse(404, b'{"message": "Not Found"}', GH_USER), "NOT_FOUND"),
    ],
    ids=["BB-NFR02-01", "BB-NFR02-02", "BB-NFR02-03", "BB-NFR02-04"],
)
async def test_each_failure_class_gives_a_partial_run(system, candidate, job, caplog, failure, code):  # 01..04
    pipeline, repos, _, http = system
    http.routes[GH_USER] = failure
    caplog.set_level(logging.INFO, logger="pipeline")

    report = await pipeline.execute(candidate, job)

    run = repos.runs.get(report.run_id)
    assert run.status == "partial"
    assert ("github", code) in run.failures
    assert {n.source for n in repos.evidence_nodes.list_by(run_id=report.run_id)} == {"codeforces", "leetcode"}
    assert 0 <= report.total <= 100
    logged = [r.fields.get("failures") for r in caplog.records if getattr(r, "fields", {}).get("stage") == "collect"]
    assert [("github", code)] in [list(map(tuple, f)) for f in logged]


async def test_all_sources_failing_still_finishes_partial(system, candidate, job):  # BB-NFR02-05
    pipeline, repos, _, http = system
    http.routes.clear()  # every URL now answers 404
    report = await pipeline.execute(candidate, job)

    run = repos.runs.get(report.run_id)
    assert run.status == "partial"
    assert sorted(source for source, _ in run.failures) == ["codeforces", "github", "leetcode"]
    assert report.total == 0.0

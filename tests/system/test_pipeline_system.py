import pytest

from pipeline.core.errors import SnapshotError, ValidationError
from pipeline.core.inputs import CandidateInput
from pipeline.core.ports import HttpResponse

COMPONENTS = {"verified_skills", "contribution_depth", "competitive_programming", "requirement_match"}
OWNED_TABLES = ("runs", "snapshots", "evidence_nodes", "claims", "verdicts", "score_reports", "source_accounts")


async def test_full_run_produces_bounded_explainable_report(system, candidate, job):
    pipeline, repos, _, _ = system
    report = await pipeline.execute(candidate, job)

    assert 0 <= report.total <= 100
    assert repos.runs.get(report.run_id).status == "done"
    assert {c.name for c in report.components} == COMPONENTS
    assert all(c.evidence_node_ids for c in report.components if c.value > 0)  # QR-03


async def test_every_cited_evidence_node_resolves_to_a_snapshot_of_the_run(system, candidate, job):
    pipeline, repos, _, _ = system
    report = await pipeline.execute(candidate, job)

    cited = {i for c in report.components for i in c.evidence_node_ids}
    cited |= {i for v in report.verdicts for i in v.evidence_node_ids}
    assert cited
    for node_id in cited:  # QR-03 and QR-15: auditable back to the raw fetch
        node = repos.evidence_nodes.get(node_id)
        assert node.run_id == report.run_id
        assert repos.snapshots.get(node.snapshot_id).run_id == report.run_id


async def test_all_three_accounts_are_linked_with_rationale(system, candidate, job):
    pipeline, repos, _, _ = system
    report = await pipeline.execute(candidate, job)

    links = repos.source_accounts.list_by(run_id=report.run_id)
    assert {(link.source, link.linked) for link in links} == {
        ("github", True),
        ("codeforces", True),
        ("leetcode", True),
    }
    assert all(link.rationale for link in links)


async def test_unlinked_account_evidence_is_excluded(system, job):
    pipeline, repos, _, _ = system
    stranger = CandidateInput("Someone Else", "else@example.org", "2 years of Python", {"codeforces": "octo-dev"})
    report = await pipeline.execute(stranger, job)

    links = repos.source_accounts.list_by(run_id=report.run_id)
    assert [link.linked for link in links] == [False]  # FR-09: refuse to guess
    assert report.total == 0


async def test_one_source_failing_gives_partial_run_with_other_evidence(system, candidate, job):
    pipeline, repos, _, http = system
    http.routes["https://api.github.com/users/octo-dev"] = HttpResponse(503, b"unavailable", "gh")
    report = await pipeline.execute(candidate, job)  # QR-04 / NFR-02 fault injection

    run = repos.runs.get(report.run_id)
    assert run.status == "partial"
    assert ("github", "HTTP_503") in run.failures
    sources = {n.source for n in repos.evidence_nodes.list_by(run_id=report.run_id)}
    assert sources == {"codeforces", "leetcode"}


async def test_replay_reproduces_evidence_and_score_without_network(system, candidate, job):
    pipeline, _, _, http = system
    report = await pipeline.execute(candidate, job)
    calls_before = len(http.calls)

    result = await pipeline.replay(report.run_id)  # FR-14 / NFR-07

    assert len(http.calls) == calls_before
    assert result.evidence_identical and result.score_identical
    assert result.report.total == report.total


async def test_replay_of_tampered_snapshot_is_refused(system, candidate, job):
    pipeline, _, blobs, _ = system
    report = await pipeline.execute(candidate, job)
    key = next(iter(blobs.objects))
    blobs.objects[key] = blobs.objects[key] + b" "

    with pytest.raises(SnapshotError):  # QR-14
        await pipeline.replay(report.run_id)


async def test_delete_candidate_removes_rows_and_blobs(system, candidate, job):
    pipeline, repos, blobs, _ = system
    report = await pipeline.execute(candidate, job)

    pipeline.delete_candidate(report.candidate_id)  # FR-16

    assert repos.candidates.get(report.candidate_id) is None
    for name in OWNED_TABLES:
        assert getattr(repos, name).list_by(candidate_id=report.candidate_id) == []
    assert blobs.objects == {}


async def test_replay_of_unknown_run_is_rejected(system):
    pipeline, _, _, _ = system
    with pytest.raises(ValidationError):
        await pipeline.replay("missing")

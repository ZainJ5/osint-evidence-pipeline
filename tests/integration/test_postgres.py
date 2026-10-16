from datetime import datetime, timezone

import pytest

from pipeline.adapters.fakes import InMemoryBlobStore
from pipeline.adapters.postgres import PostgresEraser
from pipeline.core.errors import SnapshotError
from pipeline.core.inputs import JobRequirementInput
from pipeline.core.models import (
    AccountLink,
    CandidateRecord,
    Claim,
    EvidenceNode,
    RawFetch,
    RunRecord,
    ScoreComponent,
    ScoreReport,
    SkillMatch,
    Verdict,
)
from pipeline.core.snapshot.store import SnapshotStore

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def seed(repos, uid):
    """A candidate with one run, one snapshot and one evidence node; returns (candidate, run, snapshot, node)."""
    candidate = CandidateRecord(
        uid("cand"), "Octo Dev", "octo.dev@example.com", "Python dev", {"github": "octo-dev"}, NOW
    )
    run = RunRecord(uid("run"), candidate.id, "job-1", "running", NOW)
    repos["candidates"].add(candidate)
    repos["runs"].add(run)
    store = SnapshotStore(InMemoryBlobStore(), repos["snapshots"])
    snapshot = store.freeze(RawFetch("github", "octo-dev", "github/repos", b"[]", NOW), run.id, candidate.id)
    node = EvidenceNode(
        uid("node"), run.id, candidate.id, snapshot.id, "github", "octo-dev", "skill", {"name": "Python"}, "$[0]"
    )
    repos["evidence_nodes"].add(node)
    return candidate, run, snapshot, node


def test_candidate_run_snapshot_evidence_round_trip(repos, uid):
    candidate, run, snapshot, node = seed(repos, uid)
    assert repos["candidates"].get(candidate.id) == candidate
    assert repos["runs"].get(run.id) == run
    assert repos["snapshots"].get(snapshot.id) == snapshot
    assert repos["evidence_nodes"].list_by(run_id=run.id) == [node]


def test_run_add_is_an_upsert_for_status_changes(repos, uid):
    _, run, _, _ = seed(repos, uid)
    finished = RunRecord(
        run.id, run.candidate_id, run.job_id, "partial", NOW, NOW, {"w": 4}, (("leetcode", "TIMEOUT"),)
    )
    repos["runs"].add(finished)
    assert repos["runs"].get(run.id) == finished


def test_other_repositories_round_trip(repos, uid):
    candidate, run, _, node = seed(repos, uid)
    job = JobRequirementInput(uid("job"), "Backend", "Python APIs", ("python", "docker"))
    claim = Claim(uid("claim"), candidate.id, "3 years of Python", "skill", "Python", years=3.0)
    verdict = Verdict(claim.id, run.id, candidate.id, "supported", (node.id,), "repo language")
    link = AccountLink(candidate.id, run.id, "github", "octo-dev", 0.9, True, ("email match",))
    solved = Claim(uid("claim"), candidate.id, "300 problems on LeetCode", "solved", "leetcode", solved=300)
    matches = (SkillMatch("python", (node.id,), 1.0), SkillMatch("docker", (), 0.0))
    report = ScoreReport(
        run.id, candidate.id, job.id, 80.0, (ScoreComponent("coverage", 1.0, 0.8, (node.id,)),), (verdict,), matches
    )
    for name, item in [
        ("job_requirements", job),
        ("claims", claim),
        ("claims", solved),
        ("verdicts", verdict),
        ("source_accounts", link),
        ("score_reports", report),
    ]:
        repos[name].add(item)
    assert repos["job_requirements"].get(job.id) == job
    assert repos["claims"].get(claim.id) == claim
    assert repos["claims"].get(solved.id) == solved
    assert repos["verdicts"].get(f"{claim.id}:{run.id}") == verdict
    assert repos["source_accounts"].get(f"{run.id}:github:octo-dev") == link
    assert repos["score_reports"].get(run.id) == report


def test_freeze_is_idempotent_in_postgres(repos, uid):
    candidate, run, snapshot, _ = seed(repos, uid)
    store = SnapshotStore(InMemoryBlobStore(), repos["snapshots"])
    again = store.freeze(RawFetch("github", "octo-dev", "github/repos", b"[]", NOW), run.id, candidate.id)
    other = store.freeze(RawFetch("github", "octo-dev", "github/commits/x", b"[]", NOW), run.id, candidate.id)
    assert again == snapshot
    assert other.id != snapshot.id and other.object_key == snapshot.object_key
    assert len(store.list_for_run(run.id)) == 2


def test_snapshot_insert_violating_foreign_key_raises_snapshot_error(repos, uid):
    store = SnapshotStore(InMemoryBlobStore(), repos["snapshots"])
    with pytest.raises(SnapshotError) as err:
        store.freeze(RawFetch("github", "octo-dev", "github/user", b"{}", NOW), uid("no-run"), uid("no-cand"))
    assert err.value.code == "DB_ERROR"


def test_eraser_removes_every_candidate_row_and_unshared_blobs(database, repos, uid):
    blobs = InMemoryBlobStore()
    candidate, run, snapshot, _ = seed(repos, uid)
    store = SnapshotStore(blobs, repos["snapshots"])
    mine = store.freeze(RawFetch("github", "octo-dev", "github/user", b'{"only": "mine"}', NOW), run.id, candidate.id)
    other_candidate, other_run, _, _ = seed(repos, uid)
    shared = store.freeze(
        RawFetch("github", "octo-dev", "github/user", b'{"only": "mine"}', NOW), other_run.id, other_candidate.id
    )
    unshared_key = store.freeze(
        RawFetch("leetcode", "octo-dev", "leetcode/profile", b'{"me": 1}', NOW), run.id, candidate.id
    ).object_key

    PostgresEraser(database, blobs).delete_candidate(candidate.id)

    assert repos["candidates"].get(candidate.id) is None
    for name in ["runs", "snapshots", "evidence_nodes"]:
        assert repos[name].list_by(candidate_id=candidate.id) == []
    assert repos["snapshots"].get(snapshot.id) is None
    assert unshared_key not in blobs.objects
    assert mine.object_key == shared.object_key and shared.object_key in blobs.objects  # still used by the other
    assert repos["candidates"].get(other_candidate.id) is not None

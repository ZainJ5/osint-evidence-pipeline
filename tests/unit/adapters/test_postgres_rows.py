import json
from datetime import datetime, timezone

import pytest

from pipeline.adapters.postgres import TABLES, PostgresRepository, build_repositories
from pipeline.core.errors import ValidationError
from pipeline.core.models import Claim, RunRecord, ScoreComponent, ScoreReport, SkillMatch, Verdict

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class NoDatabase:
    """Any query is a test failure: these tests cover the pure mapping code only."""

    def query(self, *args, **kwargs):
        raise AssertionError("database must not be touched")


def test_every_table_has_a_repository():
    repos = build_repositories(NoDatabase())
    assert set(repos) == set(TABLES)
    assert all(isinstance(r, PostgresRepository) for r in repos.values())


def test_runs_are_the_only_upserted_table():
    assert [name for name, table in TABLES.items() if table.upsert] == ["runs"]


def test_run_round_trips_through_row():
    repo = build_repositories(NoDatabase())["runs"]
    run = RunRecord("r1", "c1", "j1", "partial", NOW, NOW, {"workers": 4}, (("github", "TIMEOUT"),), None)
    row = repo.to_row(run)
    assert row["config"].obj == {"workers": 4}
    plain = {k: getattr(v, "obj", v) for k, v in row.items()}
    plain["failures"] = [list(f) for f in plain["failures"]]  # what JSONB gives back
    assert repo.from_row(plain) == run


def test_score_report_round_trips_through_row():
    repo = build_repositories(NoDatabase())["score_reports"]
    verdict = Verdict("cl1", "r1", "c1", "supported", ("n1", "n2"), "seen in repo")
    report = ScoreReport("r1", "c1", "j1", 72.5, (ScoreComponent("coverage", 0.5, 0.8, ("n1",)),), (verdict,))
    row = repo.to_row(report)
    plain = {
        "run_id": "r1",
        "candidate_id": "c1",
        "job_id": "j1",
        "total": 72.5,
        "components": [{"name": "coverage", "weight": 0.5, "value": 0.8, "evidence_node_ids": ["n1"]}],
        "verdicts": [{**row["verdicts"].obj[0], "evidence_node_ids": ["n1", "n2"]}],
    }
    assert repo.from_row(plain) == report


def test_score_report_matches_round_trip_as_skill_matches():
    repo = build_repositories(NoDatabase())["score_reports"]
    matches = (SkillMatch("python", ("n1",), 1.0), SkillMatch("kubernetes", (), 0.0))
    report = ScoreReport("r1", "c1", "j1", 50.0, (), (), matches)
    row = {k: json.loads(json.dumps(getattr(v, "obj", v))) for k, v in repo.to_row(report).items()}  # as JSONB
    assert row["matches"] == [
        {"skill": "python", "node_ids": ["n1"], "similarity": 1.0},
        {"skill": "kubernetes", "node_ids": [], "similarity": 0.0},
    ]
    assert repo.from_row(row) == report


def test_report_stored_before_matches_existed_reads_with_no_matches():
    repo = build_repositories(NoDatabase())["score_reports"]
    row = {"run_id": "r1", "candidate_id": "c1", "job_id": "j1", "total": 0.0, "components": [], "verdicts": []}
    assert repo.from_row(row).matches == ()


def test_claim_solved_is_a_column():
    repo = build_repositories(NoDatabase())["claims"]
    claim = Claim("cl1", "c1", "300 LeetCode problems", "solved", "leetcode", solved=300)
    row = repo.to_row(claim)
    assert row["solved"] == 300
    assert repo.from_row(row) == claim


def test_list_by_rejects_unknown_columns():
    repo = build_repositories(NoDatabase())["snapshots"]
    with pytest.raises(ValidationError):
        repo.list_by(**{"run_id; DROP TABLE snapshots": "x"})


def test_get_with_malformed_composite_key_returns_none():
    repo = build_repositories(NoDatabase())["verdicts"]
    assert repo.get("only-one-part") is None

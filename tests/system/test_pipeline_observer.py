"""Orchestrator features the web UI relies on: progress events, fixed run ids, stored claims, matches, anchor links."""

import pytest

from pipeline.core.errors import ValidationError
from pipeline.core.inputs import CandidateInput, JobRequirementInput
from pipeline.core.pipeline import RunObserver

STAGES = ["collect", "freeze", "extract", "resolve", "match", "verify", "score"]


class Recorder(RunObserver):
    def __init__(self):
        self.events = []

    def on_event(self, run_id, stage, status, detail):
        self.events.append((run_id, stage, status, detail))


class Broken(RunObserver):
    def on_event(self, run_id, stage, status, detail):
        raise RuntimeError("observer bug")


async def test_observer_sees_every_stage_start_and_finish_in_order(system, candidate, job):
    pipeline, _, _, _ = system
    recorder = Recorder()

    report = await pipeline.execute(candidate, job, run_id="run-fixed", observer=recorder)

    assert report.run_id == "run-fixed"
    assert {e[0] for e in recorder.events} == {"run-fixed"}
    assert [(e[1], e[2]) for e in recorder.events] == [(s, st) for s in STAGES for st in ("started", "done")]
    done = {e[1]: e[3] for e in recorder.events if e[2] == "done"}
    assert done["collect"]["fetches"] > 0 and done["collect"]["failures"] == []
    assert done["freeze"]["snapshots"] > 0
    assert done["extract"]["nodes"] > 0
    assert done["resolve"]["linked"] == ["codeforces:octo-dev", "github:octo-dev", "leetcode:octo-dev"]
    assert done["match"]["coverage"] == pytest.approx(2 / 3)
    assert done["verify"]["claims"] == 4
    assert done["score"]["total"] == report.total


async def test_a_failing_observer_never_breaks_the_run(system, candidate, job):
    pipeline, repos, _, _ = system

    report = await pipeline.execute(candidate, job, observer=Broken())

    assert repos.runs.get(report.run_id).status == "done"


async def test_register_job_rejects_a_conflicting_job_before_any_run(system, job):
    pipeline, repos, _, _ = system
    pipeline.register_job(job)

    with pytest.raises(ValidationError) as err:
        pipeline.register_job(JobRequirementInput(job.id, job.title, job.text, ("Go",)))

    assert err.value.code == "JOB_CONFLICT"
    assert repos.runs.list_by() == []


async def test_report_keeps_the_per_skill_matches(system, candidate, job):
    pipeline, repos, _, _ = system

    report = await pipeline.execute(candidate, job)

    assert [m.skill for m in report.matches] == ["python", "rust", "kubernetes"]
    assert [m.covered for m in report.matches] == [True, True, False]
    assert repos.score_reports.get(report.run_id).matches == report.matches


async def test_replay_reuses_the_stored_claims_instead_of_asking_the_llm_again(system, candidate, job):
    pipeline, _, _, _ = system
    report = await pipeline.execute(candidate, job)

    def changed_answer(prompt, schema):  # a real LLM may answer differently the second time
        return {"claims": [{"text": "10 years of COBOL", "kind": "skill", "subject": "COBOL", "years": 10}]}

    pipeline._claims._llm.complete = changed_answer  # pylint: disable=protected-access

    result = await pipeline.replay(report.run_id)

    assert result.score_identical and result.evidence_identical  # NFR-07


async def test_resume_link_to_the_github_profile_links_an_account_with_another_name(system, job):
    pipeline, repos, _, _ = system
    resume = "Jane Smith - backend developer. 3 years of Python. https://github.com/octo-dev"
    candidate = CandidateInput("Jane Smith", "jane@example.net", resume, {"github": "octo-dev"})
    without_link = CandidateInput("Jane Smith", "jane@example.net", "3 years of Python.", {"github": "octo-dev"})

    linked = await pipeline.execute(candidate, job)
    unlinked = await pipeline.execute(without_link, job)

    [link] = repos.source_accounts.list_by(run_id=linked.run_id)
    assert link.linked and any(r.startswith("cross_link") for r in link.rationale)
    assert [a.linked for a in repos.source_accounts.list_by(run_id=unlinked.run_id)] == [False]


def test_preview_claims_uses_the_run_extractor(system):
    pipeline, repos, _, _ = system

    claims = pipeline.preview_claims("3 years of Python. Codeforces rating 1600.")

    assert {(c.kind, c.subject) for c in claims} == {("rating", "codeforces"), ("skill", "Python")}
    assert repos.claims.list_by() == []  # nothing is stored for a preview

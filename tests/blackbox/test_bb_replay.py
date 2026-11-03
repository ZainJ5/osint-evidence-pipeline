"""FR-14 replay: EP on the state of the run being replayed (done / partial = valid; running / failed / unknown =
invalid). Referenced from tests/system/test_pipeline_system.py: replay of a done run
(test_replay_reproduces_evidence_and_score_without_network) and of an unknown id
(test_replay_of_unknown_run_is_rejected).
"""

from datetime import datetime, timezone

import pytest

from pipeline.core.errors import ValidationError
from pipeline.core.models import RunRecord
from pipeline.core.ports import HttpResponse


@pytest.mark.parametrize("state", ["running", "failed"], ids=["BB-FR14-01", "BB-FR14-02"])
async def test_replay_of_a_run_that_is_not_finished_is_refused(system, state):  # BB-FR14-01..02
    pipeline, repos, _, http = system
    repos.runs.add(RunRecord("run-x", "cand-x", "job-1", state, datetime.now(timezone.utc)))
    with pytest.raises(ValidationError) as err:
        await pipeline.replay("run-x")
    assert err.value.code == "RUN_NOT_FOUND"
    assert http.calls == []


async def test_replay_of_empty_run_id_is_refused(system):  # BB-FR14-03
    with pytest.raises(ValidationError):
        await system[0].replay("")


async def test_replay_of_a_partial_run_reproduces_it(system, candidate, job):  # BB-FR14-04
    pipeline, repos, _, http = system
    http.routes["https://api.github.com/users/octo-dev"] = HttpResponse(404, b"{}", "gh")
    report = await pipeline.execute(candidate, job)
    assert repos.runs.get(report.run_id).status == "partial"
    calls = len(http.calls)

    result = await pipeline.replay(report.run_id)

    assert len(http.calls) == calls
    assert result.evidence_identical and result.score_identical

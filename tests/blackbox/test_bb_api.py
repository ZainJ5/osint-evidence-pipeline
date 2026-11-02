"""FR-15 REST API: EP on request bodies and on known / unknown resource ids.

Referenced from tests/system/test_api.py: valid body 200 + report + replay + delete 204
(test_run_report_replay_delete_round_trip) and invalid email 422 VALIDATION_ERROR
(test_invalid_input_is_rejected_at_the_boundary).
"""

import pytest
from fastapi.testclient import TestClient

from pipeline.core.inputs import MAX_RESUME_CHARS
from pipeline.interface.api import create_app

CANDIDATE = {
    "name": "Octo Developer",
    "email": "octo@example.org",
    "resume_text": "3 years of Python. Codeforces rating 1600.",
    "handles": {"github": "octo-dev", "codeforces": "octo-dev", "leetcode": "octo-dev"},
}
JOB = {"id": "job-1", "title": "Backend", "text": "", "required_skills": ["Python", "Rust"]}


@pytest.fixture
def client(system):
    return TestClient(create_app(system[0]))


def body(candidate=None, job=None):
    return {"candidate": {**CANDIDATE, **(candidate or {})}, "job": {**JOB, **(job or {})}}


@pytest.mark.parametrize(
    "overrides",
    [
        {"job": {"required_skills": []}},
        {"job": {"required_skills": [f"s{i}" for i in range(51)]}},
        {"job": {"required_skills": ["Python", "  "]}},
        {"candidate": {"name": ""}},
        {"candidate": {"handles": {"github": "-octo"}}},
        {"candidate": {"handles": {"gitlab": "octo"}}},
        {"candidate": {"resume_text": "x" * (MAX_RESUME_CHARS + 1)}},
    ],
    ids=["BB-FR15-01", "BB-FR15-02", "BB-FR15-03", "BB-FR15-04", "BB-FR15-05", "BB-FR15-06", "BB-FR15-07"],
)
def test_domain_invalid_body_is_422_validation_error(client, overrides):  # BB-FR15-01..07
    response = client.post("/runs", json=body(**overrides))
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_fifty_required_skills_is_accepted(client):  # BB-FR15-08 (upper boundary, valid)
    response = client.post("/runs", json=body(job={"required_skills": [f"s{i}" for i in range(49)] + ["Python"]}))
    assert response.status_code == 200
    assert 0 <= response.json()["total"] <= 100


def test_body_missing_a_field_is_422(client):  # BB-FR15-09 (schema-invalid class)
    bad = body()
    del bad["candidate"]["email"]
    assert client.post("/runs", json=bad).status_code == 422


def test_report_of_unknown_run_is_404(client):  # BB-FR15-10
    assert client.get("/runs/no-such-run/report").status_code == 404


def test_replay_of_unknown_run_is_404_run_not_found(client):  # BB-FR15-11
    response = client.post("/runs/no-such-run/replay")
    assert response.status_code == 404
    assert response.json()["code"] == "RUN_NOT_FOUND"


def test_delete_of_unknown_candidate_is_404_candidate_not_found(client):  # BB-FR15-12
    response = client.delete("/candidates/no-such-candidate")
    assert response.status_code == 404
    assert response.json()["code"] == "CANDIDATE_NOT_FOUND"


def test_delete_twice_is_204_then_404(client):  # BB-FR15-13
    candidate_id = client.post("/runs", json=body()).json()["candidate_id"]
    assert client.delete(f"/candidates/{candidate_id}").status_code == 204
    assert client.delete(f"/candidates/{candidate_id}").status_code == 404

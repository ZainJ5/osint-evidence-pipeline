from fastapi.testclient import TestClient

from pipeline.interface.api import create_app

BODY = {
    "candidate": {
        "name": "Octo Developer",
        "email": "octo@example.org",
        "resume_text": "3 years of Python. Codeforces rating 1600.",
        "handles": {"github": "octo-dev", "codeforces": "octo-dev", "leetcode": "octo-dev"},
    },
    "job": {"id": "job-1", "title": "Backend", "text": "", "required_skills": ["Python", "Rust"]},
}


def test_run_report_replay_delete_round_trip(system):
    client = TestClient(create_app(system[0]))

    created = client.post("/runs", json=BODY)
    assert created.status_code == 200
    body = created.json()

    assert client.get(f"/runs/{body['run_id']}/report").json()["total"] == body["total"]
    assert client.post(f"/runs/{body['run_id']}/replay").json()["score_identical"] is True
    assert client.delete(f"/candidates/{body['candidate_id']}").status_code == 204
    assert client.get(f"/runs/{body['run_id']}/report").status_code == 404


def test_invalid_input_is_rejected_at_the_boundary(system):
    client = TestClient(create_app(system[0]))
    bad = {**BODY, "candidate": {**BODY["candidate"], "email": "not-an-email"}}

    response = client.post("/runs", json=bad)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_openapi_schema_is_published(system):
    schema = TestClient(create_app(system[0])).get("/openapi.json").json()  # QR-16
    paths = {"/runs", "/runs/{run_id}/replay", "/runs/{run_id}/report", "/candidates/{candidate_id}"}
    assert paths <= set(schema["paths"])


def test_shutting_down_the_app_closes_the_http_client(system):
    """INS-11 / V-10: the FastAPI lifespan releases the HTTP connection pool at shutdown."""
    pipeline, _, _, http = system
    closed = []

    async def aclose():
        closed.append(True)

    http.aclose = aclose
    with TestClient(create_app(pipeline)) as client:
        assert client.get("/health").status_code == 200
        assert closed == []
    assert closed == [True]

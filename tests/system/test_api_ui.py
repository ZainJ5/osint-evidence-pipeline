"""Endpoints of docs/api-contract.md used by the web UI, over the in-memory pipeline."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pipeline.interface.api import create_app
from tests.resume_files import make_docx

SAMPLE_TXT = Path(__file__).resolve().parents[1] / "fixtures" / "resumes" / "sample.txt"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
BODY = {
    "candidate": {
        "name": "Octo Developer",
        "email": "octo@example.org",
        "resume_text": "3 years of Python. Codeforces rating 1600. Skills: Rust",
        "handles": {"github": "octo-dev", "codeforces": "octo-dev", "leetcode": "octo-dev"},
    },
    "job": {"id": "backend-1", "title": "Backend Engineer", "text": "", "required_skills": ["Python", "Kubernetes"]},
}
STAGES = ["collect", "freeze", "extract", "resolve", "match", "verify", "score"]


@pytest.fixture
def client(system):
    with TestClient(create_app(system[0], storage="memory")) as test_client:  # one event loop for background runs
        yield test_client


def finished(client, run_id: str) -> dict:
    for _ in range(200):
        detail = client.get(f"/runs/{run_id}").json()
        if detail["run"]["status"] != "running":
            return detail
        time.sleep(0.02)
    raise AssertionError("run did not finish")


def test_health_names_storage_and_extractor(client):
    assert client.get("/health").json() == {"status": "ok", "storage": "memory", "extractor": "rule-based"}


def test_parse_txt_resume_returns_text_identity_and_claim_preview(client):
    response = client.post("/resumes/parse", files={"file": ("octo_cv.txt", SAMPLE_TXT.read_bytes(), "text/plain")})

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "octo_cv.txt"
    assert body["name"] == "Octo Developer"
    assert body["email"] == "octo@example.org"
    assert body["handles"] == {"github": "octo-dev", "codeforces": "octo-dev"}
    assert body["links"] == ["https://github.com/octo-dev", "https://codeforces.com/profile/octo-dev"]
    assert body["extractor"] == "rule-based"
    assert {c["subject"] for c in body["claims"]} >= {"Python", "codeforces", "Rust"}
    assert set(body["claims"][0]) == {"text", "kind", "subject", "years", "rating", "solved"}


def test_parse_docx_resume(client):
    data = make_docx(["Jane Doe", "jane@example.org", "4 years of Go"], link="https://leetcode.com/u/jane-lc/")

    body = client.post("/resumes/parse", files={"file": ("cv.docx", data, DOCX_MIME)}).json()

    assert body["name"] == "Jane Doe"
    assert body["handles"] == {"leetcode": "jane-lc"}
    assert [c["subject"] for c in body["claims"]] == ["Go"]


@pytest.mark.parametrize(
    ("filename", "data", "code"),
    [("cv.exe", b"MZ", "UNSUPPORTED_FILE"), ("cv.txt", b"   ", "EMPTY_RESUME")],
)
def test_parse_rejects_bad_files_with_422(client, filename, data, code):
    response = client.post("/resumes/parse", files={"file": (filename, data, "application/octet-stream")})
    assert response.status_code == 422
    assert response.json()["code"] == code


def test_start_runs_in_the_background_and_detail_is_consistent(client):
    started = client.post("/runs/start", json=BODY)
    assert started.status_code == 202

    detail = finished(client, started.json()["run_id"])

    run = detail["run"]
    assert run["status"] == "done" and run["stage"] == "finished" and run["finished_at"]
    assert run["failures"] == [] and run["config"]["link_threshold"] == 0.5
    assert [(p["stage"], p["status"]) for p in detail["progress"]] == [
        (s, x) for s in STAGES for x in ("started", "done")
    ]
    assert detail["candidate"]["email_masked"] == "o***@example.org"
    assert "email" not in detail["candidate"]
    assert detail["job"]["required_skills"] == ["Python", "Kubernetes"]
    assert {a["profile_url"] for a in detail["accounts"]} == {
        "https://github.com/octo-dev",
        "https://codeforces.com/profile/octo-dev",
        "https://leetcode.com/u/octo-dev/",
    }
    assert all(a["linked"] and a["rationale"] for a in detail["accounts"])
    snapshot_ids = {s["id"] for s in detail["snapshots"]}
    assert all(e["snapshot_id"] in snapshot_ids and e["linked"] for e in detail["evidence"])
    evidence_ids = {e["id"] for e in detail["evidence"]}
    assert detail["claims"] and all(c["verdict"]["label"] for c in detail["claims"])
    assert all(set(c["verdict"]["evidence_node_ids"]) <= evidence_ids for c in detail["claims"])
    assert [(m["skill"], m["covered"]) for m in detail["matches"]] == [("python", True), ("kubernetes", False)]
    assert detail["coverage"] == 0.5
    report = detail["report"]
    assert abs(sum(c["contribution"] for c in report["components"]) - report["total"]) <= 0.05
    for component in report["components"]:
        assert component["label"] and component["formula"]
        assert set(component["evidence_node_ids"]) <= evidence_ids


def test_runs_list_is_newest_first_with_summary_fields(client):
    first = client.post("/runs", json=BODY).json()["run_id"]
    second = client.post("/runs", json=BODY).json()["run_id"]

    runs = client.get("/runs").json()

    assert [r["run_id"] for r in runs] == [second, first]
    assert runs[0]["candidate_name"] == "Octo Developer"
    assert runs[0]["job_title"] == "Backend Engineer"
    assert runs[0]["status"] == "done" and runs[0]["total"] > 0
    assert runs[0]["sources"] == ["codeforces", "github", "leetcode"]
    assert [r["run_id"] for r in client.get("/runs?limit=1").json()] == [second]


def test_start_rejects_a_conflicting_job_with_409(client):
    assert client.post("/runs", json=BODY).status_code == 200
    changed = {**BODY, "job": {**BODY["job"], "required_skills": ["Go"]}}

    response = client.post("/runs/start", json=changed)

    assert response.status_code == 409
    assert response.json()["code"] == "JOB_CONFLICT"


def test_start_rejects_invalid_input_with_422(client):
    bad = {**BODY, "candidate": {**BODY["candidate"], "email": "nope"}}
    assert client.post("/runs/start", json=bad).status_code == 422


def test_snapshot_raw_is_verified_and_tampering_gives_409(client, system):
    run_id = client.post("/runs", json=BODY).json()["run_id"]
    snapshot = next(s for s in client.get(f"/runs/{run_id}").json()["snapshots"] if s["endpoint"] == "github/user")

    raw = client.get(f"/snapshots/{snapshot['id']}/raw").json()
    assert raw["verified"] is True
    assert raw["snapshot"] == snapshot
    assert raw["payload"]["login"] == "octo-dev"

    blobs = system[2]
    key = next(s.object_key for s in system[1].snapshots.list_by() if s.id == snapshot["id"])
    blobs.objects[key] = b'{"login": "someone-else"}'
    tampered = client.get(f"/snapshots/{snapshot['id']}/raw")
    assert tampered.status_code == 409
    assert tampered.json()["code"] == "HASH_MISMATCH"


def test_unknown_run_and_snapshot_are_404(client):
    assert client.get("/runs/no-such-run").status_code == 404
    assert client.get("/snapshots/no-such-snapshot/raw").status_code == 404

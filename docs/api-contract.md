# REST API contract (v0.3) — shared by the backend and the `ui/` web app

Base URL: `http://localhost:8000`. The Next.js app calls it through a rewrite (`/api/*` → `http://localhost:8000/*`),
so the browser never needs CORS; the backend also allows `http://localhost:3000` via CORS for direct calls.
All bodies are JSON unless stated. Timestamps are ISO-8601 UTC strings. Errors from the domain are
`{"code": "<ERROR_CODE>", "message": "<text>"}` with 422 (validation), 404 (`*_NOT_FOUND`), 409 (`JOB_CONFLICT`,
`HASH_MISMATCH`) or 502 (other pipeline errors).

## Resume intake

### `POST /resumes/parse` — multipart/form-data, field `file`
Accepts `.pdf`, `.docx`, `.txt`, `.md` up to 5 MB. Returns what the system read from the file, before anything runs:

```json
{
  "filename": "jane_doe_cv.pdf",
  "text": "full extracted text …",
  "name": "Jane Doe",                       // best guess or null
  "email": "jane@example.org",              // first email found or null
  "handles": {"github": "janedoe", "codeforces": "jane_d", "leetcode": "janedoe"},  // only those found
  "links": ["https://github.com/janedoe", "https://leetcode.com/u/janedoe/"],
  "claims": [                               // preview from the same extractor the run uses
    {"text": "3 years of Python", "kind": "skill", "subject": "Python", "years": 3, "rating": null, "solved": null}
  ],
  "extractor": "rule-based" | "claude"
}
```
Errors: 422 `UNSUPPORTED_FILE`, `EMPTY_RESUME`, `FILE_TOO_LARGE`.

## Runs

### `POST /runs/start` — body = `RunBody` (same as `POST /runs`) → **202** `{"run_id": "…"}`
Validates input and the job id synchronously (422 / 409 `JOB_CONFLICT`), then runs the pipeline in the background.
`POST /runs` (synchronous, returns the report) is kept for scripts and tests.

`RunBody`:
```json
{
  "candidate": {"name": "…", "email": "…", "resume_text": "…", "handles": {"github": "…"}},
  "job": {"id": "backend-engineer-3f2a", "title": "Backend Engineer", "text": "…", "required_skills": ["Python", "Docker"]}
}
```
The UI derives `job.id` from the title plus a short hash of title, text and skills, so the same job reuses one id and
a changed job never collides (`JOB_CONFLICT`).

### `GET /runs?limit=50` → list, newest first
```json
[{"run_id": "…", "candidate_id": "…", "candidate_name": "Jane Doe", "job_id": "…", "job_title": "Backend Engineer",
  "status": "running|partial|done|failed", "started_at": "…", "finished_at": "…|null", "total": 72.5,
  "sources": ["github", "codeforces"]}]
```

### `GET /runs/{run_id}` → full, auditable detail (poll every ~1.5 s while `status == "running"`)
```json
{
  "run": {"id": "…", "status": "running", "stage": "collect|freeze|extract|resolve|match|verify|score|finished",
          "started_at": "…", "finished_at": null, "failures": [{"source": "github", "code": "HTTP_403"}],
          "config": {"link_threshold": 0.5, "max_repos": 50, "…": "…"}},
  "progress": [{"stage": "collect", "status": "started|done", "at": "…", "detail": {"fetches": 12}}],
  "candidate": {"id": "…", "name": "Jane Doe", "email_masked": "j***@example.org", "handles": {"github": "janedoe"},
                "resume_text": "…"},
  "job": {"id": "…", "title": "…", "text": "…", "required_skills": ["Python"]},
  "accounts": [{"source": "github", "handle": "janedoe", "profile_url": "https://github.com/janedoe",
                "confidence": 0.95, "linked": true, "rationale": ["cross_link (1.00) on resume~github:janedoe: …"]}],
  "snapshots": [{"id": "…", "source": "github", "handle": "janedoe", "endpoint": "github/repos", "sha256": "…",
                 "size": 18234, "fetched_at": "…"}],
  "evidence": [{"id": "…", "snapshot_id": "…", "source": "github", "handle": "janedoe",
                "kind": "skill|project|contribution|achievement", "value": {"name": "Python", "…": "…"},
                "locator": "$[3]", "linked": true}],
  "claims": [{"id": "…", "text": "3 years of Python", "kind": "skill", "subject": "Python", "years": 3,
              "rating": null, "solved": null,
              "verdict": {"label": "supported|partially_supported|unsupported", "rationale": "…",
                          "evidence_node_ids": ["…"]} }],
  "matches": [{"skill": "python", "covered": true, "similarity": 1.0, "node_ids": ["…"]}],
  "coverage": 0.67,
  "report": {"total": 72.5,
             "components": [{"name": "verified_skills", "label": "Verified resume claims", "weight": 0.35,
                             "value": 0.8, "contribution": 28.0, "formula": "mean of claim verdicts …",
                             "evidence_node_ids": ["…"]}]}    // null until scoring is done
}
```
`contribution` = `100 × weight × value / Σ weights` (the components' contributions add up to `total`).
`progress` is kept in memory by the API process and is empty for runs started before a restart; `run.stage` is
derived from it (or `finished`).

### `GET /snapshots/{snapshot_id}/raw` → the frozen raw response, integrity-checked on read
```json
{"snapshot": { /* same fields as in snapshots[] */ }, "verified": true, "payload": { /* parsed JSON */ }}
```
409 `HASH_MISMATCH` if the stored bytes no longer match the SHA-256 (QR-14).

### `POST /runs/{run_id}/replay` → `{"report": {...}, "evidence_identical": true, "score_identical": true}`
Recomputes from stored snapshots and the stored claims; no network, nothing written (FR-14).

### `GET /runs/{run_id}/report` — unchanged. `DELETE /candidates/{candidate_id}` → 204 (FR-16).

### `GET /health` → `{"status": "ok", "storage": "postgres|memory", "extractor": "rule-based|claude"}`

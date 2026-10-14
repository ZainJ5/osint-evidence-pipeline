# OSINT Evidence Pipeline

Collects public developer data from GitHub, Codeforces and LeetCode, freezes every raw response as an immutable
snapshot, extracts typed evidence, resolves which accounts belong to the candidate, matches evidence to a job
requirement, verifies resume claims and produces an explainable score. Any finished run can be replayed from its
snapshots without network access.

Joint semester project for SE423 (Software Construction) and SE431 (Software Quality Assurance), GIKI, Fall 2026.
Team: Zain Jamshaid, Rabbin Batool, Ilsa Maryam.

## Architecture

```
pipeline/
  core/            business logic, no I/O imports (coverage target applies here)
    collection/    M1  CollectorFactory (Factory Method), GitHub/Codeforces/LeetCode collectors, RateLimiter, CollectionRunner
    snapshot/      M2  SnapshotStore (SHA-256, immutable), parsers, EvidenceExtractor (worker pool)
    identity/      M3  MatchSignal strategies, IdentityResolver (confidence + rationale, threshold)
    matching/      M4  SkillNormalizer, RequirementMatcher, InMemoryVectorIndex
    scoring/       M5  ClaimExtractor, VerificationRule strategies, ScoringStrategy, ScoreCalculator
    pipeline.py    PipelineRun orchestrator (ESRC order: collect, freeze, extract, resolve, match, verify, score)
    ports.py       HttpClient, BlobStore, LLMProvider, Embedder, Repository[T], CandidateEraser
    errors.py      PipelineError hierarchy with error codes
  adapters/        HttpAdapter, PostgresRepository, MinioBlobStore, migrations runner, in-memory fakes
  interface/       FastAPI app and composition root
migrations/        versioned SQL schema
ui/                Next.js web app (resume upload, live run progress, explainable report)
tests/             unit/ system/ stress/ integration/ blackbox/ whitebox/ fixtures/
docs/              requirements, milestone reports, SQA records, AI usage log
```

| Module | Owner |
|---|---|
| M1 Source Collection, M4 Semantic Matching | Zain Jamshaid |
| M2 Snapshot Store & Evidence Extraction, interface layer, persistence & CI | Rabbin Batool |
| M3 Identity Resolution, M5 Claim Verification & Scoring | Ilsa Maryam |

## Setup

Requirements: Python 3.10+ (CI uses 3.12) and Docker.

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"          # Windows: .venv\Scripts\pip install -e ".[dev]"
cp .env.example .env                        # then export the variables (see below)
docker compose up -d --wait                 # PostgreSQL 16 and MinIO
python -m pipeline.adapters.migrate         # applies migrations/*.sql
```

Environment variables (`.env.example`): `DATABASE_URL`, `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`,
`MINIO_BUCKET`, `MINIO_SECURE`, and optional `GITHUB_TOKEN`. Without a token GitHub allows 60 requests per hour,
which a single candidate with many repositories can exhaust. Never commit a real token.

If `DATABASE_URL` is not set, the API runs with in-memory storage, which is handy for a quick local demo.

## Running the API

```bash
uvicorn pipeline.interface.api:app --reload
```

Open http://localhost:8000/docs for the OpenAPI UI.

| Method | Path | Purpose |
|---|---|---|
| POST | `/runs` | Register a candidate and run the pipeline against a job requirement (FR-01..FR-13) |
| GET | `/runs/{run_id}/report` | Show the explainable score report |
| POST | `/runs/{run_id}/replay` | Recompute from stored snapshots with no network (FR-14) |
| DELETE | `/candidates/{candidate_id}` | Delete all data for a candidate (FR-16) |
| POST | `/resumes/parse` | Upload a PDF/DOCX/TXT/MD resume; returns text, detected name, email, handles and claims |
| POST | `/runs/start` | Start a run in the background (202), then poll `GET /runs/{run_id}` |
| GET | `/runs`, `/runs/{run_id}` | Run list; full auditable run detail (accounts, snapshots, evidence, claims, matches, score) |
| GET | `/snapshots/{snapshot_id}/raw` | Raw frozen response, SHA-256 verified on read |

Full shapes: [docs/api-contract.md](docs/api-contract.md).

## Web UI

```bash
cd ui
npm install
npm run dev          # http://localhost:3000, calls the API at API_URL (default http://localhost:8000)
```

Flow: drop a resume on **New analysis** → check the detected handles and claims → add the job's required skills →
start. The run page shows live pipeline progress, then the score breakdown, every claim with its verdict and evidence,
requirement coverage, identity decisions, all evidence nodes and the raw snapshots behind them. See `ui/README.md`.

## Claim extraction

Without configuration the deterministic rule-based extractor is used. Set `ANTHROPIC_API_KEY` to extract claims with
Claude (`claude-opus-5-5`, structured JSON output). Claims are stored per run, so replay reproduces a run without
calling the model again.

Example body for `POST /runs`:

```json
{
  "candidate": {
    "name": "Jane Doe",
    "email": "jane@example.org",
    "resume_text": "3 years of Python. Codeforces rating 1600. Skills: Docker, Go",
    "handles": {"github": "janedoe", "codeforces": "janedoe", "leetcode": "janedoe"}
  },
  "job": {"id": "backend-1", "title": "Backend Engineer", "text": "", "required_skills": ["Python", "Go"]}
}
```

## Tests

```bash
pytest -m "not integration" --cov=pipeline/core      # unit, system, stress, black-box, white-box
pytest -m integration                                # needs docker compose up and the env variables
ruff check pipeline tests && ruff format --check pipeline tests
pylint pipeline
```

CI (`.github/workflows/ci.yml`) runs all of this on every push and pull request, with PostgreSQL and MinIO containers,
a 60 % coverage gate on `pipeline.core`, a dependency-direction check (core must not import adapters or interface)
and secret scanning.

## Working rules

- `main` is protected. Work on `feature/<milestone>-<module>` branches, open a pull request, get one review from a
  member who is not the author, and merge with a merge commit (never squash) so the test-first history stays visible.
- Commit the failing test first, then the implementation, then any refactor.
- Every task is a GitHub issue labelled `module:Mx` and `milestone:Mx`; defects are labelled `defect` with a severity.

## Documentation

- [docs/requirements.md](docs/requirements.md): FR, NFR and QR identifiers
- [docs/milestone2/](docs/milestone2/): SE423 and SE431 Milestone 2 deliverables
- [docs/ai-usage-log.md](docs/ai-usage-log.md): AI usage log required by the course

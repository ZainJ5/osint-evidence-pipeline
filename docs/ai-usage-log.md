# AI Usage Log

Required by Section 9 of the joint project guidelines. One row per significant use. "Team review" records which
member has read, understood and can defend the adopted material; it must be filled in by that member before
submission.

Tool for every row below: Claude Code (Anthropic), model Claude Opus 5.5 (`claude-opus-5-5`), run as one main session
that delegated module work to parallel sub-agents. Date: 2026-11-19.

| # | Purpose | Prompt / activity summary | Material adopted | Modifications made | Verification performed | Team review |
|---|---|---|---|---|---|---|
| 1 | Shared contracts | Asked to set up the repository and build Milestone 2 from the M1 proposal; generated package layout, `errors.py`, `ports.py`, `models.py`, `inputs.py`, `adapters/fakes.py`, `pyproject.toml` | All files as listed | Fixed a claim regex that kept a trailing full stop ("Python."); pinned pytest to 8.4.2 after pytest 9.2 crashed with an internal error | Ruff clean; unit tests of every module build on these contracts | [member to fill in] |
| 2 | M1 Source Collection, M4 Matching (Zain's modules) | Sub-agent briefed with the M1 design: Factory Method registry, RateLimiter, retry policy, three collectors, runner, matcher | `pipeline/core/collection/*`, `pipeline/core/matching/*`, their tests, API fixtures | Agent added `CollectorFactory.unregister`, shared limiters per runner, Codeforces 2 s floor as a minimum | Tests written first and seen failing; 194 tests passing; stress test run 3 times; live check against the real Codeforces and LeetCode APIs | Zain Jamshaid: [to fill in] |
| 3 | M2 Snapshot/Extraction, adapters, migrations, Docker Compose, CI (Rabbin's work) | Sub-agent briefed with FR-06/07/14/16 and the adapter design | `pipeline/core/snapshot/*`, `pipeline/adapters/{http,postgres,minio_store,migrate}.py`, `migrations/001_initial.sql`, `docker-compose.yml`, `.github/workflows/ci.yml`, tests | Snapshot unique key changed to (run_id, endpoint, sha256); MinIO image switched to `cgr.dev/chainguard/minio` because `minio/minio` is no longer on Docker Hub | 41 unit tests; 9 integration tests passing against real PostgreSQL 16 and MinIO containers | Rabbin Batool: [to fill in] |
| 4 | M3 Identity, M5 Scoring (Ilsa's modules) | Sub-agent briefed with FR-08/09/11/12/13 and the Strategy design | `pipeline/core/identity/*`, `pipeline/core/scoring/*`, tests | Agent chose noisy-OR fusion with one-hop linking, sorted name tokens, extra claim validation | 115 tests passing (TDD, red first) | Ilsa Maryam: [to fill in] |
| 5 | Orchestrator, API, logging | Generated `pipeline/core/pipeline.py`, `pipeline/interface/{api,composition}.py`, `pipeline/core/log.py`, system tests | All | None after review | 12 system tests + 1 Postgres/MinIO end-to-end test passing; live run against real GitHub/Codeforces APIs (GitHub returned 403 rate-limit, handled as a `partial` run) | [member to fill in] |
| 6 | SE431 M2: static analysis report | Sub-agent ran Ruff and Pylint, triaged and fixed findings | `docs/milestone2/static-analysis-report.md`, `docs/records/m2/static-analysis-*` | | Raw tool output saved before and after; full test suite re-run | Rabbin Batool: [to fill in] |
| 7 | SE431 M2: Fagan inspection preparation | Sub-agent performed an AI-assisted pre-review of the inspection package and fixed confirmed defects test-first | `docs/milestone2/inspection-report.md`, defect fixes and tests | Meeting facts and external inspector's findings left as placeholders: they must come from the real meeting | Each fixed defect has a reproducing test | Zain Jamshaid: [to fill in] |
| 8 | SE431 M2: V&V plan and white-box design | Sub-agent wrote the IEEE 1012 plan, CFGs, V(G) and basis-path tests | `docs/milestone2/vv-plan.md`, `docs/milestone2/whitebox-test-design.md`, `tests/whitebox/*` | | V(G) cross-checked against Ruff's McCabe output; tests run with branch coverage | Ilsa Maryam: [to fill in] |
| 9 | SE431 M2: black-box design | Sub-agent derived EP/BVA tables from the real validation rules and wrote missing tests | `docs/milestone2/blackbox-test-design.md`, `tests/blackbox/*` | | Results table filled from a real test run | Rabbin Batool: [to fill in] |
| 10 | SE423 M2 report, README, RTM v2, risk register, SCM document | Generated from the code and test outputs | `docs/milestone2/SE423_M2_report.md`, `README.md`, `docs/milestone2/SE431_M2_report.md`, `docs/milestone2/scm.md` | | Numbers taken from commands run in this session | [member to fill in] |

| 11 | Web UI and API for it (2026-11-19) | Asked for a Next.js UI with drag-and-drop resume upload that shows collected data, claim matching and scoring; four sub-agents built the backend endpoints, claim extraction/verification, live collection checks and the UI | `ui/`, `pipeline/core/{intake,queries,skills}.py`, `pipeline/core/matching/evidence_search.py`, `pipeline/adapters/{resume_reader,rule_claims,claude_llm}.py`, `migrations/002_ui_support.sql`, API endpoints, tests | Codeforces history cap raised (1000 → 10000 submissions) after a live check showed 676 of 3060 solved problems; rationale percentages floored so they never contradict the 80 % threshold; resume limit raised to 50 000 characters | 723 tests passing; live end-to-end run through the UI against the real GitHub, Codeforces and LeetCode APIs (verdicts checked by hand against the raw data); replay identical; UI lint and production build pass; headless-browser screenshots reviewed | [member to fill in] |

## What the team still has to do

- Each owner reads their module and the documents attributed to them and fills in the "Team review" column, so
  everyone can explain and defend the work in the individual Q&A.
- Run the real Fagan inspection meeting with the paired team's inspector and record its facts.
- Commit the work through feature branches in test-first order (see `docs/milestone2/scm.md`).

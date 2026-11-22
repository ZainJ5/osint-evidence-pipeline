# Software Verification and Validation Plan (SVVP) — OSINT Evidence Pipeline

SE431 Milestone 2 deliverable. Structure follows IEEE Std 1012-2016 (System, Software and Hardware Verification and
Validation), tailored to a three-person, three-milestone university project.

| Item | Value |
|---|---|
| V&V plan lead (M2) | Ilsa Maryam |
| Team | Zain Jamshaid (M1 collection, M4 matching), Rabbin Batool (M2 snapshot, interface, persistence, CI), Ilsa Maryam (M3 identity, M5 scoring) |
| Plan date / status | Week 10 (2026-11-19), at Milestone 2. Next revision: week 13 (Milestone 3, final) |
| Requirement baseline | `docs/requirements.md` (FR-01…FR-16, NFR-01…NFR-08, QR-01…QR-16) |
| Every figure in this plan | comes from a command run on 2026-11-19; raw output under `docs/records/m2/` |

## 1. Purpose and scope

**Purpose.** Define how the team shows (a) that each software item meets its specification and the project
standards (*verification*) and (b) that the delivered pipeline gives recruiters trustworthy, explainable candidate
evidence without misattributing anyone's public work (*validation*). The plan fixes which tasks are done, by whom,
when, against which requirement IDs, with which entry/exit criteria, and which artifact proves it.

**Software items under V&V.**

| Item | Code | Owner |
|---|---|---|
| M1 Source collection (collectors, retry, rate limiter, runner) | `pipeline/core/collection/` | Zain Jamshaid |
| M2 Snapshot store and evidence extraction | `pipeline/core/snapshot/` | Rabbin Batool |
| M3 Identity resolution | `pipeline/core/identity/` | Ilsa Maryam |
| M4 Requirement matching (normaliser, matcher, vector index) | `pipeline/core/matching/` | Zain Jamshaid |
| M5 Claim extraction, verification and scoring | `pipeline/core/scoring/` | Ilsa Maryam |
| Orchestrator, shared contracts | `pipeline/core/pipeline.py`, `models.py`, `inputs.py`, `ports.py`, `errors.py`, `log.py` | shared (module owners) |
| Interface (FastAPI REST, composition root) | `pipeline/interface/` | Rabbin Batool |
| Persistence and HTTP adapters (PostgreSQL, MinIO, httpx), migrations | `pipeline/adapters/`, `migrations/` | Rabbin Batool |
| Build and CI configuration | `pyproject.toml`, `.github/workflows/ci.yml`, `docker-compose.yml` | Rabbin Batool |

**Out of scope.** The external APIs themselves (GitHub, Codeforces, LeetCode), the LLM provider beyond its port
contract, and deployment hardening. A production LLM is not used in M2; claim extraction is verified with the
deterministic fake in `pipeline/adapters/fakes.py`.

**Related documents.** `docs/milestone2/static-analysis-report.md` (Rabbin Batool),
`docs/milestone2/blackbox-test-design.md` (Rabbin Batool), `docs/milestone2/whitebox-test-design.md` (Ilsa Maryam),
`docs/milestone2/inspection-report.md` (Fagan inspection, moderator Zain Jamshaid), `docs/milestone2/scm.md`,
`docs/milestone2/SE423_M2_report.md` (RTM v2), `docs/ai-usage-log.md`.

## 2. Verification versus validation in this project

| | Verification — "are we building it right?" | Validation — "are we building the right thing?" |
|---|---|---|
| Question | Does each item conform to its FR/NFR/QR text, the design (ports, layering) and the coding standard? | Does the pipeline actually help a recruiter judge a real candidate, fairly and explainably? |
| Reference | `docs/requirements.md`, design rules (QR-09, QR-11, QR-12), Ruff/Pylint config | Recruiter needs and the candidates' interests; hand-labelled ground truth (QR-01) |
| Techniques | Fagan inspection; static analysis (Ruff, Pylint, McCabe C901); unit tests with in-memory fakes; white-box basis-path tests; black-box EP/BVA tests; integration tests on real PostgreSQL + MinIO; system and stress tests; CI gates | (1) Demonstration with **consenting candidates** (team members and volunteers who sign a consent note) on their real public profiles; (2) labelled-corpus accuracy study for QR-01 (10 profiles, claim verdicts hand-labelled by two members, disagreements resolved by the third); (3) recruiter-facing report review: a reader outside the team scores whether each score component is understandable and traceable to evidence |
| Evidence | test runs, coverage, tool outputs, inspection log, CI artifacts | demo log, corpus labels + confusion matrix, review form |
| Status at M2 | in place and running (section 7) | planned for M3 (section 9) — nothing in M2 validates against real people yet |

Passing every verification task does **not** imply validation: e.g. FR-12 tests prove the rule logic matches the
specification, but only the labelled corpus shows whether the specification (whole-year dates from skill nodes)
produces verdicts a human agrees with.

## 3. Software integrity levels

Scheme: IEEE 1012 four-level scale, assigned from consequence × likelihood of a residual defect. Level 4 is not used
(no safety or financial-loss consequence).

| Item | Level | Justification |
|---|---|---|
| M3 Identity resolution | **3 (high)** | A false link attributes a stranger's GitHub/Codeforces work to the candidate (or a false non-link hides theirs). The error is invisible in the final score and harms a real person in a hiring decision. |
| M5 Claim verification and scoring | **3 (high)** | Labels a person's résumé claims "unsupported" and produces the number a recruiter reads first. QR-01 forbids any hand-labelled unsupported claim reported as supported. |
| M2 Snapshot store and extraction | **3 (high)** | It is the audit trail: every verdict and score must trace to an untampered stored response (FR-06, QR-14, QR-15) and replay must be identical (FR-14). Also holds personal data that must be erasable (FR-16). |
| M1 Collection | **2 (medium)** | Failures are visible (run marked `partial` with an error code, NFR-02). Wrong behaviour mostly causes missing evidence or API-terms violations, not wrong attribution. |
| M4 Matching | **2 (medium)** | Affects one component (`requirement_match`, weight 0.30) and every match cites its node ids, so errors are visible in the report. |
| Orchestrator, shared contracts | **2 (medium)** | Wiring errors are caught by system tests; validation in `inputs.py` is the trust boundary. |
| Persistence adapters | **2 (medium)** | Data loss or failed erasure matters (FR-16), but behaviour is covered by integration tests against the real services. |
| Interface (REST API) | **1 (low)** | Thin layer over the pipeline; no business decisions; schema published (QR-16). |
| Build/CI configuration | **1 (low)** | Errors block the build loudly. |

**Minimum V&V tasks per level** (tailoring of IEEE 1012 Annex tables):

| Task | Level 3 | Level 2 | Level 1 |
|---|---|---|---|
| Requirements trace to ≥1 automated test | required | required | required |
| Static analysis, no open critical finding | required | required | required |
| Unit tests with fakes, branch coverage | ≥ 90 % branch | ≥ 80 % branch | — |
| Black-box EP/BVA on every validated input | required | required | API boundary only |
| White-box basis-path tests of the highest-V(G) decision functions | required | optional | — |
| Fagan inspection of the module | required | sampled | — |
| Reviewer independent of the author | required | required | required (PR review) |
| Validation against real/consenting data | required (M3) | demo only | demo only |

Measured at M2 (`docs/records/m2/coverage-full.txt`, branch coverage per package from the same run's `coverage json`):
identity 45/46 = 97.8 %, scoring 52/52 = 100 %, snapshot 56/60 = 93.3 % — all level-3 items meet ≥ 90 %;
collection 51/52 = 98.1 %, matching 37/38 = 97.4 %, `pipeline.py` 18/18 = 100 % — level-2 items meet ≥ 80 %.

## 4. V&V activities by life-cycle phase

"Evidence" is a path in the repository or a CI artifact. Timing: M2 = week 10, M3 = week 13.

### 4.1 Requirements phase

| Task | Requirement IDs | Technique | Responsible | Timing | Entry criteria | Exit criteria | Evidence |
|---|---|---|---|---|---|---|---|
| Requirements testability review | all FR/NFR/QR | Inspection against a checklist (atomic, measurable, owner, priority) | Ilsa Maryam; reviewer Rabbin Batool | M1 (done), re-run M3 | M1 requirements baselined | every requirement has a measurable criterion or a recorded exception | `docs/requirements.md` |
| Traceability (RTM v2) | all; QR-02 | Analysis: requirement → design element → test ID | Zain Jamshaid | M2 v2, M3 final | tests exist | every Must FR has ≥1 passing traced test (QR-02) | `docs/milestone2/SE423_M2_report.md` (RTM v2); section 6 of this plan |
| Requirement anomalies found during V&V | FR-09, QR-07, NFR-03 | Analysis | Ilsa Maryam | M3 | this plan | resolved or re-baselined | section 8 (VV-AN-03, VV-AN-04) |

### 4.2 Design phase

| Task | Requirement IDs | Technique | Responsible | Timing | Entry | Exit | Evidence |
|---|---|---|---|---|---|---|---|
| Layering check (core imports no adapter/interface) | QR-09 | Static analysis (`grep` gate in CI) | Rabbin Batool | every push | code compiles | grep finds nothing (verified 2026-11-19: exit 1, no match) | CI step "Dependency direction"; `.github/workflows/ci.yml` |
| Port/fake completeness | NFR-04, QR-10 | Inspection: each ABC in `ports.py` has a fake in `adapters/fakes.py` | Ilsa Maryam | M2 | ports frozen | 1:1 mapping | `pipeline/core/ports.py`, `pipeline/adapters/fakes.py` |
| Extensibility (new collector = 1 file + 1 registration) | QR-12 | Test with a stub fourth collector | Zain Jamshaid | M2 | factory exists | test passes | `tests/unit/collection/test_collector_factory.py::test_new_source_plugs_in_without_editing_existing_code` |
| Design inspection of M3/M5 decision logic | FR-08, FR-09, FR-12, FR-13 | Fagan inspection (overview, preparation, meeting, rework, follow-up) | Moderator Zain Jamshaid; external inspector from the paired team | M2 week 10 | code complete, unit tests green, checklist issued | all major defects reworked and re-verified by a test | `docs/milestone2/inspection-report.md`; `tests/system/test_inspection_m2.py`, `tests/unit/scoring/test_inspection_m2_scoring.py` |

### 4.3 Construction (implementation) phase

| Task | Requirement IDs | Technique | Responsible | Timing | Entry | Exit | Evidence |
|---|---|---|---|---|---|---|---|
| Lint, format, static analysis | NFR-05, QR-11 | Ruff (E, F, W, I, B, C90, UP, SIM), `ruff format --check`, Pylint `--fail-under=9` | Rabbin Batool | every push (CI); recorded M2 | code on branch | no unresolved critical finding; C901 ≤ 10. Verified 2026-11-19: Ruff "All checks passed!", 107 files formatted, Pylint 10.00/10, highest core V(G) = 7 (`inputs.py` `__post_init__`) | `docs/records/m2/static-analysis-before/`, `…-after/`; `docs/milestone2/static-analysis-report.md` |
| Unit tests, test-first, with in-memory fakes | FR-01…FR-16, NFR-04 | Unit testing (pytest, pytest-asyncio) | each module owner | continuous | module interface agreed | tests green, coverage gate met | `tests/unit/` |
| White-box basis-path testing | FR-05, FR-08, FR-09, FR-12, FR-13 | CFG, V(G) three ways cross-checked with Ruff C901, basis paths, condition and loop coverage | Ilsa Maryam | M2 | functions stable, V(G) ≥ 3 | one passing test per feasible basis path; 100 % branch coverage of each analysed function | `docs/milestone2/whitebox-test-design.md`; `tests/whitebox/`; `docs/records/m2/whitebox-coverage.txt` |
| Black-box testing | FR-01, FR-05, FR-09, FR-10, FR-12…FR-15, NFR-02 | Equivalence partitioning, boundary-value analysis, decision tables | Rabbin Batool | M2 | specification of each input | every partition/boundary has a test; defects logged as xfail with BB-DEF id | `docs/milestone2/blackbox-test-design.md`; `tests/blackbox/` |
| Coverage gate | NFR-04, QR-10 | `pytest --cov=pipeline/core --cov-fail-under=60` | Rabbin Batool | every push | tests green | ≥ 60 % line coverage (M2: 99 % line, 98 % with branches) | CI artifact `coverage` (`coverage.xml`); `docs/records/m2/coverage-full.txt` |
| Secret scanning, e-mail scrubbing | NFR-06, QR-13 | gitleaks on full history (CI); unit tests of the log filter | Rabbin Batool | every push | repository has history | no finding | CI step "Secret scan"; `tests/unit/core/test_log.py` |

### 4.4 Integration and test phase

| Task | Requirement IDs | Technique | Responsible | Timing | Entry | Exit | Evidence |
|---|---|---|---|---|---|---|---|
| Integration with real PostgreSQL 16 and MinIO | FR-06, FR-14, FR-16, QR-14 | Integration tests (`-m integration`) against containers | Rabbin Batool | M2, every push in CI | `docker compose up`; migrations applied | all integration tests pass (2026-11-19 local: 10 passed) | `tests/integration/`; CI job `test` |
| System tests through the orchestrator and REST API | FR-09, FR-13…FR-16, NFR-02, NFR-07, QR-03, QR-04, QR-14…QR-16 | System testing with recorded API fixtures and fakes | Ilsa Maryam (pipeline), Rabbin Batool (API) | M2 | modules integrated | all pass | `tests/system/` |
| Concurrency / capacity stress | NFR-01, QR-08 | 20 candidates × 3 sources, timestamped fake HTTP, per-source interval check | Zain Jamshaid | M2 | rate limiter done | overlapping calls and no interval violation | `tests/stress/test_collection_stress.py` |
| Performance | NFR-03, QR-07 | Profiling harness: collection of 50 repos with simulated latency; top-k over 10 000 vectors timed | Zain Jamshaid | **M3** | harness written | collection ≤ 5 min, top-k ≤ 300 ms (median of 20 runs) | planned: `tests/performance/`, `docs/records/m3/performance.txt` |
| Recoverability | QR-05 | Fault injection: kill extraction mid-run, restart, compare evidence; assert zero HTTP calls | Rabbin Batool | **M3** | snapshot store done | identical evidence, no re-fetch | planned: `tests/system/test_recovery.py` |

### 4.5 Acceptance (validation) phase

| Task | Requirement IDs | Technique | Responsible | Timing | Entry | Exit | Evidence |
|---|---|---|---|---|---|---|---|
| Labelled-corpus accuracy | QR-01, FR-11, FR-12 | 10 consenting profiles; two members label each claim independently; Cohen's κ reported; third member resolves | Ilsa Maryam (lead), Zain Jamshaid, Rabbin Batool | M3, W13 − 14 to W13 − 5 days | consent forms; snapshots frozen | ≥ 90 % verdict agreement; **zero** labelled-unsupported reported supported | planned: `tests/validation/corpus/` (labels), `docs/records/m3/qr01-confusion-matrix.txt` |
| Demonstration with consenting candidates | FR-02…FR-04, FR-08, FR-09, FR-15, NFR-06, NFR-08 | Live run on real public profiles through the API; replay afterwards with network off | whole team | M3, W13 − 3 days | corpus done; GitHub token configured | runs complete; any `partial` explained; replay identical; data deleted after (FR-16) | planned: `docs/records/m3/demo-log.md` |
| Recruiter-facing report review | FR-13, QR-03, QR-15 | Review form: for each component, can the reader find value, weight and the evidence behind it? | Ilsa Maryam with an outside reader | M3, W13 − 3 days | demo reports | every component rated traceable | planned: `docs/records/m3/report-review.md` |
| Final RTM and defect status | QR-02, QR-06 | Analysis | Zain Jamshaid | W13 − 1 day | all above | every Must FR traced to a passing test; zero open Critical/High | final RTM in the M3 report |

## 5. Independence

IEEE 1012 asks for technical, managerial and financial independence; in a student team only technical independence
is achievable and is applied as follows:

- **Cross-member review.** No module is verified only by its author. White-box design of M1 (`Collector._fetch`) is
  done by Ilsa Maryam; black-box design of M3/M5 inputs is done by Rabbin Batool; the M5 white-box tests written by
  Ilsa Maryam (owner) are reviewed by Zain Jamshaid. Every pull request needs one approval from a non-author
  (`docs/milestone2/scm.md`, section 2).
- **External inspector.** The Fagan inspection includes one inspector from the paired team who has not seen the code
  before; the moderator (Zain Jamshaid) is not the author of the inspected M3/M5 code.
- **Independent oracle for validation.** QR-01 labels are produced by two members labelling separately, before
  they see the pipeline's verdicts.
- **Tool independence.** Complexity values are computed by hand from the CFG and cross-checked with Ruff's
  implementation rather than trusted from either alone.
- **Limitation.** All three members developed the code, so validation also uses an outside reader (4.5).

## 6. Requirement-by-requirement V&V matrix

Method: T = test, I = inspection, A = analysis, D = demonstration. Level: U = unit, Int = integration, S = system,
Acc = acceptance. Status is from the test runs of 2026-11-19 (section 7): **Pass** = traced automated evidence exists
and passes; **Partial** = only part of the requirement is verified; **Open** = no evidence yet.

| ID | Method | Level | Evidence (tests / artifacts) | M2 status |
|---|---|---|---|---|
| FR-01 | T | U, S | `tests/unit/collection/test_candidate_input.py` (EP/BVA), `tests/blackbox/test_bb_candidate.py`, `tests/system/test_api.py::test_invalid_input_is_rejected_at_the_boundary` | Pass |
| FR-02 | T | U | `tests/unit/collection/test_source_collectors.py::test_github_*`, `test_collector_retry.py`, WB-COL-01 | Pass (recorded fixtures; live API only in M3 demo) |
| FR-03 | T | U | `test_source_collectors.py::test_codeforces_*` (4 tests) | Pass (recorded fixtures) |
| FR-04 | T | U | `test_source_collectors.py::test_leetcode_*` (3 tests) | Pass (recorded fixtures) |
| FR-05 | T | U, S | `test_collection_runner.py`, `test_collector_retry.py`, `test_rate_limiter.py`, WB-COL-02…07, `tests/blackbox/test_bb_collection.py`, stress test | Pass |
| FR-06 | T | U, Int | `tests/unit/snapshot/test_snapshot_store.py`, `tests/integration/test_minio.py`, `test_postgres.py` | Pass |
| FR-07 | T | U | `tests/unit/snapshot/test_extractor.py` (determinism, worker count), `test_parsers.py` | Pass |
| FR-08 | T, I | U, S | `tests/unit/identity/` (signals, resolver), WB-IDN-01…05, inspection INS-09 test | Pass |
| FR-09 | T | U, S | `test_resolver.py::test_threshold_boundary`, WB-IDN-02/06/07, `tests/blackbox/test_bb_identity.py`, `tests/system/test_pipeline_system.py::test_unlinked_account_evidence_is_excluded` | Pass |
| FR-10 | T | U | `tests/unit/matching/test_skill_normalizer.py`, `test_requirement_matcher.py`, `tests/blackbox/test_bb_matching.py` | Pass |
| FR-11 | T; D (M3) | U; Acc | `tests/unit/scoring/test_claims.py` (deterministic fake LLM) | Partial — verified with the fake only; real-résumé extraction validated by QR-01 in M3 |
| FR-12 | T, I | U, S | `test_skill_rule.py`, `test_rating_rule.py`, `test_verifier.py`, WB-SCO-01…05, INS-05 tests, `tests/blackbox/test_bb_verification.py` | Pass |
| FR-13 | T | U, S | `tests/unit/scoring/test_scoring.py`, WB-SCO-06…11, INS-08 tests, `tests/blackbox/test_bb_scoring.py`, system report test | Pass |
| FR-14 | T | S, Int | `test_pipeline_system.py::test_replay_*` (3), `tests/integration/test_pipeline_postgres.py`, INS-03/INS-06 tests, `tests/blackbox/test_bb_replay.py` | Pass |
| FR-15 | T | S | `tests/system/test_api.py` (3), `tests/blackbox/test_bb_api.py` | Pass |
| FR-16 | T | S, Int | `test_pipeline_system.py::test_delete_candidate_removes_rows_and_blobs`, `test_postgres.py::test_eraser_removes_every_candidate_row_and_unshared_blobs` | Pass |
| NFR-01 | T | S | `tests/stress/test_collection_stress.py`, `test_rate_limiter.py` (exact interval arithmetic with a fake clock) | Pass — stress test was flaky during M2 and was revised (VV-AN-01) |
| NFR-02 | T | U, S | `test_collection_runner.py::test_one_source_failing_forever_yields_a_partial_result`, `test_pipeline_system.py::test_one_source_failing_gives_partial_run_with_other_evidence`, `tests/blackbox/test_bb_reliability.py` | Pass |
| NFR-03 | T (A) | S | none (`test_bb_inputs.py` only checks `max_repos` validation) | Open — M3 performance harness |
| NFR-04 | A, T | U | every port in `ports.py` has a fake in `fakes.py`; 99 % line coverage | Partial — tests and implementation are committed separately on each branch; failing-test-first commits are enforced from M3 (`scm.md` §6) |
| NFR-05 | A | — | Ruff clean, Pylint 10.00/10, `docs/milestone2/static-analysis-report.md` | Pass |
| NFR-06 | T, A | U | `tests/unit/core/test_log.py` (4), `tests/unit/adapters/test_http_adapter.py::test_token_defaults_to_env`, `test_github_token_sent_only_to_github` | Partial — gitleaks runs only in CI on pushed history |
| NFR-07 | T | S | `test_pipeline_system.py::test_replay_reproduces_evidence_and_score_without_network` | Pass |
| NFR-08 | A, I | — | CI grep for selenium/playwright; inspection of collector URLs (official REST/GraphQL endpoints) | Pass |
| QR-01 | D, A | Acc | labelled corpus | Open — M3 (section 4.5) |
| QR-02 | A | — | this matrix: 15 of 15 Must FRs have ≥1 passing traced test (FR-11 only with the fake LLM) | Partial — final RTM due M3 |
| QR-03 | T | U, S | `test_scoring.py::test_every_positive_component_cites_evidence`, `test_pipeline_system.py::test_every_cited_evidence_node_resolves_to_a_snapshot_of_the_run` | Pass |
| QR-04 | T | S | `test_pipeline_system.py::test_one_source_failing_gives_partial_run_with_other_evidence` | Pass |
| QR-05 | T | S | replay without network (FR-14 tests) covers "no re-fetch, same evidence" | Partial — crash-and-restart during extraction not tested (M3) |
| QR-06 | A | — | defect log (section 8); `inspection-report.md`; `blackbox-test-design.md` | Partial — inspection (INS-xx) and black-box (BB-DEF-01…04) defects found in M2 were fixed with regression tests; open: VV-AN-02…04 (all Low). Confirmed only when the GitHub issue list exists (repository not yet committed) |
| QR-07 | T | S | — | Open — requirement says "at M4"; there is no M4 (VV-AN-03) |
| QR-08 | T | S | stress test, 20 candidates | Pass (VV-AN-01) |
| QR-09 | A | — | CI grep; local run 2026-11-19 found no import | Pass |
| QR-10 | A, T | U | coverage 99 % line of `pipeline/core`; fakes for every port | Pass |
| QR-11 | A | — | max core V(G) = 7 (`inputs.py`); Ruff/Pylint clean | Pass |
| QR-12 | T | U | `test_collector_factory.py::test_new_source_plugs_in_without_editing_existing_code` | Pass |
| QR-13 | T, A | U | log filter tests; gitleaks in CI | Partial — as NFR-06 |
| QR-14 | T | U, Int, S | `test_snapshot_store.py::test_tampered_blob_raises_snapshot_error`, `test_minio.py::test_tampered_blob_in_minio_raises_snapshot_error`, `test_pipeline_system.py::test_replay_of_tampered_snapshot_is_refused` | Pass |
| QR-15 | T | S | `test_pipeline_system.py::test_every_cited_evidence_node_resolves_to_a_snapshot_of_the_run` (run id + snapshot id per node) | Pass |
| QR-16 | T | S | `test_api.py::test_openapi_schema_is_published` | Partial — schema and paths published; responses not yet validated against it (M3: validate each response body with the schema) |

Summary at M2: FR 15 Pass, 1 Partial; NFR 5 Pass, 2 Partial, 1 Open; QR 9 Pass, 5 Partial, 2 Open.

## 7. M2 verification results

| Run (2026-11-19) | Command | Result | Record |
|---|---|---|---|
| Full suite without containers | `.venv/Scripts/python -m pytest -m "not integration" --cov=pipeline/core --cov-branch --cov-report=term-missing` | 556 passed, 10 deselected (integration), 0 xfailed — the black-box xfails were removed when BB-DEF-01…04 were fixed | `docs/records/m2/coverage-full.txt` |
| Integration (PostgreSQL 16 + `cgr.dev/chainguard/minio` containers) | `set -a; . ./.env.example; set +a; .venv/Scripts/python -m pytest -m integration` | 10 passed | console |
| White-box suite | `.venv/Scripts/python -m pytest tests/whitebox --cov=pipeline/core --cov-branch` | 34 passed | `docs/records/m2/whitebox-coverage.txt` |
| Coverage of `pipeline/core` | same as full suite | **1,642 statements, 22 missed (99 % line); 380 branches, 12 partial (98 % combined)** on `m2-baseline`; CI https://github.com/ZainJ5/osint-evidence-pipeline/actions/runs/45028442893 | `docs/records/m2/coverage-full.txt` |
| Static analysis | `ruff check .`; `ruff format --check .`; `pylint pipeline --fail-under=9` | all clean; Pylint 10.00/10 | `docs/records/m2/static-analysis-after/` |

## 8. Anomaly reporting and resolution

**Process.** Every anomaly is a GitHub issue labelled `defect` plus one severity label and the module label
(`module:Mx`), titled with its source id (`INS-nn` inspection, `BB-DEF-nn` black-box, `WB-DEF-nn` white-box,
`SA-nn` static analysis, `VV-AN-nn` this plan). Until fixed, the reproducing test is committed with
`@pytest.mark.xfail(strict=True, reason="<id>: …")` so the suite stays green and the fix flips it to a pass.

| Severity | Definition | Allowed open at a milestone (QR-06) |
|---|---|---|
| Critical | wrong attribution of evidence, data leak, data not erased, crash of the API | 0 |
| High | wrong verdict/score for valid input, Must FR not met | 0 |
| Medium | wrong behaviour only for invalid/edge configuration, flaky test | allowed with justification |
| Low | robustness, readability, specification question | allowed |

**CAPA (corrective and preventive action).** Each closed defect records: root cause; correction (fix + regression
test id); preventive action (checklist item, new lint rule, or test pattern) so the class of defect does not recur.
Example from M2: WB-DEF-01 = INS-08 (NaN/inf weights accepted) — correction: range check in `_validated`
(`scoring.py:73`) with tests WB-SCO-11 and `test_ins08_*`; preventive: inspection checklist item "every float
input is checked with `math.isfinite` or an explicit range". The same class of defect was found by black-box testing in
`RunConfig` (BB-DEF-02, NaN `min_interval_seconds` silently disabled rate limiting) and fixed in M2 with the shared
helpers `_check_number` / `_check_int` in `pipeline/core/inputs.py`.

**Anomalies raised by V&V planning (this document).**

| ID | Finding | Severity | Action / owner |
|---|---|---|---|
| VV-AN-01 | `tests/stress/test_collection_stress.py` was flaky on Windows under `--cov`. Observed 2026-11-19: 1 of 5 runs failed with the original version (codeforces gap 0.0166 s vs required 0.019 s, measured at the fake HTTP call); after its owner moved the stamp to the limiter grant, the full-suite run at 03:03 still failed once (github gap 0.00075 s vs 0.009 s). Cause: the stamp is taken *after* `RateLimiter.__aenter__` returns, so an OS/GC pause of ~9 ms between the limiter's internal `_last_start` and the stamp shrinks the measured gap; the limiter's own invariant is proven with a fake clock in `test_rate_limiter.py`. The same pause would also delay a real request, so for 10 ms test intervals the spacing seen by a server can shrink — negligible against the real 2 s Codeforces interval. The test was revised (30/40 ms intervals, 25 % tolerance); after that: 10 of 10 runs passed with coverage. | Medium (flaky test); Low (design note) | Zain Jamshaid: keep watching in CI (20 runs at M3); document that the limiter spaces grants, not wire-level sends |
| VV-AN-02 | `Collector._fetch` would `raise None` (TypeError) if `max_retries` < 0 ever reached it (WB-OBS-01). | Low | Zain Jamshaid, M3 |
| VV-AN-03 | QR-07 says "measured at M4"; the course has three milestones. | Low (requirement defect) | Ilsa Maryam: re-baseline QR-07 to M3 in `requirements.md` |
| VV-AN-04 | FR-09 with `link_threshold = 0.0` links an account with no matching signal (WB-OBS-02). | Low (specification question) | Ilsa Maryam: decide at M3 requirement review whether `RunConfig` requires `threshold > 0` |

## 9. V&V for the remaining milestone (M3, week 13)

| When (relative to M3 submission, W13) | Task | Requirement IDs | Responsible | Exit criterion |
|---|---|---|---|---|
| W13 − 21 days (start of week 11) | Commit M2 work through feature branches in test-first order; enable branch protection; first CI run with gitleaks on real history | NFR-04, NFR-06, QR-13 | Rabbin Batool | CI green on `main`; gitleaks clean |
| W13 − 21 days | Close VV-AN-02…04; re-baseline QR-07 (VV-AN-03); run the stress test 20× in CI to confirm VV-AN-01 is closed | NFR-01, QR-06, QR-07 | Zain Jamshaid, Ilsa Maryam | 20/20 stress passes; issues closed |
| W13 − 18 days | Collect consent forms; freeze snapshots of 10 consenting profiles | QR-01, NFR-06 | Ilsa Maryam | 10 signed consents, frozen runs |
| W13 − 14 to − 9 days | Independent double labelling of claims; κ computed | QR-01 | all (pairs rotate) | labels complete, disagreements resolved |
| W13 − 14 days | Performance harness and recoverability test | NFR-03, QR-07, QR-05 | Zain Jamshaid, Rabbin Batool | thresholds met or defect raised |
| W13 − 10 days | Response-schema validation test | QR-16 | Rabbin Batool | every API response validates |
| W13 − 8 days | White-box extension: `RatingClaimRule.verify` (V(G) = 6), `CandidateInput.__post_init__` (V(G) = 7), `JobRequirementInput.__post_init__` (V(G) = 4), `_check_number` (V(G) = 3) | FR-01, FR-05, FR-10, FR-12 | Ilsa Maryam | basis paths tested, 100 % branch |
| W13 − 5 days | Run corpus through pipeline; confusion matrix | QR-01 | Ilsa Maryam | ≥ 90 % agreement, zero unsupported→supported |
| W13 − 3 days | Demonstration with consenting candidates; recruiter-facing report review; delete demo data | FR-02…FR-04, FR-13, FR-16, QR-03 | whole team + outside reader | demo log and review form complete |
| W13 − 1 day | Final RTM, defect status, coverage and static-analysis records into `docs/records/m3/` | QR-02, QR-06, QR-10, QR-11 | Zain Jamshaid (SCM audit), Ilsa Maryam | zero open Critical/High; every Must FR traced to a passing test |

## 10. Risks to V&V

| Risk | Effect on V&V | Mitigation |
|---|---|---|
| GitHub unauthenticated rate limit (60 requests/hour) and Codeforces "1 call / 2 s" terms | Live-API tests would be slow, flaky and could violate terms | All automated tests use recorded fixtures (`tests/fixtures/api/`, `tests/fixtures/snapshots/`) behind `FakeHttpClient`; live calls only in the M3 demo, with `GITHUB_TOKEN` from the environment and the per-source limiter (Codeforces limiter verified by `test_codeforces_limiter_honours_api_terms_of_one_call_per_two_seconds`) |
| Recorded fixtures drift from the real API shape | Tests pass but production parsing fails | M3 demo re-records one profile per source and diffs field sets against fixtures before the corpus run |
| Docker image availability: `minio/minio` is no longer published on Docker Hub | Integration tests and CI cannot start MinIO | Switched to `cgr.dev/chainguard/minio:latest` in `docker-compose.yml` and CI; pin a digest at M3 so a moved `latest` tag cannot break the baseline |
| Integration tests need containers locally | Members skip them | `-m "not integration"` split; CI always runs them with service containers |
| Timing-dependent tests on Windows (coarse timer, coverage overhead) | False failures (VV-AN-01) | Inject clocks/sleeps (already done in limiter and collector); keep timing assertions in stress tests with tolerance ≥ timer resolution |
| Few consenting candidates / privacy of real profiles | QR-01 corpus too small or unusable | Start consent collection at W13 − 18 days; team members' own profiles as fallback; delete data after validation (FR-16) |
| Concurrent edits during M2 (fixes landed while V&V ran) | Records go stale | Every record file starts with the command and timestamp; records re-generated after the last fix before submission |
| Same people build and verify | Blind spots | Cross-member assignment and external inspector (section 5) |

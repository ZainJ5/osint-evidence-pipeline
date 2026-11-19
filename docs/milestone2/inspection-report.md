# Formal Inspection Report — Milestone 2 (Fagan inspection)

SE431 M2 deliverable "formal inspection: report, defect log and CAPA tracking". Requirement IDs (FR/NFR/QR) are the
ones in [`docs/requirements.md`](../requirements.md).

| Field | Value |
|---|---|
| Inspection ID | INSP-M2-01 |
| Inspected build | Milestone 2 working tree, frozen as baseline **M2-INSP-BASE** (SHA-256 manifest, section 4) |
| Moderator / inspection lead | Zain Jamshaid |
| Report prepared | 2026-11-19 |
| Meeting date, time, place | [to fill in] |
| Status | Preparation and rework complete; **meeting and follow-up still to be held** (exit criteria not yet met, section 12) |

## 1. Objectives

1. Find defects in the highest-risk M2 code before the M2 baseline is tagged, so that QR-06 ("zero open
   Critical/High defects at each milestone submission") can be met with evidence.
2. Check the code against the requirements that tests find hard to show: concurrency (NFR-01, QR-08), reproducible
   replay (FR-14, NFR-07), exclusion of unlinked evidence (FR-09), deletion (FR-16), privacy (NFR-06, QR-13),
   accountability (QR-15) and the exception/error-code contract.
3. Produce a defect log and a CAPA (corrective and preventive action) record that the team can track to closure,
   and measure the inspection (defect density, inspection rate) for the M3 inspection.
4. Have the code read by people other than its author, including one inspector from the paired external team.

## 2. Inspection package and size

The package is the code where a defect does the most damage, chosen by the risks it carries (risk names as in the
team's risk register, R-01..R-08 style):

| Risk addressed | Why it matters | Files chosen |
|---|---|---|
| Wrong identity link (a stranger's evidence scored) | Unfair score, FR-08/FR-09 | `identity/resolver.py` |
| Non-reproducible replay | FR-14/NFR-07 fail, audit impossible | `pipeline.py`, `snapshot/store.py`, `snapshot/extractor.py`, `scoring/*` |
| Rate-limit violation / race conditions | Source bans, NFR-01/QR-08 | `collection/collector.py`, `runner.py`, `rate_limiter.py`, `pipeline.py` |
| Data deletion errors | FR-16 incomplete, or another candidate's data lost | `snapshot/store.py`, `adapters/postgres.py` |
| Wrong verdict / score | QR-01, FR-12/FR-13 | `scoring/rules.py`, `scoring/scoring.py` |
| PII leak, SQL injection, unclosed resources | NFR-06, QR-13, security | `adapters/postgres.py`, `adapters/http.py`, `pipeline.py` (logging) |

Not in the package (lower risk or already covered elsewhere): parsers and collectors per source (covered by recorded
fixtures and black-box tests), matching (M4, vector index), `inputs.py` (covered by the black-box EP/BVA design,
which already logged BB-DEF-01..04 there), the API layer (thin). `inputs.py`, `models.py`, `ports.py`, `errors.py`,
`log.py`, `identity/signals.py`, `identity/profiles.py`, `collection/github.py` and `interface/composition.py` were
read as **context only**.

**Size**, counted on the frozen baseline with
`wc -l <files>` (physical lines) and `grep -cvE '^\s*$|^\s*#' <file>` (non-blank, non-comment lines, NCLOC; docstrings
count as lines):

| File (baseline M2-INSP-BASE) | Owner (author) | Physical lines | NCLOC |
|---|---|---:|---:|
| `pipeline/core/pipeline.py` | Ilsa Maryam (M2 Team Lead/Integrator) | 194 | 169 |
| `pipeline/core/collection/collector.py` | Zain Jamshaid (M1) | 86 | 71 |
| `pipeline/core/collection/runner.py` | Zain Jamshaid (M1) | 51 | 43 |
| `pipeline/core/collection/rate_limiter.py` | Zain Jamshaid (M1) | 54 | 43 |
| `pipeline/core/snapshot/store.py` | Rabbin Batool (M2) | 63 | 52 |
| `pipeline/core/snapshot/extractor.py` | Rabbin Batool (M2) | 64 | 54 |
| `pipeline/core/identity/resolver.py` | Ilsa Maryam (M3) | 66 | 54 |
| `pipeline/core/scoring/rules.py` | Ilsa Maryam (M5) | 101 | 77 |
| `pipeline/core/scoring/scoring.py` | Ilsa Maryam (M5) | 107 | 81 |
| `pipeline/adapters/postgres.py` | Rabbin Batool (adapters) | 220 | 174 |
| `pipeline/adapters/http.py` | Rabbin Batool (adapters) | 46 | 34 |
| **Total** | | **1 052** | **852** |

852 NCLOC is inside the 600–900 line range the team set for one inspection; at the usual Fagan guideline of about
150 NCLOC per preparation hour this needs roughly 5–6 hours of individual preparation, and the meeting should be
split into two sessions of at most 2 hours each.

## 3. Roles

Rule from the quality plan: nobody inspects their own module. The author presents their own code and answers
questions; the reader paraphrases it; the recorder logs defects; inspectors look for defects; the moderator runs
the process and checks rework.

| Role | Person | Notes |
|---|---|---|
| Moderator / inspection lead | Zain Jamshaid | Plans, checks entry/exit criteria, runs the meeting, verifies rework. While his own collection code is discussed, the recorder chairs that part so that he never moderates the review of his own module. |
| Recorder | Rabbin Batool (Ilsa Maryam while Rabbin's own artifacts are discussed) | Keeps the defect log (section 8) during the meeting. |
| External inspector | [External inspector — name/team to be filled in] | From the paired external team assigned by the instructor. Inspects every artifact. |

Per-artifact assignment:

| Artifact | Author (presents) | Reader | Inspectors |
|---|---|---|---|
| `collection/collector.py`, `runner.py`, `rate_limiter.py` | Zain Jamshaid | Ilsa Maryam | Rabbin Batool, [External inspector — name/team to be filled in] |
| `snapshot/store.py`, `snapshot/extractor.py` | Rabbin Batool | Ilsa Maryam | Zain Jamshaid, [External inspector — name/team to be filled in] |
| `identity/resolver.py`, `scoring/rules.py`, `scoring/scoring.py` | Ilsa Maryam | Rabbin Batool | Rabbin Batool, Zain Jamshaid, [External inspector — name/team to be filled in] |
| `adapters/postgres.py`, `adapters/http.py` | Rabbin Batool | Ilsa Maryam | Zain Jamshaid, [External inspector — name/team to be filled in] |
| `pipeline.py` (orchestrator) | Ilsa Maryam | Rabbin Batool | Zain Jamshaid, [External inspector — name/team to be filled in] |

The orchestrator is owned by the M2 Team Lead/Integrator, Ilsa Maryam (see `docs/requirements.md` and the commit
plan in `docs/milestone2/scm.md`), so she presents it and does not read or inspect it.

## 4. Entry criteria

| # | Criterion | Evidence | Met? |
|---|---|---|---|
| E1 | Code builds and imports | `pytest` collects and imports every module of `pipeline/` | Yes |
| E2 | All tests pass | `.venv/Scripts/python -m pytest -q -m "not integration"` on the baseline: **416 passed, 10 deselected, 6 xfailed**. The 10 deselected are the PostgreSQL/MinIO integration tests (need `docker compose up`); the 6 xfailed are known black-box anomalies BB-DEF-01..04 in `inputs.py`, outside the package. | Yes (unit, system, stress, black-box) |
| E3 | Lint clean | `ruff check .` → "All checks passed!"; `ruff format --check` clean for every package file (one test file outside the package, being written in parallel, still needed formatting) | Yes for the package |
| E4 | Package frozen at a named baseline | The repository has no commits yet (see `docs/milestone2/scm.md`), so a git tag was not possible. The package was frozen as **M2-INSP-BASE** by a SHA-256 manifest: [`docs/records/m2/inspection-baseline.sha256`](../records/m2/inspection-baseline.sha256) (`sha256sum -c` shows exactly which files changed since). When the first commit exists, tag the commit holding these hashes as `m2-inspection-base`. | Yes (manifest); tag [to fill in] |
| E5 | Checklist and requirements available to every participant | Section 6 and `docs/requirements.md` | Yes |
| E6 | Moderator confirms the package is ready and distributes it | [to fill in: date distributed] | [to fill in] |

## 5. Process stages

| Stage | What happened | Date / effort |
|---|---|---|
| Planning | Moderator chose the package by risk (section 2), counted its size, assigned roles (section 3), set entry/exit criteria and the checklist (section 6), and froze the baseline. | 2026-11-19; effort [to fill in] |
| Overview | Each author gives a 10-minute walkthrough of design intent: Template Method collector and shared limiters (Zain), content-addressed snapshots and deterministic ids (Rabbin), noisy-OR one-hop resolution and Strategy scoring (Ilsa). | [to fill in] |
| Preparation | **AI-assisted pre-review** (see disclosure) read all 11 files against the checklist and confirmed 12 defects with failing tests or worked examples (section 8). Each human inspector then prepares individually on the frozen baseline, **without reading the AI findings first** so that their own findings stay independent, and records findings and preparation time. | Pre-review 2026-11-19. Human preparation time per inspector: [to fill in] |
| Meeting | Reader paraphrases each artifact; inspectors raise findings; recorder logs them; the meeting accepts, rejects or reclassifies INS-01..INS-12 and adds new ones (including the external inspector's, section 9). No fixes are discussed in the meeting. | Date [to fill in], start/end [to fill in], duration [to fill in], attendees [to fill in] |
| Rework | Done **before** the meeting for the 9 pre-review defects that were confirmed by a failing test, each test-first (section 10). Defects added at the meeting are reworked by their author after it. If the meeting rejects a pre-review defect, its fix is reverted or kept as an improvement by team decision. | 2026-11-19 for INS-01..09, INS-12; new defects [to fill in] |
| Follow-up | Moderator checks every rework item against its test, re-runs the suite, confirms deferred items have an M3 owner, and signs off (section 14). | [to fill in] |

## 6. Inspection checklist

Derived from the requirements and the team's coding rules. Every finding names the checklist item it violates.

| ID | Check | Source |
|---|---|---|
| C-01 | Every external failure is translated into the project exception hierarchy (`PipelineError` subclasses) with a stable error code; no bare `except`; broad `except Exception` only to record state and re-raise. Every exit path of a stateful operation leaves a terminal status. | NFR-02, QR-04, `errors.py` |
| C-02 | Error codes are stable strings; HTTP status mapping in the API relies on them (`*NOT_FOUND` → 404). | FR-15, QR-16 |
| C-03 | Inputs are validated at the boundary: ranges, types, and non-finite numbers (NaN, inf) for every numeric parameter. | `inputs.py`, NFR-04 |
| C-04 | Snapshots and value objects are immutable (frozen dataclasses, no `update()`); a snapshot is never rewritten. | FR-06, QR-14 |
| C-05 | Writes are idempotent (deterministic ids, `ON CONFLICT DO NOTHING`) and ordered so a crash leaves no dangling reference. | FR-06, QR-05 |
| C-06 | Shared mutable state across coroutines/threads is owned by one long-lived object and protected; nothing that must be shared (rate limiters, connections) is created per call. Check-then-act sequences are free of races. | NFR-01, QR-08 |
| C-07 | Emails and other personal data never reach logs or error contexts. | NFR-06, QR-13 |
| C-08 | Everything replay needs is read from stored data (snapshots, run record, stored job), never from current process state; ordering is deterministic. | FR-14, NFR-07, QR-05 |
| C-09 | Evidence of unlinked accounts is excluded before matching, verification and scoring. | FR-09 |
| C-10 | Every evidence node, verdict and score carries `run_id` and `snapshot_id`. | QR-15, QR-03 |
| C-11 | SQL is built only with `psycopg.sql` identifiers and placeholders; no string formatting of values. | Security |
| C-12 | Resources are released: HTTP clients closed, DB connections closed, blob responses released. | Reliability |
| C-13 | Cyclomatic complexity ≤ 10 per function (Ruff C90). | QR-11 |
| C-14 | Numeric logic: units, precision and int/float boundaries are right; derived values stay inside the bounds of their inputs (confidence in [0, 1], score in [0, 100]). | FR-08, FR-12, FR-13 |
| C-15 | Equality/“identical” checks compare the whole object that the requirement talks about, not one field. | FR-14 |
| C-16 | Names, docstrings and comments match what the code does. | Maintainability |
| C-17 | Each requirement the code implements has a test that would fail if the code broke it, at the level where it can break (unit vs orchestrator). | QR-02, NFR-04 |

## 7. Preparation results (summary)

The pre-review found **12 defects**: 0 Critical, 2 High, 3 Medium, 7 Low. Nine were fixed test-first; two Low
defects are deferred to M3 with justification; INS-12 (a test gap) is closed by the INS-01 test. Checks that found
**no** defect in the package: C-02, C-04, C-07 (no email reaches a log line; `run_failed` for unexpected errors logs
only the exception type), C-09 (`_analyse` passes only linked evidence downstream), C-10, C-11 (all SQL in
`postgres.py` uses `sql.Identifier`/placeholders; the eraser uses `%s` parameters), C-13 (Ruff C90 clean).

Severity scale used (from the SQAP): **Critical** — wrong result or data loss in normal use, or a security/privacy
breach; **High** — a Must requirement is violated in a realistic scenario; **Medium** — a requirement is violated in
an edge case, or a run is left in a wrong state; **Low** — unlikely edge case, efficiency, resource hygiene,
documentation or test gap. The meeting may reclassify any item.

## 8. Defect log

Line numbers refer to the frozen baseline M2-INSP-BASE. Phase found for all: *Inspection — preparation (AI-assisted
pre-review)*, unless stated.

| ID | Artifact (file:line) | Checklist | Description | Severity | Type | Status |
|---|---|---|---|---|---|---|
| INS-01 | `pipeline/core/pipeline.py:98` | C-06 | `execute()` builds a **new `CollectionRunner` per call**, and the runner owns the per-source `RateLimiter`s. Two candidates run concurrently (two API requests) therefore each get their own limiters: the per-source minimum interval (including the Codeforces 1 call / 2 s floor) is not enforced across runs. Reproduced: two concurrent `execute()` calls hit `api.github.com` 0.0000 s apart with a 0.05 s interval configured. Violates NFR-01/QR-08; the stress test passes only because it drives one runner directly (INS-12). | High | Logic (concurrency) | Fixed, verified |
| INS-02 | `pipeline/core/pipeline.py:92-93` | C-08, C-03 | A job id that already exists is silently kept with its **old** requirements, but the run is scored against the **new** ones passed in. Replay later loads the stored (old) job, so the replayed score differs (FR-14/NFR-07) and the stored job does not describe the report. Reproduced: second `execute()` with `job-1` and skills `("Go",)` is accepted. | High | Data | Fixed, verified |
| INS-03 | `pipeline/core/pipeline.py:80, 152` | C-08 | Replay resolves identities with the **current** process configuration (`self._config.link_threshold`), although the run record stores the configuration it ran with (`RunRecord.config`). After a configuration change or restart with other settings, replay links different accounts. Reproduced: replay with `link_threshold=1.0` gives `score_identical=False`. | Medium | Logic | Fixed, verified |
| INS-04 | `pipeline/core/pipeline.py:103-106` | C-01 | Only `PipelineError` marks a run `failed`. Any other exception (the runner deliberately re-raises non-`CollectionError` exceptions as bugs) leaves the run **`running` forever** with no `finished_at`, and replay refuses it. Reproduced with a collaborator raising `RuntimeError`. | Medium | Logic (error handling) | Fixed, verified |
| INS-05 | `pipeline/core/scoring/rules.py:45-46, 69-70` | C-14 | Skill-duration claims are compared with **whole** observed years, but claims may be fractional (`years` is a float, e.g. "2.5 years"). 2.9 observed years vs 2.5 claimed gives `partially_supported`; 7 months vs 0.5 claimed gives `partially_supported`. Wrong verdict lowers `verified_skills` (FR-12, QR-01). | Medium | Logic | Fixed, verified |
| INS-06 | `pipeline/core/pipeline.py:128` | C-15 | `score_identical` compares only `total`. A replay with different components, weights, evidence ids or verdicts but the same total is reported identical, which overstates FR-14/NFR-07 ("same evidence and score"). | Low | Logic | Fixed, verified |
| INS-07 | `pipeline/core/pipeline.py:121-123` | — (efficiency) | Replay extracts the run twice (once in `_analyse`, once more for the comparison), so every snapshot blob is fetched and hash-verified twice. | Low | Logic (efficiency) | Fixed, verified |
| INS-08 | `pipeline/core/scoring/scoring.py:72` | C-03 | `_validated` accepts `NaN` and `inf` weights: `nan < 0` is false. A `NaN` weight makes the weighted mean `NaN`, which the clamp turns into a total of 0 without any error. Also found independently by white-box testing as anomaly WB-DEF-01. | Low | Data | Fixed, verified |
| INS-09 | `pipeline/core/identity/resolver.py:54-55` | C-14 | A one-hop link takes the hop's confidence without bounding it by the confidence of the account it hops through. Worked example: GitHub `alex` linked by name only (0.50), Codeforces `alex` then linked through GitHub by identical handle with **0.60** — more confident than the link it depends on. The reported confidence overstates the evidence (FR-08 "calibrated"); the link/no-link decision does not change at the default threshold. | Low | Logic | Fixed, verified |
| INS-10 | `pipeline/core/snapshot/store.py:35, 40-42` with `pipeline/adapters/postgres.py:212-220` | C-06, C-05 | Blobs are content-addressed and shared between candidates. `PostgresEraser` selects "keys no other candidate uses" and deletes them later, while `SnapshotStore.freeze` puts the blob and only then inserts the row. If another candidate freezes a byte-identical payload (e.g. an empty Codeforces `result` list) between the eraser's SELECT and its blob delete, that candidate's new snapshot row points to a deleted blob: its replay fails with `NOT_FOUND`. Narrow window, needs concurrent deletion; QR-14 integrity check detects it (no silent wrong result). | Low | Data (concurrency) | Deferred to M3 |
| INS-11 | `pipeline/adapters/http.py:18-23, 31-32` (with `interface/composition.py:32`) | C-12 | `HttpAdapter` opens an `httpx.AsyncClient` but nothing ever calls `aclose()`: the composition root and the API have no shutdown hook. Connections are released only at process exit; in tests each app instance leaks a client. | Low | Interface (resource lifecycle) | Deferred to M3 |
| INS-12 | `tests/stress/test_collection_stress.py:1-10` | C-17 | The NFR-01 stress test drives `CollectionRunner` directly, so it cannot detect that the orchestrator bypasses the shared runner (INS-01). The requirement was tested below the level where it broke. | Low | Test | Fixed, verified |

Cross-reference: the black-box design separately logged BB-DEF-01..04 (unvalidated `RunConfig`/job fields in
`inputs.py`, outside this package). BB-DEF-02 (NaN `min_interval_seconds`) is the same pattern as INS-08; see the
preventive action for INS-08.

## 9. External inspector findings

To be filled in at the meeting by the recorder from the external inspector's own findings. Do not copy pre-review
findings into this table.

| # | Artifact (file:line) | Checklist | Description | Severity | Type | Duplicate of | Decision |
|---|---|---|---|---|---|---|---|
| EXT-01 | [to fill in] | [to fill in] | [to fill in] | [to fill in] | [to fill in] | [to fill in] | [to fill in] |
| EXT-02 | | | | | | | |
| EXT-03 | | | | | | | |

Meeting decisions on the pre-review findings (accept / reject / reclassify): INS-01 [to fill in], INS-02 [to fill in],
INS-03 [to fill in], INS-04 [to fill in], INS-05 [to fill in], INS-06 [to fill in], INS-07 [to fill in], INS-08 [to
fill in], INS-09 [to fill in], INS-10 [to fill in], INS-11 [to fill in], INS-12 [to fill in].

## 10. Defect statistics

Pre-review defects only (INS-01..INS-12); the meeting's own findings are added after it.

**By severity**

| Severity | Count | Fixed | Deferred |
|---|---:|---:|---:|
| Critical | 0 | 0 | 0 |
| High | 2 | 2 | 0 |
| Medium | 3 | 3 | 0 |
| Low | 7 | 5 | 2 |
| **Total** | **12** | **10** | **2** |

**By type:** logic 7 (INS-01, 03, 04, 05, 06, 07, 09), data 3 (INS-02, 08, 10), interface 1 (INS-11), test 1
(INS-12), documentation 0, standards 0.

**By module**

| Module | Files | Defects | IDs |
|---|---|---:|---|
| Orchestrator | `pipeline.py` | 6 | INS-01, 02, 03, 04, 06, 07 |
| M5 Scoring | `rules.py`, `scoring.py` | 2 | INS-05, 08 |
| M3 Identity | `resolver.py` | 1 | INS-09 |
| M2 Snapshot + adapters | `store.py`, `postgres.py`, `http.py` | 2 | INS-10, 11 |
| M1 Collection | `collector.py`, `runner.py`, `rate_limiter.py` (+ stress test) | 1 | INS-12 (code itself: no defect found) |

**Density**

| Measure | Value |
|---|---|
| Package size | 852 NCLOC (1 052 physical lines) |
| Defects per KLOC (all) | 12 / 0.852 = **14.1 per KLOC** |
| Major defects (Critical+High+Medium) per KLOC | 5 / 0.852 = **5.9 per KLOC** |
| Preparation rate (NCLOC per hour, per human inspector) | [to fill in — time is human data] |
| Meeting rate (NCLOC per hour) | [to fill in] |
| Total inspection effort (person-hours) | [to fill in] |
| Defects found per person-hour | [to fill in] |
| Share of defects found only by the meeting / external inspector | [to fill in] |

Observation: half the defects sit in the orchestrator, the seam where modules meet. Each module's own unit tests
were green; the defects are in how the modules are wired together (a runner rebuilt per call, a config read from
the wrong place, a job looked up in two different places).

## 11. CAPA tracking

Corrective action = what was changed to remove this defect. Preventive action = what stops the same kind of defect
from coming back. Every new test below failed against the baseline before the fix and passes after it. Closure date
2026-11-19 for every fixed item; the moderator's follow-up check (section 14) confirms closure.

| ID | Root cause | Corrective action (file) | Preventive action | Verification (test → result) | Closed | Status |
|---|---|---|---|---|---|---|
| INS-01 | The runner was designed to share limiters "per runner", but the orchestrator treated the runner as a cheap per-call helper; no test exercised two runs through the orchestrator. | `PipelineRun.__init__` creates one `CollectionRunner` for the pipeline's lifetime; `execute()` reuses it (`pipeline/core/pipeline.py`). | Checklist C-06 ("nothing that must be shared is created per call"); concurrency test at orchestrator level; M3: make the stress test also go through `PipelineRun`. | `tests/system/test_inspection_m2.py::test_ins01_concurrent_runs_share_one_rate_limiter_per_source` — failed ("api.github.com: two runs called it 0.0000s apart") → passes | 2026-11-19 | Closed |
| INS-02 | Job ids are chosen by the client, but the code assumed "same id ⇒ same content" without checking it; the run used the input job while replay used the stored one. | New `_register_job()`: stores a new job, accepts an identical one, and raises `ValidationError` code `JOB_CONFLICT` (HTTP 422) for a known id with different content, before anything is written (`pipeline/core/pipeline.py`). | Checklist C-08 (replay reads only stored data) and C-03; rule for client-supplied ids: same id must mean same content. | `tests/system/test_inspection_m2.py::test_ins02_reusing_a_job_id_with_different_requirements_is_rejected` — failed ("DID NOT RAISE") → passes | 2026-11-19 | Closed |
| INS-03 | The run configuration was recorded for audit but not treated as replay input; the resolver was built once from process state. | `_analyse()` builds the `IdentityResolver` from `run.config["link_threshold"]` (falls back to the current config for old records) (`pipeline/core/pipeline.py`). | Checklist C-08. Residual for M3: the scoring strategy's weights are code, not run configuration — record them in `RunRecord.config` when weights become configurable. | `tests/system/test_inspection_m2.py::test_ins03_replay_uses_the_configuration_recorded_with_the_run` — failed (`score_identical=False`) → passes | 2026-11-19 | Closed |
| INS-04 | Error handling only covered the project hierarchy; the "bugs are re-raised" policy in the runner was not matched by a terminal state in the orchestrator. | Second handler `except Exception` marks the run `failed` (code `UNEXPECTED_ERROR`, logs only the exception type, no message, so no PII) and re-raises; shared `_fail()` helper (`pipeline/core/pipeline.py`). | Checklist C-01 ("every exit path leaves a terminal status"); fault-injection test with a non-project exception. | `tests/system/test_inspection_m2.py::test_ins04_unexpected_error_marks_the_run_failed` — failed (`'running' == 'failed'`) → passes | 2026-11-19 | Closed |
| INS-05 | Integer "whole years" semantics were designed for integer claims; the claim model allows floats and no test used a fractional claim. | Supported when whole years ≥ claim **or** elapsed days / 365.25 ≥ claim; rationale also states the elapsed years (`pipeline/core/scoring/rules.py`). Day-exact integer behaviour is unchanged (black-box BB-FR12-09..14 and white-box WB-SCO-04/05 still pass). | Checklist C-14 (int/float boundaries); BVA on fractional values added to the M3 black-box design. | `tests/unit/scoring/test_inspection_m2_scoring.py::test_ins05_fractional_claimed_years_compare_with_elapsed_time` (4 cases) — 2 failed → all pass | 2026-11-19 | Closed |
| INS-06 | "Identical" was implemented as the cheapest field comparison. | `score_identical = original == report` (total, components and verdicts) (`pipeline/core/pipeline.py`). | Checklist C-15. Integration test `tests/integration/test_pipeline_postgres.py` must be re-run to confirm the PostgreSQL round-trip keeps equality (section 12, X5). | `tests/system/test_inspection_m2.py::test_ins06_replay_compares_components_not_only_the_total` → passes | 2026-11-19 | Closed |
| INS-07 | `_analyse` did not return the nodes it extracted, so replay extracted again. | `_analyse` returns `(report, nodes)`; replay reuses the nodes (`pipeline/core/pipeline.py`). | None beyond review: behaviour-preserving change. | Existing `tests/system/test_pipeline_system.py::test_replay_reproduces_evidence_and_score_without_network` and `::test_replay_of_tampered_snapshot_is_refused` → pass | 2026-11-19 | Closed |
| INS-08 | Validation checked sign and type but not finiteness; Python comparisons with NaN are always false. | Weights must satisfy `0 <= w < inf` (rejects NaN and inf) (`pipeline/core/scoring/scoring.py`). | Checklist C-03 (NaN/inf for every numeric parameter). Same pattern open as BB-DEF-02 in `inputs.py`: M3 action to add one shared finite-number check to `RunConfig`. | `tests/unit/scoring/test_inspection_m2_scoring.py::test_ins08_non_finite_weights_are_rejected[nan, inf]` → pass; `tests/whitebox/test_basis_paths_scoring.py::test_wb_sco_11_non_finite_weight_is_rejected` (was strict xfail WB-DEF-01) → passes | 2026-11-19 | Closed |
| INS-09 | The hop rule took the maximum of direct and hop confidence without considering the path. | Hop confidence capped by the confidence of the account it hops through: `max(direct, min(hop, direct[j]))` (`pipeline/core/identity/resolver.py`). Link decisions at the default threshold are unchanged (all identity unit, black-box and white-box tests pass). | Checklist C-14 (derived confidence bounded by its inputs). **Open design question for the meeting:** should a hop use the product rule (0.5 × 0.6 = 0.3, i.e. *not* linked) instead of the weakest link? Needs the M3 calibration corpus. | `tests/unit/identity/test_inspection_m2_identity.py::test_ins09_hop_confidence_never_exceeds_the_account_it_hops_through` — failed (`0.6 <= 0.5`) → passes | 2026-11-19 | Closed |
| INS-10 | Blob sharing across candidates (a deliberate, tested design decision) makes deletion a check-then-act across two stores without a common lock. | None yet. **Deferred, justification:** needs concurrent deletion of one candidate and a byte-identical freeze for another within milliseconds; the M2 deployment is a single API worker; the effect is detected by the QR-14 integrity check (`NOT_FOUND`), never a silent wrong score. Fixing it changes a tested design decision (shared blobs), which needs the team's agreement (risk R-05 change control). | M3 owner Rabbin Batool: choose candidate-scoped object keys **or** a PostgreSQL advisory lock taken by both `freeze` and the eraser; add an integration test that interleaves delete and freeze. Checklist C-06 (check-then-act). | Reasoned trace of the interleaving (section 8); test to be written with the fix. | — | Open |
| INS-11 | The adapter offers `aclose()`, but no owner in the composition root is responsible for calling it. | None yet. **Deferred, justification:** one client per process in production, closed at process exit; no functional effect in M2. | M3 owner Rabbin Batool: give `PipelineRun`/composition an `aclose()` and call it from a FastAPI lifespan handler; test that the client is closed on shutdown. Checklist C-12. | — | — | Open |
| INS-12 | The stress test was written at the unit that implements the limiter, not at the entry point that uses it. | New orchestrator-level concurrency test (the INS-01 test) (`tests/system/test_inspection_m2.py`). | Checklist C-17 (test at the level where the requirement can break). | `test_ins01_concurrent_runs_share_one_rate_limiter_per_source` → passes | 2026-11-19 | Closed |

Files changed by the rework: `pipeline/core/pipeline.py`, `pipeline/core/scoring/rules.py`,
`pipeline/core/scoring/scoring.py`, `pipeline/core/identity/resolver.py`. Tests added:
`tests/system/test_inspection_m2.py`, `tests/unit/scoring/test_inspection_m2_scoring.py`,
`tests/unit/identity/test_inspection_m2_identity.py`. `sha256sum -c docs/records/m2/inspection-baseline.sha256`
reports exactly these four source files as changed since M2-INSP-BASE.

## 12. Exit criteria

| # | Criterion | Status |
|---|---|---|
| X1 | Every Critical/High/Medium defect fixed and verified by a test that failed before the fix | Met for INS-01..05 (pre-review). Defects added at the meeting: [to fill in] |
| X2 | Every Low defect fixed, or deferred with justification, owner and target milestone | Met (INS-10, INS-11 deferred to M3, owner Rabbin Batool) |
| X3 | Full non-integration suite passes after rework | Met: `.venv/Scripts/python -m pytest -q -m "not integration"` → **546 passed, 10 deselected, 6 xfailed** (2026-11-19). The 6 xfailed are BB-DEF-01..04 outside the package. |
| X4 | Ruff and Pylint clean on the reworked code | Met: `ruff check .` → all checks passed; `pylint pipeline` → 10.00/10 |
| X5 | Integration tests re-run against PostgreSQL and MinIO (INS-02 and INS-06 depend on round-trip equality) | Met: `pytest -m integration` against `postgres:16` and `cgr.dev/chainguard/minio` containers → **10 passed** (2026-11-19) |
| X6 | Meeting held with the external inspector; all pre-review findings accepted/rejected; external findings logged | **Not yet met** — [to fill in] |
| X7 | Moderator follow-up confirms every rework item and signs off | **Not yet met** — [to fill in] |

**Overall: exit criteria not yet met.** Preparation, rework and the integration re-run are complete; X6–X7 depend
on the meeting.

## 13. Follow-up and lessons for the next inspection (M3)

Follow-up actions:

1. Before the meeting each inspector verifies the pre-review findings for their artifacts on the frozen baseline
   (`sha256sum -c docs/records/m2/inspection-baseline.sha256` shows the baseline differs only in the four reworked
   files; use the baseline versions for preparation).
2. Integration tests (X5) re-run after rework: 10 passed on 2026-11-19.
3. Open one GitHub issue per defect (label `defect` plus a severity label) and reference it from the fix commit, one
   commit per defect (failing test first, then fix), as `docs/milestone2/scm.md` requires.
4. Track INS-10 and INS-11 to M3 closure; decide the INS-09 design question (weakest link vs product rule).

Lessons:

1. **Inspect the seams, not only the modules.** Six of twelve defects were in the orchestrator, while every module's
   unit tests were green. The M3 package should include whatever code wires modules together, and C-17 should be
   asked explicitly: "is this requirement tested at the level where it can break?"
2. **Shared resources need one owner.** INS-01, INS-10 and INS-11 are all "who owns this shared thing for how
   long?" — a limiter, a blob, a client. Add an ownership/lifecycle pass to the overview.
3. **Replay inputs are a list, and the list must be complete.** INS-02 and INS-03 came from replay reading inputs
   from somewhere other than the stored run. For M3, write down every input of `_analyse` and where replay gets it.
4. **Numeric validation needs a NaN/inf check everywhere.** INS-08 and BB-DEF-02 are the same defect in two
   modules: fix the pattern once.
5. **Keep AI-assisted findings separate from human ones.** Human inspectors prepare before reading the pre-review
   so that the meeting measures what people find; record which findings came from which source so the M3
   comparison (defects per person-hour, share found by the external inspector) is meaningful.
6. Record preparation and meeting time as it happens; the rate fields in section 10 cannot be reconstructed later.

## 14. Sign-off

| Role | Name | Signature | Date |
|---|---|---|---|
| Moderator / inspection lead | Zain Jamshaid | [to fill in] | [to fill in] |
| Author (collection) | Zain Jamshaid | [to fill in] | [to fill in] |
| Author (snapshot, adapters) / recorder | Rabbin Batool | [to fill in] | [to fill in] |
| Author (identity, scoring) / reader | Ilsa Maryam | [to fill in] | [to fill in] |
| Author (orchestrator) | [to be confirmed] | [to fill in] | [to fill in] |
| External inspector | [External inspector — name/team to be filled in] | [to fill in] | [to fill in] |

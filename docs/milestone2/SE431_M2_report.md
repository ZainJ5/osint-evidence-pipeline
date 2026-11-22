# OSINT Evidence Pipeline — SE431 Milestone 2

Inspection, static analysis, V&V, test design and SCM baseline. SE431 Software Quality Assurance, joint project with
SE423, Fall 2026. Instructor: Dr. Mian Muaz Razaq. Team: Zain Jamshaid (2023772), Rabbin Batool (2023586),
Ilsa Maryam (2023258). Repository: https://github.com/ZainJ5/osint-evidence-pipeline

This document is the entry point for the Milestone 2 quality work. It holds the RTM v2, the risk register update and
the consolidated defect/CAPA register; each rubric deliverable has its own document, linked below. Every quality
activity was applied to the actual M2 build described in `docs/milestone2/SE423_M2_report.md`.

## 1. Roles for Milestone 2

Roles follow the rotation planned in the Milestone 1 SQA document. Black-box and white-box design were planned for
M3 but are required by the M2 rubric, so the M3 design leads did them early.

| Deliverable | Lead | Reviewers | Document |
|---|---|---|---|
| Fagan inspection, defect log, CAPA | Zain Jamshaid (moderator) | Rabbin Batool, Ilsa Maryam, external inspector | [inspection-report.md](inspection-report.md) |
| Static analysis report | Rabbin Batool | Zain Jamshaid, Ilsa Maryam | [static-analysis-report.md](static-analysis-report.md) |
| V&V plan (IEEE 1012) | Ilsa Maryam | Zain Jamshaid, Rabbin Batool | [vv-plan.md](vv-plan.md) |
| Black-box test design (EP/BVA) | Rabbin Batool | Zain Jamshaid, Ilsa Maryam | [blackbox-test-design.md](blackbox-test-design.md) |
| White-box test design (CFG, V(G), basis paths) | Ilsa Maryam | Zain Jamshaid, Rabbin Batool | [whitebox-test-design.md](whitebox-test-design.md) |
| SCM quality-gate evidence | Zain Jamshaid | Rabbin Batool, Ilsa Maryam | [scm.md](scm.md) |
| RTM v2, risk register, CAPA register | Ilsa Maryam (Team Lead M2) | all | this document |

Raw evidence (tool outputs, coverage, inspection baseline hashes) is in `docs/records/m2/`.

## 2. Summary of the M2 quality status

| Measure | Value on the `m2-baseline` code | Source |
|---|---|---|
| Automated tests | 734 passed: 723 non-integration + 11 integration against PostgreSQL 16 and MinIO | `pytest`; CI run https://github.com/ZainJ5/osint-evidence-pipeline/actions/runs/45028442893 |
| Line coverage of `pipeline.core` | 99 % (1,642 statements, 22 missed; gate: 60 %) | `docs/records/m2/coverage-full.txt` |
| Pylint | 10.00/10 (baseline 9.59), CI gate `--fail-under=9.9` | static analysis report |
| Ruff | 0 findings; max cyclomatic complexity 7 (`CandidateInput.__post_init__`) | static analysis report |
| Defects found at M2 | 12 inspection (0 Critical, 2 High, 3 Medium, 7 Low), 4 black-box, 1 white-box (duplicate of INS-08), 1 review (PII in rationale) | section 4 |
| Open defects | 1 Low (INS-10), deferred to M3 with justification | section 4 |
| Open Critical/High defects | 0 (QR-06 met) | section 4 |
| Inspection meeting | **not yet held**; preparation and rework done | inspection report §12 |
| Repository history | M2 work merged to `main` through one `feature/m2-*` branch per module; tests and implementation are separate commits, but the implementation commit precedes the test commit on each branch (see SE423 report §6.2) | `git log --graph main` |
| CI | all gates green on GitHub Actions | https://github.com/ZainJ5/osint-evidence-pipeline/actions/runs/45028442893 |

## 3. Requirements Traceability Matrix, version 2

Changes from v1: the "Implemented in" and "Test evidence" columns now point at the M2 build, and the status reflects
test execution on the `m2-baseline` code. Status values: **Verified** (passing automated tests cover the requirement at the
stated level), **Partial** (some aspects verified, gap stated), **Planned**. "BB" and "WB" IDs are defined in the
black-box and white-box design documents.

### 3.1 Functional requirements

| ID | Implemented in | Test evidence | Status |
|---|---|---|---|
| FR-01 | `core/inputs.py` `CandidateInput`; `pipeline.py` `execute` stores `CandidateRecord` | `tests/unit/collection/test_candidate_input.py` (BB-FR01-01..24); `tests/blackbox/test_bb_candidate.py` (BB-FR01-25..36); `tests/blackbox/test_bb_api.py` (BB-FR15-01..07) | Verified |
| FR-02 | `core/collection/github.py` (REST commits endpoint instead of git clone, deviation D2 in SE423 report) | `tests/unit/collection/test_source_collectors.py`, `test_collector_contract.py`; live call blocked by GitHub's 60 req/h limit on 2026-11-19 (handled as `partial`) | Verified (fixtures); live re-check with a token pending |
| FR-03 | `core/collection/codeforces.py` | `tests/unit/collection/test_source_collectors.py`; live run against the real Codeforces API produced 7 evidence nodes | Verified |
| FR-04 | `core/collection/leetcode.py` (GraphQL POST) | `tests/unit/collection/test_source_collectors.py`; live call to the LeetCode GraphQL endpoint succeeded | Verified |
| FR-05 | `core/collection/collector.py` `_fetch`, `rate_limiter.py`, `runner.py`, `factory.py` | `tests/unit/collection/test_collector_retry.py`, `test_rate_limiter.py`; BB-FR05-01..34; WB-COL-01..07; `tests/stress/test_collection_stress.py` | Verified |
| FR-06 | `core/snapshot/store.py` `freeze`/`load`; `migrations/001_initial.sql` | `tests/unit/snapshot/test_snapshot_store.py`; `tests/integration/test_minio.py`, `test_postgres.py` | Verified |
| FR-07 | `core/snapshot/parsers.py`, `extractor.py` | `tests/unit/snapshot/test_parsers.py`, `test_extractor.py` (determinism, 1 vs 4 workers); BB-FR07-01..03 | Verified |
| FR-08 | `core/identity/signals.py`, `resolver.py`, `profiles.py` | `tests/unit/identity/*`; WB-IDN-01..07; `tests/system/test_pipeline_system.py::test_all_three_accounts_are_linked_with_rationale` | Verified (precision on labelled corpus: M3, QR-01) |
| FR-09 | `resolver.py` `_link`; `pipeline.py` filters evidence by linked handles | BB-FR09-01..10, BB-FR01-21..24; `test_unlinked_account_evidence_is_excluded` | Verified |
| FR-10 | `core/matching/normalizer.py`, `matcher.py` | `tests/unit/matching/*`; BB-FR10-01..23 | Verified |
| FR-11 | `core/scoring/claims.py` with an `LLMProvider`: `ClaudeClaimProvider` when `ANTHROPIC_API_KEY` is set, otherwise `RuleBasedClaimProvider` | `tests/unit/scoring/test_claims.py`, `tests/unit/adapters/test_rule_claims.py`, `test_claude_llm.py` (SDK mocked); `test_replay_reuses_the_stored_claims_instead_of_asking_the_llm_again` | Verified with the deterministic providers; Claude output accuracy on the labelled corpus: M3 (QR-01) |
| FR-12 | `core/scoring/rules.py` (skill, rating, solved rules), `verifier.py` | `tests/unit/scoring/test_skill_rule.py`, `test_rating_rule.py`, `test_solved_rule.py`; BB-FR12-01..16; WB-SCO-01..06; INS-05 test | Verified (corpus accuracy QR-01: M3) |
| FR-13 | `core/scoring/scoring.py` | `tests/unit/scoring/test_scoring.py`; BB-FR13-01..17; WB-SCO-07..11; `test_every_cited_evidence_node_resolves_to_a_snapshot_of_the_run` | Verified |
| FR-14 | `pipeline.py` `replay` (no network, no writes) | `test_replay_reproduces_evidence_and_score_without_network`, `test_replay_of_tampered_snapshot_is_refused`; BB-FR14-01..04; INS-02/03/06 tests; `tests/integration/test_pipeline_postgres.py` | Verified |
| FR-15 | `pipeline/interface/api.py` (10 endpoints); web UI in `ui/` | `tests/system/test_api.py`, `test_api_ui.py`; BB-FR15-01..13 | Verified |
| FR-16 | `pipeline.py` `delete_candidate`; `adapters/postgres.py` `PostgresEraser`; FK cascade | `test_delete_candidate_removes_rows_and_blobs`; `tests/integration/test_pipeline_postgres.py`, `test_postgres.py` | Verified (concurrent delete/freeze race INS-10 open) |

### 3.2 Non-functional and quality requirements

| ID | Related | Test evidence | Status |
|---|---|---|---|
| NFR-01 / QR-08 | FR-05 | `tests/stress/test_collection_stress.py` (20 candidates, overlap across sources, per-source gaps); INS-01 test (limiters shared across runs) | Verified |
| NFR-02 / QR-04 | FR-05 | `test_one_source_failing_gives_partial_run_with_other_evidence`; BB-NFR02-01..05 (timeout, 5xx, malformed body, 404) | Verified |
| NFR-03 / QR-07 | FR-02, FR-10 | Not measured yet; profiling harness and 10 000-vector benchmark planned | Planned (M3) |
| NFR-04 / QR-10 | all | 99 % line coverage of `pipeline.core`; every port has a fake in `adapters/fakes.py` | Verified |
| NFR-05 / QR-11 | all | Ruff 0 findings, Pylint 10.00, max V(G) 7; CI gates | Verified |
| NFR-06 / QR-13 | FR-01 | `tests/unit/core/test_log.py` (email scrubbing); `test_rationale_does_not_store_the_email_address`; gitleaks step in CI over the full history | Verified: gitleaks passed in https://github.com/ZainJ5/osint-evidence-pipeline/actions/runs/45028442893 |
| NFR-07 / QR-05 | FR-14 | Replay tests above. A kill-and-restart test during extraction is not written yet | Partial (QR-05 restart test: M3) |
| NFR-08 | FR-02..04 | CI grep for selenium/playwright; collectors use official API/public endpoints only (inspection checklist) | Verified |
| QR-01 | FR-11, FR-12 | Labelled 10-profile corpus with consenting volunteers | Planned (M3) |
| QR-02 | all FR | Every Must FR above has ≥ 1 passing automated test | Verified |
| QR-03 | FR-13 | `test_full_run_produces_bounded_explainable_report`, `test_every_cited_evidence_node_resolves_to_a_snapshot_of_the_run` | Verified |
| QR-06 | all | 0 open Critical/High defects (section 4) | Verified at M2 |
| QR-09 | design | CI dependency-direction step; `grep` returns nothing | Verified (locally and in CI) |
| QR-12 | design | `tests/unit/collection/test_collector_factory.py::test_new_source_plugs_in_without_editing_existing_code` (stub fourth collector) | Verified |
| QR-14 | FR-06 | `test_tampered_blob_raises_snapshot_error` (unit) and the MinIO tamper integration test | Verified |
| QR-15 | FR-07, FR-12, FR-13 | Every value object carries `run_id`; cited-node test above | Verified |
| QR-16 | FR-15 | `tests/system/test_api.py::test_openapi_schema_is_published` | Partial: responses are not yet validated against the schema with a validator |

## 4. Defect and CAPA register (consolidated)

Severity per SQAP §8. Full root cause / corrective / preventive / verification details are in the source documents.

| ID | Origin | Sev. | Summary | Corrective action | Status |
|---|---|---|---|---|---|
| INS-01 | Inspection | High | New `CollectionRunner` (and rate limiters) per `execute()`; limits not shared across runs | One runner per `PipelineRun` | Closed |
| INS-02 | Inspection | High | Reused job id with different skills broke replay | `JOB_CONFLICT` validation | Closed |
| INS-03 | Inspection | Medium | Replay used current threshold, not the run's recorded config | Resolver built from `run.config` | Closed |
| INS-04 | Inspection | Medium | Unexpected exception left run `running` forever | Marked `failed` with `UNEXPECTED_ERROR`, re-raised | Closed |
| INS-05 | Inspection | Medium | Fractional year claims compared with whole years | Compare elapsed days / 365.25 | Closed |
| INS-06 | Inspection | Low | `score_identical` compared only the total | Compare whole report | Closed |
| INS-07 | Inspection | Low | Replay extracted twice | Reuse nodes | Closed |
| INS-08 / WB-DEF-01 | Inspection, white-box | Low | NaN/inf scoring weights accepted | Finite check | Closed |
| INS-09 | Inspection | Low | Hop link more confident than its intermediate link | Weakest-link cap | Closed (design question for the meeting) |
| INS-10 | Inspection | Low | Delete vs. freeze race on shared blobs | — | Open, deferred to M3 (Rabbin Batool) |
| INS-11 | Inspection | Low | `HttpAdapter` client never closed | `PipelineRun.aclose()` closes the HTTP client; the FastAPI lifespan calls it at shutdown (`api.py:130`); verified by review, shutdown test planned (V-10) | Closed |
| INS-12 | Inspection | Low (test) | Stress test bypassed the orchestrator | Covered by INS-01 test | Closed |
| BB-DEF-01 | Black-box | Medium | `RunConfig` accepted non-integer counts | `_check_int` | Closed |
| BB-DEF-02 | Black-box | Medium | `min_interval_seconds=NaN` disabled rate limiting | `_check_number` (finite) | Closed |
| BB-DEF-03 | Black-box | Low | `max_repos` unvalidated (−1 dropped a repo) | integer in [0, 100] | Closed |
| BB-DEF-04 | Black-box | Low | Blank-only job id/title accepted | strip before check | Closed |
| REV-01 | Report review | Medium | `EmailSignal` rationale persisted the email address (NFR-06) | Rationale no longer contains the address; test added | Closed |
| REV-02 | Test review | Low (test) | Stress test flaky (1 failure in ~10 runs): measured gaps after the HTTP call included event-loop and OS jitter | Measure limiter grant times; tolerance 25 % of interval; exact arithmetic stays in fake-clock unit tests; 0 failures in 20 runs | Closed |
| SA-01..73 | Static analysis | Low | 67 Pylint findings + config items | All fixed (see report) | Closed |

Preventive actions adopted for M3: CI Pylint gate raised to 9.9; new inspection checklist items (shared limiter
lifetime, recorded config used on replay, blank-after-strip, finite floats, no PII in persisted rationale);
`_check_int`/`_check_number` helpers mandatory for new configuration fields.

## 5. Risk register, version 2

Probability/impact L/M/H; priority rule as in v1. "Evidence" cites M2 artifacts used to re-rate the risk.

| ID | Risk | P | I | Prio | Mitigation (M2 status) | Evidence at M2 | Owner | Status | Residual risk |
|---|---|---|---|---|---|---|---|---|---|
| R-01 | Source API rate limits, token revocation or API changes block collection or the demo | H | H | H | Recorded fixtures for all tests (done); per-source limiter with Codeforces 2 s floor (done); replay for demo (done); `GITHUB_TOKEN` support (done) | Live smoke test hit GitHub's unauthenticated limit (HTTP 403) and the run finished `partial` as designed | Zain Jamshaid | Open — materialised once | M: demo must use a token or replay |
| R-02 | LLM output non-deterministic, flaky tests and replay | H→M | M | M | Tests use the deterministic `RuleBasedClaimProvider` (done); replay reuses the claims stored with the run instead of calling the LLM again (done); prompt-hash cache for re-runs at M3 | Replay identical in all replay tests and against PostgreSQL; `test_replay_reuses_the_stored_claims_instead_of_asking_the_llm_again`. The real `ClaudeClaimProvider` is now used when an API key is set, so two fresh runs of one resume may extract different claims | Rabbin Batool | Open | M for re-runs; L for replay |
| R-03 | Identity resolution links different people | M | H | H | Refuse-to-link threshold (done, BVA-tested); rationale stored (done); weakest-link cap on one-hop links (INS-09); labelled corpus at M3 | Stranger test shows unlinked evidence excluded; INS-09 design question still open | Ilsa Maryam | Open | M until corpus precision measured |
| R-04 | Concurrent writes cause duplicates or races | M | M | M | Deterministic ids + unique keys + `ON CONFLICT DO NOTHING` (done); limiter shared across runs (INS-01) | Idempotent-freeze unit and integration tests; INS-10 race found by inspection | Zain Jamshaid | Open (INS-10) | L–M |
| R-05 | Scope creep | M | H | H | Requirement list as contract; `scope-change` label | No new requirements added at M2; deviations documented in SE423 report | Rabbin Batool | Open | L |
| R-06 | Infrastructure setup delays (PostgreSQL, MinIO, CI) | M | M | M | Docker Compose + CI written | **Materialised:** `minio/minio` no longer pullable from Docker Hub/quay.io; switched to `cgr.dev/chainguard/minio` in Compose and CI | Rabbin Batool | Mitigated: CI green on GitHub (an invalid-YAML step name had blocked every earlier run) | L |
| R-07 | Local embedding model gives poor matches | M | M | M | Embedder is a port; exact alias matching first, embeddings only as fallback | M2 uses `HashingEmbedder`; ranking quality not measured | Zain Jamshaid | Open (M3) | M |
| R-08 | Uneven contribution / member cannot explain their module | L→M | H | H | Fixed ownership, cross-review, dry runs | Large share of M2 material was AI-assisted (`docs/ai-usage-log.md`); each owner must review and fill in the log before submission | Ilsa Maryam | Open — raised | M |
| R-09 (new) | Repository history does not show TDD or independent review | H | H | H | One branch per module merged by PR (done); branch protection with one non-author approval, CODEOWNERS and the CI check (done); failing test committed first on every branch from M3 | M2 branches put the implementation commit before the test commit, and the M2 pull requests were merged without a review by another member | Zain Jamshaid | Open | M: the M2 history stays as it is; M3 history is audited (`scm.md` §7) |
| R-10 (new) | Fagan inspection exit criteria not met in time (meeting with external inspector) | M | M | M | Package frozen with SHA-256 manifest; checklist and pre-review ready; placeholders for meeting facts | Inspection report §12: X6, X7 open | Zain Jamshaid | Open | M |

## 6. What remains before submission

1. Hold the inspection meeting with the paired team's inspector; fill in the placeholders in the inspection report.
2. Done: CI green on GitHub (https://github.com/ZainJ5/osint-evidence-pipeline/actions/runs/45028442893); branch protection enabled on `main`; `.github/CODEOWNERS` added.
3. Done: GitHub issues opened for the defects in section 4 (label `defect` + severity + origin).
4. Each owner reviews the AI usage log rows for their work and fills in the "Team review" column.

# Requirements (from the Milestone 1 documents)

Identifiers are shared by the SE423 proposal and the SE431 quality documents. Owners: Zain Jamshaid (M1, M4),
Rabbin Batool (M2, interface layer, persistence/CI), Ilsa Maryam (M3, M5, orchestrator `pipeline.py` as M2
Team Lead/Integrator).

## Functional requirements

| ID | Requirement | Module | Priority |
|---|---|---|---|
| FR-01 | Register a candidate with name, email, resume text and zero or more handles (GitHub, Codeforces, LeetCode). | M1 | Must |
| FR-02 | Collect GitHub profile, public repositories, languages and candidate-authored commit metadata through the official REST API. | M1 | Must |
| FR-03 | Collect Codeforces user info, rating history and accepted submissions through the official API. | M1 | Must |
| FR-04 | Collect LeetCode user info and submissions. | M1 | Must |
| FR-05 | Run all enabled collectors for one candidate concurrently, with a per-source rate limit and at most three retries with exponential back-off for timeouts, HTTP 429 and 5xx. | M1 | Must |
| FR-06 | Freeze every raw response in MinIO with metadata (endpoint, SHA-256, fetch time) in PostgreSQL. A snapshot is never updated. | M2 | Must |
| FR-07 | Extract typed evidence nodes (skill, project, contribution, achievement) from a snapshot, each with snapshot id and locator. The same snapshot always yields the same nodes. | M2 | Must |
| FR-08 | Resolve accounts across sources with pluggable match signals; output a link confidence in [0, 1] and a rationale. | M3 | Must |
| FR-09 | Mark an account unlinked when confidence is below a configurable threshold (default 0.50); exclude its evidence. | M3 | Must |
| FR-10 | Normalise skill names through an alias table; per required skill return matching nodes and the coverage fraction. | M4 | Must |
| FR-11 | Extract discrete claims from resume text. | M5 | Must |
| FR-12 | Verify each claim as supported, partially supported or unsupported, with evidence links. | M5 | Must |
| FR-13 | Score report: total in [0, 100], per-component values and weights, and the evidence behind each. | M5 | Must |
| FR-14 | Replay a completed run from stored snapshots with network disabled and reproduce the same evidence and score. | M2, M5 | Must |
| FR-15 | REST API with run, replay and show report. | Interface | Must |
| FR-16 | Delete all stored data for a candidate on request, including snapshots. | M2 | Should |

## Non-functional requirements

| ID | Quality | Requirement |
|---|---|---|
| NFR-01 | Concurrency | Three collectors run concurrently; a 20-candidate stress test shows overlapping calls and zero rate-limit violations. |
| NFR-02 | Reliability | A failing source (timeout, 5xx, malformed body) does not abort the run; run is `partial`, failure logged with an error code. |
| NFR-03 | Performance | Collection for ≤50 repos within 5 min; top-k search over 10 000 vectors within 300 ms. |
| NFR-04 | Testability | Every external dependency behind an interface with an in-memory fake; ≥60 % line coverage of core, test-first. |
| NFR-05 | Maintainability | Ruff and Pylint in CI; no open critical finding without justification. |
| NFR-06 | Security/privacy | Public data only; tokens from environment; no email addresses in logs. |
| NFR-07 | Reproducibility | Replay identical in evidence set and score with the deterministic LLM provider. |
| NFR-08 | Compliance | Every collector uses an official API or public endpoint; no browser automation. |

## Quality requirements (ISO/IEC 25010)

| QR | Characteristic / sub-characteristic | Testable requirement | Constrains |
|---|---|---|---|
| QR-01 | Functional correctness | ≥90 % of claim verdicts match hand labels on a 10-profile corpus; no hand-labelled "unsupported" claim reported "supported". | FR-11, FR-12 |
| QR-02 | Functional completeness | Every Must FR has ≥1 passing automated test traced in the RTM by M3. | All FR |
| QR-03 | Functional appropriateness | Every score component has weight, value and ≥1 evidence node id; every id resolves to a stored node with a snapshot id. | FR-13 |
| QR-04 | Fault tolerance | With one source returning 503, run finishes `partial`, other sources' evidence present, failure logged with code. | NFR-02 |
| QR-05 | Recoverability | Restarting after a crash during extraction resumes from stored snapshots without re-fetching and gives the same evidence. | FR-06, FR-07, FR-14 |
| QR-06 | Maturity | Zero open Critical/High defects at each milestone submission. | All |
| QR-07 | Time behaviour | See NFR-03; measured with the profiling harness at M4. | NFR-03 |
| QR-08 | Capacity | 20 candidates in one batch without rate-limit violation (stress test). | NFR-01 |
| QR-09 | Modularity | `pipeline.core` imports nothing from `pipeline.adapters` or `pipeline.interface`; CI check. | Design |
| QR-10 | Testability | ≥60 % line coverage of `pipeline.core`; every port has an in-memory fake. | NFR-04 |
| QR-11 | Analysability | No core function above cyclomatic complexity 10 without justification; no unresolved critical Ruff/Pylint finding. | NFR-05 |
| QR-12 | Modifiability | A new collector needs one new file plus one registration line (stub fourth collector test). | Design (OCP) |
| QR-13 | Confidentiality | No token in repository history (secret scanning); emails scrubbed by a log filter. | NFR-06 |
| QR-14 | Integrity | Loading a snapshot whose bytes do not match the stored SHA-256 raises `SnapshotError` (tamper test). | FR-06 |
| QR-15 | Accountability | Every evidence node, verdict and score carries the run id and snapshot id that produced it. | FR-07, FR-12, FR-13 |
| QR-16 | Interoperability | REST API JSON validates against a published OpenAPI schema. | FR-15 |

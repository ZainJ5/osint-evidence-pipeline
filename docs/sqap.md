# Software Quality Assurance Plan (IEEE 730) — OSINT Evidence Pipeline

**Status:** Milestone 2 draft. Sections 1–6, 8, 9, 10 and 15 are drafted, as committed in the SE431 M1 report
(§4, Table 5), because the M2 inspection, static analysis and V&V work depend on them. Sections 7, 11–14, 16 and 17
are still at outline level and are completed for Milestone 4 (final SQAP lead: Ilsa Maryam).

## Change history

| Version | Milestone | Author | Summary |
|---|---|---|---|
| 0.1 | M1 | Rabbin Batool | Scope and one-line outline per IEEE 730 section (SE431 M1 report §4) |
| 0.2 | M2 | Owner Rabbin Batool; drafted with AI assistance (AI usage log) | Sections 1–6, 8, 9, 10, 15 drafted; team review through the PR that adds this file |

Changes to this document go through a pull request reviewed by the SQA lead of the current milestone (§17).

---

## 1. Purpose

This plan defines how the team assures the quality of the OSINT Evidence Pipeline across all four milestones of the
SE423/SE431 joint project. It covers these software items:

| Item | Location |
|---|---|
| M1 Source Collection | `pipeline/core/collection/` |
| M2 Snapshot Store & Evidence Extraction | `pipeline/core/snapshot/` |
| M3 Identity Resolution | `pipeline/core/identity/` |
| M4 Semantic Matching | `pipeline/core/matching/` |
| M5 Claim Verification & Scoring | `pipeline/core/scoring/` |
| Orchestration and shared contracts | `pipeline/core/{pipeline,ports,models,errors,inputs,intake,queries,skills}.py` |
| Interface layer (REST API, composition root) | `pipeline/interface/` |
| Persistence and external adapters | `pipeline/adapters/`, `migrations/` |
| Web UI | `ui/` |
| Tests and recorded API fixtures | `tests/` |

Out of scope: third-party services (GitHub, Codeforces, LeetCode, Anthropic APIs) other than through their adapters.

## 2. Reference documents

| Ref | Document |
|---|---|
| [R1] | SE423 M1 proposal and SE423 M2 report (`docs/milestone2/SE423_M2_report.md`) |
| [R2] | SE431 M1 report and SE431 M2 report (`docs/milestone2/SE431_M2_report.md`) |
| [R3] | IEEE Std 730-2014, Software Quality Assurance Processes |
| [R4] | IEEE Std 1012-2016, System, Software and Hardware Verification and Validation |
| [R5] | ISO/IEC 25010:2011, Product quality model |
| [R6] | ISO/IEC 29110 Basic profile |
| [R7] | Fagan, M. E., "Design and code inspections to reduce errors in program development", IBM Systems Journal, 1976 |
| [R8] | Tool documentation: Ruff 0.17.5, Pylint 4.1.4, pytest 8.4.2, pytest-cov 7.1.0 |
| [R9] | Project requirements (`docs/requirements.md`) and RTM v2 (SE431 M2 report) |

## 3. Management

### 3.1 Organisation

Three members. The Team Lead and the SQA leads rotate per milestone so that every member leads each kind of
activity once.

| Milestone | Inspection lead | Static analysis lead | V&V plan lead | Black-box lead | White-box lead | SCM audit lead | Integrator |
|---|---|---|---|---|---|---|---|
| M1 | — | — | — | — | — | — | Rabbin Batool |
| M2 | Zain Jamshaid | Rabbin Batool | Ilsa Maryam | Rabbin Batool | Ilsa Maryam | — | Ilsa Maryam |
| M3 | — | — | — | Rabbin Batool | Ilsa Maryam | Zain Jamshaid | — |
| M4 | — | — | — | — | — | Rabbin Batool (audit) | — |

### 3.2 Tasks per milestone

| Milestone | SQA tasks |
|---|---|
| M1 | Quality requirements (ISO/IEC 25010), RTM v1, SQAP outline, cost of quality, risk register v1 |
| M2 | This draft; Fagan inspection with an external inspector; static analysis; IEEE 1012 V&V plan; black-box and white-box test design; SCM quality gates; RTM v2; risk register update |
| M3 | Test execution report; SCM audit (scm.md §7); CAPA closure for M2 defects |
| M4 | Final SQAP; GQM measurement report; final risk register and audit |

### 3.3 Responsibilities

- Module owners write the tests and code for their module and fix defects raised against it.
- No member reviews their own module: every pull request needs approval from a member who is not the author
  (§6.1), and `.github/CODEOWNERS` requests the owning member's review automatically.
- In the inspection, authors never act as moderator, reader or recorder for their own artifact.

## 4. Documentation

| Document | Location | Owner | Review point |
|---|---|---|---|
| SE423 proposal / milestone reports | `docs/milestone2/SE423_M2_report.md` | Team Lead of the milestone | PR review before each submission |
| SE431 milestone reports | `docs/milestone2/SE431_M2_report.md` | SQA leads of the milestone | PR review before each submission |
| SQAP (this document) | `docs/sqap.md` | Rabbin Batool (M2 draft), Ilsa Maryam (M4 final) | M2, M4 |
| Requirements and RTM | `docs/requirements.md`, SE431 report RTM | Zain Jamshaid | every milestone |
| V&V plan | `docs/milestone2/vv-plan.md` | Ilsa Maryam | M2, updated M3 |
| Inspection report | `docs/milestone2/inspection-report.md` | Zain Jamshaid | M2 follow-up |
| Static analysis report | `docs/milestone2/static-analysis-report.md` | Rabbin Batool | M2 |
| Test design documents | `docs/milestone2/{blackbox,whitebox}-test-design.md` | Rabbin Batool, Ilsa Maryam | M2, M3 |
| SCM plan and audit | `docs/milestone2/scm.md` | Zain Jamshaid | M3 audit |
| API contract | `docs/api-contract.md` | Rabbin Batool | any API change |
| AI usage log | `docs/ai-usage-log.md` | every member for their own use | every milestone |
| README | `README.md` | Integrator of the milestone | every milestone |

## 5. Standards, practices, conventions and metrics

### 5.1 Standards and conventions

| Area | Convention | Enforced by |
|---|---|---|
| Style | PEP 8, line length 120, import order | `ruff check .`, `ruff format --check .` (CI) |
| Static analysis | Pylint score at least 9.9 / 10 | `pylint pipeline --fail-under=9.9` (CI) |
| Complexity | Cyclomatic complexity at most 10 per function | Ruff rule C901, `max-complexity = 10` |
| Architecture | `pipeline/core` never imports `pipeline.adapters` or `pipeline.interface` | grep step in CI (QR-09) |
| Error handling | No bare `except:`; every broad handler is logged and justified in the SE423 report | review checklist |
| Documentation | Docstring on every public class | Pylint, review checklist |
| Dependencies | Exact pinned versions in `pyproject.toml` | review checklist |
| Commits | Plain-sentence messages describing one step | review checklist |

### 5.2 Metrics

| Metric | Target | Source |
|---|---|---|
| Line coverage of `pipeline/core` | at least 60 % (gate); actual is reported per milestone | `pytest --cov` in CI |
| Pylint score | at least 9.9 | CI |
| Max cyclomatic complexity | at most 10 | Ruff C901 |
| Defect density | defects per KLOC per module | issues labelled `defect` |
| Inspection rate | defects found per person-hour; NCLOC inspected per hour | inspection report §11 |
| CI pass rate | share of green runs on `main` | GitHub Actions |

These feed the GQM programme at M4.

## 6. Software reviews

### 6.1 Pull request review

Every change to `main` goes through a pull request that needs:

1. CI green (all quality gates in `docs/milestone2/scm.md` §3);
2. one approving review from a member who is not the author (branch protection on `main`);
3. a linked issue (`Closes #n`);
4. the checklist in `.github/pull_request_template.md` completed.

### 6.2 Fagan inspection (M2)

One formal inspection of the M2 build, following Fagan [R7]: planning, overview, preparation, meeting, rework and
follow-up. Roles: moderator, author, reader, recorder and inspectors, including one external inspector from a paired
team. Entry and exit criteria, the checklist, the defect log and the metrics are in
`docs/milestone2/inspection-report.md`.

### 6.3 Walkthroughs

A walkthrough of the black-box and white-box test designs at M3 before test execution, led by the respective
design lead.

## 7. Test (outline — completed at M4)

Test levels: unit (test-first), integration (PostgreSQL and MinIO containers), system (REST API), stress and fault
injection. Black-box EP/BVA and white-box CFG/basis-path designs are in `docs/milestone2/`. Test environment: the
GitHub Actions runner plus Docker Compose locally.

## 8. Problem reporting and corrective action

### 8.1 Reporting

Every defect is a GitHub issue created from `.github/ISSUE_TEMPLATE/defect.md`, with:

- label `defect`;
- a severity label: `severity:critical`, `severity:high`, `severity:medium`, `severity:low`;
- an origin label: `origin:inspection`, `origin:static-analysis`, `origin:test`, `origin:demo`;
- the location, the requirement it affects and a reproducing test where possible.

Severity definitions:

| Severity | Meaning |
|---|---|
| Critical | Wrong verdict or data loss with no workaround |
| High | Wrong result in a reachable path, or a requirement not met |
| Medium | Incorrect behaviour in an edge case, or a robustness gap |
| Low | Maintainability, clarity or resource handling with no wrong result today |

### 8.2 Corrective and preventive action (CAPA)

Each defect issue records root cause, corrective action, preventive action, verification (the test or CI run that
proves the fix) and closure date. The fix lands in a pull request that references the issue; a failing test that
reproduces the defect is committed before the fix. The CAPA table is reported in each SE431 milestone report.

### 8.3 Deferral

A Low defect may be deferred with a written justification, an owner and a target milestone. Critical, High and
Medium defects block the milestone baseline.

## 9. Tools, techniques and methodologies

| Tool | Version | Use |
|---|---|---|
| Ruff | 0.17.5 | lint, formatting, McCabe complexity |
| Pylint | 4.1.4 | static analysis |
| pytest, pytest-asyncio, pytest-cov | 8.4.2, 1.5.0, 7.1.0 | unit, integration, system tests; coverage |
| GitHub Actions | — | CI quality gates |
| gitleaks | action v2 | secret scanning of the full history |
| Docker Compose | — | PostgreSQL 16 and MinIO for integration tests |

Techniques: test-driven development, Fagan inspection, equivalence partitioning and boundary value analysis,
basis-path testing from control-flow graphs, GQM (M4), fault injection.

## 10. Code control

- `main` is protected: changes only by pull request; one non-author approval; CI must pass; no force pushes or
  deletion.
- One branch per unit of work: `feature/<milestone>-<module>`, `fix/<milestone>-<topic>`, `docs/<milestone>-<topic>`.
- Merge commits only, so each branch's commit sequence stays visible on `main`.
- Each milestone is baselined with an annotated tag (`m1-baseline`, `m2-baseline`, …) on a commit whose CI run is
  green. Baselines are never moved.
- Database schema changes are numbered migrations (`migrations/NNN_*.sql`) versioned with the code.
- Details and the audit checklist: `docs/milestone2/scm.md`.

## 11. Media control (outline)

Repository on GitHub with branch protection; recorded API fixtures under `tests/fixtures/`; documents under `docs/`.

## 12. Supplier control (outline)

Third-party code only through pinned versions in `pyproject.toml`; external APIs (GitHub, Codeforces, LeetCode,
Anthropic) are suppliers whose terms and rate limits are recorded in the risk register.

## 13. Records collection, maintenance and retention (outline)

CI logs and coverage artifacts kept by GitHub Actions for 90 days and copied to `docs/records/` at each milestone.

## 14. Training (outline)

Short internal sessions before M2 (Fagan roles, reading Ruff and Pylint output) and before M3 (EP/BVA, basis path).

## 15. Risk management

The risk register is maintained in the SE431 milestone report (M1 §7, M2 risk register section) and updated at
every milestone with status, mitigation evidence and residual risk.

| Step | Practice |
|---|---|
| Identify | Any member may add a risk; inspection, static analysis and test results are reviewed for new risks each milestone |
| Assess | Likelihood and impact rated H/M/L; exposure = likelihood × impact |
| Mitigate | Each risk has an owner and a concrete mitigation with evidence (test, CI step, document) |
| Monitor | Status and residual exposure re-rated at each milestone; closed risks stay in the register with their evidence |
| Escalate | A risk rated H/H, or one that threatens a milestone deliverable, is raised with the instructor |

## 16. Glossary (outline)

OSINT, snapshot, evidence node, claim, verdict, match signal, link confidence, CAPA, RTM, GQM, EP, BVA, V(G).

## 17. SQAP change procedure and history

Changes go through a pull request reviewed by the SQA lead of that milestone; the change history table at the top
records version, milestone, author and summary.

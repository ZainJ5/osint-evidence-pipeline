# Software Configuration Management — Milestone 2

SE431 M2 deliverable "SCM quality-gate evidence". SCM audit lead for M3: Zain Jamshaid. Repository:
https://github.com/ZainJ5/osint-evidence-pipeline

## 1. Configuration items

| Item | Location | Owner | Baseline at |
|---|---|---|---|
| Source code, core | `pipeline/core/` | module owners (README) | every milestone tag |
| Adapters and interface | `pipeline/adapters/`, `pipeline/interface/` | Rabbin Batool | every milestone tag |
| Database schema | `migrations/NNN_*.sql` (applied in order, tracked in `schema_migrations`) | Rabbin Batool | versioned with the code |
| Tests and recorded API fixtures | `tests/`, `tests/fixtures/` | module owners | every milestone tag |
| Build and dependency definition | `pyproject.toml` (exact pinned versions) | Rabbin Batool | every milestone tag |
| Infrastructure | `docker-compose.yml`, `.github/workflows/ci.yml`, `.env.example` | Rabbin Batool | every milestone tag |
| Quality documents | `docs/` | SQA lead of the milestone | every milestone tag |
| Quality records | `docs/records/m2/` (tool outputs, coverage) | SQA lead of the milestone | copied at each milestone |

Not configuration items: `.venv/`, caches, `coverage.xml`, `.env` (all in `.gitignore`).

## 2. Branching strategy

- `main` is protected and always green. It only changes through pull requests.
- One branch per feature: `feature/<milestone>-<module>`, e.g. `feature/m2-collection`, `feature/m2-snapshot`.
- Pull requests need: CI passing, one approving review from a member who is not the author, and a linked issue.
- Merge with **merge commits only** (squash and rebase merges disabled), so the red → green → refactor commit
  sequence on each branch stays visible on `main`.
- Commit messages are plain sentences describing the step, e.g. "Added failing test for the email match signal",
  "Implemented the email match signal", "Extracted email normalisation into a helper".

## 3. Quality gates (merge criteria)

Every gate below runs in `.github/workflows/ci.yml` on every push and pull request; a failing step blocks the merge
once "require status checks" is enabled on `main`.

| Gate | CI step | Requirement |
|---|---|---|
| Secret scanning of full history | `gitleaks/gitleaks-action@v2` | QR-13, NFR-06 |
| Lint | `ruff check .` | NFR-05, QR-11 |
| Formatting | `ruff format --check .` | NFR-05 |
| Static analysis | `pylint pipeline --fail-under=9` | NFR-05, QR-11 |
| Complexity ≤ 10 | Ruff rule C901 with `max-complexity = 10` (pyproject.toml) | QR-11 |
| Dependency direction | `grep` that `pipeline/core` never imports `pipeline.adapters` / `pipeline.interface` | QR-09 |
| No browser automation | `grep` for selenium/playwright in `pyproject.toml` | NFR-08 |
| Schema applies cleanly | `python -m pipeline.adapters.migrate` against a PostgreSQL 16 service container | FR-06 |
| Tests incl. integration | `pytest` with PostgreSQL and MinIO containers | NFR-04 |
| Coverage ≥ 60 % of core | `--cov=pipeline/core --cov-fail-under=60`, `coverage.xml` uploaded as artifact | NFR-04, QR-10 |
| Human review | GitHub branch protection: 1 approval, author cannot approve own PR | SQAP §6 |

## 4. Baselines

| Baseline | Tag | Content | Status |
|---|---|---|---|
| M1 | `m1-baseline` | Proposal and quality documents, README | to be tagged retroactively on the first commit that contains them |
| M2 | `m2-baseline` | This build: all five modules, API, web UI, persistence, CI, M2 documents | Created on `main`. It was tagged before CI had ever run (the workflow file was invalid YAML); the first green run is https://github.com/ZainJ5/osint-evidence-pipeline/actions/runs/45028442893, on the CI fix. Per the rule below the tag is not moved: the corrected state is tagged `m2-baseline.1` once the M2 fix pull requests are merged and CI is green on `main` |
| M3 | `m3-baseline` | Final system | Week 13 |

A baseline is an annotated tag on `main` created by the milestone Integrator after CI is green:
`git tag -a m2-baseline -m "Milestone 2 baseline" && git push origin m2-baseline`. Baselines are never moved; a fix
after the tag goes into a new commit and, if needed, `m2-baseline.1`.

Change control after a baseline: a change to a baselined requirement, schema or interface needs an issue labelled
`scope-change` agreed by all three members (risk R-05), and the RTM is updated in the same pull request.

## 5. Branch protection settings to apply on `main`

Settings → Branches → Add rule for `main`:

- Require a pull request before merging; required approvals: 1; dismiss stale approvals on new commits.
- Require status checks to pass: `test` (the CI job); require branches to be up to date.
- Do not allow bypassing the above settings; block force pushes and deletions.
- Settings → General → Pull Requests: allow merge commits only (untick squash and rebase).

Evidence to capture: a screenshot of the rule, plus `gh api repos/ZainJ5/osint-evidence-pipeline/branches/main/protection`.

**Status:** applied to `main` (required review, CODEOWNERS review, required `test` check, no force push or
deletion; squash and rebase merging disabled in the repository settings).

## 6. Commit plan (as used for M2)

Each owner commits **their own** files from their own GitHub account, on their own branch. The M2 work was merged
through one `feature/m2-*` branch per module. On those branches the implementation commit precedes the test commit,
so test-first order is not visible for M2 (SE423 report §6.2); from M3 the failing test is committed first.
Sequence used (one pull request per branch, merged in dependency order):

| Order | Branch | Author | Commits (in order) |
|---|---|---|---|
| 1 | `feature/m2-foundation` | Rabbin Batool (Integrator M1) | `pyproject.toml`, `.gitignore`, `docker-compose.yml`, `.env.example`, CI workflow; then `pipeline/core/{errors,ports,models,inputs}.py`, `pipeline/adapters/fakes.py` |
| 2 | `feature/m2-collection` | Zain Jamshaid | per class: failing test (`tests/unit/collection/test_rate_limiter.py`) → `rate_limiter.py`; tests → `collector.py`; tests → collectors; tests → `factory.py`; tests → `runner.py`; stress test |
| 3 | `feature/m2-snapshot` | Rabbin Batool | tests → `store.py`; tests + fixtures → `parsers.py`; tests → `extractor.py` |
| 4 | `feature/m2-identity` | Ilsa Maryam | per signal: test → implementation; tests → `profiles.py`; tests → `resolver.py` |
| 5 | `feature/m2-matching` | Zain Jamshaid | tests → `normalizer.py`, `vector_index.py`, `matcher.py` |
| 6 | `feature/m2-scoring` | Ilsa Maryam | tests → `claims.py`; tests → `rules.py`; tests → `verifier.py`; tests → `scoring.py` |
| 7 | `feature/m2-persistence` | Rabbin Batool | `migrations/001_initial.sql`, `migrate.py`; adapter unit tests → `http.py`, `postgres.py`, `minio_store.py`; integration tests |
| 8 | `feature/m2-orchestrator-api` | Ilsa Maryam (Integrator M2) | system tests → `pipeline/core/pipeline.py`, `log.py`; API tests → `pipeline/interface/*` |
| 9 | `feature/m2-sqa` | per document lead | `docs/` files, `tests/blackbox`, `tests/whitebox`, inspection fixes (one commit per defect: failing test, then fix) |

Then tag `m2-baseline` (section 4) and record the CI run URL of the tagged commit in the SE431 report.

GitHub issues exist for the inspection and black-box defects (label `defect`, a severity label and an origin
label); new pull requests reference their issue with `Closes #n`.

## 7. Audit checklist (to run at M3 by the SCM audit lead)

- Every commit on `main` reachable from `m2-baseline` came through a merged pull request with one non-author approval.
- No squash merges (`git log --merges main` shows one merge commit per feature branch).
- Each feature branch shows a test commit before the implementation commit.
- `gitleaks` reports no findings over the full history.
- CI was green on the tagged commit; coverage artifact present.
- Schema migrations in the tag apply cleanly to an empty database.

# SE431 Milestone 2: Static Analysis Report

Owner: Rabbin Batool (static analysis lead, M2). Date: 2026-11-19.

## 1. Purpose and scope

This report covers the static analysis for Milestone 2. It provides evidence for two requirements:

- **NFR-05 (Maintainability):** Ruff and Pylint run in CI, and no critical finding stays open without a justification.
- **QR-11 (Analysability):** no core function has cyclomatic complexity above 10 unless it is justified, and no critical Ruff or Pylint finding is left unresolved.

Scope:

- **Ruff** (lint and format) checks `pipeline/` and `tests/`. CI runs `ruff check .` over the whole repository.
- **Pylint** checks `pipeline/` (core, adapters, interface).
- **Complexity** is measured for every function in `pipeline/`.

Raw tool output, used for every number in this report:

| Run | Files |
|---|---|
| Baseline | `docs/records/m2/static-analysis-before/ruff.txt`, `pylint.txt`, `complexity.txt` |
| After fixes | `docs/records/m2/static-analysis-after/ruff.txt`, `pylint.txt`, `complexity.txt`, `pylint-suppressed-messages.txt` |

## 2. Tools, versions and configuration

| Tool | Version (from `--version`) | Runtime |
|---|---|---|
| Ruff | 0.17.5 | – |
| Pylint | 4.1.4 (astroid 4.3.4) | Python 3.10.0, local; CI uses Python 3.12 |

These versions match the pins in `pyproject.toml` (`ruff==0.17.5`, `pylint==4.1.4`).

### Ruff configuration (`[tool.ruff]`)

- `line-length = 120`, `target-version = "py310"`.
- `select = ["E", "F", "W", "I", "B", "C90", "UP", "SIM"]`:

  | Code | Rule set |
  |---|---|
  | E, W | pycodestyle errors and warnings |
  | F | Pyflakes |
  | I | isort import order |
  | B | flake8-bugbear |
  | C90 | McCabe complexity |
  | UP | pyupgrade |
  | SIM | flake8-simplify |

- `[tool.ruff.lint.mccabe] max-complexity = 10`. This is the QR-11 threshold, enforced by rule C901.
- Formatter: `ruff format` with default style at line length 120.

### Pylint configuration (`[tool.pylint]`)

- `py-version = "3.10"`, `max-line-length = 120`. All other thresholds are Pylint defaults (for example `max-args = 5`, `max-attributes = 7`).
- The disabled messages are reviewed in section 8.

### Complexity measurement

The listing for every function comes from:

```
ruff check pipeline --select C901 --config "lint.mccabe.max-complexity=0" --output-format concise
```

With the threshold at 0, Ruff reports V(G) for every function.

Ruff's McCabe counts a nested `def` as +1 and adds its decision points to the enclosing function.

## 3. How static analysis runs in CI

`.github/workflows/ci.yml` runs on every push and pull request, in the `test` job, in this order:

1. `ruff check .`: lint, including C901 at max-complexity 10.
2. `ruff format --check .`
3. `pylint pipeline --fail-under=9.9`. This was `--fail-under=9` before this milestone (see CAPA-SA-2).
4. A grep gate for dependency direction (QR-09) and a grep gate for no browser automation (NFR-08). These are not part of this report.

Each step fails the job on a non-zero exit, so any Ruff finding, any formatting difference, or a Pylint score below 9.9 blocks the merge.

## 4. Baseline summary

| Tool / check | Baseline | After |
|---|---|---|
| `ruff check pipeline tests` | 0 findings ("All checks passed!") | 0 findings |
| `ruff check .` (CI scope) | not recorded separately | 0 findings |
| `ruff format --check pipeline tests` | 0 files to reformat (80 files) | 0 files to reformat (97 files) |
| Pylint findings | 67 | 0 |
| Pylint score | **9.59/10** | **10.00/10** |
| Functions measured (C901) | 216 | 219 |
| Functions with V(G) > 10 | 0 | 0 |
| Maximum V(G) | 10 | 10 |

Notes on the table:

- The "After" Ruff results include test files that other M2 work added while this analysis was running (see SA-68 to SA-71).
- The "After" count of functions measured includes 3 functions added by concurrent defect fixes.

Baseline Pylint findings by category:

| Message | ID | Category | Count |
|---|---|---|---|
| missing-class-docstring | C0115 | Convention | 63 |
| redefined-outer-name | W0621 | Warning | 3 |
| use-implicit-booleaness-not-len | C1802 | Convention | 1 |
| **Total** | | | **67** |

Complexity distribution (number of functions at each V(G)):

| V(G) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|
| Baseline | 114 | 42 | 28 | 22 | 4 | 3 | 1 | 1 | 1 |
| After | 116 | 42 | 29 | 22 | 4 | 3 | 1 | 1 | 1 |

## 5. Triage of every finding

### Severity scale

| Severity | Meaning |
|---|---|
| Critical | Likely runtime fault or security issue. |
| High | Probable defect, or it breaks a requirement gate. |
| Medium | Can hide a defect, or makes the code misleading to read. |
| Low | Style or documentation only. |

No Critical or High findings were raised.

### Baseline Pylint findings

Locations are the baseline file and line numbers.

| ID | Tool | Rule | Location | Message | Sev. | Disposition | Action / justification | CAPA |
|---|---|---|---|---|---|---|---|---|
| SA-01 | Pylint | W0621 redefined-outer-name | `pipeline/adapters/fakes.py:24` | Redefining name 'json' from outer scope (line 4) | Medium | Fixed | See below. | CAPA-SA-1 |
| SA-02 | Pylint | W0621 redefined-outer-name | `pipeline/adapters/fakes.py:50` | Redefining name 'json' from outer scope (line 4) | Medium | Fixed | Same fix as SA-01 (`OfflineHttpClient.post`). | CAPA-SA-1 |
| SA-03 | Pylint | W0621 redefined-outer-name | `pipeline/interface/api.py:65` | Redefining name 'app' from outer scope (line 103) | Medium | Fixed | See below. | CAPA-SA-1 |
| SA-04 | Pylint | C1802 use-implicit-booleaness-not-len | `pipeline/core/matching/matcher.py:67` | Do not use `len(SEQUENCE)` without comparison | Low | Fixed | See below. | – |
| SA-05 | Pylint | C0115 missing-class-docstring | `pipeline/adapters/fakes.py:54` (`InMemoryBlobStore`) | Missing class docstring | Low | Fixed | Added a one-line docstring. | – |
| SA-06 to SA-12 | Pylint | C0115 | `pipeline/core/errors.py:17, 21, 25, 29, 33, 37, 41` (the 7 `PipelineError` subclasses) | Missing class docstring | Low | Fixed | One-line docstrings naming the module (M1 to M5) that raises each error. | – |
| SA-13 to SA-15 | Pylint | C0115 | `pipeline/core/inputs.py:19, 42, 58` | Missing class docstring | Low | Fixed | One-line docstrings. | – |
| SA-16 to SA-17 | Pylint | C0115 | `pipeline/core/log.py:20, 29` | Missing class docstring | Low | Fixed | One-line docstrings. | – |
| SA-18 to SA-33 | Pylint | C0115 | `pipeline/core/models.py:18, 28, 42, 51, 62, 76, 90, 97, 104, 115, 125, 136, 149, 160, 170, 178` | Missing class docstring | Low | Fixed | One-line docstrings on the 16 value-object dataclasses. | – |
| SA-34 to SA-36 | Pylint | C0115 | `pipeline/core/pipeline.py:32, 45, 55` | Missing class docstring | Low | Fixed | One-line docstrings. | – |
| SA-37 to SA-42 | Pylint | C0115 | `pipeline/core/ports.py:14, 20, 30, 41, 47, 65` | Missing class docstring | Low | Fixed | One-line docstrings on the port ABCs. | – |
| SA-43 | Pylint | C0115 | `pipeline/core/collection/codeforces.py:13` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-44 | Pylint | C0115 | `pipeline/core/collection/factory.py:16` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-45 | Pylint | C0115 | `pipeline/core/collection/github.py:11` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-46 | Pylint | C0115 | `pipeline/core/collection/leetcode.py:24` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-47 to SA-50 | Pylint | C0115 | `pipeline/core/identity/signals.py:33, 43, 74, 89` | Missing class docstring | Low | Fixed | One-line docstrings on the 4 signal strategies. | – |
| SA-51 | Pylint | C0115 | `pipeline/core/matching/matcher.py:11` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-52 | Pylint | C0115 | `pipeline/core/matching/normalizer.py:40` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-53 | Pylint | C0115 | `pipeline/core/matching/vector_index.py:8` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-54 | Pylint | C0115 | `pipeline/core/scoring/claims.py:71` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-55 to SA-57 | Pylint | C0115 | `pipeline/core/scoring/rules.py:13, 47, 74` | Missing class docstring | Low | Fixed | One-line docstrings. | – |
| SA-58 | Pylint | C0115 | `pipeline/core/scoring/scoring.py:19` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-59 | Pylint | C0115 | `pipeline/core/scoring/verifier.py:8` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-60 | Pylint | C0115 | `pipeline/core/snapshot/extractor.py:12` | Missing class docstring | Low | Fixed | One-line docstring. | – |
| SA-61 to SA-67 | Pylint | C0115 | `pipeline/interface/api.py:15, 22, 29, 34, 41, 48, 57` | Missing class docstring | Low | Fixed | See below. | – |

Details for the longer actions:

- **SA-01 and SA-02 (`json`).** The parameter name `json` is part of the `HttpClient.post` port contract: callers pass `json=` by keyword (`collector.py:65`, `http.py:29`). Renaming the parameter would break the contract. Instead, the module import changed from `import json` to `from json import dumps`, so nothing is shadowed. `json_response` now calls `dumps(...)`. Behaviour is unchanged.
- **SA-03 (`app`).** Inside `create_app`, the local FastAPI instance was renamed from `app` to `application`. The module-level `app = create_app()` that uvicorn uses is unchanged.
- **SA-04 (`len`).** `if not len(index):` became `if not index:`. `InMemoryVectorIndex` defines `__len__` and no `__bool__`, so the truth value is identical.
- **SA-61 to SA-67 (API models).** These are Pydantic request and response models, so the new docstrings also appear as schema descriptions in the generated OpenAPI document. The JSON request and response shapes do not change.

All 63 C0115 docstrings were added by class name, not by line number, so concurrent edits could not misplace them. `ruff format` then added the blank line it requires after a class docstring.

### Findings in new M2 code

These were not in the baseline. They appeared in the after-run, in test files that other M2 work added while this analysis was running.

| ID | Tool | Rule | Location | Message | Sev. | Disposition | Action / justification | CAPA |
|---|---|---|---|---|---|---|---|---|
| SA-68 | Ruff | format | `tests/blackbox/test_bb_inputs.py:53` | File would be reformatted (`@pytest.mark.parametrize` fits on one line) | Low | Fixed | Ran `ruff format` on this file; whitespace only. | CAPA-SA-4 |
| SA-69 | Ruff | E501, format | `tests/whitebox/test_basis_paths_scoring.py:100` | Line too long (123 > 120) | Low | Fixed | Fixed by the file's author before the final run. The re-run is clean. | CAPA-SA-4 |
| SA-70 | Ruff | E501 | `tests/blackbox/test_bb_matching.py:5` | Line too long (122 > 120), in a docstring | Low | Fixed | The author rewrapped the docstring. The re-run is clean. | CAPA-SA-4 |
| SA-71 | Ruff | B905 | `tests/system/test_inspection_m2.py:37` | `zip()` without an explicit `strict=` parameter | Low | Fixed | See below. | CAPA-SA-4 |

**SA-71.** The fix is `strict=False`. The zip pairs `sorted(times)` with `sorted(times)[1:]`, so the lengths differ by design, and `strict=True` would raise an error. Making `False` explicit keeps the behaviour the same and records the intent.

### Configuration finding

| ID | Tool | Rule | Location | Message | Sev. | Disposition | Action / justification | CAPA |
|---|---|---|---|---|---|---|---|---|
| SA-72 | Pylint (config) | missing-module-docstring disabled | `pyproject.toml` `[tool.pylint."messages control"]` | The disable suppressed 0 findings: every module already has a docstring (`pylint-suppressed-messages.txt`). | Low | Fixed | Removed from the disable list so that a regression is reported. | CAPA-SA-3 |
| SA-73 | Pylint (inline) | `# pylint: disable=import-outside-toplevel` | `pipeline/adapters/fakes.py:28-29` (`FakeHttpClient._serve`) | Inline disables on function-level `import asyncio` and `import time`. There was no reason to defer these stdlib imports. | Low | Fixed | Moved both imports to module level and removed the two disables. Calls still resolve `asyncio.sleep` and `time.monotonic` at call time, so patching behaves the same. | – |

### Totals

- 73 items in all.
- 73 Fixed, 0 Justified, 0 Deferred.
- No inline `# pylint: disable` was added.

Three inline disables remain, all `import-outside-toplevel`, and all are Justified:

- **`pipeline/interface/composition.py:20-21`.** The PostgreSQL and MinIO adapters (and with them psycopg and minio) are imported only when `DATABASE_URL` is set. This lets the in-memory demo run without those drivers.
- **`pipeline/adapters/fakes.py`, in `in_memory_repositories`.** It imports `Repositories` from the orchestrator module only when it is called, so importing the fakes does not load the whole pipeline.

## 6. Complexity: most complex functions

Every function with V(G) of 5 or more on the current code (same Ruff command as above). QR-11's limit is V(G) ≤ 10;
no function exceeds it, and the highest is 7.

| # | Function | Location | V(G) | White-box (basis-path) target? | Other tests |
|---|---|---|---|---|---|
| 1 | `CandidateInput.__post_init__` | `pipeline/core/inputs.py:28` | 7 | No | `tests/blackbox/test_bb_inputs.py`, `tests/unit/collection/test_candidate_input.py` |
| 2 | `RequirementMatcher.match` | `pipeline/core/matching/matcher.py:31` | 6 | No | `tests/unit/matching/test_requirement_matcher.py`, `tests/blackbox/test_bb_matching.py` |
| 3 | `Collector._fetch` | `pipeline/core/collection/collector.py:40` | 6 | **Yes**: WB-COL-01 to 07 | `tests/whitebox/test_basis_paths_collection.py` |
| 4 | `build_account_ref` | `pipeline/core/identity/profiles.py:44` | 5 | No | `tests/unit/identity/test_profiles.py` |
| 5 | `_valid` | `pipeline/core/scoring/claims.py:53` | 5 | No | `tests/unit/scoring/test_claims.py`, `test_claim_extraction_realistic.py` |
| 6 | `_profile_handle` | `pipeline/core/intake.py:38` | 5 | No | `tests/unit/core/test_intake.py` |
| 7 | `RuleBasedClaimProvider.complete` | `pipeline/adapters/rule_claims.py:164` | 5 | No | `tests/unit/adapters/test_rule_claims.py`, `tests/unit/scoring/test_claim_extraction_realistic.py` |
| 8 | `classified_lines` | `pipeline/adapters/rule_claims.py:79` | 5 | No | `tests/unit/adapters/test_rule_claims.py` |
| 9 | `_platform_claims` | `pipeline/adapters/rule_claims.py:123` | 5 | No | `tests/unit/adapters/test_rule_claims.py` |
| 10 | `read_resume` | `pipeline/adapters/resume_reader.py:61` | 5 | No | `tests/unit/adapters/test_resume_reader.py` |
| 11 | `ClaudeClaimProvider._create` | `pipeline/adapters/claude_llm.py:75` | 5 | No | `tests/unit/adapters/test_claude_llm.py` (SDK mocked) |
| 12 | `FakeHttpClient._serve` | `pipeline/adapters/fakes.py:28` | 5 | No: test double. | Used by every collection test |

Notes:

- **White-box targets.** The basis-path suites cover `Collector._fetch`, `IdentityResolver.resolve`,
  `IdentityResolver._link`, `SkillClaimRule.verify` and `_validated` (Section 4 of the white-box design).
- **#1 is not basis-path tested.** It is the most complex core function (the candidate input validator) and is covered
  by black-box and unit tests. See residual item R-3.

## 7. Significant findings and corrective/preventive actions (CAPA)

| CAPA | Type | Trigger | Action | Status |
|---|---|---|---|---|
| CAPA-SA-1 | Corrective | SA-01 to SA-03: names shadowing outer scope (`json` module, module-level `app`). A later edit inside those functions could silently use the wrong object. | Removed the shadowing: a `from json import dumps` import, and a local `application` in `create_app`. W0621 stays enabled. | Done |
| CAPA-SA-2 | Preventive | The CI gate was `pylint pipeline --fail-under=9`. The baseline scored 9.59 with 67 open findings and still passed CI, so the gate did not enforce NFR-05. | Raised to `--fail-under=9.9` in `.github/workflows/ci.yml`. The code now scores 10.00, so any new Pylint finding in a small change drops the score towards the gate. | Done |
| CAPA-SA-3 | Preventive | SA-72: a disable that suppressed nothing. | Removed `missing-module-docstring` from the disable list. | Done |
| CAPA-SA-4 | Preventive | SA-68 to SA-71: new test code arrived with Ruff findings. CI would block them on push, but only after the push. | Recommend a pre-commit hook that runs `ruff check` and `ruff format --check` before commit. | Deferred to M3 |
| CAPA-SA-5 | Preventive | Global disables of `too-many-arguments`, `too-many-positional-arguments` and `too-many-instance-attributes` hide every future occurrence, but there are only 4, 4 and 5 current hits (section 8). | Replace the global disables with config thresholds that fit the current design, such as `max-args = 8` and `max-attributes = 11`, so that growth beyond today's level is reported. | Deferred to M3 |

## 8. Review of the Pylint disable list in `pyproject.toml`

The counts come from re-running Pylint with only these messages enabled (`static-analysis-after/pylint-suppressed-messages.txt`; score 9.45/10 with them enabled).

| Disabled message | Hits suppressed | Where | Justified? |
|---|---|---|---|
| `missing-module-docstring` | 0 | – | **No.** It suppressed nothing, so it was removed (SA-72, CAPA-SA-3). |
| `missing-function-docstring` | 50 | See below. | **Partly.** See below. |
| `too-few-public-methods` | 29 | See below. | **Yes.** See below. |
| `too-many-arguments` | 4 | `pipeline/core/pipeline.py:62` (`PipelineRun.__init__`, 8/5) and `pipeline/core/scoring/scoring.py:24, 86, 107` (6/5) | **Acceptable but too broad.** See below. |
| `too-many-positional-arguments` | 4 | The same 4 functions as `too-many-arguments`. | Same as `too-many-arguments`. |
| `too-many-instance-attributes` | 5 | `pipeline/core/models.py:30` (`RunRecord`, 9/7), `:70` (`Snapshot`, 10/7), `:86` (`EvidenceNode`, 9/7), `pipeline/core/pipeline.py:32` (`Repositories`, 9/7), `:59` (`PipelineRun`, 11/7) | **Acceptable but too broad.** See below. |

**`missing-function-docstring` (50 hits).** The largest groups are `ports.py` (8), `collection/factory.py` (5), `adapters/postgres.py` (5) and `models.py` (4).

- Most hits are small methods with descriptive names and type hints, where a docstring would repeat the signature.
- The abstract port methods in `ports.py` are the contracts between core and adapters. They should state their error contract the way `HttpClient.get` already does (residual R-1).

**`too-few-public-methods` (29 hits).** These are frozen dataclasses, Strategy classes (signals, rules, scoring) and port ABCs that have one method by design. This message is a known false positive for these patterns.

**`too-many-arguments` and `too-many-positional-arguments` (4 hits each).**

- `PipelineRun.__init__` takes its 8 collaborators by constructor injection. That is the composition root's contract.
- The 3 scoring methods follow the `ScoringStrategy.score` signature.
- Both are deliberate, but a global disable also hides future growth. See CAPA-SA-5.

**`too-many-instance-attributes` (5 hits).** These are immutable records that mirror database rows, plus the orchestrator. Splitting them would add indirection without benefit. A global disable is wider than needed; see CAPA-SA-5.

## 9. Behaviour preservation

All changes are docstrings, one import form, one local rename, one `len()` truth test, formatter whitespace and one explicit `strict=False`. None of them changes behaviour.

The full non-integration suite was run after the final static-analysis capture:

```
.venv/Scripts/python -m pytest -q -m "not integration"
546 passed, 10 deselected, 6 xfailed, 1 warning
```

This result was the same on three consecutive runs.

- **One flaky stress test.** On one earlier full run, while other agents were running tests on the same machine, `tests/stress/test_collection_stress.py::test_twenty_candidates_overlap_across_sources_but_respect_per_source_intervals` failed once. That test measures real `time.perf_counter` gaps, so it is sensitive to CPU load. It passed on 4 isolated runs and on the 3 full re-runs. None of the static-analysis changes touch the rate limiter or the collector.

- **Deselected (10):** the `integration` tests, which need PostgreSQL and MinIO.
- **Xfailed (6):** expected failures that other M2 work recorded for known defects. They are not caused by these changes.
- **Warning (1):** a third-party `StarletteDeprecationWarning` from `fastapi.testclient`.

## 10. Residual items

| ID | Item | Target |
|---|---|---|
| R-1 | Add docstrings to the abstract methods in `pipeline/core/ports.py` that state each method's contract and the errors it raises. This is the useful part of the 50 suppressed `missing-function-docstring` hits. | M3 |
| R-2 | Pylint is not run on `tests/`; only Ruff checks them. Accepted for now: test code is checked by Ruff (E, F, B, SIM), and Pylint conventions such as docstrings and redefined pytest fixtures produce mostly noise there. | Review in M3 |
| R-3 | `CandidateInput.__post_init__` (V(G) = 7) is the most complex core function and has no basis-path tests, only black-box and unit tests. It is a candidate for the M3 white-box set. | M3 |
| R-4 | CAPA-SA-4 (pre-commit hook) and CAPA-SA-5 (narrower thresholds instead of global disables). | M3 |
| R-5 | `ruff check` in CI runs over `.`, but the local commands in this report use `pipeline tests`. Both returned 0 findings in the after-run (`static-analysis-after/ruff.txt`). | – |

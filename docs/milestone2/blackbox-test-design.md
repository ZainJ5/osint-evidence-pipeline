# Black-Box Test Design (SE431 Milestone 2)

Owner: Rabbin Batool. Techniques: Equivalence Partitioning (EP) and Boundary Value Analysis (BVA).
Scope: the real input rules and requirement conditions of `pipeline.core` and the REST API, taken from
`docs/requirements.md` (FR/NFR/QR IDs) and from the validation code at each module boundary
(`pipeline/core/inputs.py`, `collection/collector.py`, `collection/factory.py`, `identity/resolver.py`,
`matching/matcher.py`, `scoring/rules.py`, `scoring/scoring.py`, `pipeline.py`, `interface/api.py`).

## 1. Method and conventions

- Every input or condition is split into valid and invalid equivalence classes (`EC`), then the edges of each
  ordered class are tested with the standard BVA values (min-1, min, min+1, max-1, max, max+1, where they apply).
- Each test case has an ID `BB-<REQ>-NN`. It is written as a comment on the test and, for parametrised tables,
  as the pytest `ids=` value, so the IDs appear in the run log.
- **Referenced** cases are tests that already existed in `tests/unit` or `tests/system` and already cover a class or
  boundary. They were not copied. They get document-only IDs `BB-<REQ>-Rnn`. FR-01 is the exception: its existing
  tests already carry `BB-FR01-01..24`.
- **New** cases are in `tests/blackbox/test_bb_<area>.py`. The whole-pipeline fixtures (`system`, `candidate`, `job`)
  are reused from `tests/system/conftest.py` through `tests/blackbox/conftest.py`.
- A case that exposes a defect stays in the suite marked
  `@pytest.mark.xfail(reason="BB defect BB-DEF-nn: ...", strict=True)`. Nothing in `pipeline/` was changed.
- Result column: the outcome from the real runs recorded in `docs/records/m2/blackbox-run.txt` (new cases and
  FR-01) and `docs/records/m2/blackbox-referenced-run.txt` (referenced cases). `XFail` means the expected
  behaviour is not met: a confirmed defect.

Test files created:

| File | Area |
|---|---|
| `tests/blackbox/conftest.py` | fixture re-use, recording sleep |
| `tests/blackbox/test_bb_candidate.py` | FR-01 gaps |
| `tests/blackbox/test_bb_inputs.py` | JobRequirementInput, RunConfig |
| `tests/blackbox/test_bb_collection.py` | FR-05 retry, back-off, rate limit |
| `tests/blackbox/test_bb_identity.py` | FR-09 |
| `tests/blackbox/test_bb_matching.py` | FR-10 |
| `tests/blackbox/test_bb_verification.py` | FR-12 |
| `tests/blackbox/test_bb_scoring.py` | FR-13 |
| `tests/blackbox/test_bb_replay.py` | FR-14 |
| `tests/blackbox/test_bb_api.py` | FR-15 |
| `tests/blackbox/test_bb_reliability.py` | NFR-02 |

File abbreviations used in the tables: `CI` = `tests/unit/collection/test_candidate_input.py`,
`CR` = `tests/unit/collection/test_collector_retry.py`, `RUN` = `tests/unit/collection/test_collection_runner.py`,
`RES` = `tests/unit/identity/test_resolver.py`, `MAT` = `tests/unit/matching/test_requirement_matcher.py`,
`RR` = `tests/unit/scoring/test_rating_rule.py`, `SR` = `tests/unit/scoring/test_skill_rule.py`,
`SC` = `tests/unit/scoring/test_scoring.py`, `SYS` = `tests/system/test_pipeline_system.py`,
`API` = `tests/system/test_api.py`, and `bb/x` = `tests/blackbox/test_bb_x.py`.

---

## 2. FR-01 Candidate registration input (`CandidateInput`)

**Input/condition.** `name` 1-200 characters and not blank; `email` matches `^[^@\s]+@[^@\s]+\.[^@\s]+$`;
`resume_text` 1-50 000 characters (raised from 20 000 after M2 so long CVs parse and run); `handles` maps a known source (`github`, `codeforces`, `leetcode`) to a handle
matching that source's rule: GitHub 1-39 alphanumerics or single inner hyphens; Codeforces 3-24 of `[A-Za-z0-9_.-]`;
LeetCode 1-30 of `[A-Za-z0-9_-]`. Zero handles is allowed.

**Equivalence classes**

| EC | Input | Valid/Invalid | Representative |
|---|---|---|---|
| EC-01-1 | name 1-200 non-blank | V | `"Octo Developer"` |
| EC-01-2 | name empty | I | `""` |
| EC-01-3 | name whitespace only | I | `"   "` |
| EC-01-4 | name > 200 | I | 201 x `a` |
| EC-01-5 | email well formed | V | `octo@example.org`, `first.last+tag@uni.edu.pk` |
| EC-01-6 | email malformed (no @, no local, no domain, no TLD, space, empty) | I | `octo.example.org` |
| EC-01-7 | resume 1-50 000 | V | `"Python developer."` |
| EC-01-8 | resume empty | I | `""` |
| EC-01-9 | resume > 50 000 | I | 50 001 x `x` |
| EC-01-10 | handles: known source + valid handle (incl. zero handles) | V | `{"github": "octo-dev"}`, `{}` |
| EC-01-11 | handles: unknown source | I | `{"gitlab": "octo-dev"}` |
| EC-01-12 | handle breaks its source rule (length, character, leading hyphen, missing) | I | `{"github": "-octo"}` |

**Boundary values**

| Field | min-1 | min | max | max+1 |
|---|---|---|---|---|
| name length | 0 | 1 | 200 | 201 |
| resume length | 0 | 1 | 50 000 | 50 001 |
| GitHub handle length | - | 1 (implicit) | 39 | 40 |
| Codeforces handle length | 2 | 3 | 24 | 25 |
| LeetCode handle length | 0 | 1 | 30 | 31 |

**Test cases**

| TC | Req | Class/boundary | Input | Expected | Test (file::name) | Result |
|---|---|---|---|---|---|---|
| BB-FR01-01 | FR-01 | EC-01-2, name min-1 | name `""` | ValidationError field `name` | CI::test_name_length_0_rejected | Pass |
| BB-FR01-02 | FR-01 | name min | `"A"` | accepted | CI::test_name_length_1_accepted | Pass |
| BB-FR01-03 | FR-01 | name max | 200 chars | accepted | CI::test_name_length_200_accepted | Pass |
| BB-FR01-04 | FR-01 | EC-01-4, max+1 | 201 chars | rejected `name` | CI::test_name_length_201_rejected | Pass |
| BB-FR01-05 | FR-01 | EC-01-3 | `"   "` | rejected `name` | CI::test_name_whitespace_only_rejected | Pass |
| BB-FR01-06 | FR-01 | EC-01-5 | 2 valid emails | accepted | CI::test_email_valid_class_accepted | Pass (2 items) |
| BB-FR01-07 | FR-01 | EC-01-6 | 6 malformed emails | rejected `email` | CI::test_email_invalid_class_rejected | Pass (6 items) |
| BB-FR01-08 | FR-01 | GitHub max | 39 chars | accepted | CI::test_github_handle_length_39_accepted | Pass |
| BB-FR01-09 | FR-01 | GitHub max+1 | 40 chars | rejected `handles.github` | CI::test_github_handle_length_40_rejected | Pass |
| BB-FR01-10 | FR-01 | EC-01-12 | `-octo` | rejected | CI::test_github_handle_leading_hyphen_rejected | Pass |
| BB-FR01-11 | FR-01 | EC-01-10 | `octo-dev` | accepted | CI::test_github_handle_inner_hyphen_accepted | Pass |
| BB-FR01-12 | FR-01 | EC-01-11 | `gitlab` | rejected `handles` | CI::test_unknown_source_rejected | Pass |
| BB-FR01-13 | FR-01 | EC-01-10 | all 3 sources | accepted | CI::test_all_three_known_sources_accepted | Pass |
| BB-FR01-14 | FR-01 | resume max | 50 000 | accepted | CI::test_resume_length_max_accepted | Pass |
| BB-FR01-15 | FR-01 | EC-01-9, max+1 | 50 001 | rejected | CI::test_resume_length_max_plus_one_rejected | Pass |
| BB-FR01-16 | FR-01 | EC-01-8, min-1 | `""` | rejected | CI::test_resume_empty_rejected | Pass |
| BB-FR01-17..20 | FR-05 | max_retries -1/0/3/4 | RunConfig | -1, 4 rejected; 0, 3 accepted | CI::test_run_config_max_retries_boundaries | Pass (4) |
| BB-FR01-21..24 | FR-09 | link_threshold -0.01/0/1/1.01 | RunConfig | outside [0,1] rejected | CI::test_run_config_link_threshold_boundaries | Pass (4) |
| BB-FR01-25 | FR-01 | Codeforces min-1 | `ab` | rejected `handles.codeforces` | bb/candidate::test_handle_rules_per_source | Pass |
| BB-FR01-26 | FR-01 | Codeforces min | `abc` | accepted | bb/candidate::test_handle_rules_per_source | Pass |
| BB-FR01-27 | FR-01 | Codeforces max | 24 chars | accepted | bb/candidate::test_handle_rules_per_source | Pass |
| BB-FR01-28 | FR-01 | Codeforces max+1 | 25 chars | rejected | bb/candidate::test_handle_rules_per_source | Pass |
| BB-FR01-29 | FR-01 | EC-01-12 (character) | `octo@dev` | rejected | bb/candidate::test_handle_rules_per_source | Pass |
| BB-FR01-30 | FR-01 | LeetCode min | `a` | accepted | bb/candidate::test_handle_rules_per_source | Pass |
| BB-FR01-31 | FR-01 | LeetCode max | 30 chars | accepted | bb/candidate::test_handle_rules_per_source | Pass |
| BB-FR01-32 | FR-01 | LeetCode max+1 | 31 chars | rejected | bb/candidate::test_handle_rules_per_source | Pass |
| BB-FR01-33 | FR-01 | LeetCode min-1 | `""` | rejected | bb/candidate::test_handle_rules_per_source | Pass |
| BB-FR01-34 | FR-01 | EC-01-12 (missing) | GitHub `None` | rejected | bb/candidate::test_handle_rules_per_source | Pass |
| BB-FR01-35 | FR-01 | resume min | `"x"` | accepted | bb/candidate::test_resume_length_1_accepted | Pass |
| BB-FR01-36 | FR-01 | EC-01-10 (zero handles) | `{}` | accepted | bb/candidate::test_zero_handles_accepted | Pass |

Note: BB-FR01-17..24 test `RunConfig` and are traced to FR-05 / FR-09 in the summary (section 13), not to FR-01.

---

## 3. Job requirement input (`JobRequirementInput`, input to FR-10)

**Input/condition.** `id` and `title` non-empty; `required_skills` has 1-50 entries; no entry is empty, blank or
`None`.

| EC | Input | V/I | Representative |
|---|---|---|---|
| EC-J-1 | 1-50 non-blank skills | V | `("Python",)` |
| EC-J-2 | 0 skills | I | `()` |
| EC-J-3 | > 50 skills | I | 51 skills |
| EC-J-4 | contains empty / whitespace / None entry | I | `("Python", "\t")` |
| EC-J-5 | entry with surrounding spaces | V | `(" Python ",)` |
| EC-J-6 | id or title empty | I | `""` |
| EC-J-7 | title whitespace only | I (expected) | `"   "` |

| Boundary | min-1 | min | min+1 | max-1 | max | max+1 |
|---|---|---|---|---|---|---|
| skill count | 0 | 1 | 2 | 49 | 50 | 51 |

| TC | Req | Class/boundary | Input | Expected | Test | Result |
|---|---|---|---|---|---|---|
| BB-FR10-01 | FR-10 | EC-J-2, min-1 | 0 skills | rejected `required_skills` | bb/inputs::test_required_skills_count_boundaries | Pass |
| BB-FR10-02 | FR-10 | min | 1 | accepted | same | Pass |
| BB-FR10-03 | FR-10 | min+1 | 2 | accepted | same | Pass |
| BB-FR10-04 | FR-10 | max-1 | 49 | accepted | same | Pass |
| BB-FR10-05 | FR-10 | max | 50 | accepted | same | Pass |
| BB-FR10-06 | FR-10 | EC-J-3, max+1 | 51 | rejected | same | Pass |
| BB-FR10-07 | FR-10 | EC-J-4 | `[""]` | rejected | bb/inputs::test_blank_skill_entry_rejected | Pass |
| BB-FR10-08 | FR-10 | EC-J-4 | `["   "]` | rejected | same | Pass |
| BB-FR10-09 | FR-10 | EC-J-4 | `["Python", ""]` | rejected | same | Pass |
| BB-FR10-10 | FR-10 | EC-J-4 | `["Python", "\t"]` | rejected | same | Pass |
| BB-FR10-11 | FR-10 | EC-J-4 | `["Python", None]` | rejected | same | Pass |
| BB-FR10-12 | FR-10 | EC-J-5 | `[" Python "]` | accepted | bb/inputs::test_padded_skill_entry_accepted | Pass |
| BB-FR10-13 | FR-10 | EC-J-6 | id `""` | rejected `id` | bb/inputs::test_missing_job_id_or_title_rejected | Pass |
| BB-FR10-14 | FR-10 | EC-J-6 | title `""` | rejected `id` | same | Pass |
| BB-FR10-15 | FR-10 | EC-J-7 | title `"   "` | rejected | bb/inputs::test_whitespace_only_job_title_rejected | XFail at design → **Pass after fix (BB-DEF-04)** |

---

## 4. RunConfig fields (FR-05, FR-07, FR-09, NFR-03)

**Input/condition** (`RunConfig.__post_init__`): `link_threshold` in [0, 1]; `max_requests_per_source` >= 1;
`min_interval_seconds` >= 0; `max_retries` in [0, 3]; `extraction_workers` >= 1. `max_repos` (default 50,
NFR-03 "<= 50 repos") has **no** check. The fields are declared `int` / `float`.

| EC | Field | V/I | Representative |
|---|---|---|---|
| EC-C-1 | link_threshold in [0, 1] | V | 0.5 |
| EC-C-2 | link_threshold outside [0, 1] | I | -0.01, 1.01 |
| EC-C-3 | link_threshold NaN | I | `nan` |
| EC-C-4 | max_requests_per_source integer >= 1 | V | 2 |
| EC-C-5 | max_requests_per_source < 1 | I | 0 |
| EC-C-6 | min_interval_seconds >= 0 | V | 0.5 |
| EC-C-7 | min_interval_seconds < 0 | I | -0.01 |
| EC-C-8 | min_interval_seconds NaN | I | `nan` |
| EC-C-9 | max_retries integer 0-3 | V | 2 |
| EC-C-10 | max_retries outside 0-3 | I | -1, 4 |
| EC-C-11 | integer field given a non-integer | I | 2.5 / 1.5 |
| EC-C-12 | extraction_workers integer >= 1 | V | 4 |
| EC-C-13 | extraction_workers < 1 | I | 0 |
| EC-C-14 | max_repos >= 1 | V | 50 |
| EC-C-15 | max_repos negative | I | -1 |

| Field | Boundary values tested |
|---|---|
| link_threshold | -0.01, 0.0, 1.0, 1.01 (BB-FR01-21..24), NaN |
| max_requests_per_source | 0, 1 |
| min_interval_seconds | -0.01, 0.0, 2.0 |
| max_retries | -1, 0, 3, 4 (BB-FR01-17..20), 1, 2, 2.5 |
| extraction_workers | 0, 1, 1.5 |
| max_repos | -1, 1, 50 |

| TC | Req | Class/boundary | Input | Expected | Test | Result |
|---|---|---|---|---|---|---|
| BB-FR05-01 | FR-05 | EC-C-5, min-1 | max_requests_per_source=0 | rejected | bb/inputs::test_run_config_field_boundaries | Pass |
| BB-FR05-02 | FR-05 | EC-C-4, min | 1 | accepted | same | Pass |
| BB-FR05-03 | FR-05 | EC-C-7 | min_interval_seconds=-0.01 | rejected | same | Pass |
| BB-FR05-04 | FR-05 | EC-C-6, min | 0.0 | accepted | same | Pass |
| BB-FR05-05 | FR-05 | EC-C-6 | 2.0 | accepted | same | Pass |
| BB-FR07-01 | FR-07 | EC-C-13 | extraction_workers=0 | rejected | same | Pass |
| BB-FR07-02 | FR-07 | EC-C-12, min | 1 | accepted | same | Pass |
| BB-FR05-06 | FR-05 | EC-C-9 | max_retries=1 | accepted | same | Pass |
| BB-FR05-07 | FR-05 | EC-C-9 | max_retries=2 | accepted | same | Pass |
| BB-FR09-01 | FR-09 | EC-C-3 | link_threshold=NaN | rejected | bb/inputs::test_link_threshold_nan_rejected | Pass |
| BB-FR05-08 | FR-05 | EC-C-11 | max_retries=2.5 | rejected | bb/inputs::test_run_config_non_integer_count_rejected | XFail at design → **Pass after fix (BB-DEF-01)** |
| BB-FR07-03 | FR-07 | EC-C-11 | extraction_workers=1.5 | rejected | same | XFail at design → **Pass after fix (BB-DEF-01)** |
| BB-FR05-09 | FR-05 | EC-C-11 | max_requests_per_source=1.5 | rejected | same | XFail at design → **Pass after fix (BB-DEF-01)** |
| BB-FR05-10 | FR-05 | EC-C-8 | min_interval_seconds=NaN | rejected | bb/inputs::test_min_interval_nan_rejected | XFail at design → **Pass after fix (BB-DEF-02)** |
| BB-NFR03-01 | NFR-03 | EC-C-14, min | max_repos=1 | accepted | bb/inputs::test_max_repos_valid_values_accepted | Pass |
| BB-NFR03-02 | NFR-03 | EC-C-14, max | 50 | accepted | same | Pass |
| BB-NFR03-03 | NFR-03 | EC-C-15 | max_repos=-1 | rejected | bb/inputs::test_max_repos_negative_rejected | XFail at design → **Pass after fix (BB-DEF-03)** |

---

## 5. FR-05 Retry count, back-off and per-source rate limit

**Input/condition.** One logical request is tried `max_retries + 1` times. Retried: HTTP 429, every status >= 500,
and transport errors `TIMEOUT` / `NETWORK`. Not retried: other statuses (`NOT_FOUND` for 404, `HTTP_<n>` otherwise)
and `MALFORMED_BODY`. Back-off before retry k is `0.5 * 2^(k-1)` s (0.5, 1, 2). Accepted: 200-299. Rate limiter:
concurrency `max_requests_per_source`; interval `max(min_interval_seconds, source floor)`, with a Codeforces floor of
2.0 s.

| EC | Response class | Expected | Representative |
|---|---|---|---|
| EC-05-1 | 2xx with JSON | accepted, 1 attempt | 200 |
| EC-05-2 | 429 | retried | 429 |
| EC-05-3 | 5xx | retried | 503 |
| EC-05-4 | transient transport | retried | `TIMEOUT` |
| EC-05-5 | 404 | `NOT_FOUND`, not retried | 404 |
| EC-05-6 | other 4xx / 3xx / 1xx | `HTTP_<n>`, not retried | 403 |
| EC-05-7 | 2xx with non-JSON body | `MALFORMED_BODY`, not retried | `<html>` |
| EC-05-8 | non-transient transport | not retried | `NETWORK_DISABLED` |
| EC-05-9 | success after k <= max_retries transient failures | accepted | 503, 500, 429, 200 |
| EC-05-10 | success only after max_retries + 1 failures | failure | 4 x 503, 200 |

| Boundary | Values |
|---|---|
| max_retries -> attempts | 0 -> 1, 1 -> 2, 2 -> 3, 3 -> 4 |
| status, retried edge | 428 / **429** / 430; 499 / **500**; 599 |
| status, accepted edge | 199 / **200**, **201**; **299** / 300 |
| transient failures before success | 3 (last allowed) / 4 (one too many) |
| Codeforces interval floor | config 0.0, 1.99 -> 2.0; 2.01 -> 2.01 |

| TC | Req | Class/boundary | Input | Expected | Test | Result |
|---|---|---|---|---|---|---|
| BB-FR05-R01 | FR-05 | max_retries 0 | 500 always | 1 attempt, no sleep | CR::test_zero_retries_means_a_single_attempt | Pass |
| BB-FR05-R02 | FR-05 | max_retries 3 | 503 always | 4 attempts, sleeps 0.5/1/2, `HTTP_503` | CR::test_gives_up_after_max_retries_with_last_status_code | Pass |
| BB-FR05-R03 | FR-05 | EC-05-3, EC-05-9 | 503 then 200 | success, 2 attempts | CR::test_succeeds_on_second_try_after_503 | Pass |
| BB-FR05-R04 | FR-05 | EC-05-2 | 429 then 200 | success, sleep 0.5 | CR::test_429_is_retried | Pass |
| BB-FR05-R05 | FR-05 | EC-05-5 | 404 | `NOT_FOUND`, 1 attempt | CR::test_404_is_not_found_and_not_retried | Pass |
| BB-FR05-R06 | FR-05 | EC-05-6 | 403 | `HTTP_403`, 1 attempt | CR::test_other_client_error_is_reported_with_its_status | Pass |
| BB-FR05-R07 | FR-05 | EC-05-4 | TIMEOUT then 200 | success | CR::test_transport_failure_is_retried[TIMEOUT] | Pass |
| BB-FR05-R08 | FR-05 | EC-05-4 | NETWORK then 200 | success | CR::test_transport_failure_is_retried[NETWORK] | Pass |
| BB-FR05-R09 | FR-05 | EC-05-4 exhausted | TIMEOUT always | `TIMEOUT` | CR::test_timeout_forever_keeps_timeout_code | Pass |
| BB-FR05-R10 | FR-05 | EC-05-7 | 200 `<html>` | `MALFORMED_BODY`, 1 attempt | CR::test_malformed_body_is_reported_and_not_retried | Pass |
| BB-FR05-R11 | FR-05 | EC-05-8 | NETWORK_DISABLED | 1 attempt | CR::test_non_transient_transport_error_is_not_retried | Pass |
| BB-FR05-11 | FR-05 | max_retries 1 | 503 always | 2 attempts, sleeps [0.5] | bb/collection::test_attempts_and_backoff_follow_max_retries | Pass |
| BB-FR05-12 | FR-05 | max_retries 2 | 503 always | 3 attempts, sleeps [0.5, 1.0] | same | Pass |
| BB-FR05-13 | FR-05 | EC-05-2 | 429 always | `HTTP_429`, 4 attempts | bb/collection::test_429_and_5xx_are_retried_until_exhausted | Pass |
| BB-FR05-14 | FR-05 | EC-05-3, lower edge | 500 | `HTTP_500`, 4 attempts | same | Pass |
| BB-FR05-15 | FR-05 | EC-05-3 | 502 | 4 attempts | same | Pass |
| BB-FR05-16 | FR-05 | EC-05-3 | 504 | 4 attempts | same | Pass |
| BB-FR05-17 | FR-05 | EC-05-3, upper edge | 599 | 4 attempts | same | Pass |
| BB-FR05-18 | FR-05 | EC-05-6 | 400 | `HTTP_400`, 1 attempt | bb/collection::test_other_status_codes_fail_without_retry | Pass |
| BB-FR05-19 | FR-05 | EC-05-6 | 401 | 1 attempt | same | Pass |
| BB-FR05-20 | FR-05 | 429-1 | 428 | 1 attempt | same | Pass |
| BB-FR05-21 | FR-05 | 429+1 | 430 | 1 attempt | same | Pass |
| BB-FR05-22 | FR-05 | 500-1 | 499 | 1 attempt | same | Pass |
| BB-FR05-23 | FR-05 | 299+1 | 300 | 1 attempt | same | Pass |
| BB-FR05-24 | FR-05 | 200-1 | 199 | 1 attempt | same | Pass |
| BB-FR05-25 | FR-05 | EC-05-1, 200+1 | 201 | accepted | bb/collection::test_2xx_edges_are_accepted | Pass |
| BB-FR05-26 | FR-05 | EC-05-1, upper edge | 299 | accepted | same | Pass |
| BB-FR05-27 | FR-05 | EC-05-9, last allowed | 503, 500, 429, 200 | accepted after 4 attempts | bb/collection::test_success_on_the_last_allowed_attempt | Pass |
| BB-FR05-28 | FR-05 | EC-05-10 | 4 x 503, 200 | `HTTP_503` after 4 attempts | bb/collection::test_success_one_attempt_too_late_is_a_failure | Pass |
| BB-FR05-29 | FR-05 | EC-05-4, last allowed | 3 x TIMEOUT, 200 | accepted after 4 | bb/collection::test_timeout_recovers_on_the_last_allowed_attempt | Pass |
| BB-FR05-30 | FR-05 | no floor | github, 0.0 | interval 0.0 | bb/collection::test_limiter_interval_respects_source_floor | Pass |
| BB-FR05-31 | FR-05 | floor | codeforces, 0.0 | 2.0 | same | Pass |
| BB-FR05-32 | FR-05 | floor-0.01 | codeforces, 1.99 | 2.0 | same | Pass |
| BB-FR05-33 | FR-05 | floor+0.01 | codeforces, 2.01 | 2.01 | same | Pass |
| BB-FR05-34 | FR-05 | concurrency min | max_requests_per_source=1 | limiter concurrency 1 | bb/collection::test_limiter_concurrency_comes_from_config | Pass |

(BB-FR05-01..10 are the RunConfig cases in section 4; BB-FR01-17..20 also trace here.)

---

## 6. FR-09 Link threshold

**Input/condition.** `confidence >= threshold` is linked, below is not. Threshold in [0, 1], default 0.50; an
unlinked rationale names the threshold. Unlinked evidence is excluded from scoring.

| EC | Condition | Expected | Representative |
|---|---|---|---|
| EC-09-1 | confidence >= threshold | linked | 0.5 at 0.5 |
| EC-09-2 | confidence < threshold | not linked, rationale | 0.4999 at 0.5 |
| EC-09-3 | threshold outside [0, 1] or not a number | refused | 1.0001, `"0.5"`, None, NaN |

| Boundary | Values |
|---|---|
| default threshold 0.50 | 0.4999 / 0.5 / 0.5001 |
| threshold 0.0 | confidence 0.0, 0.0001 |
| threshold 1.0 | confidence 0.9999, 1.0 |
| threshold range | -0.0001, -0.01, 0.0, 1.0, 1.0001, 1.01 |

| TC | Req | Class/boundary | Input | Expected | Test | Result |
|---|---|---|---|---|---|---|
| BB-FR09-R01 | FR-09 | 0.5 - 0.0001 | conf 0.4999, thr 0.5 | not linked | RES::test_threshold_boundary[0.4999-False] | Pass |
| BB-FR09-R02 | FR-09 | on threshold | 0.5 | linked | RES::test_threshold_boundary[0.5-True] | Pass |
| BB-FR09-R03 | FR-09 | 0.5 + 0.0001 | 0.5001 | linked | RES::test_threshold_boundary[0.5001-True] | Pass |
| BB-FR09-R04..R07 | FR-09 | EC-09-3 | -0.01, 1.01, `"0.5"`, None | ResolutionError | RES::test_invalid_threshold_raises | Pass (4) |
| BB-FR09-R08 | FR-09 | configurable | custom threshold | honoured | RES::test_threshold_is_configurable | Pass |
| BB-FR09-R09 | FR-09 | EC-09-2 end to end | stranger account | not linked, total 0 | SYS::test_unlinked_account_evidence_is_excluded | Pass |
| BB-FR09-01 | FR-09 | EC-09-3 | RunConfig NaN | rejected | bb/inputs::test_link_threshold_nan_rejected | Pass |
| BB-FR09-02 | FR-09 | thr 0.0, on | conf 0.0 | linked | bb/identity::test_extreme_thresholds | Pass |
| BB-FR09-03 | FR-09 | thr 0.0, above | 0.0001 | linked | same | Pass |
| BB-FR09-04 | FR-09 | thr 1.0, below | 0.9999 | not linked | same | Pass |
| BB-FR09-05 | FR-09 | thr 1.0, on | 1.0 | linked | same | Pass |
| BB-FR09-06 | FR-09 | default, below | 0.4999, no threshold given | not linked | bb/identity::test_default_threshold_is_0_50 | Pass |
| BB-FR09-07 | FR-09 | default, on | 0.5 | linked | same | Pass |
| BB-FR09-08 | FR-09 | EC-09-2 rationale | 0.4999 | rationale "below threshold 0.50" | bb/identity::test_unlinked_rationale_names_the_threshold | Pass |
| BB-FR09-09 | FR-09 | 0 - 0.0001 | -0.0001 | ResolutionError | bb/identity::test_threshold_just_outside_range_is_refused | Pass |
| BB-FR09-10 | FR-09 | 1 + 0.0001 | 1.0001 | ResolutionError | same | Pass |

(BB-FR01-21..24 also trace here.)

---

## 7. FR-10 Coverage fraction

**Input/condition.** Required skills are normalised (alias table, case, whitespace) and de-duplicated; coverage =
matched distinct skills / distinct required skills, in [0, 1].

| EC | Condition | Expected | Representative |
|---|---|---|---|
| EC-10-1 | none matched | 0.0 | Haskell evidence for Python, Go |
| EC-10-2 | some matched | (0, 1) | 1 of 2 |
| EC-10-3 | all matched | 1.0 | Python for Python |
| EC-10-4 | duplicates that normalise equal | counted once | Python, py, python3 |
| EC-10-5 | no evidence at all | 0.0 | `[]` |

| Boundary | Values |
|---|---|
| coverage | 0, 1/50 = 0.02, 1/3, 1/2, 49/50 = 0.98, 1 |
| distinct count | 3 entries -> 1 distinct; 3 entries -> 2 distinct |

| TC | Req | Class/boundary | Input | Expected | Test | Result |
|---|---|---|---|---|---|---|
| BB-FR10-R01 | FR-10 | EC-10-1, coverage 0 | Python, Go vs Haskell | 0.0 | MAT::test_no_skill_matched_gives_zero_coverage | Pass |
| BB-FR10-R02..R04 | FR-10 | EC-10-2/3: 1/2, 1/3, 1 | `py` evidence | 0.5, 0.333, 1.0 | MAT::test_partial_and_full_coverage | Pass (3) |
| BB-FR10-R05 | FR-10 | EC-10-3 via aliases | golang, Python3, GNU C++17 | 1.0 | MAT::test_all_skills_matched_through_aliases | Pass |
| BB-FR10-R06 | FR-10 | EC-10-4 order | Python, Go, py, PYTHON, golang | [python, go] | MAT::test_required_skills_are_normalised_and_deduplicated_in_order | Pass |
| BB-FR10-16 | FR-10 | EC-10-4 | Python, py, python3 | (1.0, 1 distinct) | bb/matching::test_duplicates_that_normalise_equal_count_once | Pass |
| BB-FR10-17 | FR-10 | EC-10-4 + EC-10-2 | Python, py, Go | (0.5, 2) not 2/3 | same | Pass |
| BB-FR10-18 | FR-10 | EC-10-4 case/space | `"  PYTHON "`, Python | (1.0, 1) | same | Pass |
| BB-FR10-19 | FR-10 | EC-10-4 aliases | Node.js, JS, javascript, Rust | (0.5, 2) | same | Pass |
| BB-FR10-20 | FR-10 | 1 of 50 | 50 skills, 1 matched | 0.02 | bb/matching::test_coverage_with_fifty_required_skills | Pass |
| BB-FR10-21 | FR-10 | 49 of 50 | 49 matched | 0.98 | same | Pass |
| BB-FR10-22 | FR-10 | 50 of 50 | 50 matched | 1.0 | same | Pass |
| BB-FR10-23 | FR-10 | EC-10-5 | no nodes | (0.0, 1) | bb/matching::test_no_evidence_gives_zero_coverage | Pass |

(BB-FR10-01..15, the job input cases, are in section 3.)

---

## 8. FR-12 Claim verification rules

**Rating rule.** Best observed rating (rating or max_rating, same platform, case-insensitive) `>= claimed` ->
supported; `>= 0.8 x claimed` -> partially supported; else unsupported; no rating evidence or no claimed value ->
unsupported.
**Skill duration rule.** No matching skill node -> unsupported; no years claimed -> supported; years claimed but no
parseable dates -> partially supported; whole years between earliest and latest date `>= claimed` -> supported,
else partially supported.

| EC | Rule | Condition | Expected |
|---|---|---|---|
| EC-12-1 | rating | best >= claimed | supported |
| EC-12-2 | rating | 0.8 x claimed <= best < claimed | partially_supported |
| EC-12-3 | rating | best < 0.8 x claimed | unsupported |
| EC-12-4 | rating | no evidence / other platform / no rating / claimed missing or 0 | unsupported |
| EC-12-5 | skill | observed >= claimed years | supported |
| EC-12-6 | skill | observed < claimed years | partially_supported |
| EC-12-7 | skill | no parseable dates | partially_supported |
| EC-12-8 | skill | no matching skill node | unsupported |

| Boundary | Values |
|---|---|
| rating, claim 1600 (80 % = 1280) | 1601, 1600, 1599, 1280, 1279 |
| rating, claim 1601 (80 % = 1280.8) | 1601, 1281, 1280 |
| rating, LeetCode claim 1800 (80 % = 1440) | 1440 |
| duration, day-exact | 2021-03-15 -> 2024-03-15 (3 y) vs -> 2024-03-14 (2 y) |
| duration, leap day | 2020-02-29 -> 2021-02-28 (0 y) vs -> 2021-03-01 (1 y) |
| claimed years | 0, 1, 2, 2.5, 3 |

| TC | Req | Class/boundary | Input | Expected | Test | Result |
|---|---|---|---|---|---|---|
| BB-FR12-R01 | FR-12 | claimed+1 | claim 1600, best 1601 | supported | RR::test_rating_boundaries[1601-supported] | Pass |
| BB-FR12-R02 | FR-12 | claimed ≤ best (equal) | 1600 | supported | RR::test_rating_boundaries[1600-supported] | Pass |
| BB-FR12-R03 | FR-12 | claimed-1 | 1599 | partial | RR::test_rating_boundaries[1599-partially_supported] | Pass |
| BB-FR12-R04 | FR-12 | exactly 80 % | 1280 | partial | RR::test_rating_boundaries[1280-partially_supported] | Pass |
| BB-FR12-R05 | FR-12 | just below 80 % | 1279 | unsupported | RR::test_rating_boundaries[1279-unsupported] | Pass |
| BB-FR12-R06 | FR-12 | EC-12-4 other platform | LeetCode 2000 for CF claim | unsupported | RR::test_other_platform_is_not_evidence | Pass |
| BB-FR12-R07 | FR-12 | EC-12-4 no rating | achievement without rating | unsupported | RR::test_achievement_without_rating_is_unsupported | Pass |
| BB-FR12-R08 | FR-12 | EC-12-5 equal | observed 3 vs 3 | supported | SR::test_sufficient_duration_is_supported | Pass |
| BB-FR12-R09 | FR-12 | EC-12-6 one less | observed 2 vs 3 | partial | SR::test_insufficient_duration_is_partially_supported | Pass |
| BB-FR12-R10 | FR-12 | EC-12-7 no dates | years 1, no dates | partial | SR::test_dates_missing_with_years_claimed_is_partially_supported | Pass |
| BB-FR12-R11 | FR-12 | fractional claim | 2.5 vs observed 2 | partial | SR::test_fractional_years_need_the_next_whole_year | Pass |
| BB-FR12-R12 | FR-12 | EC-12-8 | Go evidence for Python | unsupported | SR::test_no_matching_node_is_unsupported | Pass |
| BB-FR12-01 | FR-12 | EC-12-1 | claim 1601, best 1601 | supported | bb/verification::test_rating_rule_with_fractional_80_percent | Pass |
| BB-FR12-02 | FR-12 | ceil(80 %) | 1281 (>= 1280.8) | partial | same | Pass |
| BB-FR12-03 | FR-12 | below fractional 80 % | 1280 (< 1280.8) | unsupported | same | Pass |
| BB-FR12-04 | FR-12 | EC-12-4 no evidence | `[]` | unsupported | bb/verification::test_rating_without_evidence_or_claimed_value_is_unsupported | Pass |
| BB-FR12-05 | FR-12 | EC-12-4 claimed missing | rating None | unsupported | same | Pass |
| BB-FR12-06 | FR-12 | EC-12-4 claimed 0 | rating 0 | unsupported | same | Pass |
| BB-FR12-07 | FR-12 | platform case | subject `Codeforces` | supported | bb/verification::test_rating_platform_name_is_case_insensitive | Pass |
| BB-FR12-08 | FR-12 | exactly 80 %, LeetCode | claim 1800, best 1440 | partial | bb/verification::test_leetcode_rating_exactly_80_percent_is_partial | Pass |
| BB-FR12-09 | FR-12 | EC-12-5 equal to the day | 3 y claimed, 2021-03-15..2024-03-15 | supported | bb/verification::test_skill_duration_boundaries | Pass |
| BB-FR12-10 | FR-12 | EC-12-6 one day short | ..2024-03-14 | partial | same | Pass |
| BB-FR12-11 | FR-12 | EC-12-5 more | 2 y claimed, 3 observed | supported | same | Pass |
| BB-FR12-12 | FR-12 | leap day, 0 y | 1 y claimed, 2020-02-29..2021-02-28 | partial | same | Pass |
| BB-FR12-13 | FR-12 | leap day, 1 y | ..2021-03-01 | supported | same | Pass |
| BB-FR12-14 | FR-12 | claimed 0 | same-day dates | supported | same | Pass |
| BB-FR12-15 | FR-12 | EC-12-7 unparseable | `not-a-date`, `2024-13-45` | partial | bb/verification::test_unparseable_dates_count_as_no_dates | Pass |
| BB-FR12-16 | FR-12 | EC-12-8 no evidence | `[]` | unsupported | bb/verification::test_skill_claim_without_any_evidence_is_unsupported | Pass |

---

## 9. FR-13 Score total and weights

**Input/condition.** Total = 100 x weighted mean of four components, clamped to [0, 100] and rounded to 2 decimals.
contribution_depth = min(1, commits / 200); competitive_programming = min(1, max(0, best rating) / 2400). Weights
override defaults by name and must be known names, non-negative numbers (not bool), with a sum > 0.

| EC | Input | V/I | Representative |
|---|---|---|---|
| EC-13-1 | inputs inside the full-score range | V | 150 commits |
| EC-13-2 | inputs above the full-score range | V (clamped) | 10 000 commits, rating 4000 |
| EC-13-3 | negative rating / unknown verdict label | V (floored at 0) | -50 |
| EC-13-4 | weights: known, >= 0, sum > 0 | V | `{"verified_skills": 0}` |
| EC-13-5 | weight negative | I | -0.0001 |
| EC-13-6 | weight not a number (str, bool, None) | I | `True` |
| EC-13-7 | unknown component | I | `popularity` |
| EC-13-8 | all weights 0 | I | sum 0 |

| Boundary | Values |
|---|---|
| total | 0 and 100 |
| commits | 0, 199, 200, 201 |
| rating | -50, 2399, 2400, 2401 |
| weight | -0.0001, 0, 1e-9 (sum just > 0), 5, 10 |

| TC | Req | Class/boundary | Input | Expected | Test | Result |
|---|---|---|---|---|---|---|
| BB-FR13-R01 | FR-13 | total min | nothing | total 0 | SC::test_all_zero_scores_zero | Pass |
| BB-FR13-R02 | FR-13 | total max | perfect inputs | total 100 | SC::test_all_perfect_scores_one_hundred | Pass |
| BB-FR13-R03..R06 | FR-13 | EC-13-5/7/8/6 | -0.1, `popularity`, all 0, `"high"` | ScoringError | SC::test_invalid_weights_raise | Pass (4) |
| BB-FR13-R07 | FR-13 | EC-13-4 | custom weights | override defaults | SC::test_custom_weights_override_defaults | Pass |
| BB-FR13-01 | FR-13 | commits 0 | 0 | 0.0 | bb/scoring::test_contribution_depth_saturates_at_200_commits | Pass |
| BB-FR13-02 | FR-13 | full-1 | 199 | 0.995 | same | Pass |
| BB-FR13-03 | FR-13 | full | 200 | 1.0 | same | Pass |
| BB-FR13-04 | FR-13 | full+1 | 201 | 1.0 | same | Pass |
| BB-FR13-05 | FR-13 | EC-13-3 | rating -50 | 0.0 | bb/scoring::test_competitive_programming_saturates_at_2400 | Pass |
| BB-FR13-06 | FR-13 | full-1 | 2399 | 0.9996 | same | Pass |
| BB-FR13-07 | FR-13 | full | 2400 | 1.0 | same | Pass |
| BB-FR13-08 | FR-13 | full+1 | 2401 | 1.0 | same | Pass |
| BB-FR13-09 | FR-13 | EC-13-2, total max | 10 000 commits, 4000 rating, weights 10 | total exactly 100 | bb/scoring::test_total_never_exceeds_100_with_out_of_range_inputs | Pass |
| BB-FR13-10 | FR-13 | EC-13-3, total min | unknown verdict label | total 0 | bb/scoring::test_unknown_verdict_label_counts_as_zero_not_negative | Pass |
| BB-FR13-11 | FR-13 | weight 0 | verified_skills 0 | accepted, total in [0,100] | bb/scoring::test_weight_valid_boundaries_accepted | Pass |
| BB-FR13-12 | FR-13 | sum just > 0 | one weight 1e-9 | accepted | same | Pass |
| BB-FR13-13 | FR-13 | large weight | 5 | accepted | same | Pass |
| BB-FR13-14 | FR-13 | EC-13-5, 0-0.0001 | -0.0001 | ScoringError | bb/scoring::test_weight_invalid_classes_rejected | Pass |
| BB-FR13-15 | FR-13 | EC-13-6 bool | True | ScoringError | same | Pass |
| BB-FR13-16 | FR-13 | EC-13-6 None | None | ScoringError | same | Pass |
| BB-FR13-17 | FR-13 | sum just > 0 value | only requirement_match 1e-9, coverage 0.5 | total 50.0 | bb/scoring::test_single_tiny_positive_weight_gives_that_component_alone | Pass |

---

## 10. FR-14 Replay

**Input/condition.** Replay is allowed only for a stored run whose status is `done` or `partial`; it must not use the
network and must reproduce evidence and score. Otherwise `ValidationError` with code `RUN_NOT_FOUND`.

| EC | Run state | V/I | Representative |
|---|---|---|---|
| EC-14-1 | done | V | normal run |
| EC-14-2 | partial | V | one source 404 |
| EC-14-3 | running | I | inserted RunRecord |
| EC-14-4 | failed | I | inserted RunRecord |
| EC-14-5 | unknown / empty id | I | `"missing"`, `""` |

| TC | Req | Class | Input | Expected | Test | Result |
|---|---|---|---|---|---|---|
| BB-FR14-R01 | FR-14 | EC-14-1 | finished run | no new HTTP calls; evidence and score identical | SYS::test_replay_reproduces_evidence_and_score_without_network | Pass |
| BB-FR14-R02 | FR-14 | EC-14-5 | `"missing"` | ValidationError | SYS::test_replay_of_unknown_run_is_rejected | Pass |
| BB-FR14-01 | FR-14 | EC-14-3 | status running | `RUN_NOT_FOUND`, no HTTP | bb/replay::test_replay_of_a_run_that_is_not_finished_is_refused | Pass |
| BB-FR14-02 | FR-14 | EC-14-4 | status failed | `RUN_NOT_FOUND`, no HTTP | same | Pass |
| BB-FR14-03 | FR-14 | EC-14-5 | `""` | ValidationError | bb/replay::test_replay_of_empty_run_id_is_refused | Pass |
| BB-FR14-04 | FR-14 | EC-14-2 | partial run | no new HTTP calls; identical | bb/replay::test_replay_of_a_partial_run_reproduces_it | Pass |

---

## 11. FR-15 REST API

**Input/condition.** `POST /runs` (body = candidate + job), `GET /runs/{id}/report`, `POST /runs/{id}/replay`,
`DELETE /candidates/{id}`. A domain validation failure is 422 with `{"code": "VALIDATION_ERROR"}`; a pipeline error
whose code ends in `NOT_FOUND` is 404; a body that does not fit the schema is 422 (FastAPI).

| EC | Request | Expected | Representative |
|---|---|---|---|
| EC-15-1 | valid body | 200 + report | sample body |
| EC-15-2 | schema-valid but domain-invalid body | 422 `VALIDATION_ERROR` | bad email, 0 / 51 skills |
| EC-15-3 | schema-invalid body | 422 | missing `email` |
| EC-15-4 | known run id | 200 | id from POST |
| EC-15-5 | unknown run id | 404 | `no-such-run` |
| EC-15-6 | known candidate id on DELETE | 204 | id from POST |
| EC-15-7 | unknown / already deleted candidate | 404 `CANDIDATE_NOT_FOUND` | `no-such-candidate` |

| Boundary | Values |
|---|---|
| required_skills in body | 0, 50, 51 |
| resume_text in body | 50 001 |
| DELETE sequence | 1st (204), 2nd (404) |

| TC | Req | Class/boundary | Input | Expected | Test | Result |
|---|---|---|---|---|---|---|
| BB-FR15-R01 | FR-15 | EC-15-1/4/6 | run, report, replay, delete | 200, same total, identical, 204, then report 404 | API::test_run_report_replay_delete_round_trip | Pass |
| BB-FR15-R02 | FR-15 | EC-15-2 | invalid email | 422 `VALIDATION_ERROR` | API::test_invalid_input_is_rejected_at_the_boundary | Pass |
| BB-FR15-01 | FR-15 | EC-15-2, skills min-1 | `required_skills: []` | 422 `VALIDATION_ERROR` | bb/api::test_domain_invalid_body_is_422_validation_error | Pass |
| BB-FR15-02 | FR-15 | skills max+1 | 51 skills | 422 | same | Pass |
| BB-FR15-03 | FR-15 | blank skill | `["Python", "  "]` | 422 | same | Pass |
| BB-FR15-04 | FR-15 | empty name | `""` | 422 | same | Pass |
| BB-FR15-05 | FR-15 | bad handle | GitHub `-octo` | 422 | same | Pass |
| BB-FR15-06 | FR-15 | unknown source | `gitlab` | 422 | same | Pass |
| BB-FR15-07 | FR-15 | resume max+1 | 50 001 chars | 422 | same | Pass |
| BB-FR15-08 | FR-15 | EC-15-1, skills max | 50 skills | 200, total in [0,100] | bb/api::test_fifty_required_skills_is_accepted | Pass |
| BB-FR15-09 | FR-15 | EC-15-3 | no `email` | 422 | bb/api::test_body_missing_a_field_is_422 | Pass |
| BB-FR15-10 | FR-15 | EC-15-5 report | `no-such-run` | 404 | bb/api::test_report_of_unknown_run_is_404 | Pass |
| BB-FR15-11 | FR-15 | EC-15-5 replay | `no-such-run` | 404 `RUN_NOT_FOUND` | bb/api::test_replay_of_unknown_run_is_404_run_not_found | Pass |
| BB-FR15-12 | FR-15 | EC-15-7 | `no-such-candidate` | 404 `CANDIDATE_NOT_FOUND` | bb/api::test_delete_of_unknown_candidate_is_404_candidate_not_found | Pass |
| BB-FR15-13 | FR-15 | EC-15-6 then EC-15-7 | delete twice | 204 then 404 | bb/api::test_delete_twice_is_204_then_404 | Pass |

---

## 12. NFR-02 Reliability per failure class (QR-04)

**Input/condition.** A single failing source must not abort the run: status `partial`, the failure recorded as
`(source, code)` and logged on the `collect` stage, other sources' evidence kept. The failure is injected on the
GitHub profile URL in the fake HTTP client; the other two sources answer normally.

| EC | Failure class | Recorded code | Representative |
|---|---|---|---|
| EC-N2-1 | timeout (transport) | `TIMEOUT` | CollectionError TIMEOUT |
| EC-N2-2 | 5xx | `HTTP_5xx` | 500, 503 |
| EC-N2-3 | malformed body | `MALFORMED_BODY` | 200 `<html>` |
| EC-N2-4 | 404 handle not found | `NOT_FOUND` | 404 |
| EC-N2-5 | no source fails | status `done` | fixtures |

| Boundary (failing sources out of 3) | 0 | 1 | 3 |
|---|---|---|---|
| expected status | done | partial | partial (total 0) |

| TC | Req | Class/boundary | Input | Expected | Test | Result |
|---|---|---|---|---|---|---|
| BB-NFR02-R01 | NFR-02 | EC-N2-2 (503), 1 of 3 | GitHub 503 | partial, `(github, HTTP_503)`, CF + LC evidence | SYS::test_one_source_failing_gives_partial_run_with_other_evidence | Pass |
| BB-NFR02-R02 | NFR-02 | EC-N2-5, 0 of 3 | fixtures | done | SYS::test_full_run_produces_bounded_explainable_report | Pass |
| BB-NFR02-R03 | NFR-02 | runner level | one source failing forever | partial result | RUN::test_one_source_failing_forever_yields_a_partial_result | Pass |
| BB-NFR02-01 | NFR-02 | EC-N2-1 | GitHub TIMEOUT | partial, `(github, TIMEOUT)` recorded and logged, CF + LC evidence | bb/reliability::test_each_failure_class_gives_a_partial_run | Pass |
| BB-NFR02-02 | NFR-02 | EC-N2-2 | GitHub 500 | `(github, HTTP_500)` | same | Pass |
| BB-NFR02-03 | NFR-02 | EC-N2-3 | GitHub 200 `<html>` | `(github, MALFORMED_BODY)` | same | Pass |
| BB-NFR02-04 | NFR-02 | EC-N2-4 | GitHub 404 | `(github, NOT_FOUND)` | same | Pass |
| BB-NFR02-05 | NFR-02 | 3 of 3 | every URL 404 | partial, 3 failures, total 0 | bb/reliability::test_all_sources_failing_still_finishes_partial | Pass |

---

## 13. Defects found

| ID | Severity | Requirement | Found by | Description | Evidence |
|---|---|---|---|---|---|
| BB-DEF-01 | Medium | FR-05, FR-07 | BB-FR05-08, BB-FR07-03, BB-FR05-09 | `RunConfig` accepts non-integer values for its integer counts. `max_retries=2.5` and `extraction_workers=1.5` pass validation, then fail with `TypeError: 'float' object cannot be interpreted as an integer` in `range()` (collector retry loop / extractor workers). The collection runner re-raises any non-`CollectionError` as a bug, so the run crashes instead of failing at the boundary. `max_requests_per_source=1.5` gives a semaphore that let **2** requests run at once (measured), breaking the per-source limit (FR-05, NFR-01). | `pipeline/core/inputs.py` `RunConfig.__post_init__` checks only ranges, not types. |
| BB-DEF-02 | Medium | FR-05, NFR-01 | BB-FR05-10 | `min_interval_seconds=NaN` is accepted (`nan < 0` is False). In `RateLimiter._wait_for_turn`, `now < last + nan` is always False, so no spacing is ever applied: rate limiting is silently off (measured: 3 back-to-back calls, 0 sleeps). `link_threshold=NaN` is correctly rejected, so the two float fields are inconsistent. | `RunConfig.__post_init__` |
| BB-DEF-03 | Low | NFR-03 | BB-NFR03-03 | `max_repos` has no validation. `max_repos=-1` is accepted, and `GitHubCollector` slices `repos[: -1]`, silently dropping the last repository (measured: 3 repos -> 2). | `RunConfig.__post_init__`; `pipeline/core/collection/github.py` line 23 |
| BB-DEF-04 | Low | FR-10 (job input), FR-15 | BB-FR10-15 | A whitespace-only job `title` (and `id`) is accepted. Blank checks use `.strip()` for candidate names and skills but not for job id and title, so a job can be stored with a blank title. | `JobRequirementInput.__post_init__` uses `not self.id or not self.title` |

Suggested fix for 01-03 (for the developers, not applied): check `isinstance(value, int) and not isinstance(value,
bool)` for the count fields, `math.isfinite` for the float fields, and `max_repos >= 1`. For 04: `.strip()` the id
and title before the emptiness check.

**Observations (not counted as defects; for the team to decide):**

1. Error bodies differ by path: domain errors return `{"code", "message"}`; schema errors return FastAPI's
   `{"detail": [...]}`; an unknown report returns `{"detail": "report not found"}` without a `code`. A client cannot
   rely on one error shape (QR-16 interoperability).
2. Replaying a run that exists but is `running` or `failed` returns 404 `RUN_NOT_FOUND`, the same as an unknown id.
   409 Conflict, or a separate code such as `RUN_NOT_FINISHED`, would tell the two cases apart.
3. With `link_threshold=0.0`, an account with confidence 0.0 (no matching signal) is linked (BB-FR09-02). This
   matches FR-09 as written ("below the threshold" is unlinked), but such a configuration links strangers.
4. `test_run_config_max_retries_boundaries` and `test_run_config_link_threshold_boundaries` carry `BB-FR01-17..24`
   but test FR-05 and FR-09 configuration. The RTM should trace them to FR-05 / FR-09 (done in section 14).

---

### 13.1 Corrective actions after test design (2026-11-19)

All four defects were fixed in `pipeline/core/inputs.py` after this design was executed; their `xfail` markers were
removed and the tests now pass.

| Defect | Root cause | Corrective action | Preventive action | Verification | Status |
|---|---|---|---|---|---|
| BB-DEF-01 | Validation checked ranges, not types | `_check_int` helper: integer counts only (bool rejected) | Every new `RunConfig` field must go through `_check_int`/`_check_number` | BB-FR05-08, BB-FR07-03, BB-FR05-09 pass | Closed |
| BB-DEF-02 | `nan < 0` is False, so NaN slipped through | `_check_number` helper: finite numbers only | Same helper for all float fields | BB-FR05-10 passes | Closed |
| BB-DEF-03 | Field had no validation | `max_repos` must be an integer in [0, 100] (one GitHub page) | Same | BB-NFR03-03 and new BB-NFR03-04..07 pass | Closed |
| BB-DEF-04 | Blank check without `strip()` | Job id and title are stripped before the blank check | Checklist item "blank = empty after strip" added for the M3 inspection | BB-FR10-15 passes | Closed |

## 14. Traceability summary (for the RTM)

| Requirement | New BB test IDs (tests/blackbox) | Referenced BB IDs (existing tests) |
|---|---|---|
| FR-01 | BB-FR01-25..36 | BB-FR01-01..16 |
| FR-05 | BB-FR05-01..34 | BB-FR01-17..20, BB-FR05-R01..R11 |
| FR-07 | BB-FR07-01..03 | - |
| FR-09 | BB-FR09-01..10 | BB-FR01-21..24, BB-FR09-R01..R09 |
| FR-10 | BB-FR10-01..23 | BB-FR10-R01..R06 |
| FR-12 | BB-FR12-01..16 | BB-FR12-R01..R12 |
| FR-13 | BB-FR13-01..17 | BB-FR13-R01..R07 |
| FR-14 | BB-FR14-01..04 | BB-FR14-R01..R02 |
| FR-15 | BB-FR15-01..13 | BB-FR15-R01..R02 |
| NFR-02 / QR-04 | BB-NFR02-01..05 | BB-NFR02-R01..R03 |
| NFR-03 | BB-NFR03-01..07 | - |

Machine-readable form (requirement, test id, file::function):

```csv
requirement,bb_id,test
FR-01,BB-FR01-01..16,tests/unit/collection/test_candidate_input.py (see section 2)
FR-01,BB-FR01-25..34,tests/blackbox/test_bb_candidate.py::test_handle_rules_per_source
FR-01,BB-FR01-35,tests/blackbox/test_bb_candidate.py::test_resume_length_1_accepted
FR-01,BB-FR01-36,tests/blackbox/test_bb_candidate.py::test_zero_handles_accepted
FR-05,BB-FR01-17..20,tests/unit/collection/test_candidate_input.py::test_run_config_max_retries_boundaries
FR-05,BB-FR05-01..07,tests/blackbox/test_bb_inputs.py::test_run_config_field_boundaries
FR-05,BB-FR05-08;BB-FR05-09,tests/blackbox/test_bb_inputs.py::test_run_config_non_integer_count_rejected
FR-05,BB-FR05-10,tests/blackbox/test_bb_inputs.py::test_min_interval_nan_rejected
FR-05,BB-FR05-11..12,tests/blackbox/test_bb_collection.py::test_attempts_and_backoff_follow_max_retries
FR-05,BB-FR05-13..17,tests/blackbox/test_bb_collection.py::test_429_and_5xx_are_retried_until_exhausted
FR-05,BB-FR05-18..24,tests/blackbox/test_bb_collection.py::test_other_status_codes_fail_without_retry
FR-05,BB-FR05-25..26,tests/blackbox/test_bb_collection.py::test_2xx_edges_are_accepted
FR-05,BB-FR05-27,tests/blackbox/test_bb_collection.py::test_success_on_the_last_allowed_attempt
FR-05,BB-FR05-28,tests/blackbox/test_bb_collection.py::test_success_one_attempt_too_late_is_a_failure
FR-05,BB-FR05-29,tests/blackbox/test_bb_collection.py::test_timeout_recovers_on_the_last_allowed_attempt
FR-05,BB-FR05-30..33,tests/blackbox/test_bb_collection.py::test_limiter_interval_respects_source_floor
FR-05,BB-FR05-34,tests/blackbox/test_bb_collection.py::test_limiter_concurrency_comes_from_config
FR-05,BB-FR05-R01..R11,tests/unit/collection/test_collector_retry.py (see section 5)
FR-07,BB-FR07-01..02,tests/blackbox/test_bb_inputs.py::test_run_config_field_boundaries
FR-07,BB-FR07-03,tests/blackbox/test_bb_inputs.py::test_run_config_non_integer_count_rejected
FR-09,BB-FR01-21..24,tests/unit/collection/test_candidate_input.py::test_run_config_link_threshold_boundaries
FR-09,BB-FR09-01,tests/blackbox/test_bb_inputs.py::test_link_threshold_nan_rejected
FR-09,BB-FR09-02..05,tests/blackbox/test_bb_identity.py::test_extreme_thresholds
FR-09,BB-FR09-06..07,tests/blackbox/test_bb_identity.py::test_default_threshold_is_0_50
FR-09,BB-FR09-08,tests/blackbox/test_bb_identity.py::test_unlinked_rationale_names_the_threshold
FR-09,BB-FR09-09..10,tests/blackbox/test_bb_identity.py::test_threshold_just_outside_range_is_refused
FR-09,BB-FR09-R01..R08,tests/unit/identity/test_resolver.py (see section 6)
FR-09,BB-FR09-R09,tests/system/test_pipeline_system.py::test_unlinked_account_evidence_is_excluded
FR-10,BB-FR10-01..06,tests/blackbox/test_bb_inputs.py::test_required_skills_count_boundaries
FR-10,BB-FR10-07..11,tests/blackbox/test_bb_inputs.py::test_blank_skill_entry_rejected
FR-10,BB-FR10-12,tests/blackbox/test_bb_inputs.py::test_padded_skill_entry_accepted
FR-10,BB-FR10-13..14,tests/blackbox/test_bb_inputs.py::test_missing_job_id_or_title_rejected
FR-10,BB-FR10-15,tests/blackbox/test_bb_inputs.py::test_whitespace_only_job_title_rejected
FR-10,BB-FR10-16..19,tests/blackbox/test_bb_matching.py::test_duplicates_that_normalise_equal_count_once
FR-10,BB-FR10-20..22,tests/blackbox/test_bb_matching.py::test_coverage_with_fifty_required_skills
FR-10,BB-FR10-23,tests/blackbox/test_bb_matching.py::test_no_evidence_gives_zero_coverage
FR-10,BB-FR10-R01..R06,tests/unit/matching/test_requirement_matcher.py (see section 7)
FR-12,BB-FR12-01..03,tests/blackbox/test_bb_verification.py::test_rating_rule_with_fractional_80_percent
FR-12,BB-FR12-04..06,tests/blackbox/test_bb_verification.py::test_rating_without_evidence_or_claimed_value_is_unsupported
FR-12,BB-FR12-07,tests/blackbox/test_bb_verification.py::test_rating_platform_name_is_case_insensitive
FR-12,BB-FR12-08,tests/blackbox/test_bb_verification.py::test_leetcode_rating_exactly_80_percent_is_partial
FR-12,BB-FR12-09..14,tests/blackbox/test_bb_verification.py::test_skill_duration_boundaries
FR-12,BB-FR12-15,tests/blackbox/test_bb_verification.py::test_unparseable_dates_count_as_no_dates
FR-12,BB-FR12-16,tests/blackbox/test_bb_verification.py::test_skill_claim_without_any_evidence_is_unsupported
FR-12,BB-FR12-R01..R07,tests/unit/scoring/test_rating_rule.py (see section 8)
FR-12,BB-FR12-R08..R12,tests/unit/scoring/test_skill_rule.py (see section 8)
FR-13,BB-FR13-01..04,tests/blackbox/test_bb_scoring.py::test_contribution_depth_saturates_at_200_commits
FR-13,BB-FR13-05..08,tests/blackbox/test_bb_scoring.py::test_competitive_programming_saturates_at_2400
FR-13,BB-FR13-09,tests/blackbox/test_bb_scoring.py::test_total_never_exceeds_100_with_out_of_range_inputs
FR-13,BB-FR13-10,tests/blackbox/test_bb_scoring.py::test_unknown_verdict_label_counts_as_zero_not_negative
FR-13,BB-FR13-11..13,tests/blackbox/test_bb_scoring.py::test_weight_valid_boundaries_accepted
FR-13,BB-FR13-14..16,tests/blackbox/test_bb_scoring.py::test_weight_invalid_classes_rejected
FR-13,BB-FR13-17,tests/blackbox/test_bb_scoring.py::test_single_tiny_positive_weight_gives_that_component_alone
FR-13,BB-FR13-R01..R07,tests/unit/scoring/test_scoring.py (see section 9)
FR-14,BB-FR14-01..02,tests/blackbox/test_bb_replay.py::test_replay_of_a_run_that_is_not_finished_is_refused
FR-14,BB-FR14-03,tests/blackbox/test_bb_replay.py::test_replay_of_empty_run_id_is_refused
FR-14,BB-FR14-04,tests/blackbox/test_bb_replay.py::test_replay_of_a_partial_run_reproduces_it
FR-14,BB-FR14-R01..R02,tests/system/test_pipeline_system.py (see section 10)
FR-15,BB-FR15-01..07,tests/blackbox/test_bb_api.py::test_domain_invalid_body_is_422_validation_error
FR-15,BB-FR15-08,tests/blackbox/test_bb_api.py::test_fifty_required_skills_is_accepted
FR-15,BB-FR15-09,tests/blackbox/test_bb_api.py::test_body_missing_a_field_is_422
FR-15,BB-FR15-10,tests/blackbox/test_bb_api.py::test_report_of_unknown_run_is_404
FR-15,BB-FR15-11,tests/blackbox/test_bb_api.py::test_replay_of_unknown_run_is_404_run_not_found
FR-15,BB-FR15-12,tests/blackbox/test_bb_api.py::test_delete_of_unknown_candidate_is_404_candidate_not_found
FR-15,BB-FR15-13,tests/blackbox/test_bb_api.py::test_delete_twice_is_204_then_404
FR-15,BB-FR15-R01..R02,tests/system/test_api.py (see section 11)
NFR-02,BB-NFR02-01..04,tests/blackbox/test_bb_reliability.py::test_each_failure_class_gives_a_partial_run
NFR-02,BB-NFR02-05,tests/blackbox/test_bb_reliability.py::test_all_sources_failing_still_finishes_partial
NFR-02,BB-NFR02-R01..R02,tests/system/test_pipeline_system.py (see section 12)
NFR-02,BB-NFR02-R03,tests/unit/collection/test_collection_runner.py::test_one_source_failing_forever_yields_a_partial_result
NFR-03,BB-NFR03-01..02,tests/blackbox/test_bb_inputs.py::test_max_repos_valid_values_accepted
NFR-03,BB-NFR03-03,tests/blackbox/test_bb_inputs.py::test_max_repos_negative_rejected
```

---

## 15. Execution summary

Command (run on 2026-11-19, Windows 11, project venv):

```
.venv/Scripts/python -m pytest tests/blackbox tests/unit/collection/test_candidate_input.py -q -rA
```

Full output: `docs/records/m2/blackbox-run.txt`. Final line:

```
164 passed, 6 xfailed, 1 warning in 10.33s
```

| Group | Test IDs | pytest items | Passed | XFail (defect) | Failed |
|---|---|---|---|---|---|
| New black-box cases (tests/blackbox) | 140 | 140 | 134 | 6 | 0 |
| FR-01 existing cases (BB-FR01-01..24) | 24 | 30 | 30 | 0 | 0 |
| **Recorded run total** | **164** | **170** | **164** | **6** | **0** |
| Referenced cases in other suites (BB-*-Rnn) | 52 | 52 | 52 | 0 | 0 |
| **All black-box cases in this design** | **216** | **222** | **216** | **6** | **0** |

The referenced cases were run with an explicit node-id list; output in `docs/records/m2/blackbox-referenced-run.txt`
(final line `52 passed, 1 warning in 5.46s`). The single warning in both runs is a third-party
`StarletteDeprecationWarning` from `fastapi.testclient`, not from project code.

All six XFail results are `strict=True`: when a defect is fixed, the test will XPASS and fail the suite, which
tells the team to remove the marker.

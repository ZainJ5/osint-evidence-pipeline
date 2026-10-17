"""Input validation: JobRequirementInput (FR-10 input) and RunConfig fields (FR-05, FR-07, FR-09, NFR-03).

Equivalence Partitioning and Boundary Value Analysis. FR-01 CandidateInput and the RunConfig max_retries /
link_threshold boundaries are already covered in tests/unit/collection/test_candidate_input.py (BB-FR01-01..24).
"""

import math

import pytest

from pipeline.core.errors import ValidationError
from pipeline.core.inputs import JobRequirementInput, RunConfig


def job(skills, job_id="job-1", title="Backend Engineer"):
    return JobRequirementInput(job_id, title, "text", tuple(skills))


def rejects_job(**kw):
    with pytest.raises(ValidationError) as err:
        job(**{"skills": ["Python"], **kw})
    return err.value.context["field"]


# JobRequirementInput.required_skills count: BVA on [1, 50]
@pytest.mark.parametrize(
    ("count", "valid"),
    [(0, False), (1, True), (2, True), (49, True), (50, True), (51, False)],
    ids=["BB-FR10-01", "BB-FR10-02", "BB-FR10-03", "BB-FR10-04", "BB-FR10-05", "BB-FR10-06"],
)
def test_required_skills_count_boundaries(count, valid):  # BB-FR10-01..06
    skills = [f"skill{i}" for i in range(count)]
    if valid:
        assert len(job(skills).required_skills) == count
    else:
        assert rejects_job(skills=skills) == "required_skills"


# required_skills entries: EP on blank / non-blank
@pytest.mark.parametrize(
    "skills",
    [[""], ["   "], ["Python", ""], ["Python", "\t"], ["Python", None]],
    ids=["BB-FR10-07", "BB-FR10-08", "BB-FR10-09", "BB-FR10-10", "BB-FR10-11"],
)
def test_blank_skill_entry_rejected(skills):  # BB-FR10-07..11
    assert rejects_job(skills=skills) == "required_skills"


def test_padded_skill_entry_accepted():  # BB-FR10-12 (valid class: text with surrounding spaces)
    assert job([" Python "]).required_skills == (" Python ",)


@pytest.mark.parametrize(("job_id", "title"), [("", "Backend"), ("job-1", "")], ids=["BB-FR10-13", "BB-FR10-14"])
def test_missing_job_id_or_title_rejected(job_id, title):  # BB-FR10-13..14
    assert rejects_job(job_id=job_id, title=title) == "id"


# BB-DEF-04 fixed in pipeline/core/inputs.py (was a strict xfail at M2 test design)
def test_whitespace_only_job_title_rejected():  # BB-FR10-15
    rejects_job(title="   ")


# RunConfig: BVA on the lower bound of each count/interval field
@pytest.mark.parametrize(
    ("field", "value", "valid"),
    [
        ("max_requests_per_source", 0, False),
        ("max_requests_per_source", 1, True),
        ("min_interval_seconds", -0.01, False),
        ("min_interval_seconds", 0.0, True),
        ("min_interval_seconds", 2.0, True),
        ("extraction_workers", 0, False),
        ("extraction_workers", 1, True),
        ("max_retries", 1, True),
        ("max_retries", 2, True),
    ],
    ids=[f"BB-FR05-{i:02d}" for i in range(1, 6)] + ["BB-FR07-01", "BB-FR07-02", "BB-FR05-06", "BB-FR05-07"],
)
def test_run_config_field_boundaries(field, value, valid):  # BB-FR05-01..07, BB-FR07-01..02
    if valid:
        assert getattr(RunConfig(**{field: value}), field) == value
    else:
        with pytest.raises(ValidationError) as err:
            RunConfig(**{field: value})
        assert err.value.context["field"] == field


def test_link_threshold_nan_rejected():  # BB-FR09-01 (invalid class: not a number)
    with pytest.raises(ValidationError):
        RunConfig(link_threshold=math.nan)


# BB-DEF-01 fixed in pipeline/core/inputs.py (was a strict xfail at M2 test design)
@pytest.mark.parametrize(
    ("field", "value"),
    [("max_retries", 2.5), ("extraction_workers", 1.5), ("max_requests_per_source", 1.5)],
    ids=["BB-FR05-08", "BB-FR07-03", "BB-FR05-09"],
)
def test_run_config_non_integer_count_rejected(field, value):  # BB-FR05-08, BB-FR07-03, BB-FR05-09
    with pytest.raises(ValidationError):
        RunConfig(**{field: value})


# BB-DEF-02 fixed in pipeline/core/inputs.py (was a strict xfail at M2 test design)
def test_min_interval_nan_rejected():  # BB-FR05-10
    with pytest.raises(ValidationError):
        RunConfig(min_interval_seconds=math.nan)


@pytest.mark.parametrize("value", [1, 50], ids=["BB-NFR03-01", "BB-NFR03-02"])
def test_max_repos_valid_values_accepted(value):  # BB-NFR03-01..02
    assert RunConfig(max_repos=value).max_repos == value


# BB-DEF-03 fixed in pipeline/core/inputs.py (was a strict xfail at M2 test design)
def test_max_repos_negative_rejected():  # BB-NFR03-03
    with pytest.raises(ValidationError):
        RunConfig(max_repos=-1)


@pytest.mark.parametrize(
    ("value", "valid"),
    [(0, True), (100, True), (101, False), (True, False)],
    ids=["BB-NFR03-04", "BB-NFR03-05", "BB-NFR03-06", "BB-NFR03-07"],
)
def test_max_repos_upper_boundary_and_type(value, valid):  # BB-NFR03-04..07: one GitHub page holds 100 repos
    if valid:
        assert RunConfig(max_repos=value).max_repos == value
    else:
        with pytest.raises(ValidationError):
            RunConfig(max_repos=value)

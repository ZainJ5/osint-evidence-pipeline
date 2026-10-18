"""FR-01 registration input: Equivalence Partitioning (EP) and Boundary Value Analysis (BVA)."""

import pytest

from pipeline.core.errors import ValidationError
from pipeline.core.inputs import MAX_RESUME_CHARS, CandidateInput, RunConfig

VALID = {"name": "Octo Developer", "email": "octo@example.org", "resume_text": "Python developer.", "handles": {}}


def candidate(**overrides) -> CandidateInput:
    return CandidateInput(**{**VALID, **overrides})


def rejects(field: str, **overrides) -> None:
    with pytest.raises(ValidationError) as err:
        candidate(**overrides)
    assert err.value.context["field"] == field


# Name length: BVA on [1, 200]
def test_name_length_0_rejected():  # BB-FR01-01
    rejects("name", name="")


def test_name_length_1_accepted():  # BB-FR01-02
    assert candidate(name="A").name == "A"


def test_name_length_200_accepted():  # BB-FR01-03
    assert len(candidate(name="a" * 200).name) == 200


def test_name_length_201_rejected():  # BB-FR01-04
    rejects("name", name="a" * 201)


def test_name_whitespace_only_rejected():  # BB-FR01-05 (EP: blank class)
    rejects("name", name="   ")


# Email: EP valid / invalid classes
@pytest.mark.parametrize("email", ["octo@example.org", "first.last+tag@uni.edu.pk"])
def test_email_valid_class_accepted(email):  # BB-FR01-06
    assert candidate(email=email).email == email


@pytest.mark.parametrize(
    "email", ["", "octo.example.org", "octo@", "@example.org", "octo@example", "oc to@example.org"]
)
def test_email_invalid_class_rejected(email):  # BB-FR01-07
    rejects("email", email=email)


# GitHub handle: BVA on 39 characters, leading hyphen
def test_github_handle_length_39_accepted():  # BB-FR01-08
    handle = "a" * 39
    assert candidate(handles={"github": handle}).handles["github"] == handle


def test_github_handle_length_40_rejected():  # BB-FR01-09
    rejects("handles.github", handles={"github": "a" * 40})


def test_github_handle_leading_hyphen_rejected():  # BB-FR01-10
    rejects("handles.github", handles={"github": "-octo"})


def test_github_handle_inner_hyphen_accepted():  # BB-FR01-11
    assert candidate(handles={"github": "octo-dev"}).handles == {"github": "octo-dev"}


def test_unknown_source_rejected():  # BB-FR01-12
    rejects("handles", handles={"gitlab": "octo-dev"})


def test_all_three_known_sources_accepted():  # BB-FR01-13
    handles = {"github": "octo-dev", "codeforces": "octo_dev", "leetcode": "octo-dev"}
    assert candidate(handles=handles).handles == handles


# Resume length: BVA on [1, 50000]
def test_resume_length_max_accepted():  # BB-FR01-14
    assert len(candidate(resume_text="x" * MAX_RESUME_CHARS).resume_text) == 50_000


def test_resume_length_max_plus_one_rejected():  # BB-FR01-15
    rejects("resume_text", resume_text="x" * (MAX_RESUME_CHARS + 1))


def test_resume_empty_rejected():  # BB-FR01-16
    rejects("resume_text", resume_text="")


# RunConfig: BVA on max_retries [0, 3] and link_threshold [0, 1]
@pytest.mark.parametrize(
    ("max_retries", "valid"),
    [(-1, False), (0, True), (3, True), (4, False)],
    ids=["BB-FR01-17", "BB-FR01-18", "BB-FR01-19", "BB-FR01-20"],
)
def test_run_config_max_retries_boundaries(max_retries, valid):  # BB-FR01-17..20
    if valid:
        assert RunConfig(max_retries=max_retries).max_retries == max_retries
    else:
        with pytest.raises(ValidationError):
            RunConfig(max_retries=max_retries)


@pytest.mark.parametrize(
    ("threshold", "valid"),
    [(-0.01, False), (0.0, True), (1.0, True), (1.01, False)],
    ids=["BB-FR01-21", "BB-FR01-22", "BB-FR01-23", "BB-FR01-24"],
)
def test_run_config_link_threshold_boundaries(threshold, valid):  # BB-FR01-21..24
    if valid:
        assert RunConfig(link_threshold=threshold).link_threshold == threshold
    else:
        with pytest.raises(ValidationError):
            RunConfig(link_threshold=threshold)

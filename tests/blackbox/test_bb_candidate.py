"""FR-01 CandidateInput: only the partitions and boundaries that tests/unit/collection/test_candidate_input.py
(BB-FR01-01..24) does not already cover: Codeforces handle length [3, 24], LeetCode handle length [1, 30],
resume length 1, zero handles, and a missing handle value.
"""

import pytest

from pipeline.core.errors import ValidationError
from pipeline.core.inputs import CandidateInput

VALID = {"name": "Octo Developer", "email": "octo@example.org", "resume_text": "Python developer.", "handles": {}}


def candidate(**overrides) -> CandidateInput:
    return CandidateInput(**{**VALID, **overrides})


@pytest.mark.parametrize(
    ("source", "handle", "valid"),
    [
        ("codeforces", "ab", False),
        ("codeforces", "abc", True),
        ("codeforces", "a" * 24, True),
        ("codeforces", "a" * 25, False),
        ("codeforces", "octo@dev", False),
        ("leetcode", "a", True),
        ("leetcode", "a" * 30, True),
        ("leetcode", "a" * 31, False),
        ("leetcode", "", False),
        ("github", None, False),
    ],
    ids=[f"BB-FR01-{i}" for i in range(25, 35)],
)
def test_handle_rules_per_source(source, handle, valid):  # BB-FR01-25..34
    if valid:
        assert candidate(handles={source: handle}).handles[source] == handle
    else:
        with pytest.raises(ValidationError) as err:
            candidate(handles={source: handle})
        assert err.value.context["field"] == f"handles.{source}"


def test_resume_length_1_accepted():  # BB-FR01-35
    assert candidate(resume_text="x").resume_text == "x"


def test_zero_handles_accepted():  # BB-FR01-36 (FR-01: "zero or more handles")
    assert candidate(handles={}).handles == {}

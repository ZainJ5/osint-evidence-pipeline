import uuid

import pytest

from pipeline.adapters.fakes import FakeLLMProvider
from pipeline.core.errors import ScoringError
from pipeline.core.ports import LLMProvider
from pipeline.core.scoring.claims import CLAIM_NAMESPACE, CLAIM_SCHEMA, ClaimExtractor

RESUME = """Ilsa Maryam
Backend developer with 3 years of Python.
Codeforces rating 1600
Skills: Docker, Go
"""


class StubLLM(LLMProvider):
    def __init__(self, output):
        self.output = output
        self.calls = []

    def complete(self, prompt, schema):
        self.calls.append((prompt, schema))
        return self.output


def test_extracts_claims_from_sample_resume_with_fake_llm():
    claims = ClaimExtractor(FakeLLMProvider()).extract("cand-1", RESUME)
    summary = [(c.kind, c.subject, c.years, c.rating) for c in claims]
    assert summary == [
        ("skill", "Python", 3.0, None),
        ("rating", "codeforces", None, 1600),
        ("skill", "Docker", None, None),
        ("skill", "Go", None, None),
    ]
    assert all(c.candidate_id == "cand-1" for c in claims)


def test_prompt_contains_resume_and_schema_is_passed():
    llm = StubLLM({"claims": []})
    ClaimExtractor(llm).extract("cand-1", RESUME)
    prompt, schema = llm.calls[0]
    assert RESUME in prompt
    assert schema == CLAIM_SCHEMA


def test_claim_ids_are_deterministic_uuid5():
    first = ClaimExtractor(FakeLLMProvider()).extract("cand-1", RESUME)
    second = ClaimExtractor(FakeLLMProvider()).extract("cand-1", RESUME)
    assert [c.id for c in first] == [c.id for c in second]
    assert first[0].id == str(uuid.uuid5(CLAIM_NAMESPACE, "cand-1:skill:python"))


def test_claim_ids_differ_per_candidate():
    one = ClaimExtractor(FakeLLMProvider()).extract("cand-1", RESUME)
    two = ClaimExtractor(FakeLLMProvider()).extract("cand-2", RESUME)
    assert {c.id for c in one}.isdisjoint({c.id for c in two})


def test_invalid_items_are_dropped():
    output = {
        "claims": [
            {"text": "Python", "kind": "skill", "subject": "Python"},
            {"text": "x", "kind": "degree", "subject": "BSc"},
            {"text": "x", "kind": "skill", "subject": ""},
            {"text": "x", "kind": "rating", "subject": "codeforces"},
            {"text": "x", "kind": "rating", "subject": "codeforces", "rating": "high"},
            {"text": "x", "kind": "skill", "subject": "Go", "years": -1},
            "not a dict",
        ]
    }
    claims = ClaimExtractor(StubLLM(output)).extract("cand-1", RESUME)
    assert [c.subject for c in claims] == ["Python"]


def test_duplicate_claims_keep_the_first():
    output = {
        "claims": [
            {"text": "3 years of Python", "kind": "skill", "subject": "Python", "years": 3},
            {"text": "python", "kind": "skill", "subject": "python"},
        ]
    }
    claims = ClaimExtractor(StubLLM(output)).extract("cand-1", RESUME)
    assert len(claims) == 1
    assert claims[0].years == 3.0


@pytest.mark.parametrize("output", [None, [], {"items": []}, {"claims": "Python"}, "claims"])
def test_bad_top_level_output_raises(output):
    with pytest.raises(ScoringError) as info:
        ClaimExtractor(StubLLM(output)).extract("cand-1", RESUME)
    assert info.value.code == "LLM_BAD_OUTPUT"


def test_solved_claims_are_parsed_with_platform_subject():
    output = {
        "claims": [
            {"text": "solved 500+ problems on LeetCode", "kind": "solved", "subject": " LeetCode ", "solved": 500}
        ]
    }
    claim = ClaimExtractor(StubLLM(output)).extract("cand-1", RESUME)[0]
    assert (claim.kind, claim.subject, claim.solved, claim.rating, claim.years) == (
        "solved",
        "leetcode",
        500,
        None,
        None,
    )
    assert claim.id == str(uuid.uuid5(CLAIM_NAMESPACE, "cand-1:solved:leetcode"))


@pytest.mark.parametrize(
    "item",
    [
        {"kind": "solved", "subject": "leetcode"},
        {"kind": "solved", "subject": "leetcode", "solved": 0},
        {"kind": "solved", "subject": "leetcode", "solved": 2.5},
        {"kind": "solved", "subject": "leetcode", "solved": True},
        {"kind": "solved", "subject": "hackerrank", "solved": 10},
        {"kind": "rating", "subject": "atcoder", "rating": 1500},
        {"kind": "rating", "subject": "codeforces", "rating": None},
    ],
)
def test_invalid_platform_claims_are_dropped(item):
    assert ClaimExtractor(StubLLM({"claims": [{"text": "x", **item}]})).extract("cand-1", RESUME) == []


def test_null_optional_fields_from_strict_schemas_are_accepted():
    item = {"text": "Docker", "kind": "skill", "subject": "Docker", "years": None, "rating": None, "solved": None}
    claim = ClaimExtractor(StubLLM({"claims": [item]})).extract("cand-1", RESUME)[0]
    assert (claim.subject, claim.years) == ("Docker", None)


def test_later_duplicate_with_years_replaces_one_without():
    output = {
        "claims": [
            {"text": "Python", "kind": "skill", "subject": "Python"},
            {"text": "3 years of Python", "kind": "skill", "subject": "python", "years": 3},
        ]
    }
    claims = ClaimExtractor(StubLLM(output)).extract("cand-1", RESUME)
    assert [(c.text, c.years) for c in claims] == [("3 years of Python", 3.0)]

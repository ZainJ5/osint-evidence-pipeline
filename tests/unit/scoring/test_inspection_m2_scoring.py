"""Regression tests for scoring defects found in the SE431 M2 Fagan inspection (INS ids in the report)."""

import math

import pytest

from pipeline.core.errors import ScoringError
from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import Claim, EvidenceNode
from pipeline.core.scoring.rules import SkillClaimRule
from pipeline.core.scoring.scoring import WeightedEvidenceScoring

RULE = SkillClaimRule(SkillNormalizer())


def skill(node_id, first, last):
    value = {"name": "Python", "first_seen": first, "last_seen": last}
    return EvidenceNode(node_id, "run-1", "cand-1", "snap-1", "github", "octo", "skill", value, "$")


def claim(years):
    return Claim("claim-1", "cand-1", f"{years} years of Python", "skill", "Python", years=years)


@pytest.mark.parametrize(
    ("years", "first", "last", "label"),
    [
        (2.5, "2020-01-01", "2022-12-01", "supported"),  # 2.9 years observed: was 'partial' (floored to 2)
        (2.5, "2020-01-01", "2022-03-01", "partially_supported"),  # 2.16 years observed
        (2, "2021-01-01", "2023-01-01", "supported"),  # whole-year anniversary still counts
        (0.5, "2024-01-01", "2024-08-01", "supported"),  # 7 months observed: was 'partial' (0 whole years)
    ],
)
def test_ins05_fractional_claimed_years_compare_with_elapsed_time(years, first, last, label):
    verdict = RULE.verify(claim(years), [skill("n1", first, last)], "run-1")
    assert verdict.label == label


@pytest.mark.parametrize("bad", [math.nan, math.inf])
def test_ins08_non_finite_weights_are_rejected(bad):
    with pytest.raises(ScoringError):
        WeightedEvidenceScoring({"verified_skills": bad})

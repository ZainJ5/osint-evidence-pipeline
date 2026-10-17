"""FR-13 score total bounds and weight validation.

Referenced from tests/unit/scoring/test_scoring.py: total 0 (test_all_zero_scores_zero), total 100
(test_all_perfect_scores_one_hundred) and invalid weights negative / unknown / all zero / string
(test_invalid_weights_raise). New here: BVA on the full-score constants (200 commits, rating 2400), clamping of
out-of-range inputs, and the weight boundaries 0, just below 0, bool, None and a tiny positive sum.
"""

import pytest

from pipeline.core.errors import ScoringError
from pipeline.core.models import EvidenceNode, MatchResult, SkillMatch, Verdict
from pipeline.core.scoring.scoring import WeightedEvidenceScoring

ZERO = {"verified_skills": 0, "contribution_depth": 0, "competitive_programming": 0, "requirement_match": 0}


def node(node_id, kind, **value):
    return EvidenceNode(node_id, "run-1", "cand-1", "snap", "github", "octo", kind, value, "$")


def report(evidence=(), verdicts=(), match=None, weights=None):
    match = match or MatchResult("job-1", ())
    return WeightedEvidenceScoring(weights).score("run-1", "cand-1", "job-1", list(verdicts), match, list(evidence))


def component(rep, name):
    return next(c.value for c in rep.components if c.name == name)


@pytest.mark.parametrize(
    ("commits", "value"),
    [(0, 0.0), (199, 0.995), (200, 1.0), (201, 1.0)],
    ids=["BB-FR13-01", "BB-FR13-02", "BB-FR13-03", "BB-FR13-04"],
)
def test_contribution_depth_saturates_at_200_commits(commits, value):  # BB-FR13-01..04
    assert component(report([node("c1", "contribution", commits=commits)]), "contribution_depth") == value


@pytest.mark.parametrize(
    ("rating", "value"),
    [(-50, 0.0), (2399, 0.9996), (2400, 1.0), (2401, 1.0)],
    ids=["BB-FR13-05", "BB-FR13-06", "BB-FR13-07", "BB-FR13-08"],
)
def test_competitive_programming_saturates_at_2400(rating, value):  # BB-FR13-05..08
    rep = report([node("a1", "achievement", platform="codeforces", rating=rating, max_rating=None)])
    assert component(rep, "competitive_programming") == value


def test_total_never_exceeds_100_with_out_of_range_inputs():  # BB-FR13-09
    evidence = [
        node("c1", "contribution", commits=10_000),
        node("a1", "achievement", platform="codeforces", rating=4000, max_rating=None),
        node("s1", "skill", name="Python"),
    ]
    verdicts = [Verdict("k1", "run-1", "cand-1", "supported", ("s1",), "ok")]
    match = MatchResult("job-1", (SkillMatch("python", ("s1",)),))
    assert report(evidence, verdicts, match, weights={k: 10 for k in ZERO}).total == 100.0


def test_unknown_verdict_label_counts_as_zero_not_negative():  # BB-FR13-10
    assert report(verdicts=[Verdict("k1", "run-1", "cand-1", "invented", (), "?")]).total == 0.0


@pytest.mark.parametrize(
    "weights",
    [{"verified_skills": 0}, {**ZERO, "requirement_match": 1e-9}, {"verified_skills": 5}],
    ids=["BB-FR13-11", "BB-FR13-12", "BB-FR13-13"],
)
def test_weight_valid_boundaries_accepted(weights):  # BB-FR13-11..13
    assert 0.0 <= report(weights=weights).total <= 100.0


@pytest.mark.parametrize(
    "weights",
    [{"verified_skills": -0.0001}, {"verified_skills": True}, {"verified_skills": None}],
    ids=["BB-FR13-14", "BB-FR13-15", "BB-FR13-16"],
)
def test_weight_invalid_classes_rejected(weights):  # BB-FR13-14..16
    with pytest.raises(ScoringError):
        WeightedEvidenceScoring(weights)


def test_single_tiny_positive_weight_gives_that_component_alone():  # BB-FR13-17
    match = MatchResult("job-1", (SkillMatch("python", ("s1",)), SkillMatch("go", ())))
    assert report(match=match, weights={**ZERO, "requirement_match": 1e-9}).total == 50.0

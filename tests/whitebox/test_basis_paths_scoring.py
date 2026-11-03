"""White-box basis-path tests for M5 scoring: SkillClaimRule.verify (FR-12, QR-01) and _validated (FR-13).

Design, CFGs and path lists: docs/milestone2/whitebox-test-design.md, sections 3 and 4.
SkillClaimRule.verify: V(G) = 4 (WB-SCO-01..04, plus WB-SCO-05 for the conditional expression mccabe ignores).
_validated (via WeightedEvidenceScoring): V(G) = 4 (WB-SCO-06..09, plus WB-SCO-10/11 for the compound predicate).
"""

import pytest

from pipeline.core.errors import ScoringError
from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import Claim, EvidenceNode, MatchResult
from pipeline.core.scoring.rules import SkillClaimRule
from pipeline.core.scoring.scoring import DEFAULT_WEIGHTS, WeightedEvidenceScoring

RULE = SkillClaimRule(SkillNormalizer())


def node(node_id, kind="skill", **value):
    return EvidenceNode(node_id, "run-1", "cand-1", "snap-1", "github", "octo", kind, value, "$")


def claim(subject="Python", years=None):
    return Claim("claim-1", "cand-1", f"{years} years of {subject}", "skill", subject, years=years)


# ---- SkillClaimRule.verify -----------------------------------------------------------------------------------


def test_wb_sco_01_no_matching_skill_node_is_unsupported():
    """WB-SCO-01, verify P1: 1-2-3-X. Only a Go skill and a project that does not mention Python exist."""
    evidence = [node("n1", name="Go"), node("p1", kind="project", name="notes", description="Rust CLI")]
    verdict = RULE.verify(claim(years=2), evidence, "run-1")
    assert verdict.label == "unsupported"
    assert verdict.evidence_node_ids == ()
    assert verdict.rationale == "no 'python' skill evidence found"


def test_wb_sco_02_skill_without_claimed_duration_is_supported():
    """WB-SCO-02, verify P2: 1-2-4-5-X. Alias 'py' normalises to python; no years claimed."""
    verdict = RULE.verify(claim(years=None), [node("n1", name="py")], "run-1")
    assert verdict.label == "supported"
    assert verdict.evidence_node_ids == ("n1",)
    assert verdict.rationale.endswith("no duration claimed")


def test_wb_sco_03_years_claimed_but_no_usable_dates_is_partial():
    """WB-SCO-03, verify P3: 1-2-4-6-7-X. One date missing, one unparseable -> no dates to check."""
    evidence = [node("n1", name="Python", first_seen=None, last_seen="not-a-date")]
    verdict = RULE.verify(claim(years=2), evidence, "run-1")
    assert verdict.label == "partially_supported"
    assert verdict.rationale == "1 'python' skill node(s) but no dates to check 2 claimed year(s)"


def test_wb_sco_04_observed_years_equal_to_claim_is_supported():
    """WB-SCO-04, verify P4: 1-2-4-6-8-X. Exactly 2 whole years observed for a 2-year claim (boundary)."""
    evidence = [node("n1", name="Python", first_seen="2020-01-01T00:00:00Z", last_seen="2022-01-01T00:00:00Z")]
    verdict = RULE.verify(claim(years=2), evidence, "run-1")
    assert verdict.label == "supported"
    assert "observed 2 whole year(s) from 2020-01-01 to 2022-01-01 vs 2 claimed" in verdict.rationale


@pytest.mark.parametrize(
    "years, first, last, label",
    [
        (2.5, "2020-01-01", "2022-12-01", "supported"),  # whole years 2 < 2.5, elapsed 2.92 >= 2.5
        (2, "2020-01-02", "2022-01-01", "partially_supported"),  # whole years 1, elapsed 2.00 - 1 day < 2
    ],
)
def test_wb_sco_05_conditional_expression_in_node_8(years, first, last, label):
    """WB-SCO-05 (node 8 `observed >= years or elapsed >= years`, ignored by mccabe): remaining condition outcomes.

    WB-SCO-04 covers the first operand true; these cover (false, true) and (false, false).
    """
    evidence = [node("n1", name="Python", first_seen=first, last_seen=last)]
    verdict = RULE.verify(claim(years=years), evidence, "run-1")
    assert verdict.label == label


# ---- _validated (weights) ------------------------------------------------------------------------------------


def weights_of(scoring):
    report = scoring.score("run-1", "cand-1", "job-1", [], MatchResult("job-1", ()), [])
    return {c.name: c.weight for c in report.components}


def test_wb_sco_06_unknown_component_is_rejected():
    """WB-SCO-06, _validated P1: 1-2-3-X."""
    with pytest.raises(ScoringError, match="unknown score components"):
        WeightedEvidenceScoring({"charisma": 1.0})


def test_wb_sco_07_negative_weight_is_rejected():
    """WB-SCO-07, _validated P2: 1-2-4-5-X."""
    with pytest.raises(ScoringError, match="non-negative"):
        WeightedEvidenceScoring({"verified_skills": -0.01})


def test_wb_sco_08_all_zero_weights_are_rejected():
    """WB-SCO-08, _validated P3: 1-2-4-6-7-X."""
    with pytest.raises(ScoringError, match="sum to more than 0"):
        WeightedEvidenceScoring(dict.fromkeys(DEFAULT_WEIGHTS, 0))


def test_wb_sco_09_valid_weights_are_merged_over_the_defaults():
    """WB-SCO-09, _validated P4: 1-2-4-6-8-X. None keeps defaults; a partial dict overrides by name."""
    assert weights_of(WeightedEvidenceScoring()) == DEFAULT_WEIGHTS
    overridden = weights_of(WeightedEvidenceScoring({"requirement_match": 0.5}))
    assert overridden == {**DEFAULT_WEIGHTS, "requirement_match": 0.5}


@pytest.mark.parametrize(
    "weight, accepted",
    [(True, False), ("0.3", False), (None, False), (0, True), (0.0, True)],
)
def test_wb_sco_10_compound_weight_predicate(weight, accepted):
    """WB-SCO-10 (condition coverage, node 4): not-a-number, is-a-bool and negative operands each decide once."""
    weights = {"verified_skills": weight}
    if accepted:
        assert weights_of(WeightedEvidenceScoring(weights))["verified_skills"] == 0
    else:
        with pytest.raises(ScoringError):
            WeightedEvidenceScoring(weights)


@pytest.mark.parametrize("weight", [float("nan"), float("inf")])
def test_wb_sco_11_non_finite_weight_is_rejected(weight):
    """WB-SCO-11 (node 4, boundary of 'number'): NaN/inf must be rejected. Anomaly WB-DEF-01 = INS-08 (fixed)."""
    with pytest.raises(ScoringError, match="finite non-negative"):
        WeightedEvidenceScoring({"verified_skills": weight})

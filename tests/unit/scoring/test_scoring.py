import pytest

from pipeline.core.errors import ScoringError
from pipeline.core.models import EvidenceNode, MatchResult, ScoreComponent, ScoreReport, SkillMatch, Verdict
from pipeline.core.scoring.scoring import DEFAULT_WEIGHTS, ScoreCalculator, ScoringStrategy, WeightedEvidenceScoring


def node(node_id, kind, **value):
    return EvidenceNode(node_id, "run-1", "cand-1", "snap", "github", "octo", kind, value, "$")


def verdict(label, *ids):
    return Verdict(f"claim-{label}", "run-1", "cand-1", label, ids, "because")


EVIDENCE = [
    node("c1", "contribution", repo="a", commits=150, first=None, last=None),
    node("c2", "contribution", repo="b", commits=100, first=None, last=None),
    node("a1", "achievement", platform="codeforces", rating=2000, max_rating=2500, solved=300),
    node("a2", "achievement", platform="leetcode", rating=None, max_rating=None, solved=50),
    node("s1", "skill", name="Python", first_seen=None, last_seen=None),
]
PERFECT_MATCH = MatchResult("job-1", (SkillMatch("python", ("s1",)), SkillMatch("go", ("s1", "p1"))))
PERFECT_VERDICTS = [verdict("supported", "s1")]


def components(report):
    return {c.name: c for c in report.components}


def score(verdicts, match, evidence, weights=None):
    return WeightedEvidenceScoring(weights).score("run-1", "cand-1", "job-1", verdicts, match, evidence)


def test_all_zero_scores_zero():
    report = score([], MatchResult("job-1", ()), [])
    assert report.total == 0.0
    assert all(c.value == 0.0 for c in report.components)


def test_all_perfect_scores_one_hundred():
    report = score(PERFECT_VERDICTS, PERFECT_MATCH, EVIDENCE)
    assert report.total == 100.0
    assert all(c.value == 1.0 for c in report.components)


def test_component_values_and_evidence():
    verdicts = [verdict("supported", "s1"), verdict("partially_supported", "a1"), verdict("unsupported")]
    match = MatchResult("job-1", (SkillMatch("python", ("s1",)), SkillMatch("rust", ())))
    evidence = [
        node("c1", "contribution", repo="a", commits=50, first=None, last=None),
        node("a1", "achievement", platform="leetcode", rating=1200, max_rating=None, solved=5),
    ]
    parts = components(score(verdicts, match, evidence))
    assert parts["verified_skills"].value == 0.5
    assert parts["verified_skills"].evidence_node_ids == ("a1", "s1")
    assert parts["contribution_depth"].value == 0.25
    assert parts["contribution_depth"].evidence_node_ids == ("c1",)
    assert parts["competitive_programming"].value == 0.5
    assert parts["competitive_programming"].evidence_node_ids == ("a1",)
    assert parts["requirement_match"].value == 0.5
    assert parts["requirement_match"].evidence_node_ids == ("s1",)


def test_total_is_weighted_mean_scaled_to_100():
    match = MatchResult("job-1", (SkillMatch("python", ("s1",)), SkillMatch("rust", ())))
    report = score([], match, [])
    assert report.total == 15.0  # 100 * 0.30 * 0.5 / 1.0


def test_report_carries_ids_weights_and_verdicts():
    report = score(PERFECT_VERDICTS, PERFECT_MATCH, EVIDENCE)
    assert (report.run_id, report.candidate_id, report.job_id) == ("run-1", "cand-1", "job-1")
    assert {c.name: c.weight for c in report.components} == DEFAULT_WEIGHTS
    assert report.verdicts == tuple(PERFECT_VERDICTS)


def test_every_positive_component_cites_evidence():  # QR-03
    verdicts = [verdict("supported", "s1"), verdict("partially_supported", "a1")]
    match = MatchResult("job-1", (SkillMatch("python", ("s1",)), SkillMatch("rust", ())))
    for report in (score(verdicts, match, EVIDENCE), score(PERFECT_VERDICTS, PERFECT_MATCH, EVIDENCE)):
        for component in report.components:
            assert component.value == 0 or component.evidence_node_ids, component.name


def test_custom_weights_override_defaults():
    weights = {"verified_skills": 0, "contribution_depth": 0, "competitive_programming": 0, "requirement_match": 1}
    match = MatchResult("job-1", (SkillMatch("python", ("s1",)), SkillMatch("rust", ())))
    assert score(PERFECT_VERDICTS, match, EVIDENCE, weights).total == 50.0
    assert score(PERFECT_VERDICTS, match, EVIDENCE, {"requirement_match": 0.3}).total < 100.0


@pytest.mark.parametrize(
    "weights",
    [
        {"verified_skills": -0.1},
        {"popularity": 0.2},
        {"verified_skills": 0, "contribution_depth": 0, "competitive_programming": 0, "requirement_match": 0},
        {"verified_skills": "high"},
    ],
)
def test_invalid_weights_raise(weights):
    with pytest.raises(ScoringError):
        WeightedEvidenceScoring(weights)


class StubStrategy(ScoringStrategy):
    def score(self, run_id, candidate_id, job_id, verdicts, match, evidence):
        return ScoreReport(run_id, candidate_id, job_id, 42.0, (ScoreComponent("stub", 1.0, 0.42, ("x",)),))


def test_calculator_delegates_to_the_injected_strategy():
    report = ScoreCalculator(StubStrategy()).calculate("run-1", "cand-1", "job-1", [], PERFECT_MATCH, [])
    assert report.total == 42.0
    assert report.components[0].name == "stub"


def test_calculator_with_default_strategy():
    calculator = ScoreCalculator(WeightedEvidenceScoring())
    report = calculator.calculate("run-1", "cand-1", "job-1", PERFECT_VERDICTS, PERFECT_MATCH, EVIDENCE)
    assert report.total == 100.0

import pytest

from pipeline.core.models import Claim, EvidenceNode
from pipeline.core.scoring.rules import RatingClaimRule


def achievement(node_id, platform="codeforces", rating=None, max_rating=None):
    value = {"platform": platform, "rating": rating, "max_rating": max_rating, "solved": None}
    return EvidenceNode(node_id, "run-1", "cand-1", "snap-1", platform, "octo", "achievement", value, "$")


def claim(rating=1600, platform="codeforces"):
    return Claim("claim-1", "cand-1", f"{platform} rating {rating}", "rating", platform, rating=rating)


RULE = RatingClaimRule()


@pytest.mark.parametrize(
    "best, label",
    [
        (1601, "supported"),
        (1600, "supported"),
        (1599, "partially_supported"),
        (1280, "partially_supported"),
        (1279, "unsupported"),
    ],
)
def test_rating_boundaries(best, label):
    verdict = RULE.verify(claim(1600), [achievement("a1", rating=best)], "run-1")
    assert verdict.label == label


def test_max_rating_counts_as_best():
    verdict = RULE.verify(claim(1600), [achievement("a1", rating=1400, max_rating=1650)], "run-1")
    assert verdict.label == "supported"
    assert verdict.evidence_node_ids == ("a1",)
    assert "1650" in verdict.rationale


def test_other_platform_is_not_evidence():
    verdict = RULE.verify(claim(1600), [achievement("a1", platform="leetcode", rating=2000)], "run-1")
    assert verdict.label == "unsupported"
    assert verdict.evidence_node_ids == ()


def test_achievement_without_rating_is_unsupported():
    verdict = RULE.verify(claim(1600), [achievement("a1")], "run-1")
    assert verdict.label == "unsupported"
    assert verdict.evidence_node_ids == ()


def test_evidence_lists_every_node_used():
    nodes = [achievement("a2", rating=1500), achievement("a1", max_rating=1700)]
    verdict = RULE.verify(claim(1600), nodes, "run-1")
    assert verdict.evidence_node_ids == ("a1", "a2")
    assert (verdict.candidate_id, verdict.run_id) == ("cand-1", "run-1")
    assert RULE.kind == "rating"

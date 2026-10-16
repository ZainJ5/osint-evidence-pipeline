import pytest

from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import Claim, EvidenceNode
from pipeline.core.scoring.rules import RatingClaimRule, SkillClaimRule, SolvedClaimRule, default_rules


def achievement(node_id, platform="leetcode", solved=None, **extra):
    value = {"platform": platform, "rating": None, "max_rating": None, "solved": solved, **extra}
    return EvidenceNode(node_id, "run-1", "cand-1", "snap-1", platform, "octo", "achievement", value, "$")


def claim(solved=500, platform="leetcode"):
    return Claim("claim-1", "cand-1", f"solved {solved} problems on {platform}", "solved", platform, solved=solved)


RULE = SolvedClaimRule()


@pytest.mark.parametrize(
    ("best", "label"),
    [
        (501, "supported"),
        (500, "supported"),
        (499, "partially_supported"),
        (400, "partially_supported"),
        (399, "unsupported"),
    ],
)
def test_solved_boundaries(best, label):
    verdict = RULE.verify(claim(500), [achievement("a1", solved=best)], "run-1")
    assert verdict.label == label
    assert verdict.rationale.startswith(f"{best} leetcode problems solved observed, ")
    assert "claimed 500" in verdict.rationale


def test_best_count_over_several_nodes_and_all_are_cited():
    nodes = [
        achievement("a2", solved=120),
        achievement("a1", solved=510),
        achievement("a3", platform="codeforces", solved=900),
    ]
    verdict = RULE.verify(claim(500), nodes, "run-1")
    assert verdict.label == "supported"
    assert verdict.evidence_node_ids == ("a1", "a2")


def test_no_solved_count_is_unsupported():
    verdict = RULE.verify(claim(300, "codeforces"), [achievement("a1", platform="codeforces")], "run-1")
    assert verdict.label == "unsupported"
    assert verdict.evidence_node_ids == ()
    assert verdict.rationale == "no codeforces solved-problem evidence found"


def test_rating_rationale_names_the_rank():
    node = achievement("a1", platform="codeforces", rank="expert")
    node.value.update(rating=1650, max_rating=1720)
    rating_claim = Claim("c2", "cand-1", "Codeforces Expert", "rating", "codeforces", rating=1600)
    verdict = RatingClaimRule().verify(rating_claim, [node], "run-1")
    assert verdict.rationale == "best observed codeforces rating 1720 (rank expert) meets the claimed 1600"


@pytest.mark.parametrize(
    ("solved", "claimed", "label", "text"),
    [
        (500, 500, "supported", "500 leetcode problems solved observed, meets the claimed 500"),
        (
            400,
            500,
            "partially_supported",
            "400 leetcode problems solved observed, 80% of the claimed 500 (partial from 80%)",
        ),
        (399, 500, "unsupported", "399 leetcode problems solved observed, only 79.8% of the claimed 500 (below 80%)"),
        (
            499,
            500,
            "partially_supported",
            "499 leetcode problems solved observed, 99.8% of the claimed 500 (partial from 80%)",
        ),
        (704, 2000, "unsupported", "704 leetcode problems solved observed, only 35.2% of the claimed 2000 (below 80%)"),
    ],
)
def test_rationale_wording_matches_the_verdict(solved, claimed, label, text):
    node = achievement("a1", platform="leetcode")
    node.value.update(solved=solved)
    solved_claim = Claim("c3", "cand-1", "LeetCode", "solved", "leetcode", solved=claimed)
    verdict = SolvedClaimRule().verify(solved_claim, [node], "run-1")
    assert (verdict.label, verdict.rationale) == (label, text)


def test_default_rules_cover_every_claim_kind():
    rules = default_rules(SkillNormalizer())
    assert [type(r) for r in rules] == [SkillClaimRule, RatingClaimRule, SolvedClaimRule]
    assert [r.kind for r in rules] == ["skill", "rating", "solved"]

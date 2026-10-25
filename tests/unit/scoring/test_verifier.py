import pytest

from pipeline.core.errors import ScoringError
from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import Claim, EvidenceNode
from pipeline.core.scoring.rules import RatingClaimRule, SkillClaimRule
from pipeline.core.scoring.verifier import ClaimVerifier

NODES = [
    EvidenceNode("s1", "run-1", "cand-1", "snap", "github", "octo", "skill", {"name": "Python"}, "$"),
    EvidenceNode(
        "a1",
        "run-1",
        "cand-1",
        "snap",
        "codeforces",
        "octo",
        "achievement",
        {"platform": "codeforces", "rating": 1700, "max_rating": None, "solved": 10},
        "$",
    ),
]


def verifier():
    return ClaimVerifier([SkillClaimRule(SkillNormalizer()), RatingClaimRule()])


def test_each_claim_goes_to_the_rule_for_its_kind():
    claims = [
        Claim("c1", "cand-1", "Python", "skill", "Python"),
        Claim("c2", "cand-1", "Codeforces rating 1600", "rating", "codeforces", rating=1600),
    ]
    verdicts = verifier().verify_all(claims, NODES, "run-1")
    assert [(v.claim_id, v.label, v.evidence_node_ids) for v in verdicts] == [
        ("c1", "supported", ("s1",)),
        ("c2", "supported", ("a1",)),
    ]


def test_unknown_claim_kind_raises():
    with pytest.raises(ScoringError):
        verifier().verify_all([Claim("c1", "cand-1", "BSc", "degree", "BSc")], NODES, "run-1")


def test_no_claims_gives_no_verdicts():
    assert verifier().verify_all([], NODES, "run-1") == []

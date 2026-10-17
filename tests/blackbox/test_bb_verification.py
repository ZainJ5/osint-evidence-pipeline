"""FR-12 claim verification rules.

Referenced from tests/unit/scoring/test_rating_rule.py::test_rating_boundaries (claim 1600: best 1601, 1600,
1599, 1280 = exactly 80 %, 1279) and tests/unit/scoring/test_skill_rule.py (equal, one less, no dates).
New here: an 80 % share that is not a whole number, no evidence at all, a missing claimed value, the case of the
platform name, and day-exact year boundaries for the duration rule.
"""

import pytest

from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import Claim, EvidenceNode
from pipeline.core.scoring.rules import RatingClaimRule, SkillClaimRule


def achievement(rating, platform="codeforces"):
    value = {"platform": platform, "rating": rating, "max_rating": None, "solved": None}
    return EvidenceNode("a1", "run-1", "cand-1", "snap-1", platform, "octo", "achievement", value, "$")


def rating_label(claimed, evidence, subject="codeforces"):
    claim = Claim("c1", "cand-1", f"{subject} rating {claimed}", "rating", subject, rating=claimed)
    return RatingClaimRule().verify(claim, evidence, "run-1").label


def skill(first=None, last=None):
    value = {"name": "Python", "first_seen": first, "last_seen": last}
    return EvidenceNode("s1", "run-1", "cand-1", "snap-1", "github", "octo", "skill", value, "$")


def skill_label(years, evidence):
    claim = Claim("c1", "cand-1", f"{years} years of Python", "skill", "Python", years=years)
    return SkillClaimRule(SkillNormalizer()).verify(claim, evidence, "run-1").label


# Rating rule: claimed 1601, so 80 % = 1280.8 is not a whole number
@pytest.mark.parametrize(
    ("best", "label"),
    [(1601, "supported"), (1281, "partially_supported"), (1280, "unsupported")],
    ids=["BB-FR12-01", "BB-FR12-02", "BB-FR12-03"],
)
def test_rating_rule_with_fractional_80_percent(best, label):  # BB-FR12-01..03
    assert rating_label(1601, [achievement(best)]) == label


@pytest.mark.parametrize(
    ("claimed", "evidence"),
    [(1600, []), (None, [achievement(2000)]), (0, [achievement(2000)])],
    ids=["BB-FR12-04", "BB-FR12-05", "BB-FR12-06"],
)
def test_rating_without_evidence_or_claimed_value_is_unsupported(claimed, evidence):  # BB-FR12-04..06
    assert rating_label(claimed, evidence) == "unsupported"


def test_rating_platform_name_is_case_insensitive():  # BB-FR12-07
    assert rating_label(1500, [achievement(1500)], subject="Codeforces") == "supported"


def test_leetcode_rating_exactly_80_percent_is_partial():  # BB-FR12-08
    assert rating_label(1800, [achievement(1440, "leetcode")], subject="leetcode") == "partially_supported"


# Skill duration rule: observed whole years vs claimed years, day-exact
@pytest.mark.parametrize(
    ("years", "first", "last", "label"),
    [
        (3, "2021-03-15", "2024-03-15", "supported"),  # observed == claimed, to the day
        (3, "2021-03-15", "2024-03-14", "partially_supported"),  # one day short = one year less
        (2, "2021-03-15", "2024-03-15", "supported"),  # observed > claimed
        (1, "2020-02-29", "2021-02-28", "partially_supported"),  # leap day: 0 whole years
        (1, "2020-02-29", "2021-03-01", "supported"),
        (0, "2024-01-01", "2024-01-01", "supported"),  # zero claimed, same-day evidence
    ],
    ids=["BB-FR12-09", "BB-FR12-10", "BB-FR12-11", "BB-FR12-12", "BB-FR12-13", "BB-FR12-14"],
)
def test_skill_duration_boundaries(years, first, last, label):  # BB-FR12-09..14
    assert skill_label(years, [skill(first, last)]) == label


def test_unparseable_dates_count_as_no_dates():  # BB-FR12-15
    assert skill_label(2, [skill("not-a-date", "2024-13-45")]) == "partially_supported"


def test_skill_claim_without_any_evidence_is_unsupported():  # BB-FR12-16
    assert skill_label(2, []) == "unsupported"

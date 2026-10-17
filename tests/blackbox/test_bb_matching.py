"""FR-10 coverage fraction.

Referenced (not repeated) from tests/unit/matching/test_requirement_matcher.py: coverage 0
(test_no_skill_matched_gives_zero_coverage), 1/3, 1/2 and 1 (test_partial_and_full_coverage), alias matching
(test_all_skills_matched_through_aliases) and dedup order
(test_required_skills_are_normalised_and_deduplicated_in_order).
New here: duplicate requirements that normalise equal must count once in the fraction, and the 1-of-50 / 49-of-50
edges of a maximum-size job.
"""

import pytest

from pipeline.core.inputs import JobRequirementInput
from pipeline.core.matching.matcher import RequirementMatcher
from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import EvidenceNode


def skill(node_id, name):
    return EvidenceNode(node_id, "run-1", "cand-1", "snap-1", "github", "octo-dev", "skill", {"name": name}, "$")


def coverage(required, names):
    """Returns (coverage fraction, number of distinct required skills)."""
    job = JobRequirementInput("job-1", "Backend", "text", tuple(required))
    result = RequirementMatcher(SkillNormalizer()).match(job, [skill(f"n{i}", n) for i, n in enumerate(names)])
    return result.coverage, len(result.matches)


@pytest.mark.parametrize(
    ("required", "expected"),
    [
        (("Python", "py", "python3"), (1.0, 1)),
        (("Python", "py", "Go"), (0.5, 2)),
        (("  PYTHON ", "Python"), (1.0, 1)),
        (("Node.js", "JS", "javascript", "Rust"), (0.5, 2)),
    ],
    ids=["BB-FR10-16", "BB-FR10-17", "BB-FR10-18", "BB-FR10-19"],
)
def test_duplicates_that_normalise_equal_count_once(required, expected):  # BB-FR10-16..19
    assert coverage(required, ["Python", "JavaScript"]) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("matched", "expected"), [(1, 0.02), (49, 0.98), (50, 1.0)], ids=["BB-FR10-20", "BB-FR10-21", "BB-FR10-22"]
)
def test_coverage_with_fifty_required_skills(matched, expected):  # BB-FR10-20..22
    required = [f"skill{i}" for i in range(50)]
    assert coverage(required, required[:matched])[0] == pytest.approx(expected)


def test_no_evidence_gives_zero_coverage():  # BB-FR10-23
    assert coverage(["Python"], []) == (0.0, 1)

"""FR-09 link threshold. The 0.4999 / 0.5 / 0.5001 boundary is already covered by
tests/unit/identity/test_resolver.py::test_threshold_boundary (referenced). Here: the extreme thresholds 0.0 and
1.0, the default threshold, the rationale, and thresholds just outside [0, 1].
"""

import pytest

from pipeline.core.errors import ResolutionError
from pipeline.core.identity.profiles import anchor_ref
from pipeline.core.identity.resolver import IdentityResolver
from pipeline.core.identity.signals import MatchSignal
from pipeline.core.models import AccountRef, SignalScore

ANCHOR = anchor_ref("Octo Developer", "octo@example.org")


class FixedSignal(MatchSignal):
    """Gives a fixed score for the anchor pair, so the link confidence equals that score (weight 1.0)."""

    name = "fixed"

    def __init__(self, value):
        self.value = value

    def score(self, a, b):
        return SignalScore(self.name, self.value if "resume" in (a.source, b.source) else 0.0, "fixed")


def link(confidence, **kw):
    resolver = IdentityResolver([(FixedSignal(confidence), 1.0)], **kw)
    account = AccountRef("github", "octo-dev", {"name": None, "email": None, "handle": "octo-dev", "links": []})
    return resolver.resolve("cand-1", "run-1", ANCHOR, [account]).links[0]


@pytest.mark.parametrize(
    ("threshold", "confidence", "linked"),
    [(0.0, 0.0, True), (0.0, 0.0001, True), (1.0, 0.9999, False), (1.0, 1.0, True)],
    ids=["BB-FR09-02", "BB-FR09-03", "BB-FR09-04", "BB-FR09-05"],
)
def test_extreme_thresholds(threshold, confidence, linked):  # BB-FR09-02..05
    assert link(confidence, threshold=threshold).linked is linked


@pytest.mark.parametrize(("confidence", "linked"), [(0.4999, False), (0.5, True)], ids=["BB-FR09-06", "BB-FR09-07"])
def test_default_threshold_is_0_50(confidence, linked):  # BB-FR09-06..07
    assert link(confidence).linked is linked


def test_unlinked_rationale_names_the_threshold():  # BB-FR09-08
    assert "below threshold 0.50" in link(0.4999).rationale[-1]


@pytest.mark.parametrize("threshold", [-0.0001, 1.0001], ids=["BB-FR09-09", "BB-FR09-10"])
def test_threshold_just_outside_range_is_refused(threshold):  # BB-FR09-09..10
    with pytest.raises(ResolutionError):
        IdentityResolver(threshold=threshold)

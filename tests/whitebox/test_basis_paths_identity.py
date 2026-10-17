"""White-box basis-path tests for IdentityResolver.resolve and IdentityResolver._link (M3, FR-08, FR-09).

Design, CFGs and path lists: docs/milestone2/whitebox-test-design.md, section 2.
resolve: V(G) = 4 (WB-IDN-01..04). _link: V(G) = 3 (WB-IDN-05..07).
"""

from pipeline.core.identity.profiles import anchor_ref
from pipeline.core.identity.resolver import DEFAULT_SIGNALS, IdentityResolver
from pipeline.core.identity.signals import MatchSignal
from pipeline.core.models import AccountRef, SignalScore

ANCHOR = anchor_ref("Ilsa Maryam", "ilsa@example.com")


class FixedSignal(MatchSignal):
    """Scores `value` for any pair that includes the resume anchor, 0 otherwise (so it never fires on a hop)."""

    name = "fixed"

    def __init__(self, value):
        self.value = value

    def score(self, a, b):
        value = self.value if "resume" in (a.source, b.source) else 0.0
        return SignalScore(self.name, value, f"fixed {value}")


def account(source, handle, email=None, links=()):
    return AccountRef(source, handle, {"name": None, "email": email, "handle": handle, "links": list(links)})


def resolve(resolver, accounts):
    return resolver.resolve("cand-1", "run-1", ANCHOR, accounts)


# ---- resolve -------------------------------------------------------------------------------------------------


def test_wb_idn_01_no_accounts_gives_an_empty_profile():
    """WB-IDN-01, resolve P1: 1-2-8. Outer loop runs zero times."""
    profile = resolve(IdentityResolver([(FixedSignal(1.0), 1.0)]), [])
    assert profile.candidate_id == "cand-1"
    assert profile.links == ()


def test_wb_idn_02_single_account_below_threshold_has_no_anchor_to_hop_through():
    """WB-IDN-02, resolve P2: 1-2-3-4-7-2-8. `anchored` is empty, so the inner loop runs zero times."""
    link = resolve(IdentityResolver([(FixedSignal(0.3), 1.0)]), [account("github", "octo")]).links[0]
    assert link.confidence == 0.3
    assert link.linked is False


def test_wb_idn_03_single_anchored_account_does_not_hop_through_itself():
    """WB-IDN-03, resolve P3: 1-2-3-4-5-4-7-2-8. Inner loop visits j == i and skips it (5 -> 4)."""
    link = resolve(IdentityResolver([(FixedSignal(1.0), 1.0)]), [account("github", "octo")]).links[0]
    assert link.confidence == 1.0
    assert link.linked is True
    assert len(link.rationale) == 1  # only the direct reason; no self-hop reasons appended


def test_wb_idn_04_second_account_links_by_one_hop_through_the_anchored_one():
    """WB-IDN-04, resolve P4: ...-4-5-6-4-7-2-8. GitHub shares the email; LeetCode links to GitHub only."""
    github = account("github", "octo-dev", email="ilsa@example.com")
    leetcode = account("leetcode", "lc_user", links=["https://github.com/octo-dev"])
    profile = resolve(IdentityResolver(DEFAULT_SIGNALS), [github, leetcode])
    gh_link, lc_link = profile.links
    assert gh_link.linked and gh_link.confidence == 0.9
    assert len(gh_link.rationale) == 1  # i = 0 is the only anchored account, so it never hops through itself
    assert lc_link.linked is True
    assert lc_link.confidence == 0.9  # max(direct 0.0, hop 0.9)
    assert any("github:octo-dev~leetcode:lc_user" in line for line in lc_link.rationale)


# ---- _link ---------------------------------------------------------------------------------------------------


def test_wb_idn_05_linked_with_reasons_keeps_rationale_unchanged():
    """WB-IDN-05, _link P1: 1-2-4-6. Rationale non-empty and confidence >= threshold."""
    link = resolve(IdentityResolver([(FixedSignal(0.8), 1.0)]), [account("github", "octo")]).links[0]
    assert link.linked is True
    assert link.rationale == ("fixed (0.80) on resume~github:octo: fixed 0.8",)


def test_wb_idn_06_no_signal_but_zero_threshold_is_linked_with_placeholder_reason():
    """WB-IDN-06, _link P2: 1-2-3-4-6. Empty rationale is replaced; threshold 0.0 makes confidence 0.0 linked."""
    resolver = IdentityResolver([(FixedSignal(0.0), 1.0)], threshold=0.0)
    link = resolve(resolver, [account("github", "octo")]).links[0]
    assert link.confidence == 0.0
    assert link.linked is True
    assert link.rationale == ("no matching signals",)


def test_wb_idn_07_reasons_below_threshold_get_the_not_linked_note():
    """WB-IDN-07, _link P3: 1-2-4-5-6. Rationale non-empty but confidence < threshold."""
    link = resolve(IdentityResolver([(FixedSignal(0.3), 1.0)]), [account("github", "octo")]).links[0]
    assert link.linked is False
    assert link.rationale == ("fixed (0.30) on resume~github:octo: fixed 0.3", "below threshold 0.50 — not linked")

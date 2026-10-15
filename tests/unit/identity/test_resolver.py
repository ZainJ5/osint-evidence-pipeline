import pytest

from pipeline.core.errors import ResolutionError
from pipeline.core.identity.profiles import anchor_ref
from pipeline.core.identity.resolver import DEFAULT_SIGNALS, IdentityResolver
from pipeline.core.identity.signals import MatchSignal
from pipeline.core.models import AccountRef, SignalScore

ANCHOR = anchor_ref("Ilsa Maryam", "ilsa@example.com")


class StubSignal(MatchSignal):
    """Returns a fixed score whenever the anchor is one side of the pair."""

    name = "stub"

    def __init__(self, value):
        self.value = value

    def score(self, a, b):
        value = self.value if "resume" in (a.source, b.source) else 0.0
        return SignalScore(self.name, value, f"stub said {value}")


def account(source, handle, name=None, email=None, links=()):
    return AccountRef(source, handle, {"name": name, "email": email, "handle": handle, "links": list(links)})


def resolve(resolver, accounts):
    return resolver.resolve("cand-1", "run-1", ANCHOR, accounts)


@pytest.mark.parametrize("value, linked", [(0.4999, False), (0.5, True), (0.5001, True)])
def test_threshold_boundary(value, linked):
    resolver = IdentityResolver([(StubSignal(value), 1.0)], threshold=0.5)
    link = resolve(resolver, [account("github", "octo")]).links[0]
    assert link.confidence == value
    assert link.linked is linked


def test_link_carries_ids_and_account():
    link = resolve(IdentityResolver([(StubSignal(1.0), 1.0)]), [account("github", "octo")]).links[0]
    assert (link.candidate_id, link.run_id, link.source, link.handle) == ("cand-1", "run-1", "github", "octo")


def test_signals_combine_as_noisy_or():
    resolver = IdentityResolver([(StubSignal(1.0), 0.5), (StubSignal(1.0), 0.6)])
    link = resolve(resolver, [account("github", "octo")]).links[0]
    assert link.confidence == 0.8  # 1 - (1 - 0.5)(1 - 0.6)


def test_confidence_rounded_to_four_decimals():
    link = resolve(IdentityResolver([(StubSignal(1 / 3), 1.0)]), [account("github", "octo")]).links[0]
    assert link.confidence == 0.3333


def test_account_with_no_matching_signal_is_not_linked_by_default():
    profile = resolve(IdentityResolver(DEFAULT_SIGNALS), [account("github", "stranger", name="Someone Else")])
    link = profile.links[0]
    assert link.confidence == 0.0
    assert link.linked is False
    assert any("below threshold 0.50" in line and "not linked" in line for line in link.rationale)
    assert profile.linked_handles() == set()


def test_default_weights_name_alone_links_and_email_is_strong():
    accounts = [account("github", "a", name="Ilsa Maryam"), account("codeforces", "b", email="ILSA@example.com")]
    links = resolve(IdentityResolver(DEFAULT_SIGNALS), accounts).links
    assert [(link.confidence, link.linked) for link in links] == [(0.5, True), (0.9, True)]


def test_one_hop_link_through_cross_link():
    github = account("github", "octo-dev", email="ilsa@example.com")
    leetcode = account("leetcode", "lc_user", links=["https://github.com/octo-dev"])
    profile = resolve(IdentityResolver(DEFAULT_SIGNALS), [github, leetcode])
    assert profile.linked_handles() == {("github", "octo-dev"), ("leetcode", "lc_user")}
    hop = profile.links[1]
    assert hop.confidence == 0.9
    assert any("cross_link" in line and "github:octo-dev" in line for line in hop.rationale)


def test_no_hop_through_an_unlinked_account():
    weak = account("github", "octo-dev")  # nothing ties it to the anchor
    leetcode = account("leetcode", "lc_user", links=["https://github.com/octo-dev"])
    profile = resolve(IdentityResolver(DEFAULT_SIGNALS), [weak, leetcode])
    assert profile.linked_handles() == set()


def test_rationale_names_signal_reason_and_pair():
    link = resolve(IdentityResolver(DEFAULT_SIGNALS), [account("github", "a", email="ilsa@example.com")]).links[0]
    assert len(link.rationale) == 1
    line = link.rationale[0]
    assert "email" in line and "resume~github:a" in line and "same email" in line and "@" not in line


def test_threshold_is_configurable():
    resolver = IdentityResolver(DEFAULT_SIGNALS, threshold=0.6)
    link = resolve(resolver, [account("github", "a", name="Ilsa Maryam")]).links[0]
    assert link.linked is False
    assert any("below threshold 0.60" in line for line in link.rationale)


@pytest.mark.parametrize("threshold", [-0.01, 1.01, "0.5", None])
def test_invalid_threshold_raises(threshold):
    with pytest.raises(ResolutionError):
        IdentityResolver(DEFAULT_SIGNALS, threshold=threshold)


@pytest.mark.parametrize("signals", [[], [(StubSignal(1.0), 1.5)], [(StubSignal(1.0), -0.1)]])
def test_invalid_signal_configuration_raises(signals):
    with pytest.raises(ResolutionError):
        IdentityResolver(signals)


def test_configuration_is_private():
    resolver = IdentityResolver(DEFAULT_SIGNALS)
    assert not hasattr(resolver, "signals")
    assert not hasattr(resolver, "threshold")


def test_empty_account_list_gives_empty_profile():
    assert resolve(IdentityResolver(DEFAULT_SIGNALS), []).links == ()

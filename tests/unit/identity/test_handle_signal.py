import pytest

from pipeline.core.identity.signals import HandleSignal
from pipeline.core.models import AccountRef


def ref(handle, source="github"):
    return AccountRef(source, handle, {"name": None, "email": None, "handle": handle, "links": []})


def test_identical_handles_score_one():
    result = HandleSignal().score(ref("octo-dev"), ref("octo-dev", "codeforces"))
    assert result.score == 1.0
    assert result.signal == "handle"


def test_identical_handles_ignore_case():
    assert HandleSignal().score(ref("Octo-Dev"), ref("octo-dev", "leetcode")).score == 1.0


@pytest.mark.parametrize("other", ["octo_dev", "octodev", "OctoDev"])
def test_handles_equal_after_stripping_punctuation_are_near(other):
    assert HandleSignal().score(ref("octo-dev"), ref(other, "codeforces")).score == 0.6


def test_handles_with_high_similarity_are_near():
    assert HandleSignal().score(ref("ilsamaryam"), ref("ilsamaryam1", "leetcode")).score == 0.6


@pytest.mark.parametrize("other", ["tourist", "octo", "zzz"])
def test_far_handles_score_zero(other):
    assert HandleSignal().score(ref("octo-dev"), ref(other, "codeforces")).score == 0.0


def test_empty_handle_never_matches():
    anchor = AccountRef("resume", "", {"name": "A B", "email": "a@b.co", "handle": None, "links": []})
    assert HandleSignal().score(anchor, ref("")).score == 0.0

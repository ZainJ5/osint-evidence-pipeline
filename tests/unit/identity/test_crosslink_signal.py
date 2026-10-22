import pytest

from pipeline.core.identity.signals import CrossLinkSignal
from pipeline.core.models import AccountRef


def ref(source, handle, links=()):
    return AccountRef(source, handle, {"name": None, "email": None, "handle": handle, "links": list(links)})


def test_leetcode_github_url_links_to_github_account():
    leetcode = ref("leetcode", "lc_user", ["https://github.com/octo-dev"])
    result = CrossLinkSignal().score(ref("github", "octo-dev"), leetcode)
    assert result.score == 1.0
    assert result.signal == "cross_link"
    assert "github.com/octo-dev" in result.reason


@pytest.mark.parametrize(
    "link",
    [
        "https://codeforces.com/profile/Octo_CF",
        "http://www.codeforces.com/profile/octo_cf/",
        "codeforces.com/profile/octo_cf",
    ],
)
def test_github_blog_pointing_to_codeforces_profile(link):
    github = ref("github", "octo-dev", [link])
    assert CrossLinkSignal().score(github, ref("codeforces", "octo_cf")).score == 1.0


@pytest.mark.parametrize("link", ["https://leetcode.com/octo_lc", "https://leetcode.com/u/octo_lc/"])
def test_link_to_leetcode_profile(link):
    github = ref("github", "octo-dev", [link])
    assert CrossLinkSignal().score(ref("leetcode", "octo_lc"), github).score == 1.0


def test_link_to_a_different_account_does_not_count():
    leetcode = ref("leetcode", "lc_user", ["https://github.com/someone-else"])
    assert CrossLinkSignal().score(ref("github", "octo-dev"), leetcode).score == 0.0


def test_link_must_match_whole_handle_not_prefix():
    leetcode = ref("leetcode", "lc_user", ["https://github.com/octo-dev-2"])
    assert CrossLinkSignal().score(ref("github", "octo-dev"), leetcode).score == 0.0


def test_no_links_scores_zero():
    assert CrossLinkSignal().score(ref("github", "octo-dev"), ref("leetcode", "octo-dev")).score == 0.0

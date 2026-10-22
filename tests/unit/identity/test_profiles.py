import json

import pytest

from pipeline.core.errors import ResolutionError
from pipeline.core.identity.profiles import anchor_ref, build_account_ref

GITHUB = {
    "login": "octo-dev",
    "name": "Ilsa Maryam",
    "email": "ilsa@example.com",
    "blog": "https://codeforces.com/profile/octo_cf",
    "twitter_username": "octotweets",
    "html_url": "https://github.com/octo-dev",
}
CODEFORCES = {"status": "OK", "result": [{"handle": "octo_cf", "firstName": "Ilsa", "lastName": "Maryam"}]}
LEETCODE = {
    "data": {
        "matchedUser": {
            "username": "octo_lc",
            "githubUrl": "https://github.com/octo-dev",
            "profile": {"realName": "Ilsa Maryam", "websites": ["https://ilsa.dev"]},
        }
    }
}


def test_github_profile_is_normalised():
    ref = build_account_ref("github", "octo-dev", GITHUB)
    assert ref.source == "github"
    assert ref.handle == "octo-dev"
    assert ref.profile["name"] == "Ilsa Maryam"
    assert ref.profile["email"] == "ilsa@example.com"
    assert ref.profile["handle"] == "octo-dev"
    assert "https://codeforces.com/profile/octo_cf" in ref.profile["links"]
    assert "https://github.com/octo-dev" in ref.profile["links"]
    assert "https://twitter.com/octotweets" in ref.profile["links"]


def test_github_missing_fields_become_none_and_empty():
    ref = build_account_ref("github", "octo-dev", {"login": "octo-dev", "name": None, "blog": ""})
    assert ref.profile == {"name": None, "email": None, "handle": "octo-dev", "links": []}


def test_codeforces_profile_joins_first_and_last_name():
    ref = build_account_ref("codeforces", "octo_cf", CODEFORCES)
    assert ref.profile == {"name": "Ilsa Maryam", "email": None, "handle": "octo_cf", "links": []}


def test_codeforces_without_names():
    payload = {"status": "OK", "result": [{"handle": "octo_cf"}]}
    assert build_account_ref("codeforces", "octo_cf", payload).profile["name"] is None


def test_leetcode_profile_collects_github_url_and_websites():
    ref = build_account_ref("leetcode", "octo_lc", LEETCODE)
    assert ref.profile["name"] == "Ilsa Maryam"
    assert ref.profile["handle"] == "octo_lc"
    assert ref.profile["email"] is None
    assert ref.profile["links"] == ["https://github.com/octo-dev", "https://ilsa.dev"]


def test_leetcode_missing_profile_block():
    payload = {"data": {"matchedUser": {"username": "octo_lc", "githubUrl": None}}}
    assert build_account_ref("leetcode", "octo_lc", payload).profile == {
        "name": None,
        "email": None,
        "handle": "octo_lc",
        "links": [],
    }


def test_raw_json_bytes_are_accepted():
    ref = build_account_ref("github", "octo-dev", json.dumps(GITHUB).encode())
    assert ref.profile["email"] == "ilsa@example.com"


@pytest.mark.parametrize(
    "source, payload",
    [("gitlab", {}), ("github", b"not json"), ("codeforces", {"status": "FAILED"}), ("leetcode", {"data": None})],
)
def test_unusable_payloads_raise_resolution_error(source, payload):
    with pytest.raises(ResolutionError):
        build_account_ref(source, "h", payload)


def test_anchor_ref_holds_what_the_candidate_told_us():
    ref = anchor_ref("Ilsa Maryam", "ilsa@example.com")
    assert ref.source == "resume"
    assert ref.handle == ""
    assert ref.profile == {"name": "Ilsa Maryam", "email": "ilsa@example.com", "handle": None, "links": []}

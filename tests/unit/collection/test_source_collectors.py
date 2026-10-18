"""GitHub, Codeforces and LeetCode collectors against hand-written API fixtures (FR-02..FR-04)."""

import pytest

from pipeline.adapters.fakes import FakeHttpClient, json_response
from pipeline.core.collection.codeforces import CodeforcesCollector
from pipeline.core.collection.github import GitHubCollector
from pipeline.core.collection.leetcode import LeetCodeCollector
from pipeline.core.errors import CollectionError
from pipeline.core.inputs import RunConfig
from pipeline.core.ports import HttpResponse

HANDLE = "octo-dev"
GH = f"https://api.github.com/users/{HANDLE}"
GH_REPO = f"https://api.github.com/repos/{HANDLE}"
CF = "https://codeforces.com/api"
LEETCODE = "https://leetcode.com/graphql"


async def collect(make_collector, source, routes, run_config=None):
    return await make_collector(source, FakeHttpClient(routes), run_config).collect(HANDLE)


# GitHub
async def test_github_collects_user_repos_and_per_repo_endpoints(make_collector, source_routes, fixture_bytes):
    fetches = await collect(make_collector, "github", source_routes["github"])
    assert [f.endpoint for f in fetches] == [
        "github/user",
        "github/repos",
        "github/languages/evidence-kit",
        "github/commits/evidence-kit",
        "github/languages/rust-playground",
        "github/commits/rust-playground",
    ]
    assert {(f.source, f.handle) for f in fetches} == {("github", HANDLE)}
    assert fetches[0].payload == fixture_bytes("github_user.json")


async def test_github_sends_documented_query_params(make_collector, source_routes, recording_http):
    http = recording_http(source_routes["github"])
    await make_collector("github", http).collect(HANDLE)
    params = {url: p for _, url, p in http.requests}
    assert params[f"{GH}/repos"] == {"per_page": 100, "type": "owner", "sort": "pushed"}
    assert params[f"{GH_REPO}/evidence-kit/commits"] == {"author": HANDLE, "per_page": 100}


async def test_github_skips_forks(make_collector, source_routes):
    http = FakeHttpClient(source_routes["github"])
    await make_collector("github", http).collect(HANDLE)
    assert not any("forked-lib" in url for url, _ in http.calls)


@pytest.mark.parametrize(("max_repos", "repo_fetches"), [(0, 0), (1, 2), (2, 4), (3, 4)])
async def test_github_respects_max_repos(make_collector, source_routes, max_repos, repo_fetches):
    run_config = RunConfig(min_interval_seconds=0.0, max_repos=max_repos)
    fetches = await collect(make_collector, "github", source_routes["github"], run_config)
    assert len(fetches) == 2 + repo_fetches


async def test_github_empty_repo_409_on_commits_is_skipped(make_collector, source_routes):
    routes = source_routes["github"]
    routes[f"{GH_REPO}/rust-playground/commits"] = HttpResponse(409, b'{"message": "Git Repository is empty."}', "")
    endpoints = [f.endpoint for f in await collect(make_collector, "github", routes)]
    assert "github/commits/rust-playground" not in endpoints
    assert "github/languages/rust-playground" in endpoints


async def test_github_unknown_user_is_not_found(make_collector):
    with pytest.raises(CollectionError) as err:
        await collect(make_collector, "github", {})
    assert err.value.code == "NOT_FOUND"


RATE_LIMIT_BODY = (
    b'{"message":"API rate limit exceeded for 203.0.113.7. (But here is the good news: Authenticated requests get a '
    b'higher rate limit. Check out the documentation for more details.)","documentation_url":'
    b'"https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting"}'
)


async def test_github_rate_limit_403_is_rate_limited_and_not_retried(make_collector, sleep):
    http = FakeHttpClient({GH: HttpResponse(403, RATE_LIMIT_BODY, GH)})
    with pytest.raises(CollectionError) as err:
        await make_collector("github", http).collect(HANDLE)
    assert err.value.code == "RATE_LIMITED"
    assert len(http.calls) == 1 and sleep.delays == []


async def test_github_secondary_rate_limit_403_is_rate_limited(make_collector, source_routes):
    routes = source_routes["github"]
    body = b'{"message": "You have exceeded a secondary rate limit. Please wait a few minutes before you try again."}'
    routes[f"{GH_REPO}/evidence-kit/commits"] = HttpResponse(403, body, "")
    with pytest.raises(CollectionError) as err:
        await collect(make_collector, "github", routes)
    assert err.value.code == "RATE_LIMITED"


async def test_github_other_403_keeps_its_http_code(make_collector):
    body = b'{"message": "Repository access blocked"}'
    with pytest.raises(CollectionError) as err:
        await collect(make_collector, "github", {GH: HttpResponse(403, body, GH)})
    assert err.value.code == "HTTP_403"


async def test_github_repos_that_are_not_a_list_are_malformed(make_collector, source_routes):
    routes = source_routes["github"]
    routes[f"{GH}/repos"] = json_response(f"{GH}/repos", {"message": "unexpected"})
    with pytest.raises(CollectionError) as err:
        await collect(make_collector, "github", routes)
    assert err.value.code == "MALFORMED_BODY"


# Codeforces
async def test_codeforces_collects_three_endpoints(make_collector, source_routes, fixture_bytes):
    fetches = await collect(make_collector, "codeforces", source_routes["codeforces"])
    assert [f.endpoint for f in fetches] == ["codeforces/user.info", "codeforces/user.rating", "codeforces/user.status"]
    assert fetches[2].payload == fixture_bytes("codeforces_user_status.json")


async def test_codeforces_sends_documented_query_params(make_collector, source_routes, recording_http):
    http = recording_http(source_routes["codeforces"])
    await make_collector("codeforces", http).collect(HANDLE)
    assert [p for _, _, p in http.requests] == [
        {"handles": HANDLE},
        {"handle": HANDLE},
        {"handle": HANDLE, "from": 1, "count": 10000},
    ]


@pytest.mark.parametrize("http_status", [200, 400])
async def test_codeforces_failed_status_is_not_found(make_collector, http_status):
    body = {"status": "FAILED", "comment": "handles: User with handle octo-dev not found"}
    routes = {f"{CF}/user.info": json_response(f"{CF}/user.info", body, http_status)}
    with pytest.raises(CollectionError) as err:
        await collect(make_collector, "codeforces", routes)
    assert err.value.code == "NOT_FOUND"


async def test_codeforces_failed_status_for_a_bad_parameter_is_not_not_found(make_collector, source_routes):
    # Real Codeforces answer to count=abc: HTTP 400 with a FAILED envelope that is not about the handle.
    body = {"status": "FAILED", "comment": "count: Field should contain integer value"}
    routes = source_routes["codeforces"]
    routes[f"{CF}/user.status"] = json_response(f"{CF}/user.status", body, 400)
    with pytest.raises(CollectionError) as err:
        await collect(make_collector, "codeforces", routes)
    assert err.value.code == "HTTP_400"


async def test_codeforces_body_without_ok_status_is_malformed(make_collector, source_routes):
    routes = source_routes["codeforces"]
    routes[f"{CF}/user.rating"] = json_response(f"{CF}/user.rating", {"result": []})
    with pytest.raises(CollectionError) as err:
        await collect(make_collector, "codeforces", routes)
    assert err.value.code == "MALFORMED_BODY"


# LeetCode
async def test_leetcode_collects_profile_with_one_graphql_post(
    make_collector, source_routes, recording_http, fixture_bytes
):
    http = recording_http(source_routes["leetcode"])
    fetches = await make_collector("leetcode", http).collect(HANDLE)
    assert [f.endpoint for f in fetches] == ["leetcode/profile"]
    assert fetches[0].payload == fixture_bytes("leetcode_profile.json")
    method, url, body = http.requests[0]
    assert (method, url, body["variables"]) == ("POST", LEETCODE, {"username": HANDLE})
    for field in ("matchedUser", "githubUrl", "realName", "acSubmissionNum", "languageProblemCount", "rating"):
        assert field in body["query"]


async def test_leetcode_unknown_user_is_not_found(make_collector):
    body = {"errors": [{"message": "That user does not exist."}], "data": {"matchedUser": None}}
    with pytest.raises(CollectionError) as err:
        await collect(make_collector, "leetcode", {LEETCODE: json_response(LEETCODE, body)})
    assert err.value.code == "NOT_FOUND"


async def test_leetcode_body_without_data_is_malformed(make_collector):
    with pytest.raises(CollectionError) as err:
        await collect(make_collector, "leetcode", {LEETCODE: json_response(LEETCODE, {"errors": []})})
    assert err.value.code == "MALFORMED_BODY"


def test_collectors_declare_their_source_names():
    assert (GitHubCollector.source_name, CodeforcesCollector.source_name, LeetCodeCollector.source_name) == (
        "github",
        "codeforces",
        "leetcode",
    )

"""GitHub, Codeforces and LeetCode parsers against the octo-dev snapshot fixtures (FR-07)."""

import json

import pytest

from pipeline.core.collection.codeforces import STATUS_COUNT
from pipeline.core.collection.github import COMMITS_PER_PAGE
from pipeline.core.snapshot.extractor import EvidenceExtractor
from pipeline.core.snapshot.parsers import default_parsers


@pytest.fixture
async def nodes(frozen_store):
    return await EvidenceExtractor(frozen_store, default_parsers()).extract_run("run-1", "cand-1")


def of(nodes, endpoint_source, kind):
    return [n for n in nodes if n.source == endpoint_source and n.kind == kind]


def test_every_node_carries_audit_fields(nodes, frozen_store):
    snapshot_ids = {s.id for s in frozen_store.list_for_run("run-1")}
    for node in nodes:
        assert node.run_id == "run-1"
        assert node.candidate_id == "cand-1"
        assert node.snapshot_id in snapshot_ids
        assert node.handle == "octo-dev"
        assert node.locator.startswith("$")
    assert len({n.id for n in nodes}) == len(nodes)


def test_github_projects_skip_forks(nodes):
    projects = sorted(n.value["name"] for n in of(nodes, "github", "project"))
    assert projects == ["algo-notes", "hello-api"]
    hello = next(n for n in of(nodes, "github", "project") if n.value["name"] == "hello-api")
    assert hello.value == {
        "name": "hello-api",
        "description": "A small REST API",
        "language": "Python",
        "stars": 12,
        "url": "https://github.com/octo-dev/hello-api",
        "created_at": "2021-03-01T09:00:00Z",
        "pushed_at": "2024-05-10T18:30:00Z",
        "topics": ["fastapi", "rest-api"],
    }
    assert hello.locator == "$[0]"


def test_github_archived_repo_is_still_a_project_and_keeps_its_raw_index(nodes):
    algo = next(n for n in of(nodes, "github", "project") if n.value["name"] == "algo-notes")
    assert algo.locator == "$[2]"  # index in the raw list, the fork at $[1] is skipped
    assert algo.value["topics"] == []


async def test_github_project_without_topics_gets_an_empty_list(store, make_raw):
    repos = [{"name": "bare", "fork": False, "html_url": "https://github.com/octo-dev/bare"}]
    store.freeze(make_raw("github", "github/repos", json.dumps(repos).encode()), "run-t", "cand-1")
    [node] = await EvidenceExtractor(store, default_parsers()).extract_run("run-t", "cand-1")
    assert node.value["topics"] == []


def test_github_language_skills_take_dates_from_repo(nodes):
    skills = {n.value["name"]: n.value for n in of(nodes, "github", "skill")}
    assert set(skills) == {"Python", "Dockerfile", "C++"}
    assert skills["Python"]["first_seen"] == "2021-03-01T09:00:00Z"
    assert skills["Python"]["last_seen"] == "2024-05-10T18:30:00Z"
    assert skills["Python"]["evidence"] == "repo language"
    assert skills["C++"]["first_seen"] == "2020-06-15T12:00:00Z"


def test_github_contributions_use_author_dates_and_skip_empty_commit_lists(nodes):
    # The fixture's committer dates are all 2024 (rebase / web-flow); authorship dates span 2021..2024.
    contributions = of(nodes, "github", "contribution")
    assert [n.value for n in contributions] == [
        {
            "repo": "hello-api",
            "commits": 3,
            "first": "2021-03-01T09:05:00Z",
            "last": "2024-05-10T18:00:00Z",
            "capped": False,
        }
    ]


def commit(day: int) -> dict:
    return {"sha": f"s{day}", "commit": {"author": {"date": f"2024-01-{day:02d}T00:00:00Z"}}}


@pytest.mark.parametrize(("count", "capped"), [(COMMITS_PER_PAGE - 1, False), (COMMITS_PER_PAGE, True)])
async def test_github_full_commit_page_is_flagged_capped(store, make_raw, count, capped):
    commits = [commit(1 + i % 28) for i in range(count)]
    store.freeze(make_raw("github", "github/commits/big", json.dumps(commits).encode()), "run-c", "cand-1")
    [node] = await EvidenceExtractor(store, default_parsers()).extract_run("run-c", "cand-1")
    assert (node.value["commits"], node.value["capped"]) == (count, capped)


def test_github_user_yields_no_nodes(nodes, frozen_store):
    user = next(s for s in frozen_store.list_for_run("run-1") if s.endpoint == "github/user")
    assert not [n for n in nodes if n.snapshot_id == user.id]


def test_codeforces_skills_from_accepted_submissions(nodes):
    skills = {n.value["name"]: n.value for n in of(nodes, "codeforces", "skill")}
    assert set(skills) == {"GNU C++17", "Python 3"}  # Java was never accepted
    assert skills["GNU C++17"]["first_seen"] == "2020-09-13T12:26:40+00:00"  # the PARTIAL one is ignored
    assert skills["GNU C++17"]["last_seen"] == "2023-11-14T22:13:20+00:00"
    assert skills["GNU C++17"]["submissions"] == 3
    assert skills["Python 3"]["first_seen"] == "2021-01-07T06:13:20+00:00"  # the acmsguru submission
    assert skills["Python 3"]["submissions"] == 2


def test_codeforces_achievements(nodes):
    values = sorted((n.value for n in of(nodes, "codeforces", "achievement")), key=lambda v: v["solved"] is None)
    assert values == [
        {
            "platform": "codeforces",
            "solved": 4,  # 71A, 1A (twice), 4A and acmsguru 100, which has no contestId
            "rating": None,
            "max_rating": None,
            "rank": None,
            "max_rank": None,
            "capped": False,
        },
        {
            "platform": "codeforces",
            "rating": 1650,
            "max_rating": 1720,
            "rank": "expert",
            "max_rank": "expert",
            "solved": None,
        },
    ]


def submission(contest_id, index: str, name: str) -> dict:
    problem = {"index": index, "name": name}
    problem.update({"contestId": contest_id} if contest_id is not None else {"problemsetName": "acmsguru"})
    return {"creationTimeSeconds": 1700000000, "problem": problem, "programmingLanguage": "C++", "verdict": "OK"}


async def codeforces_status(store, make_raw, result) -> list:
    body = json.dumps({"status": "OK", "result": result}).encode()
    store.freeze(make_raw("codeforces", "codeforces/user.status", body), "run-cf", "cand-1")
    return await EvidenceExtractor(store, default_parsers()).extract_run("run-cf", "cand-1")


async def test_codeforces_solved_is_keyed_by_contest_and_index_not_name(store, make_raw):
    renamed = [submission(1, "A", "Theatre Square"), submission(1, "A", "Theatre Square (statement fix)")]
    gym = [submission(100001, "A", "Gym A"), submission(None, "A", "Gym A")]  # no contestId: keyed by problemsetName
    nodes = await codeforces_status(store, make_raw, renamed + gym)
    [achievement] = of(nodes, "codeforces", "achievement")
    assert achievement.value["solved"] == 3


@pytest.mark.parametrize(("count", "capped"), [(STATUS_COUNT - 1, False), (STATUS_COUNT, True)])
async def test_codeforces_full_status_page_is_flagged_capped(store, make_raw, count, capped):
    result = [submission(1, "A", "Theatre Square")] * count
    nodes = await codeforces_status(store, make_raw, result)
    [achievement] = of(nodes, "codeforces", "achievement")
    assert achievement.value["capped"] is capped


def test_leetcode_nodes(nodes):
    skills = {n.value["name"]: n.value for n in of(nodes, "leetcode", "skill")}
    assert set(skills) == {"Python3", "C++"}
    assert skills["Python3"]["first_seen"] is None and skills["Python3"]["last_seen"] is None
    assert skills["Python3"]["solved"] == 120
    [achievement] = of(nodes, "leetcode", "achievement")
    assert achievement.value == {"platform": "leetcode", "solved": 150, "rating": 1835, "max_rating": 1835}


async def test_leetcode_unknown_user_yields_nothing(store, make_raw):
    store.freeze(make_raw("leetcode", "leetcode/profile", b'{"data": {"matchedUser": null}}'), "run-9", "cand-1")
    assert await EvidenceExtractor(store, default_parsers()).extract_run("run-9", "cand-1") == []

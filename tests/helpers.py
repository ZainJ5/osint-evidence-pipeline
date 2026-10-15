"""Recorded API responses for the fictional user octo-dev, keyed by the URL the collectors request."""

from pathlib import Path

from pipeline.core.ports import HttpResponse

API = Path(__file__).resolve().parent / "fixtures" / "api"
GH = "https://api.github.com"


def _ok(url: str, name: str) -> HttpResponse:
    return HttpResponse(200, (API / name).read_bytes(), url)


def fixture_routes() -> dict:
    routes = {
        f"{GH}/users/octo-dev": _ok(f"{GH}/users/octo-dev", "github_user.json"),
        f"{GH}/users/octo-dev/repos": _ok(f"{GH}/users/octo-dev/repos", "github_repos.json"),
        "https://codeforces.com/api/user.info": _ok("cf", "codeforces_user_info.json"),
        "https://codeforces.com/api/user.rating": _ok("cf", "codeforces_user_rating.json"),
        "https://codeforces.com/api/user.status": _ok("cf", "codeforces_user_status.json"),
        "https://leetcode.com/graphql": _ok("lc", "leetcode_profile.json"),
    }
    for repo in ("evidence-kit", "rust-playground"):
        routes[f"{GH}/repos/octo-dev/{repo}/languages"] = _ok(repo, "github_languages.json")
        routes[f"{GH}/repos/octo-dev/{repo}/commits"] = _ok(repo, "github_commits.json")
    return routes

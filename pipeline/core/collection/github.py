"""GitHub REST collector: profile, owned repositories, languages and the candidate's commits (FR-02)."""

import json

from pipeline.core.collection.collector import Collector
from pipeline.core.collection.factory import CollectorFactory
from pipeline.core.errors import CollectionError
from pipeline.core.models import RawFetch
from pipeline.core.ports import HttpResponse

API = "https://api.github.com"
COMMITS_PER_PAGE = 100  # one page only: a full page means the count is a lower bound (see parsers "capped")


class GitHubCollector(Collector):
    """Collects a GitHub profile and repositories."""

    source_name = "github"

    async def _collect(self, handle: str) -> list[RawFetch]:
        user, _ = await self._fetch(handle, "github/user", f"{API}/users/{handle}")
        repos_fetch, repos = await self._fetch(
            handle,
            "github/repos",
            f"{API}/users/{handle}/repos",
            params={"per_page": 100, "type": "owner", "sort": "pushed"},
        )
        fetches = [user, repos_fetch]
        for repo in self._own_repo_names(repos)[: self._config.max_repos]:
            fetches.append(await self._languages(handle, repo))
            commits = await self._commits(handle, repo)
            if commits:
                fetches.append(commits)
        return fetches

    def _own_repo_names(self, repos) -> list[str]:
        if not isinstance(repos, list):
            raise self._malformed("github/repos", "repository list expected")
        return [
            r["name"] for r in repos if isinstance(r, dict) and isinstance(r.get("name"), str) and not r.get("fork")
        ]

    async def _languages(self, handle: str, repo: str) -> RawFetch:
        fetch, _ = await self._fetch(handle, f"github/languages/{repo}", f"{API}/repos/{handle}/{repo}/languages")
        return fetch

    async def _commits(self, handle: str, repo: str) -> RawFetch | None:
        # REST commits endpoint instead of `git clone` (documented M2 deviation): same authorship data,
        # no disk I/O, and we stay within the official API (NFR-08).
        try:
            fetch, _ = await self._fetch(
                handle,
                f"github/commits/{repo}",
                f"{API}/repos/{handle}/{repo}/commits",
                params={"author": handle, "per_page": COMMITS_PER_PAGE},
            )
        except CollectionError as err:
            if err.code == "HTTP_409":  # empty repository
                return None
            raise
        return fetch

    def _is_rate_limited(self, response: HttpResponse) -> bool:
        # Primary and secondary limits are a 403 whose message mentions the rate limit. HttpResponse carries no
        # headers, so x-ratelimit-remaining cannot be read here; the message is GitHub's documented signal too.
        if response.status != 403:
            return False
        try:
            message = json.loads(response.body).get("message", "")
        except (ValueError, AttributeError):
            return False
        return isinstance(message, str) and "rate limit" in message.lower()


CollectorFactory.register(GitHubCollector.source_name, GitHubCollector)

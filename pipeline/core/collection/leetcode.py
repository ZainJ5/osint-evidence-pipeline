"""LeetCode collector: one query against the public GraphQL endpoint (FR-04)."""

from pipeline.core.collection.collector import Collector
from pipeline.core.collection.factory import CollectorFactory
from pipeline.core.errors import CollectionError
from pipeline.core.models import RawFetch

URL = "https://leetcode.com/graphql"
ENDPOINT = "leetcode/profile"
PROFILE_QUERY = """
query profile($username: String!) {
  matchedUser(username: $username) {
    username
    githubUrl
    profile { realName websites }
    submitStatsGlobal { acSubmissionNum { difficulty count } }
    languageProblemCount { languageName problemsSolved }
  }
  userContestRanking(username: $username) { rating }
}
"""


class LeetCodeCollector(Collector):
    """Collects a LeetCode profile via GraphQL."""

    source_name = "leetcode"

    async def _collect(self, handle: str) -> list[RawFetch]:
        body = {"query": PROFILE_QUERY, "variables": {"username": handle}}
        fetch, parsed = await self._fetch(handle, ENDPOINT, URL, json_body=body)
        data = parsed.get("data") if isinstance(parsed, dict) else None
        if not isinstance(data, dict):
            raise self._malformed(ENDPOINT, "GraphQL response without data")
        if data.get("matchedUser") is None:
            raise CollectionError("leetcode handle not found", code="NOT_FOUND", context={"source": self.source_name})
        return [fetch]


CollectorFactory.register(LeetCodeCollector.source_name, LeetCodeCollector)

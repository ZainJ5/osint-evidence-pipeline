"""Per-source parsers (Strategy) turning raw API JSON into EvidenceNodes (FR-07)."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pipeline.core.collection.codeforces import STATUS_COUNT
from pipeline.core.collection.github import COMMITS_PER_PAGE
from pipeline.core.errors import ExtractionError
from pipeline.core.models import EvidenceNode, Snapshot
from pipeline.core.snapshot.store import NAMESPACE


def make_node(snapshot: Snapshot, kind: str, value: dict, locator: str) -> EvidenceNode:
    node_id = uuid.uuid5(NAMESPACE, f"{snapshot.run_id}:{snapshot.id}:{kind}:{locator}")
    return EvidenceNode(
        id=str(node_id),
        run_id=snapshot.run_id,
        candidate_id=snapshot.candidate_id,
        snapshot_id=snapshot.id,
        source=snapshot.source,
        handle=snapshot.handle,
        kind=kind,
        value=value,
        locator=locator,
    )


def expect(payload, kind: type, snapshot: Snapshot):
    """Return payload if it has the expected JSON type, else raise ExtractionError."""
    if not isinstance(payload, kind):
        raise ExtractionError(
            f"unexpected payload shape for {snapshot.endpoint}",
            code="UNEXPECTED_SHAPE",
            context={"snapshot_id": snapshot.id, "endpoint": snapshot.endpoint},
        )
    return payload


def iso_from_epoch(seconds: int) -> str:
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


class SourceParser(ABC):
    """Strategy: one parser per source, chosen by snapshot.source."""

    source_name = ""

    @abstractmethod
    def parse(self, snapshot: Snapshot, payload: dict | list, context: dict | None = None) -> list[EvidenceNode]:
        """Parse one snapshot. `context` maps endpoint -> list of decoded payloads from the same run."""


class GitHubParser(SourceParser):
    """github/repos -> projects, github/languages/* -> skills, github/commits/* -> contributions."""

    source_name = "github"

    def parse(self, snapshot, payload, context=None):
        endpoint = snapshot.endpoint
        if endpoint == "github/repos":
            return self._repos(snapshot, expect(payload, list, snapshot))
        if endpoint.startswith("github/languages/"):
            repo_name = endpoint.split("/", 2)[2]
            repo = self._find_repo(repo_name, (context or {}).get("github/repos", []))
            return self._languages(snapshot, expect(payload, dict, snapshot), repo_name, repo)
        if endpoint.startswith("github/commits/"):
            return self._commits(snapshot, expect(payload, list, snapshot), endpoint.split("/", 2)[2])
        return []  # github/user feeds identity resolution, not evidence

    @staticmethod
    def _repos(snapshot, repos):
        nodes = []
        for i, repo in enumerate(repos):
            if repo.get("fork"):
                continue
            value = {
                "name": repo["name"],
                "description": repo.get("description"),
                "language": repo.get("language"),
                "stars": repo.get("stargazers_count", 0),
                "url": repo.get("html_url"),
                "created_at": repo.get("created_at"),
                "pushed_at": repo.get("pushed_at"),
                "topics": [t for t in repo.get("topics") or [] if isinstance(t, str)],
            }
            nodes.append(make_node(snapshot, "project", value, f"$[{i}]"))
        return nodes

    @staticmethod
    def _find_repo(name: str, repo_pages: list) -> dict:
        for page in repo_pages:
            for repo in page if isinstance(page, list) else []:
                if isinstance(repo, dict) and repo.get("name") == name:
                    return repo
        return {}

    @staticmethod
    def _languages(snapshot, languages, repo_name, repo):
        nodes = []
        for language, size in sorted(languages.items()):
            value = {
                "name": language,
                "first_seen": repo.get("created_at"),
                "last_seen": repo.get("pushed_at"),
                "evidence": "repo language",
                "repo": repo_name,
                "bytes": size,
            }
            nodes.append(make_node(snapshot, "skill", value, f"$['{language}']"))
        return nodes

    @staticmethod
    def _commits(snapshot, commits, repo_name):
        if not commits:
            return []
        # Authorship date, not committer date: rebases and web merges rewrite the latter.
        dates = sorted(c["commit"]["author"]["date"] for c in commits)
        value = {
            "repo": repo_name,
            "commits": len(commits),
            "first": dates[0],
            "last": dates[-1],
            "capped": len(commits) >= COMMITS_PER_PAGE,  # one page fetched: the true count may be higher
        }
        return [make_node(snapshot, "contribution", value, "$")]


class CodeforcesParser(SourceParser):
    """user.info -> rating achievement, user.status -> skills and solved count."""

    source_name = "codeforces"

    def parse(self, snapshot, payload, context=None):
        if expect(payload, dict, snapshot).get("status") != "OK":
            raise ExtractionError(
                "codeforces response is not OK", code="UNEXPECTED_SHAPE", context={"snapshot_id": snapshot.id}
            )
        result = expect(payload.get("result"), list, snapshot)
        if snapshot.endpoint == "codeforces/user.info":
            return self._info(snapshot, result)
        if snapshot.endpoint == "codeforces/user.status":
            return self._status(snapshot, result)
        return []  # user.rating: current and max rating already come from user.info

    @staticmethod
    def _info(snapshot, result):
        if not result:
            return []
        user = result[0]
        value = {
            "platform": "codeforces",
            "rating": user.get("rating"),
            "max_rating": user.get("maxRating"),
            "rank": user.get("rank"),
            "max_rank": user.get("maxRank"),
            "solved": None,
        }
        return [make_node(snapshot, "achievement", value, "$.result[0]")]

    @staticmethod
    def _status(snapshot, result):
        languages: dict[str, dict] = {}
        solved = set()
        for i, submission in enumerate(result):
            if submission.get("verdict") != "OK":
                continue
            problem = submission.get("problem", {})
            # acmsguru (and some gym) problems carry problemsetName instead of contestId.
            solved.add((problem.get("contestId") or problem.get("problemsetName"), problem.get("index")))
            seen = submission["creationTimeSeconds"]
            entry = languages.setdefault(submission["programmingLanguage"], {"index": i, "first": seen, "last": seen})
            entry.update(first=min(entry["first"], seen), last=max(entry["last"], seen), n=entry.get("n", 0) + 1)
        nodes = []
        for name, entry in languages.items():
            value = {
                "name": name,
                "first_seen": iso_from_epoch(entry["first"]),
                "last_seen": iso_from_epoch(entry["last"]),
                "evidence": "accepted submissions",
                "submissions": entry["n"],
            }
            nodes.append(make_node(snapshot, "skill", value, f"$.result[{entry['index']}].programmingLanguage"))
        achievement = {
            "platform": "codeforces",
            "solved": len(solved),
            "rating": None,
            "max_rating": None,
            "rank": None,
            "max_rank": None,
            "capped": len(result) >= STATUS_COUNT,  # a full page: older submissions were not fetched
        }
        nodes.append(make_node(snapshot, "achievement", achievement, "$.result"))
        return nodes


class LeetCodeParser(SourceParser):
    """leetcode/profile -> language skills and a solved/rating achievement."""

    source_name = "leetcode"

    def parse(self, snapshot, payload, context=None):
        data = expect(expect(payload, dict, snapshot).get("data"), dict, snapshot)
        user = data.get("matchedUser")
        if not user:
            return []
        nodes = []
        for i, entry in enumerate(user.get("languageProblemCount") or []):
            if entry.get("problemsSolved", 0) <= 0:
                continue
            value = {
                "name": entry["languageName"],
                "first_seen": None,
                "last_seen": None,
                "evidence": "leetcode problems solved",
                "solved": entry["problemsSolved"],
            }
            nodes.append(make_node(snapshot, "skill", value, f"$.data.matchedUser.languageProblemCount[{i}]"))
        counts = (user.get("submitStatsGlobal") or {}).get("acSubmissionNum") or []
        solved = next((c["count"] for c in counts if c.get("difficulty") == "All"), None)
        contest_rating = (data.get("userContestRanking") or {}).get("rating")
        rating = int(round(contest_rating)) if contest_rating is not None else None
        value = {"platform": "leetcode", "solved": solved, "rating": rating, "max_rating": rating}
        nodes.append(make_node(snapshot, "achievement", value, "$.data.matchedUser.submitStatsGlobal"))
        return nodes


def default_parsers() -> list[SourceParser]:
    return [GitHubParser(), CodeforcesParser(), LeetCodeParser()]

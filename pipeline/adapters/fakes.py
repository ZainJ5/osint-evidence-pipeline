"""In-memory fakes for every port (NFR-04). Used by unit tests and by offline replay."""

import asyncio
import hashlib
import math
import re
import time
from json import dumps

from pipeline.core.errors import CollectionError
from pipeline.core.ports import BlobStore, CandidateEraser, Embedder, HttpClient, HttpResponse, LLMProvider, Repository


class FakeHttpClient(HttpClient):
    """Serves canned responses keyed by URL. Records every call with a timestamp for stress tests."""

    def __init__(self, routes: dict | None = None, clock=None, delay: float = 0.0):
        self.routes = routes or {}  # url -> HttpResponse | Exception | list of these (served in order)
        self.calls: list[tuple[str, float]] = []
        self.delay = delay
        self._clock = clock

    async def get(self, url: str, params: dict | None = None) -> HttpResponse:
        return await self._serve(url)

    async def post(self, url: str, json: dict) -> HttpResponse:
        return await self._serve(url)

    async def _serve(self, url: str) -> HttpResponse:
        self.calls.append((url, (self._clock or time.monotonic)()))
        if self.delay:
            await asyncio.sleep(self.delay)
        route = self.routes.get(url)
        if route is None:
            return HttpResponse(404, b'{"message": "Not Found"}', url)
        if isinstance(route, list):
            route = route.pop(0) if len(route) > 1 else route[0]
        if isinstance(route, Exception):
            raise route
        return route


class OfflineHttpClient(HttpClient):
    """Used during replay (FR-14): any network call is a bug."""

    async def get(self, url: str, params: dict | None = None) -> HttpResponse:
        raise CollectionError("network access attempted during replay", code="NETWORK_DISABLED", context={"url": url})

    async def post(self, url: str, json: dict) -> HttpResponse:
        raise CollectionError("network access attempted during replay", code="NETWORK_DISABLED", context={"url": url})


class InMemoryBlobStore(BlobStore):
    """Dict-backed BlobStore for tests and offline replay."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> None:
        self.objects[key] = bytes(data)

    def get(self, key: str) -> bytes:
        if key not in self.objects:
            raise KeyError(key)
        return self.objects[key]

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


class InMemoryRepository(Repository):
    """Stores frozen dataclasses by their `id` attribute (or a key function)."""

    def __init__(self, key=lambda item: item.id):
        self._items: dict[str, object] = {}
        self._key = key

    def add(self, item) -> None:
        self._items[self._key(item)] = item

    def get(self, item_id: str):
        return self._items.get(item_id)

    def list_by(self, **filters) -> list:
        return [i for i in self._items.values() if all(getattr(i, k) == v for k, v in filters.items())]

    def remove_where(self, **filters) -> None:
        for key in [self._key(i) for i in self.list_by(**filters)]:
            del self._items[key]


class InMemoryEraser(CandidateEraser):
    """Deletes the candidate row, every row carrying its candidate_id, and its snapshot blobs."""

    def __init__(self, candidates: InMemoryRepository, owned: list[InMemoryRepository], snapshots, blob_store):
        self.candidates = candidates
        self.owned = owned
        self.snapshots = snapshots
        self.blob_store = blob_store

    def delete_candidate(self, candidate_id: str) -> None:
        mine = self.snapshots.list_by(candidate_id=candidate_id)
        others = {s.object_key for s in self.snapshots.list_by() if s.candidate_id != candidate_id}
        for snap in mine:
            if snap.object_key not in others:  # blobs are content-addressed and may be shared
                self.blob_store.delete(snap.object_key)
        for repo in [self.snapshots, *self.owned]:
            repo.remove_where(candidate_id=candidate_id)
        self.candidates.remove_where(id=candidate_id)


CLAIM_PATTERNS = [
    # "3 years of Python", "2+ yrs experience with Django"
    (
        re.compile(
            r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience\s+(?:with|in)\s+)?"
            r"([A-Za-z][\w+#\-]*(?:\.[A-Za-z]+)?)",
            re.I,
        ),
        "skill_years",
    ),
    # "Codeforces rating 1600", "rated 1600 on Codeforces"
    (re.compile(r"(codeforces|leetcode)\s+rating\s+(?:of\s+)?(\d{3,4})", re.I), "rating"),
    (re.compile(r"rated\s+(\d{3,4})\s+on\s+(codeforces|leetcode)", re.I), "rating_rev"),
    # "Skills: Python, Go, Docker"
    (re.compile(r"skills?\s*:\s*([^\n.]+)", re.I), "skill_list"),
]


class FakeLLMProvider(LLMProvider):
    """Deterministic stand-in for the LLM: rule-based claim extraction from resume text.

    Same prompt in -> same output out, which is what makes tests and replay reproducible (R-02).
    """

    def complete(self, prompt: str, schema: dict) -> dict:
        claims: list[dict] = []
        seen = set()

        def add(claim: dict) -> None:
            key = (claim["kind"], claim["subject"].lower())
            if key not in seen:
                seen.add(key)
                claims.append(claim)

        for pattern, kind in CLAIM_PATTERNS:
            for m in pattern.finditer(prompt):
                if kind == "skill_years":
                    add(
                        {"text": m.group(0).strip(), "kind": "skill", "subject": m.group(2), "years": float(m.group(1))}
                    )
                elif kind == "rating":
                    add(
                        {
                            "text": m.group(0).strip(),
                            "kind": "rating",
                            "subject": m.group(1).lower(),
                            "rating": int(m.group(2)),
                        }
                    )
                elif kind == "rating_rev":
                    add(
                        {
                            "text": m.group(0).strip(),
                            "kind": "rating",
                            "subject": m.group(2).lower(),
                            "rating": int(m.group(1)),
                        }
                    )
                else:
                    for skill in re.split(r"[,;/]| and ", m.group(1)):
                        if skill.strip():
                            add({"text": skill.strip(), "kind": "skill", "subject": skill.strip()})
        return {"claims": claims}


class HashingEmbedder(Embedder):
    """Deterministic bag-of-words embedder (384 dims) so matching works without a model download."""

    DIM = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * self.DIM
            for token in re.findall(r"[a-z0-9+#]+", text.lower()):
                digest = hashlib.sha256(token.encode()).digest()
                vec[int.from_bytes(digest[:4], "big") % self.DIM] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


def json_response(url: str, data, status: int = 200) -> HttpResponse:
    """Helper for tests: build an HttpResponse from a Python object."""
    return HttpResponse(status, dumps(data).encode(), url)


def in_memory_repositories():
    """Repositories keyed exactly like the PostgreSQL tables (composite keys for verdicts/accounts/reports)."""
    from pipeline.core.pipeline import Repositories  # pylint: disable=import-outside-toplevel

    return Repositories(
        candidates=InMemoryRepository(),
        job_requirements=InMemoryRepository(),
        runs=InMemoryRepository(),
        source_accounts=InMemoryRepository(key=lambda a: f"{a.run_id}:{a.source}:{a.handle}"),
        snapshots=InMemoryRepository(),
        evidence_nodes=InMemoryRepository(),
        claims=InMemoryRepository(),
        verdicts=InMemoryRepository(key=lambda v: f"{v.claim_id}:{v.run_id}"),
        score_reports=InMemoryRepository(key=lambda r: r.run_id),
    )


def in_memory_eraser(repos, blob_store: InMemoryBlobStore) -> InMemoryEraser:
    owned = [repos.runs, repos.source_accounts, repos.evidence_nodes, repos.claims, repos.verdicts, repos.score_reports]
    return InMemoryEraser(repos.candidates, owned, repos.snapshots, blob_store)

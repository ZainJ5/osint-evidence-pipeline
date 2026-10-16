"""Small in-memory cosine-similarity index (the pgvector-backed index is deferred to M3)."""

import math

from pipeline.core.errors import MatchingError


class InMemoryVectorIndex:
    """Cosine-similarity index over embeddings."""

    def __init__(self):
        self._vectors: dict[str, list[float]] = {}

    def __len__(self) -> int:
        return len(self._vectors)

    def upsert(self, node_id: str, vector: list[float]) -> None:
        self._vectors[node_id] = list(vector)

    def search(self, query: list[float], k: int) -> list[tuple[str, float]]:
        """Top-k (node_id, cosine) pairs, highest first; equal scores are ordered by node_id."""
        scored = [(node_id, _cosine(query, vector)) for node_id, vector in self._vectors.items()]
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored[: max(k, 0)]


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise MatchingError("vector dimensions differ", context={"query": len(a), "stored": len(b)})
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norm == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm

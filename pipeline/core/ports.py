"""Abstract interfaces (ports) that core business logic depends on.

Concrete implementations live in pipeline.adapters; in-memory fakes in pipeline.adapters.fakes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class HttpResponse:
    """Library-independent HTTP response."""

    status: int
    body: bytes
    url: str


class HttpClient(ABC):
    """Port for outbound HTTP."""

    @abstractmethod
    async def get(self, url: str, params: dict | None = None) -> HttpResponse:
        """GET a URL. Raises CollectionError on transport failure (never a library exception)."""

    @abstractmethod
    async def post(self, url: str, json: dict) -> HttpResponse:
        """POST JSON. Needed only for LeetCode's public GraphQL endpoint."""


class BlobStore(ABC):
    """Port for raw snapshot storage."""

    @abstractmethod
    def put(self, key: str, data: bytes) -> None:
        """Store bytes under a key; storing the same key again replaces them."""

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Return the bytes for a key. Raises KeyError if the key does not exist, SnapshotError on store failure."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove a key; removing a missing key is not an error."""


class LLMProvider(ABC):
    """Port for structured LLM completion."""

    @abstractmethod
    def complete(self, prompt: str, schema: dict) -> dict:
        """Return a dict meant to follow `schema` (ClaimExtractor validates it). Raises ScoringError on failure."""


class Embedder(ABC):
    """Port for text embeddings."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per text, in the same order, all of the same length."""


class Repository(ABC, Generic[T]):
    """Append-only store for one value-object type. There is deliberately no update()."""

    @abstractmethod
    def add(self, item: T) -> None:
        """Store an item under its id. Ids are deterministic, so adding the same item twice has no effect."""

    @abstractmethod
    def get(self, item_id: str) -> T | None:
        """Return the item with this id, or None."""

    @abstractmethod
    def list_by(self, **filters) -> list[T]:
        """Return the items whose fields equal every filter value; no filters returns every item."""


class CandidateEraser(ABC):
    """Port for erasing all data of a candidate."""

    @abstractmethod
    def delete_candidate(self, candidate_id: str) -> None:
        """Erase every row of a candidate and every blob no other candidate uses (FR-16)."""

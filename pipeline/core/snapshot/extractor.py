"""M2 Evidence Extraction: a bounded pool of worker coroutines parses a run's verified snapshots (FR-07)."""

import asyncio
import json

from pipeline.core.errors import ExtractionError, ValidationError
from pipeline.core.models import EvidenceNode, Snapshot
from pipeline.core.snapshot.parsers import SourceParser
from pipeline.core.snapshot.store import SnapshotStore


class EvidenceExtractor:
    """Parses snapshots into evidence nodes in parallel."""

    def __init__(self, store: SnapshotStore, parsers: list[SourceParser], workers: int = 4):
        if workers < 1:
            raise ValidationError("workers must be >= 1", context={"field": "workers"})
        self._store = store
        self._parsers = {p.source_name: p for p in parsers}
        self._workers = workers

    async def extract_run(self, run_id: str, candidate_id: str) -> list[EvidenceNode]:
        """Parse every snapshot of the run. Output order is deterministic whatever the worker count."""
        loaded = [self._load(s) for s in self._store.list_for_run(run_id) if s.candidate_id == candidate_id]
        context: dict[str, list] = {}
        for snapshot, payload in loaded:
            context.setdefault(snapshot.endpoint, []).append(payload)

        queue: asyncio.Queue = asyncio.Queue()
        for item in loaded:
            queue.put_nowait(item)
        results: list[tuple[tuple, EvidenceNode]] = []
        await asyncio.gather(*(self._worker(queue, context, results) for _ in range(self._workers)))
        results.sort(key=lambda r: r[0])
        return [node for _, node in results]

    def _load(self, snapshot: Snapshot) -> tuple[Snapshot, dict | list]:
        snapshot, raw = self._store.load(snapshot.id)  # SnapshotError if missing or tampered
        try:
            return snapshot, json.loads(raw)
        except ValueError as exc:  # JSONDecodeError and UnicodeDecodeError
            raise ExtractionError(
                "snapshot is not valid JSON", code="INVALID_JSON", context={"snapshot_id": snapshot.id}
            ) from exc

    async def _worker(self, queue: asyncio.Queue, context: dict, results: list) -> None:
        while not queue.empty():
            snapshot, payload = queue.get_nowait()
            for node in self._parse(snapshot, payload, context):
                results.append(((snapshot.source, snapshot.endpoint, node.locator, node.kind, node.id), node))
            await asyncio.sleep(0)  # let the other workers take a turn

    def _parse(self, snapshot: Snapshot, payload, context: dict) -> list[EvidenceNode]:
        parser = self._parsers.get(snapshot.source)
        if parser is None:
            raise ExtractionError(
                f"no parser for source '{snapshot.source}'", code="UNKNOWN_SOURCE", context={"snapshot_id": snapshot.id}
            )
        try:
            return parser.parse(snapshot, payload, context)
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise ExtractionError(
                f"cannot parse {snapshot.endpoint}", context={"snapshot_id": snapshot.id, "error": type(exc).__name__}
            ) from exc

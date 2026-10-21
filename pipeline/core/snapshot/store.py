"""M2 Snapshot Store: content-addressed, hash-verified, write-once raw payloads (FR-06, FR-14, FR-16, QR-14)."""

import hashlib
import uuid

from pipeline.core.errors import SnapshotError
from pipeline.core.models import RawFetch, Snapshot
from pipeline.core.ports import BlobStore, Repository

# Fixed namespace so snapshot and evidence ids are reproducible across processes and replays.
NAMESPACE = uuid.UUID("5d0c4f4e-8a3b-4c1e-9f57-2b6f0e1a7c33")


class SnapshotStore:
    """Freezes raw fetches as immutable snapshots and loads them back hash-verified."""

    def __init__(self, blob_store: BlobStore, repo: Repository[Snapshot]):
        self._blobs = blob_store
        self._repo = repo

    def freeze(self, raw: RawFetch, run_id: str, candidate_id: str) -> Snapshot:
        """Store the payload once. Freezing the same fetch twice in a run returns the existing snapshot."""
        sha256 = hashlib.sha256(raw.payload).hexdigest()
        snapshot_id = str(uuid.uuid5(NAMESPACE, f"{run_id}:{raw.source}:{raw.endpoint}:{sha256}"))
        existing = self._repo.get(snapshot_id)
        if existing is not None:
            return existing
        snapshot = Snapshot(
            id=snapshot_id,
            run_id=run_id,
            candidate_id=candidate_id,
            source=raw.source,
            handle=raw.handle,
            endpoint=raw.endpoint,
            object_key=f"snapshots/{raw.source}/{sha256}",
            sha256=sha256,
            fetched_at=raw.fetched_at,
            size=len(raw.payload),
        )
        # Blob first, then metadata: a crash in between leaves an unreferenced blob, never a dangling row.
        self._blobs.put(snapshot.object_key, raw.payload)
        self._repo.add(snapshot)
        return snapshot

    def load(self, snapshot_id: str) -> tuple[Snapshot, bytes]:
        """Return metadata and bytes, after checking the bytes still hash to the recorded SHA-256."""
        snapshot = self._repo.get(snapshot_id)
        if snapshot is None:
            raise SnapshotError("snapshot not found", code="NOT_FOUND", context={"snapshot_id": snapshot_id})
        try:
            payload = self._blobs.get(snapshot.object_key)
        except KeyError as exc:
            raise SnapshotError(
                "snapshot blob missing", code="NOT_FOUND", context={"snapshot_id": snapshot_id}
            ) from exc
        if hashlib.sha256(payload).hexdigest() != snapshot.sha256:
            raise SnapshotError(
                "snapshot bytes do not match recorded hash", code="HASH_MISMATCH", context={"snapshot_id": snapshot_id}
            )
        return snapshot, payload

    def list_for_run(self, run_id: str) -> list[Snapshot]:
        return sorted(self._repo.list_by(run_id=run_id), key=lambda s: (s.source, s.endpoint, s.sha256))

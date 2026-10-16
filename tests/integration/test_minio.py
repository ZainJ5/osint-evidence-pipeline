import uuid
from datetime import datetime, timezone

import pytest

from pipeline.adapters.fakes import InMemoryRepository
from pipeline.core.errors import SnapshotError
from pipeline.core.models import RawFetch
from pipeline.core.snapshot.store import SnapshotStore

pytestmark = pytest.mark.integration


def test_put_get_delete_round_trip(minio_store):
    key = f"test/{uuid.uuid4()}"
    minio_store.put(key, b"hello")
    assert minio_store.get(key) == b"hello"
    minio_store.delete(key)
    with pytest.raises(KeyError):
        minio_store.get(key)


def test_delete_missing_key_is_a_no_op(minio_store):
    minio_store.delete(f"test/{uuid.uuid4()}")


def test_tampered_blob_in_minio_raises_snapshot_error(minio_store):
    store = SnapshotStore(minio_store, InMemoryRepository())
    payload = f'{{"login": "octo-dev", "nonce": "{uuid.uuid4()}"}}'.encode()
    fetch = RawFetch("github", "octo-dev", "github/user", payload, datetime.now(timezone.utc))
    snapshot = store.freeze(fetch, "run-1", "cand-1")
    assert store.load(snapshot.id)[1] == payload

    minio_store.put(snapshot.object_key, b'{"login": "mallory"}')
    with pytest.raises(SnapshotError) as err:
        store.load(snapshot.id)
    assert err.value.code == "HASH_MISMATCH"
    minio_store.delete(snapshot.object_key)

import dataclasses
import hashlib

import pytest

from pipeline.core.errors import SnapshotError


def test_freeze_hashes_payload_and_stores_blob(store, blobs, make_raw):
    snap = store.freeze(make_raw("github", "github/user", b'{"login": "octo-dev"}'), "run-1", "cand-1")
    digest = hashlib.sha256(b'{"login": "octo-dev"}').hexdigest()
    assert snap.sha256 == digest
    assert snap.object_key == f"snapshots/github/{digest}"
    assert snap.size == len(b'{"login": "octo-dev"}')
    assert (snap.run_id, snap.candidate_id, snap.handle) == ("run-1", "cand-1", "octo-dev")
    assert blobs.get(snap.object_key) == b'{"login": "octo-dev"}'


def test_freeze_is_idempotent_within_a_run(store, make_raw):
    fetch = make_raw("github", "github/user", b"{}")
    first = store.freeze(fetch, "run-1", "cand-1")
    second = store.freeze(fetch, "run-1", "cand-1")
    assert first == second
    assert store.list_for_run("run-1") == [first]


def test_same_bytes_in_another_run_gets_new_snapshot_but_shares_blob(store, make_raw):
    fetch = make_raw("github", "github/user", b"{}")
    a = store.freeze(fetch, "run-1", "cand-1")
    b = store.freeze(fetch, "run-2", "cand-1")
    assert a.id != b.id
    assert a.object_key == b.object_key


def test_identical_bytes_from_two_endpoints_are_two_snapshots(store, make_raw):
    a = store.freeze(make_raw("github", "github/commits/x", b"[]"), "run-1", "cand-1")
    b = store.freeze(make_raw("github", "github/commits/y", b"[]"), "run-1", "cand-1")
    assert a.id != b.id
    assert a.object_key == b.object_key
    assert len(store.list_for_run("run-1")) == 2


def test_snapshot_is_immutable(store, make_raw):
    snap = store.freeze(make_raw("github", "github/user", b"{}"), "run-1", "cand-1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.sha256 = "0" * 64


def test_load_returns_verified_bytes(store, make_raw):
    snap = store.freeze(make_raw("leetcode", "leetcode/profile", b'{"data": {}}'), "run-1", "cand-1")
    loaded, payload = store.load(snap.id)
    assert loaded == snap
    assert payload == b'{"data": {}}'


def test_tampered_blob_raises_snapshot_error(store, blobs, make_raw):
    snap = store.freeze(make_raw("github", "github/user", b'{"login": "octo-dev"}'), "run-1", "cand-1")
    blobs.put(snap.object_key, b'{"login": "mallory"}')
    with pytest.raises(SnapshotError) as err:
        store.load(snap.id)
    assert err.value.code == "HASH_MISMATCH"
    assert err.value.context["snapshot_id"] == snap.id


def test_unknown_snapshot_raises_not_found(store, make_raw):
    with pytest.raises(SnapshotError) as err:
        store.load("does-not-exist")
    assert err.value.code == "NOT_FOUND"


def test_missing_blob_raises_not_found(store, blobs, make_raw):
    snap = store.freeze(make_raw("github", "github/user", b"{}"), "run-1", "cand-1")
    blobs.delete(snap.object_key)
    with pytest.raises(SnapshotError) as err:
        store.load(snap.id)
    assert err.value.code == "NOT_FOUND"


def test_list_for_run_is_sorted_and_scoped(store, make_raw):
    store.freeze(make_raw("leetcode", "leetcode/profile", b"{}"), "run-1", "cand-1")
    store.freeze(make_raw("github", "github/user", b"{}"), "run-1", "cand-1")
    store.freeze(make_raw("github", "github/repos", b"[]"), "run-1", "cand-1")
    store.freeze(make_raw("github", "github/repos", b"[]"), "run-2", "cand-1")
    listed = store.list_for_run("run-1")
    assert [(s.source, s.endpoint) for s in listed] == [
        ("github", "github/repos"),
        ("github", "github/user"),
        ("leetcode", "leetcode/profile"),
    ]

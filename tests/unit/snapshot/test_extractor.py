import pytest

from pipeline.core.errors import ExtractionError, SnapshotError, ValidationError
from pipeline.core.snapshot.extractor import EvidenceExtractor
from pipeline.core.snapshot.parsers import default_parsers


async def test_extraction_is_deterministic(frozen_store):
    extractor = EvidenceExtractor(frozen_store, default_parsers())
    first = await extractor.extract_run("run-1", "cand-1")
    second = await extractor.extract_run("run-1", "cand-1")
    assert first == second
    assert len(first) > 0


async def test_worker_count_does_not_change_result(frozen_store):
    one = await EvidenceExtractor(frozen_store, default_parsers(), workers=1).extract_run("run-1", "cand-1")
    four = await EvidenceExtractor(frozen_store, default_parsers(), workers=4).extract_run("run-1", "cand-1")
    assert one == four


async def test_output_is_sorted_by_source_endpoint_locator(frozen_store):
    nodes = await EvidenceExtractor(frozen_store, default_parsers()).extract_run("run-1", "cand-1")
    endpoints = {s.id: s.endpoint for s in frozen_store.list_for_run("run-1")}
    keys = [(n.source, endpoints[n.snapshot_id], n.locator) for n in nodes]
    assert keys == sorted(keys)


async def test_empty_run_yields_no_nodes(store):
    assert await EvidenceExtractor(store, default_parsers()).extract_run("nothing", "cand-1") == []


async def test_malformed_json_raises_extraction_error(store, make_raw):
    snap = store.freeze(make_raw("github", "github/repos", b"[{not json"), "run-1", "cand-1")
    with pytest.raises(ExtractionError) as err:
        await EvidenceExtractor(store, default_parsers()).extract_run("run-1", "cand-1")
    assert err.value.context["snapshot_id"] == snap.id


async def test_unexpected_payload_shape_raises_extraction_error(store, make_raw):
    store.freeze(make_raw("github", "github/repos", b'{"message": "Not Found"}'), "run-1", "cand-1")
    with pytest.raises(ExtractionError):
        await EvidenceExtractor(store, default_parsers()).extract_run("run-1", "cand-1")


async def test_unknown_source_raises_extraction_error(store, make_raw):
    store.freeze(make_raw("gitlab", "gitlab/user", b"{}"), "run-1", "cand-1")
    with pytest.raises(ExtractionError) as err:
        await EvidenceExtractor(store, default_parsers()).extract_run("run-1", "cand-1")
    assert err.value.code == "UNKNOWN_SOURCE"


async def test_tampered_snapshot_stops_extraction(store, blobs, make_raw):
    snap = store.freeze(make_raw("github", "github/repos", b"[]"), "run-1", "cand-1")
    blobs.put(snap.object_key, b"[1]")
    with pytest.raises(SnapshotError):
        await EvidenceExtractor(store, default_parsers()).extract_run("run-1", "cand-1")


def test_workers_must_be_positive(store):
    with pytest.raises(ValidationError):
        EvidenceExtractor(store, default_parsers(), workers=0)

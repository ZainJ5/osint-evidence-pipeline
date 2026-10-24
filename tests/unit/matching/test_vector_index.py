"""InMemoryVectorIndex: cosine ranking with a deterministic tie-break."""

import pytest

from pipeline.core.errors import MatchingError
from pipeline.core.matching.vector_index import InMemoryVectorIndex


def index_with(**vectors) -> InMemoryVectorIndex:
    index = InMemoryVectorIndex()
    for node_id, vector in vectors.items():
        index.upsert(node_id, vector)
    return index


def test_results_are_ranked_by_cosine_similarity():
    index = index_with(same=[1.0, 0.0], diagonal=[1.0, 1.0], orthogonal=[0.0, 1.0])
    hits = index.search([2.0, 0.0], k=3)
    assert [node for node, _ in hits] == ["same", "diagonal", "orthogonal"]
    assert [score for _, score in hits] == pytest.approx([1.0, 0.7071, 0.0], abs=1e-4)


def test_ties_are_broken_by_node_id():
    index = index_with(b=[1.0, 0.0], a=[3.0, 0.0], c=[0.5, 0.0])
    assert [node for node, _ in index.search([1.0, 0.0], k=3)] == ["a", "b", "c"]


@pytest.mark.parametrize(("k", "expected"), [(0, 0), (1, 1), (2, 2), (5, 2)])
def test_k_bounds_the_number_of_results(k, expected):
    index = index_with(a=[1.0, 0.0], b=[0.0, 1.0])
    assert len(index.search([1.0, 1.0], k=k)) == expected


def test_upsert_replaces_an_existing_vector():
    index = index_with(a=[1.0, 0.0])
    index.upsert("a", [0.0, 1.0])
    assert index.search([0.0, 1.0], k=1) == [("a", pytest.approx(1.0))]
    assert len(index) == 1


def test_zero_vector_has_zero_similarity():
    assert index_with(a=[0.0, 0.0]).search([1.0, 0.0], k=1) == [("a", 0.0)]


def test_empty_index_returns_nothing():
    assert InMemoryVectorIndex().search([1.0], k=3) == []


def test_dimension_mismatch_is_a_matching_error():
    with pytest.raises(MatchingError):
        index_with(a=[1.0, 0.0]).search([1.0, 0.0, 0.0], k=1)

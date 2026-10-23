import pytest

from pipeline.core.identity.signals import NameSignal
from pipeline.core.models import AccountRef


def ref(name, source="github"):
    return AccountRef(source, "h", {"name": name, "email": None, "handle": "h", "links": []})


def test_same_full_name_scores_one():
    result = NameSignal().score(ref("Ilsa Maryam"), ref("Ilsa Maryam", "codeforces"))
    assert result.score == 1.0
    assert result.signal == "name"


@pytest.mark.parametrize("other", ["ilsa  maryam", "ILSA MARYAM", " Ilsa Maryam. "])
def test_name_normalisation_ignores_case_spacing_punctuation(other):
    assert NameSignal().score(ref("Ilsa Maryam"), ref(other)).score == 1.0


def test_single_token_names_do_not_match():
    assert NameSignal().score(ref("Ilsa"), ref("Ilsa")).score == 0.0


@pytest.mark.parametrize("left, right", [("Ilsa Maryam", "Ilsa Khan"), (None, "Ilsa Maryam"), ("", ""), (None, None)])
def test_different_or_missing_names_score_zero(left, right):
    assert NameSignal().score(ref(left), ref(right)).score == 0.0

import pytest

from pipeline.core.identity.signals import EmailSignal
from pipeline.core.models import AccountRef


def ref(email, source="github", handle="octo"):
    return AccountRef(source, handle, {"name": None, "email": email, "handle": handle, "links": []})


def test_same_email_scores_one():
    result = EmailSignal().score(ref("ilsa@example.com"), ref("ilsa@example.com"))
    assert result.score == 1.0
    assert result.signal == "email"
    assert "same email" in result.reason


def test_email_match_ignores_case_and_spaces():
    assert EmailSignal().score(ref(" Ilsa@Example.COM"), ref("ilsa@example.com")).score == 1.0


def test_different_emails_score_zero():
    assert EmailSignal().score(ref("a@example.com"), ref("b@example.com")).score == 0.0


@pytest.mark.parametrize("left, right", [(None, None), ("", ""), (None, "a@example.com"), ("  ", "  ")])
def test_missing_or_empty_emails_never_match(left, right):
    assert EmailSignal().score(ref(left), ref(right)).score == 0.0


def test_missing_profile_key_is_treated_as_no_email():
    bare = AccountRef("codeforces", "octo", {})
    assert EmailSignal().score(bare, ref("a@example.com")).score == 0.0


def test_rationale_does_not_store_the_email_address():
    # NFR-06: rationale is persisted in source_accounts, so it must not carry the address itself.
    a = AccountRef("github", "a", {"name": None, "email": "jane@example.org", "handle": "a", "links": []})
    b = AccountRef("resume", "", {"name": None, "email": "Jane@Example.org", "handle": None, "links": []})
    result = EmailSignal().score(a, b)
    assert result.score == 1.0
    assert "@" not in result.reason

"""Regression test for the identity defect found in the SE431 M2 Fagan inspection (INS-09 in the report)."""

from pipeline.core.identity.profiles import anchor_ref
from pipeline.core.identity.resolver import IdentityResolver
from pipeline.core.models import AccountRef


def account(source, handle, name=None):
    return AccountRef(source, handle, {"name": name, "email": None, "handle": handle, "links": []})


def test_ins09_hop_confidence_never_exceeds_the_account_it_hops_through():
    anchor = anchor_ref("Octo Developer", "octo@example.org")
    github = account("github", "alex", name="Octo Developer")  # name only: 0.50
    codeforces = account("codeforces", "alex")  # identical handle to github only: 0.60 on its own

    gh_link, cf_link = IdentityResolver().resolve("cand-1", "run-1", anchor, [github, codeforces]).links

    assert gh_link.confidence == 0.5
    assert cf_link.confidence <= gh_link.confidence  # a chain is no stronger than its weakest link
    assert cf_link.linked is True  # the linking decision itself is unchanged at the default threshold

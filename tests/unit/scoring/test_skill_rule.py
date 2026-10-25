from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import Claim, EvidenceNode
from pipeline.core.scoring.rules import SkillClaimRule


def node(node_id, kind="skill", **value):
    return EvidenceNode(node_id, "run-1", "cand-1", "snap-1", "github", "octo", kind, value, "$")


def skill(node_id, name, first=None, last=None):
    return node(node_id, name=name, first_seen=first, last_seen=last)


def claim(subject="Python", years=None):
    return Claim("claim-1", "cand-1", f"{years} years of {subject}", "skill", subject, years=years)


RULE = SkillClaimRule(SkillNormalizer())


def test_no_matching_node_is_unsupported():
    verdict = RULE.verify(claim(years=2), [skill("n1", "Go", "2019-01-01", "2024-01-01")], "run-1")
    assert verdict.label == "unsupported"
    assert verdict.evidence_node_ids == ()


def test_node_without_claimed_duration_is_supported():
    verdict = RULE.verify(claim(), [skill("n1", "Python")], "run-1")
    assert verdict.label == "supported"
    assert verdict.evidence_node_ids == ("n1",)


def test_sufficient_duration_is_supported():
    nodes = [skill("n2", "python", "2020-01-10", "2022-06-01"), skill("n1", "Python 3", "2021-01-01", "2023-02-01")]
    verdict = RULE.verify(claim(years=3), nodes, "run-1")
    assert verdict.label == "supported"
    assert verdict.evidence_node_ids == ("n1", "n2")
    assert "3" in verdict.rationale


def test_insufficient_duration_is_partially_supported():
    verdict = RULE.verify(claim(years=3), [skill("n1", "Python", "2021-01-01", "2023-12-31")], "run-1")
    assert verdict.label == "partially_supported"
    assert "2" in verdict.rationale


def test_fractional_years_need_the_next_whole_year():
    verdict = RULE.verify(claim(years=2.5), [skill("n1", "Python", "2021-01-01", "2023-06-01")], "run-1")
    assert verdict.label == "partially_supported"


def test_dates_missing_with_years_claimed_is_partially_supported():
    verdict = RULE.verify(claim(years=1), [skill("n1", "Python")], "run-1")
    assert verdict.label == "partially_supported"
    assert verdict.evidence_node_ids == ("n1",)


def test_none_dates_are_ignored_and_z_suffix_parses():
    nodes = [skill("n1", "Python", "2019-03-01T10:00:00Z", None), skill("n2", "Python", None, "2022-03-02T00:00:00Z")]
    assert RULE.verify(claim(years=3), nodes, "run-1").label == "supported"


def test_aliases_and_compiler_names_match_via_normalizer():
    verdict = RULE.verify(claim("C++"), [skill("n1", "GNU C++17")], "run-1")
    assert verdict.label == "supported"


def test_contribution_and_achievement_nodes_are_ignored():
    nodes = [node("c1", kind="contribution", repo="python", commits=3), node("a1", kind="achievement", platform="x")]
    assert RULE.verify(claim(), nodes, "run-1").label == "unsupported"


def project(node_id, name, description=None, topics=None, created=None, pushed=None):
    return node(
        node_id,
        kind="project",
        name=name,
        description=description,
        topics=topics or [],
        created_at=created,
        pushed_at=pushed,
    )


def test_one_mentioning_project_is_only_partial():
    # Previously project nodes were ignored, so a project named after the skill gave 'unsupported'.
    verdict = RULE.verify(claim("Django"), [project("p1", "django-blog")], "run-1")
    assert verdict.label == "partially_supported"
    assert verdict.evidence_node_ids == ("p1",)
    assert verdict.rationale == (
        "found in 1 project(s) (django-blog) via name; no duration claimed; "
        "fewer than 2 projects and no language evidence"
    )


def test_two_projects_support_a_framework_claim_without_language_evidence():
    nodes = [project("p2", "api-server", "REST API on Postgres"), project("p1", "evidence-kit", topics=["postgresql"])]
    verdict = RULE.verify(claim("PostgreSQL"), nodes, "run-1")
    assert verdict.label == "supported"
    assert verdict.evidence_node_ids == ("p1", "p2")
    assert verdict.rationale.startswith("found in 2 project(s) (api-server, evidence-kit) via topics/description")


def test_project_duration_runs_from_first_created_to_last_pushed():
    nodes = [
        project("p1", "kit", topics=["react"], created="2021-01-01T00:00:00Z", pushed="2021-06-01T00:00:00Z"),
        project("p2", "ui", "A React.js dashboard", created="2022-01-01T00:00:00Z", pushed="2023-06-01T00:00:00Z"),
    ]
    assert RULE.verify(claim("React", years=2), nodes, "run-1").label == "supported"
    verdict = RULE.verify(claim("React", years=3), nodes, "run-1")
    assert verdict.label == "partially_supported"
    assert "from 2021-01-01 to 2023-06-01 vs 3 claimed (2.41 years elapsed)" in verdict.rationale


def test_one_project_with_enough_years_stays_partial():
    one = project("p1", "kit", topics=["docker"], created="2018-01-01", pushed="2024-01-01")
    assert RULE.verify(claim("Docker", years=2), [one], "run-1").label == "partially_supported"


def test_language_and_project_evidence_are_both_cited():
    nodes = [
        skill("n1", "Python", "2020-01-01", "2020-06-01"),
        project("p1", "py-kit", "Python helpers", created="2018-01-01", pushed="2019-01-01"),
    ]
    verdict = RULE.verify(claim(years=2), nodes, "run-1")
    assert verdict.label == "supported"  # 2018-01-01 to 2020-06-01 across both nodes
    assert verdict.evidence_node_ids == ("n1", "p1")
    assert verdict.rationale.startswith("1 'python' skill node(s) and 1 project(s) (py-kit) via name/description")


def test_ambiguous_skill_in_project_prose_is_not_evidence():
    verdict = RULE.verify(claim("Go"), [project("p1", "todo", "Good to go"), project("p2", "x", "Go on")], "run-1")
    assert verdict.label == "unsupported"


def test_whole_word_mentions_only():
    nodes = [project("p1", "site", "JavaScript widgets"), project("p2", "web", "javascript tools")]
    assert RULE.verify(claim("Java"), nodes, "run-1").label == "unsupported"


def test_verdict_carries_ids():
    verdict = RULE.verify(claim(), [skill("n1", "Python")], "run-9")
    assert (verdict.claim_id, verdict.candidate_id, verdict.run_id) == ("claim-1", "cand-1", "run-9")
    assert RULE.kind == "skill"

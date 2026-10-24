"""RequirementMatcher: exact alias matching, project mentions, semantic fallback and coverage (FR-10)."""

import pytest

from pipeline.adapters.fakes import HashingEmbedder
from pipeline.core.errors import ValidationError
from pipeline.core.inputs import JobRequirementInput
from pipeline.core.matching.matcher import PROJECT_SIMILARITY, RequirementMatcher
from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import EvidenceNode, SkillMatch


def node(node_id: str, kind: str, **value) -> EvidenceNode:
    return EvidenceNode(node_id, "run-1", "cand-1", "snap-1", "github", "octo-dev", kind, value, "$")


def skill(node_id: str, name: str) -> EvidenceNode:
    return node(node_id, "skill", name=name, first_seen="2023-05-02T11:00:00Z", last_seen="2026-09-30T08:11:58Z")


def project(node_id: str, name: str, description: str, language: str | None) -> EvidenceNode:
    return node(node_id, "project", name=name, description=description, language=language, stars=3, url="u")


def job(*skills: str) -> JobRequirementInput:
    return JobRequirementInput("job-1", "Backend Engineer", "We need backend developers.", skills)


def matcher(embedder=None, threshold=0.6) -> RequirementMatcher:
    return RequirementMatcher(SkillNormalizer(), embedder, similarity_threshold=threshold)


class CountingEmbedder(HashingEmbedder):
    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return super().embed(texts)


# Coverage: BVA on 0, partial and all skills matched
def test_no_skill_matched_gives_zero_coverage():
    result = matcher().match(job("Python", "Go"), [skill("n1", "Haskell")])
    assert result.coverage == 0.0
    assert result.matches == (SkillMatch("python", (), 0.0), SkillMatch("go", (), 0.0))


@pytest.mark.parametrize(
    ("required", "expected"), [(("Python", "Go"), 0.5), (("Python", "Go", "Rust"), 1 / 3), (("Python",), 1.0)]
)
def test_partial_and_full_coverage(required, expected):
    result = matcher().match(job(*required), [skill("n1", "py")])
    assert result.coverage == pytest.approx(expected)


def test_all_skills_matched_through_aliases():
    nodes = [skill("n2", "golang"), skill("n1", "Python3"), skill("n3", "GNU C++17")]
    result = matcher().match(job("Python", "Go", "C++"), nodes)
    assert result.coverage == 1.0
    assert [(m.skill, m.node_ids, m.similarity) for m in result.matches] == [
        ("python", ("n1",), 1.0),
        ("go", ("n2",), 1.0),
        ("cpp", ("n3",), 1.0),
    ]


def test_every_matching_node_is_cited_in_sorted_order():
    nodes = [skill("n9", "Python"), skill("n2", "py"), skill("n5", "Go")]
    assert matcher().match(job("python"), nodes).matches[0].node_ids == ("n2", "n9")


def test_required_skills_are_normalised_and_deduplicated_in_order():
    result = matcher().match(job("Python", "Go", "py", "PYTHON", "golang"), [])
    assert [m.skill for m in result.matches] == ["python", "go"]


def test_job_id_is_carried_into_the_result():
    assert matcher().match(job("Python"), []).job_id == "job-1"


def test_contribution_and_achievement_nodes_never_match():
    nodes = [
        node("c1", "contribution", repo="python", commits=4, first="2024", last="2025"),
        node("a1", "achievement", platform="codeforces", rating=1500, max_rating=1600, solved=None),
    ]
    assert matcher().match(job("Python"), nodes).coverage == 0.0


# Project tier: topics, name or description mention the skill (similarity 0.9)
def test_project_name_mention_covers_the_skill_with_project_similarity():
    # Previously only skill nodes counted, so a project called "python" left Python uncovered.
    result = matcher().match(job("Python"), [project("p1", "python", "", "Python")])
    assert result.matches == (SkillMatch("python", ("p1",), PROJECT_SIMILARITY),)


def test_project_topics_and_description_mentions_are_all_cited():
    nodes = [
        node("p2", "project", name="api", description="REST API on Postgres", topics=[]),
        node("p1", "project", name="kit", description=None, topics=["postgresql", "docker"]),
        node("p3", "project", name="blog", description="Static site", topics=["hugo"]),
    ]
    result = matcher().match(job("PostgreSQL", "Docker", "Kubernetes"), nodes)
    assert [(m.skill, m.node_ids) for m in result.matches] == [
        ("postgresql", ("p1", "p2")),
        ("docker", ("p1",)),
        ("kubernetes", ()),
    ]


def test_language_evidence_wins_over_project_mentions():
    nodes = [skill("n1", "Python"), project("p1", "py-tools", "Python helpers", "Python")]
    assert matcher().match(job("Python"), nodes).matches[0] == SkillMatch("python", ("n1",), 1.0)


def test_ambiguous_word_in_description_is_not_a_mention_but_a_topic_is():
    prose = project("p1", "todo", "Ready to go in five minutes", None)
    tagged = node("p2", "project", name="scheduler", description="Cron service", topics=["go"])
    assert matcher().match(job("Go"), [prose]).coverage == 0.0
    assert matcher().match(job("Go"), [prose, tagged]).matches[0].node_ids == ("p2",)


def test_whole_words_only_java_is_not_javascript():
    assert matcher().match(job("Java"), [project("p1", "site", "A JavaScript site", None)]).coverage == 0.0


def test_project_tier_runs_before_the_embedder():
    embedder = CountingEmbedder()
    result = matcher(embedder).match(job("FastAPI"), [project("p1", "svc", "FastAPI service", "Python")])
    assert result.matches[0].similarity == PROJECT_SIMILARITY
    assert embedder.calls == 0


def test_skill_nodes_without_a_name_are_ignored():
    assert matcher().match(job("Python"), [node("n1", "skill", first_seen="x")]).coverage == 0.0


# Semantic fallback (HashingEmbedder)
def test_semantic_fallback_matches_close_skill_name():
    result = matcher(HashingEmbedder()).match(job("Django"), [skill("n1", "Django REST")])
    match = result.matches[0]
    assert match.node_ids == ("n1",)
    assert match.similarity == pytest.approx(0.7071, abs=1e-4)


def test_semantic_fallback_below_threshold_is_not_a_match():
    result = matcher(HashingEmbedder()).match(job("Django"), [skill("n1", "Django REST Framework")])
    assert result.matches[0] == SkillMatch("django", (), 0.0)


def test_semantic_fallback_uses_project_name_description_and_language():
    # "FastAPI service" is not mentioned verbatim, so only the embedding tier can match it.
    nodes = [project("p1", "evidence-kit", "FastAPI backend", "Python"), skill("n1", "Haskell")]
    result = matcher(HashingEmbedder(), threshold=0.3).match(job("FastAPI service"), nodes)
    assert result.matches[0].node_ids == ("p1",)
    assert 0.3 <= result.matches[0].similarity < 1.0


def test_semantic_best_score_is_reported_for_several_hits():
    nodes = [skill("n1", "Django REST"), skill("n2", "Django")]
    result = matcher(HashingEmbedder(), threshold=0.6).match(job("Django"), nodes)
    assert result.matches[0] == SkillMatch("django", ("n2",), 1.0)  # exact match wins, n1 not needed


def test_semantic_hits_are_all_cited_with_the_best_score():
    nodes = [skill("n2", "Django REST"), skill("n1", "Django ORM")]
    result = matcher(HashingEmbedder()).match(job("Django"), nodes)
    assert result.matches[0].node_ids == ("n1", "n2")
    assert result.matches[0].similarity == pytest.approx(0.7071, abs=1e-4)


def test_embedder_is_not_called_when_every_skill_matches_exactly():
    embedder = CountingEmbedder()
    matcher(embedder).match(job("Python"), [skill("n1", "python")])
    assert embedder.calls == 0


def test_semantic_fallback_with_no_nodes_is_uncovered():
    assert matcher(HashingEmbedder()).match(job("Django"), []).coverage == 0.0


@pytest.mark.parametrize(("threshold", "valid"), [(-0.01, False), (0.0, True), (1.0, True), (1.01, False)])
def test_similarity_threshold_boundaries(threshold, valid):
    if valid:
        assert matcher(threshold=threshold)
    else:
        with pytest.raises(ValidationError):
            matcher(threshold=threshold)

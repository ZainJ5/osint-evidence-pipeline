"""Matches job requirements to evidence: language nodes, then project mentions, then embedding similarity (FR-10)."""

from pipeline.core.errors import MatchingError, ValidationError
from pipeline.core.inputs import JobRequirementInput
from pipeline.core.matching.evidence_search import SkillEvidenceSearch
from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.matching.vector_index import InMemoryVectorIndex
from pipeline.core.models import EvidenceNode, MatchResult, SkillMatch
from pipeline.core.ports import Embedder

PROJECT_SIMILARITY = 0.9  # a project whose topics, name or description mention the skill: strong but indirect


class RequirementMatcher:
    """Matches required skills to evidence (M4).

    Tiers, first hit wins: language skill nodes (similarity 1.0), projects mentioning the skill in topics, name or
    description (PROJECT_SIMILARITY), then embedding similarity above the threshold when an embedder is given.
    """

    def __init__(
        self, normalizer: SkillNormalizer, embedder: Embedder | None = None, similarity_threshold: float = 0.6
    ):
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValidationError("similarity_threshold must be in [0, 1]", context={"field": "similarity_threshold"})
        self._normalizer = normalizer
        self._embedder = embedder
        self._threshold = similarity_threshold
        self._search = SkillEvidenceSearch(normalizer)

    def match(self, job: JobRequirementInput, nodes: list[EvidenceNode]) -> MatchResult:
        exact = self._skill_nodes_by_name(nodes)
        index = None
        matches = []
        for skill in self._required_skills(job):
            if skill in exact:
                matches.append(SkillMatch(skill, tuple(sorted(exact[skill])), 1.0))
                continue
            projects = self._search.project_hits(skill, nodes)
            if projects:
                matches.append(SkillMatch(skill, tuple(sorted(hit.node.id for hit in projects)), PROJECT_SIMILARITY))
                continue
            if self._embedder is None:
                matches.append(SkillMatch(skill, (), 0.0))
                continue
            if index is None:  # built once, and only when the first two tiers miss
                index = self._build_index(nodes)
            matches.append(self._semantic_match(skill, index))
        return MatchResult(job.id, tuple(matches))

    def _required_skills(self, job: JobRequirementInput) -> list[str]:
        return list(dict.fromkeys(self._normalizer.normalize(s) for s in job.required_skills))

    def _skill_nodes_by_name(self, nodes: list[EvidenceNode]) -> dict[str, list[str]]:
        by_name: dict[str, list[str]] = {}
        for node in nodes:
            name = node.value.get("name")
            if node.kind == "skill" and isinstance(name, str):
                by_name.setdefault(self._normalizer.normalize(name), []).append(node.id)
        return by_name

    def _build_index(self, nodes: list[EvidenceNode]) -> InMemoryVectorIndex:
        texts = {node.id: text for node in nodes if (text := self._node_text(node))}
        vectors = self._embed(list(texts.values()))
        index = InMemoryVectorIndex()
        for node_id, vector in zip(texts, vectors, strict=True):
            index.upsert(node_id, vector)
        return index

    def _node_text(self, node: EvidenceNode) -> str:
        value = node.value
        if node.kind == "skill":
            name = value.get("name")
            return self._normalizer.normalize(name) if isinstance(name, str) else ""
        if node.kind == "project":
            parts = (value.get("name"), value.get("description"), value.get("language"))
            return " ".join(p for p in parts if isinstance(p, str) and p)
        return ""

    def _semantic_match(self, skill: str, index: InMemoryVectorIndex) -> SkillMatch:
        if not index:
            return SkillMatch(skill, (), 0.0)
        hits = index.search(self._embed([skill])[0], len(index))
        hits = [(node_id, score) for node_id, score in hits if score >= self._threshold]
        if not hits:
            return SkillMatch(skill, (), 0.0)
        return SkillMatch(skill, tuple(sorted(node_id for node_id, _ in hits)), hits[0][1])

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._embedder.embed(texts)
        if len(vectors) != len(texts):
            raise MatchingError("embedder returned the wrong number of vectors", context={"texts": len(texts)})
        return vectors

"""Find a skill in evidence: language skill nodes, and projects whose topics, name or description mention it."""

import re
from dataclasses import dataclass

from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import EvidenceNode
from pipeline.core.skills import allowed_in_prose, mention_regex


@dataclass(frozen=True)
class ProjectHit:
    """A project node that mentions a skill, and the fields that mention it."""

    node: EvidenceNode
    fields: tuple[str, ...]  # subset of ("topics", "name", "description")

    @property
    def name(self) -> str:
        return str(self.node.value.get("name") or self.node.id)


def _name_words(name: str) -> str:
    """'api-server' -> 'api server', 'DjangoBlog' -> 'Django Blog', so repository names read like text."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", re.sub(r"[-_.]+", " ", name))


class SkillEvidenceSearch:
    """Searches evidence nodes for one canonical skill name (already passed through the normaliser)."""

    def __init__(self, normalizer: SkillNormalizer):
        self._normalizer = normalizer
        self._patterns: dict[str, re.Pattern] = {}

    def skill_nodes(self, skill: str, nodes: list[EvidenceNode]) -> list[EvidenceNode]:
        """Language evidence: skill nodes whose name normalises to the skill."""
        return [n for n in nodes if n.kind == "skill" and self._normalizer.normalize(n.value.get("name")) == skill]

    def project_hits(self, skill: str, nodes: list[EvidenceNode]) -> list[ProjectHit]:
        hits = []
        for node in nodes:
            fields = self._mentioning_fields(skill, node.value) if node.kind == "project" else ()
            if fields:
                hits.append(ProjectHit(node, fields))
        return hits

    def _mentioning_fields(self, skill: str, value: dict) -> tuple[str, ...]:
        topics, name, description = value.get("topics"), value.get("name"), value.get("description")
        fields = []
        if isinstance(topics, list) and any(self._is_topic(skill, topic) for topic in topics):
            fields.append("topics")
        if isinstance(name, str) and self._mentions(skill, _name_words(name)):
            fields.append("name")
        if isinstance(description, str) and self._mentions(skill, description):
            fields.append("description")
        return tuple(fields)

    def _is_topic(self, skill: str, topic) -> bool:
        """GitHub topics are exact tags such as 'postgresql' or 'spring-boot', so even 'go' counts here."""
        if not isinstance(topic, str):
            return False
        return skill in (self._normalizer.normalize(topic), self._normalizer.normalize(topic.replace("-", " ")))

    def _mentions(self, skill: str, text: str) -> bool:
        """Whole-word mention of the skill or an alias; ambiguous forms such as 'go' or 'node' are ignored."""
        if skill not in self._patterns:
            self._patterns[skill] = mention_regex(self._normalizer.forms(skill))
        return any(allowed_in_prose(m.group(1), strict_case=False) for m in self._patterns[skill].finditer(text))

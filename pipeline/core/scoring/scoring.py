"""Explainable 0-100 candidate score from verdicts, evidence and requirement match (FR-13)."""

import math
from abc import ABC, abstractmethod

from pipeline.core.errors import ScoringError
from pipeline.core.models import EvidenceNode, MatchResult, ScoreComponent, ScoreReport, Verdict

DEFAULT_WEIGHTS = {
    "verified_skills": 0.35,
    "contribution_depth": 0.20,
    "competitive_programming": 0.15,
    "requirement_match": 0.30,
}
VERDICT_VALUES = {"supported": 1.0, "partially_supported": 0.5, "unsupported": 0.0}
FULL_COMMITS = 200  # commits for a full contribution_depth score
FULL_RATING = 2400  # rating for a full competitive_programming score


class ScoringStrategy(ABC):
    """Strategy that turns verdicts into a score report."""

    @abstractmethod
    def score(
        self,
        run_id: str,
        candidate_id: str,
        job_id: str,
        verdicts: list[Verdict],
        match: MatchResult,
        evidence: list[EvidenceNode],
    ) -> ScoreReport: ...


def _ids(ids) -> tuple[str, ...]:
    return tuple(sorted(set(ids)))


def _verified_skills(verdicts: list[Verdict]) -> tuple[float, tuple]:
    if not verdicts:
        return 0.0, ()
    value = sum(VERDICT_VALUES.get(v.label, 0.0) for v in verdicts) / len(verdicts)
    return value, _ids(i for v in verdicts for i in v.evidence_node_ids)


def _contribution_depth(evidence: list[EvidenceNode]) -> tuple[float, tuple]:
    nodes = [n for n in evidence if n.kind == "contribution"]
    commits = sum(n.value.get("commits") or 0 for n in nodes)
    return min(1.0, commits / FULL_COMMITS), _ids(n.id for n in nodes)


def _competitive_programming(evidence: list[EvidenceNode]) -> tuple[float, tuple]:
    best, used = 0, []
    for n in evidence:
        if n.kind != "achievement" or n.value.get("platform") not in ("codeforces", "leetcode"):
            continue
        ratings = [r for r in (n.value.get("rating"), n.value.get("max_rating")) if r is not None]
        if ratings:
            used.append(n.id)
            best = max(best, *ratings)
    return min(1.0, max(0, best) / FULL_RATING), _ids(used)


def _requirement_match(match: MatchResult) -> tuple[float, tuple]:
    return match.coverage, _ids(i for m in match.matches for i in m.node_ids)


def _validated(weights: dict | None) -> dict:
    merged = {**DEFAULT_WEIGHTS, **(weights or {})}
    unknown = set(merged) - set(DEFAULT_WEIGHTS)
    if unknown:
        raise ScoringError(f"unknown score components {sorted(unknown)}", context={"weights": weights})
    if any(not isinstance(w, (int, float)) or isinstance(w, bool) or not 0 <= w < math.inf for w in merged.values()):
        raise ScoringError("weights must be finite non-negative numbers", context={"weights": weights})  # INS-08
    if sum(merged.values()) <= 0:
        raise ScoringError("weights must sum to more than 0", context={"weights": weights})
    return merged


class WeightedEvidenceScoring(ScoringStrategy):
    """Weighted mean of four evidence-backed components. Given weights override the defaults by name."""

    def __init__(self, weights: dict | None = None):
        self._weights = _validated(weights)

    def score(self, run_id, candidate_id, job_id, verdicts, match, evidence) -> ScoreReport:
        parts = {
            "verified_skills": _verified_skills(verdicts),
            "contribution_depth": _contribution_depth(evidence),
            "competitive_programming": _competitive_programming(evidence),
            "requirement_match": _requirement_match(match),
        }
        components = tuple(
            ScoreComponent(name, self._weights[name], round(value, 4), ids) for name, (value, ids) in parts.items()
        )
        weighted = sum(c.weight * c.value for c in components) / sum(c.weight for c in components)
        total = min(100.0, max(0.0, round(100 * weighted, 2)))
        return ScoreReport(run_id, candidate_id, job_id, total, components, tuple(verdicts))


class ScoreCalculator:
    """Context of the Strategy pattern: swap the scoring strategy through the constructor."""

    def __init__(self, strategy: ScoringStrategy):
        self._strategy = strategy

    def calculate(self, run_id, candidate_id, job_id, verdicts, match, evidence) -> ScoreReport:
        return self._strategy.score(run_id, candidate_id, job_id, verdicts, match, evidence)

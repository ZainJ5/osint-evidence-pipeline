"""Verification rules that check one resume claim against evidence nodes (Strategy pattern, FR-12)."""

import math
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pipeline.core.matching.evidence_search import ProjectHit, SkillEvidenceSearch
from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import Claim, EvidenceNode, Verdict

SUPPORTED, PARTIAL, UNSUPPORTED = "supported", "partially_supported", "unsupported"
PARTIAL_RATING_SHARE = 0.8  # also used for solved counts
MIN_PROJECTS = 2  # without language evidence, a skill needs this many mentioning projects to be 'supported'
DAYS_PER_YEAR = 365.25
DATE_FIELDS = ("first_seen", "last_seen", "created_at", "pushed_at")  # skill nodes, project nodes


class VerificationRule(ABC):
    """Strategy that verifies one kind of claim."""

    kind = ""

    @abstractmethod
    def verify(self, claim: Claim, evidence: list[EvidenceNode], run_id: str) -> Verdict: ...


def _verdict(claim: Claim, run_id: str, label: str, nodes: list[EvidenceNode], rationale: str) -> Verdict:
    ids = tuple(sorted({n.id for n in nodes}))
    return Verdict(claim.id, run_id, claim.candidate_id, label, ids, rationale)


def _parse_date(value) -> datetime | None:
    """ISO-8601 to naive UTC; None for missing or unparseable values. Handles 'Z' on Python 3.10."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _seen_dates(nodes: list[EvidenceNode]) -> list[datetime]:
    raw = [n.value.get(name) for n in nodes for name in DATE_FIELDS]
    return [d for d in map(_parse_date, raw) if d]


def _whole_years(start: datetime, end: datetime) -> int:
    return end.year - start.year - ((end.month, end.day) < (start.month, start.day))


def _elapsed_years(start: datetime, end: datetime) -> float:
    """Fractional years, for fractional claims such as 2.5 years (INS-05). Below N for any span short of N years."""
    return (end - start).days / DAYS_PER_YEAR


def _describe(skill: str, languages: list[EvidenceNode], projects: list[ProjectHit]) -> str:
    """Says exactly what was found, e.g. "found in 2 project(s) (evidence-kit, api-server) via topics/description"."""
    via = "/".join(f for f in ("topics", "name", "description") if any(f in hit.fields for hit in projects))
    found_in = f"{len(projects)} project(s) ({', '.join(sorted(hit.name for hit in projects))}) via {via}"
    if not languages:
        return f"found in {found_in}"
    language = f"{len(languages)} '{skill}' skill node(s)"
    return f"{language} and {found_in}" if projects else language


class SkillClaimRule(VerificationRule):
    """Verifies a skill claim against language evidence and against projects that mention the skill.

    supported: language evidence, or at least MIN_PROJECTS mentioning projects, and the claimed years (if any) fit
    between the earliest and latest evidence date. partially_supported: only one project, or the duration is short
    or cannot be checked. unsupported: no evidence at all.
    """

    kind = "skill"

    def __init__(self, normalizer: SkillNormalizer):
        self._normalizer = normalizer
        self._search = SkillEvidenceSearch(normalizer)

    def verify(self, claim: Claim, evidence: list[EvidenceNode], run_id: str) -> Verdict:
        wanted = self._normalizer.normalize(claim.subject)
        languages = self._search.skill_nodes(wanted, evidence)
        projects = self._search.project_hits(wanted, evidence)
        nodes = languages + [hit.node for hit in projects]
        if not nodes:
            return _verdict(claim, run_id, UNSUPPORTED, [], f"no '{wanted}' skill evidence found")
        found = _describe(wanted, languages, projects)
        enough = bool(languages) or len(projects) >= MIN_PROJECTS
        note = "" if enough else f"; fewer than {MIN_PROJECTS} projects and no language evidence"
        if claim.years is None:
            return _verdict(
                claim, run_id, SUPPORTED if enough else PARTIAL, nodes, f"{found}; no duration claimed{note}"
            )
        label, duration = _duration_check(claim.years, nodes)
        return _verdict(claim, run_id, label if enough else PARTIAL, nodes, f"{found}{duration}{note}")


def _duration_check(years: float, nodes: list[EvidenceNode]) -> tuple[str, str]:
    """Label and rationale suffix for a claimed number of years against the evidence dates."""
    dates = _seen_dates(nodes)
    if not dates:
        return PARTIAL, f" but no dates to check {years:g} claimed year(s)"
    start, end = min(dates), max(dates)
    observed, elapsed = _whole_years(start, end), _elapsed_years(start, end)
    label = SUPPORTED if observed >= years or elapsed >= years else PARTIAL
    rationale = (
        f"; observed {observed} whole year(s) from {start.date()} to {end.date()} "
        f"vs {years:g} claimed ({elapsed:.2f} years elapsed)"
    )
    return label, rationale


def _comparison(best: int, claimed: int) -> str:
    """Plain-language comparison that always agrees with _threshold_label."""
    if best >= claimed:
        return f"meets the claimed {claimed}"
    percent = math.floor(1000 * best / claimed) / 10  # floored, so 79.96 % never reads as "80 %"
    share = f"{percent:g}% of the claimed {claimed}"
    if best >= PARTIAL_RATING_SHARE * claimed:
        return f"{share} (partial from 80%)"
    return f"only {share} (below 80%)"


def _threshold_label(best: int, claimed: int) -> str:
    if best >= claimed:
        return SUPPORTED
    return PARTIAL if best >= PARTIAL_RATING_SHARE * claimed else UNSUPPORTED


class RatingClaimRule(VerificationRule):
    """Verifies a rating claim against achievement evidence: supported at or above, partial from 80 %."""

    kind = "rating"

    def verify(self, claim: Claim, evidence: list[EvidenceNode], run_id: str) -> Verdict:
        platform = claim.subject.lower()
        used, ratings, ranks = [], [], []
        for n in evidence:
            if n.kind == "achievement" and n.value.get("platform") == platform:
                found = [r for r in (n.value.get("rating"), n.value.get("max_rating")) if r is not None]
                used += [n] if found else []
                ratings += found
                ranks += [n.value["rank"]] if found and n.value.get("rank") else []
        if not ratings or not claim.rating:
            return _verdict(claim, run_id, UNSUPPORTED, [], f"no {platform} rating evidence found")
        best = max(ratings)
        rank = f" (rank {', '.join(sorted(set(ranks)))})" if ranks else ""
        rationale = f"best observed {platform} rating {best}{rank} {_comparison(best, claim.rating)}"
        return _verdict(claim, run_id, _threshold_label(best, claim.rating), used, rationale)


class SolvedClaimRule(VerificationRule):
    """Verifies a solved-problems claim against achievement solved counts: supported at or above, partial from 80 %."""

    kind = "solved"

    def verify(self, claim: Claim, evidence: list[EvidenceNode], run_id: str) -> Verdict:
        platform = claim.subject.lower()
        used = [
            n
            for n in evidence
            if n.kind == "achievement" and n.value.get("platform") == platform and n.value.get("solved") is not None
        ]
        if not used or not claim.solved:
            return _verdict(claim, run_id, UNSUPPORTED, [], f"no {platform} solved-problem evidence found")
        best = max(n.value["solved"] for n in used)
        rationale = f"{best} {platform} problems solved observed, {_comparison(best, claim.solved)}"
        return _verdict(claim, run_id, _threshold_label(best, claim.solved), used, rationale)


def default_rules(normalizer: SkillNormalizer) -> list[VerificationRule]:
    """One rule per claim kind, for ClaimVerifier."""
    return [SkillClaimRule(normalizer), RatingClaimRule(), SolvedClaimRule()]

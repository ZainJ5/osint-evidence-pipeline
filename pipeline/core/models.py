"""Immutable value objects exchanged between modules (data coupling only).

Every object that is a result carries run_id (and snapshot_id where it applies) so that it can be
audited back to the raw fetch (QR-15).
"""

from dataclasses import dataclass, field
from datetime import datetime

SOURCES = ("github", "codeforces", "leetcode")
EVIDENCE_KINDS = ("skill", "project", "contribution", "achievement")
VERDICT_LABELS = ("supported", "partially_supported", "unsupported")
RUN_STATUSES = ("running", "partial", "done", "failed")


# Persistence records
@dataclass(frozen=True)
class CandidateRecord:
    """Persisted candidate."""

    id: str
    name: str
    email: str
    resume_text: str
    handles: dict
    created_at: datetime


@dataclass(frozen=True)
class RunRecord:
    """Persisted pipeline run and its status."""

    id: str
    candidate_id: str
    job_id: str
    status: str  # one of RUN_STATUSES
    started_at: datetime
    finished_at: datetime | None = None
    config: dict = field(default_factory=dict)
    failures: tuple[tuple[str, str], ...] = ()
    replay_of: str | None = None


# M1 Source Collection
@dataclass(frozen=True)
class RawFetch:
    """One raw HTTP response collected from a source."""

    source: str
    handle: str
    endpoint: str
    payload: bytes
    fetched_at: datetime


@dataclass(frozen=True)
class CollectionResult:
    """All fetches of a run plus per-source failures."""

    fetches: tuple[RawFetch, ...]
    failures: tuple[tuple[str, str], ...] = ()  # (source, error code)

    @property
    def partial(self) -> bool:
        return bool(self.failures)


# M2 Snapshot Store and Evidence Extraction
@dataclass(frozen=True)
class Snapshot:
    """Immutable, content-addressed copy of a raw fetch."""

    id: str
    run_id: str
    candidate_id: str
    source: str
    handle: str
    endpoint: str
    object_key: str
    sha256: str
    fetched_at: datetime
    size: int


@dataclass(frozen=True)
class EvidenceNode:
    """One piece of evidence extracted from a snapshot."""

    id: str
    run_id: str
    candidate_id: str
    snapshot_id: str
    source: str
    handle: str
    kind: str  # one of EVIDENCE_KINDS
    value: dict
    locator: str  # e.g. JSON path "$[3].language"


# M3 Identity Resolution
@dataclass(frozen=True)
class AccountRef:
    """A candidate's account on one source with its parsed profile."""

    source: str
    handle: str
    profile: dict  # parsed profile fields: name, email, blog, links, etc.


@dataclass(frozen=True)
class SignalScore:
    """Score of one identity signal for an account pair."""

    signal: str
    score: float  # in [0, 1]
    reason: str


@dataclass(frozen=True)
class AccountLink:
    """Decision linking an account to a candidate, with signal scores."""

    candidate_id: str
    run_id: str
    source: str
    handle: str
    confidence: float
    linked: bool
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class CandidateProfile:
    """The accounts linked to one candidate."""

    candidate_id: str
    links: tuple[AccountLink, ...]

    def linked_handles(self) -> set[tuple[str, str]]:
        return {(link.source, link.handle) for link in self.links if link.linked}


# M4 Semantic Matching
@dataclass(frozen=True)
class SkillMatch:
    """Evidence nodes that satisfy one required skill."""

    skill: str
    node_ids: tuple[str, ...]
    similarity: float = 1.0

    @property
    def covered(self) -> bool:
        return bool(self.node_ids)


@dataclass(frozen=True)
class MatchResult:
    """Requirement match of a candidate against one job."""

    job_id: str
    matches: tuple[SkillMatch, ...]

    @property
    def coverage(self) -> float:
        if not self.matches:
            return 0.0
        return sum(1 for m in self.matches if m.covered) / len(self.matches)


# M5 Claim Verification and Scoring
@dataclass(frozen=True)
class Claim:
    """A claim extracted from the resume."""

    id: str
    candidate_id: str
    text: str
    kind: str  # "skill", "rating" or "solved"
    subject: str  # skill name, or platform ("codeforces"/"leetcode") for rating and solved claims
    years: float | None = None
    rating: int | None = None
    solved: int | None = None  # number of problems claimed, for kind "solved"


@dataclass(frozen=True)
class Verdict:
    """Verification outcome of one claim against evidence."""

    claim_id: str
    run_id: str
    candidate_id: str
    label: str  # one of VERDICT_LABELS
    evidence_node_ids: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class ScoreComponent:
    """One weighted component of the final score."""

    name: str
    weight: float
    value: float  # in [0, 1]
    evidence_node_ids: tuple[str, ...]


@dataclass(frozen=True)
class ScoreReport:
    """Explainable final score of a run."""

    run_id: str
    candidate_id: str
    job_id: str
    total: float  # in [0, 100]
    components: tuple[ScoreComponent, ...]
    verdicts: tuple[Verdict, ...] = field(default=())
    matches: tuple[SkillMatch, ...] = field(default=())  # per required skill, so the report can show the match

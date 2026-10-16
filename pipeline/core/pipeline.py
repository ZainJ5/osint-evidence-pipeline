"""PipelineRun orchestrator: the only class that knows the order of the ESRC stages."""

import asyncio
import dataclasses
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from pipeline.core.collection import CollectionRunner, CollectorFactory
from pipeline.core.errors import PipelineError, ResolutionError, ValidationError
from pipeline.core.identity.profiles import anchor_ref, build_account_ref
from pipeline.core.identity.resolver import IdentityResolver
from pipeline.core.inputs import CandidateInput, JobRequirementInput, RunConfig
from pipeline.core.intake import extract_links
from pipeline.core.log import log_event
from pipeline.core.matching.matcher import RequirementMatcher
from pipeline.core.matching.normalizer import SkillNormalizer
from pipeline.core.models import CandidateProfile, CandidateRecord, Claim, RunRecord, ScoreReport
from pipeline.core.ports import BlobStore, CandidateEraser, Embedder, HttpClient, LLMProvider, Repository
from pipeline.core.scoring.claims import ClaimExtractor
from pipeline.core.scoring.rules import default_rules
from pipeline.core.scoring.scoring import ScoreCalculator, ScoringStrategy, WeightedEvidenceScoring
from pipeline.core.scoring.verifier import ClaimVerifier
from pipeline.core.snapshot.extractor import EvidenceExtractor
from pipeline.core.snapshot.parsers import default_parsers
from pipeline.core.snapshot.store import SnapshotStore

log = logging.getLogger("pipeline.run")

PROFILE_ENDPOINTS = {"github/user", "codeforces/user.info", "leetcode/profile"}


@dataclass
class Repositories:
    """Repository ports used by the pipeline."""

    candidates: Repository
    job_requirements: Repository
    runs: Repository
    source_accounts: Repository
    snapshots: Repository
    evidence_nodes: Repository
    claims: Repository
    verdicts: Repository
    score_reports: Repository


@dataclass(frozen=True)
class ReplayResult:
    """Replayed report and whether it matches the original run."""

    report: ScoreReport
    evidence_identical: bool
    score_identical: bool


class RunObserver(ABC):
    """Observer notified when each stage of a run starts and finishes (status "started" or "done")."""

    @abstractmethod
    def on_event(self, run_id: str, stage: str, status: str, detail: dict) -> None: ...


class _Stages:
    """Reports stage progress to the log and, if given, to an observer that must never break the run."""

    def __init__(self, run: RunRecord, observer: RunObserver | None):
        self.run = run
        self._observer = observer

    def started(self, stage: str) -> None:
        self._notify(stage, "started", {})

    def done(self, stage: str, **detail) -> None:
        log_event(log, "stage_done", run_id=self.run.id, candidate_id=self.run.candidate_id, stage=stage, **detail)
        self._notify(stage, "done", detail)

    def _notify(self, stage: str, status: str, detail: dict) -> None:
        if self._observer is None:
            return
        try:
            self._observer.on_event(self.run.id, stage, status, detail)
        except Exception as exc:  # pylint: disable=broad-exception-caught  # a progress display never fails a run
            log_event(
                log, "observer_failed", logging.WARNING, run_id=self.run.id, stage=stage, error=type(exc).__name__
            )


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PipelineRun:
    """Orchestrates M1-M5 for one candidate and job."""

    def __init__(
        self,
        repos: Repositories,
        blob_store: BlobStore,
        http: HttpClient,
        llm: LLMProvider,
        eraser: CandidateEraser,
        embedder: Embedder | None = None,
        config: RunConfig | None = None,
        scoring: ScoringStrategy | None = None,
    ):
        self._repos = repos
        self._http = http
        self._eraser = eraser
        self._llm = llm
        self._config = config or RunConfig()
        normalizer = SkillNormalizer()
        self._store = SnapshotStore(blob_store, repos.snapshots)
        self._extractor = EvidenceExtractor(self._store, default_parsers(), self._config.extraction_workers)
        # One runner for the lifetime of the pipeline, so concurrent runs share one rate limiter per source (INS-01).
        self._runner = CollectionRunner(CollectorFactory, http, self._config)
        self._matcher = RequirementMatcher(normalizer, embedder)
        self._claims = ClaimExtractor(llm)
        self._verifier = ClaimVerifier(default_rules(normalizer))
        self._calculator = ScoreCalculator(scoring or WeightedEvidenceScoring())

    @property
    def repos(self) -> Repositories:
        return self._repos

    @property
    def snapshot_store(self) -> SnapshotStore:
        return self._store

    @property
    def extractor_name(self) -> str:
        """Name of the claim extraction provider, e.g. "rule-based" or "claude"."""
        return getattr(self._llm, "name", "rule-based")

    async def execute(
        self,
        candidate: CandidateInput,
        job: JobRequirementInput,
        run_id: str | None = None,
        observer: RunObserver | None = None,
    ) -> ScoreReport:
        """Register the candidate, run every stage, and persist each result with the run id (FR-01..FR-13)."""
        self.register_job(job)
        record = CandidateRecord(
            str(uuid.uuid4()), candidate.name, candidate.email, candidate.resume_text, dict(candidate.handles), _now()
        )
        self._repos.candidates.add(record)
        run = RunRecord(run_id or str(uuid.uuid4()), record.id, job.id, "running", _now(), config=asdict(self._config))
        self._repos.runs.add(run)
        log_event(log, "run_started", run_id=run.id, candidate_id=record.id, sources=sorted(candidate.handles))
        stages = _Stages(run, observer)
        try:
            stages.started("collect")
            collected = await self._runner.run(dict(candidate.handles))
            stages.done("collect", fetches=len(collected.fetches), failures=[list(f) for f in collected.failures])
            stages.started("freeze")
            snapshots = {self._store.freeze(raw, run.id, record.id).id for raw in collected.fetches}
            stages.done("freeze", snapshots=len(snapshots))
            report, _ = await self._analyse(stages, record, job, persist=True)
        except PipelineError as exc:
            self._fail(run, exc.code, exc.message)
            raise
        except Exception as exc:  # a bug, not a source failure: still never leave the run 'running' (INS-04)
            self._fail(run, "UNEXPECTED_ERROR", type(exc).__name__)
            raise
        status = "partial" if collected.partial else "done"
        self._repos.runs.add(
            RunRecord(**{**asdict(run), "status": status, "finished_at": _now(), "failures": collected.failures})
        )
        log_event(log, "run_finished", run_id=run.id, status=status, total=report.total)
        return report

    async def replay(self, run_id: str) -> ReplayResult:
        """Recompute a finished run from its stored snapshots only; nothing is fetched or written (FR-14)."""
        run = self._repos.runs.get(run_id)
        if run is None or run.status not in ("done", "partial"):
            raise ValidationError("run not found or not finished", code="RUN_NOT_FOUND", context={"run_id": run_id})
        record = self._repos.candidates.get(run.candidate_id)
        job = self._repos.job_requirements.get(run.job_id)
        report, replayed_nodes = await self._analyse(_Stages(run, None), record, job, persist=False)
        stored_nodes = self._repos.evidence_nodes.list_by(run_id=run_id)
        original = self._repos.score_reports.get(run_id)
        result = ReplayResult(
            report,
            evidence_identical=_node_set(stored_nodes) == _node_set(replayed_nodes),
            score_identical=original == report,  # total, components and verdicts (INS-06)
        )
        log_event(
            log,
            "run_replayed",
            run_id=run_id,
            evidence_identical=result.evidence_identical,
            score_identical=result.score_identical,
        )
        return result

    def preview_claims(self, resume_text: str) -> list[Claim]:
        """The claims a run would extract from this resume; nothing is stored."""
        return self._claims.extract("preview", resume_text)

    async def aclose(self) -> None:
        """Close the HTTP client, if it holds connections (INS-11)."""
        close = getattr(self._http, "aclose", None)
        if close is not None:
            await close()

    def report(self, run_id: str) -> ScoreReport | None:
        return self._repos.score_reports.get(run_id)

    def delete_candidate(self, candidate_id: str) -> None:
        """FR-16: remove every stored row and snapshot blob for the candidate."""
        if self._repos.candidates.get(candidate_id) is None:
            raise ValidationError("candidate not found", code="CANDIDATE_NOT_FOUND")
        self._eraser.delete_candidate(candidate_id)
        log_event(log, "candidate_deleted", candidate_id=candidate_id)

    def register_job(self, job: JobRequirementInput) -> None:
        """A job id names one fixed set of requirements, or replay would score against another job (INS-02)."""
        stored = self._repos.job_requirements.get(job.id)
        if stored is None:
            self._repos.job_requirements.add(job)
        elif stored != job:
            raise ValidationError(
                "job id is already used for different requirements", code="JOB_CONFLICT", context={"job_id": job.id}
            )

    def _fail(self, run: RunRecord, code: str, error: str) -> None:
        self._repos.runs.add(RunRecord(**{**asdict(run), "status": "failed", "finished_at": _now()}))
        log_event(log, "run_failed", logging.ERROR, run_id=run.id, code=code, error=error)

    async def _analyse(self, stages: _Stages, record, job, persist: bool) -> tuple[ScoreReport, list]:
        """Extract, resolve, match, verify and score. Returns the report and every extracted node."""
        run = stages.run
        stages.started("extract")
        nodes = await self._extractor.extract_run(run.id, record.id)
        stages.done("extract", nodes=len(nodes))
        profile, evidence = self._resolve(stages, record, nodes)
        stages.started("match")
        match = self._matcher.match(job, evidence)
        stages.done("match", coverage=match.coverage)
        stages.started("verify")
        claims = await asyncio.to_thread(self._claims_for, record, not persist)  # an LLM call blocks
        verdicts = self._verifier.verify_all(claims, evidence, run.id)
        stages.done("verify", claims=len(claims))
        stages.started("score")
        report = self._calculator.calculate(run.id, record.id, job.id, verdicts, match, evidence)
        report = dataclasses.replace(report, matches=match.matches)
        stages.done("score", total=report.total)
        if persist:
            for item in [*nodes, *profile.links, *claims, *verdicts, report]:
                self._repository_for(item).add(item)
        return report, nodes

    def _resolve(self, stages: _Stages, record: CandidateRecord, nodes: list) -> tuple[CandidateProfile, list]:
        """Link the accounts and keep only the evidence of linked accounts (FR-09)."""
        run = stages.run
        stages.started("resolve")
        # The threshold recorded with the run, so a replay after a configuration change reproduces it (INS-03).
        resolver = IdentityResolver(threshold=run.config.get("link_threshold", self._config.link_threshold))
        anchor = anchor_ref(record.name, record.email, extract_links(record.resume_text))  # resume links are evidence
        profile = resolver.resolve(record.id, run.id, anchor, self._accounts(run))
        linked = profile.linked_handles()
        evidence = [n for n in nodes if (n.source, n.handle) in linked]
        stages.done("resolve", linked=sorted(f"{s}:{h}" for s, h in linked), kept_nodes=len(evidence))
        return profile, evidence

    def _claims_for(self, record: CandidateRecord, stored: bool) -> list[Claim]:
        """Replay reuses the stored claims, as a real LLM may answer differently (NFR-07). Sorted by id for both."""
        claims = self._repos.claims.list_by(candidate_id=record.id) if stored else []
        return sorted(claims or self._claims.extract(record.id, record.resume_text), key=lambda c: c.id)

    def _accounts(self, run: RunRecord) -> list:
        accounts = []
        for snapshot in self._store.list_for_run(run.id):
            if snapshot.endpoint not in PROFILE_ENDPOINTS:
                continue
            _, payload = self._store.load(snapshot.id)
            try:
                accounts.append(build_account_ref(snapshot.source, snapshot.handle, payload))
            except ResolutionError as exc:
                log_event(log, "profile_skipped", logging.WARNING, run_id=run.id, source=snapshot.source, code=exc.code)
        return accounts

    def _repository_for(self, item) -> Repository:
        names = {
            "EvidenceNode": "evidence_nodes",
            "AccountLink": "source_accounts",
            "Claim": "claims",
            "Verdict": "verdicts",
            "ScoreReport": "score_reports",
        }
        return getattr(self._repos, names[type(item).__name__])


def _node_set(nodes) -> set:
    return {(n.id, n.snapshot_id, n.kind, n.locator, repr(sorted(n.value.items()))) for n in nodes}

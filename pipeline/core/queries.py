"""Read side for the web UI: run progress kept in memory, and runs rendered as plain JSON-ready dicts."""

import json
from datetime import datetime, timezone

from pipeline.core.errors import ValidationError
from pipeline.core.models import AccountLink, Claim, EvidenceNode, ScoreReport, Snapshot, Verdict
from pipeline.core.pipeline import Repositories, RunObserver
from pipeline.core.snapshot.store import SnapshotStore

# Labels and formulas shown next to each score component; they describe pipeline/core/scoring/scoring.py.
COMPONENTS = {
    "verified_skills": ("Verified resume claims", "mean over claims: supported 1, partial 0.5, unsupported 0"),
    "contribution_depth": ("Contribution depth", "min(1, commits across linked GitHub repos / 200)"),
    "competitive_programming": ("Competitive programming", "min(1, best Codeforces/LeetCode rating / 2400)"),
    "requirement_match": ("Job requirement coverage", "share of required skills with matching evidence"),
}
PROFILE_URLS = {
    "github": "https://github.com/{}",
    "codeforces": "https://codeforces.com/profile/{}",
    "leetcode": "https://leetcode.com/u/{}/",
}
FINISHED = "finished"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def mask_email(email: str) -> str:
    local, _, domain = (email or "").partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


class RunProgress(RunObserver):
    """In-memory progress events per run (Observer); lost when the process restarts."""

    def __init__(self):
        self._events: dict[str, list[dict]] = {}

    def on_event(self, run_id: str, stage: str, status: str, detail: dict) -> None:
        event = {"stage": stage, "status": status, "at": _iso(datetime.now(timezone.utc)), "detail": detail}
        self._events.setdefault(run_id, []).append(event)

    def events(self, run_id: str) -> list[dict]:
        return list(self._events.get(run_id, []))


def snapshot_out(snapshot: Snapshot) -> dict:
    return {
        "id": snapshot.id,
        "source": snapshot.source,
        "handle": snapshot.handle,
        "endpoint": snapshot.endpoint,
        "sha256": snapshot.sha256,
        "size": snapshot.size,
        "fetched_at": _iso(snapshot.fetched_at),
    }


def _account_out(link: AccountLink) -> dict:
    return {
        "source": link.source,
        "handle": link.handle,
        "profile_url": PROFILE_URLS.get(link.source, "{}").format(link.handle),
        "confidence": link.confidence,
        "linked": link.linked,
        "rationale": list(link.rationale),
    }


def _evidence_out(node: EvidenceNode, linked: set) -> dict:
    return {
        "id": node.id,
        "snapshot_id": node.snapshot_id,
        "source": node.source,
        "handle": node.handle,
        "kind": node.kind,
        "value": node.value,
        "locator": node.locator,
        "linked": (node.source, node.handle) in linked,
    }


def _report_out(report: ScoreReport | None) -> dict | None:
    if report is None:
        return None
    weights = sum(c.weight for c in report.components) or 1.0
    components = []
    for c in report.components:
        label, formula = COMPONENTS.get(c.name, (c.name, ""))
        components.append(
            {
                "name": c.name,
                "label": label,
                "weight": c.weight,
                "value": c.value,
                "contribution": round(100 * c.weight * c.value / weights, 2),
                "formula": formula,
                "evidence_node_ids": list(c.evidence_node_ids),
            }
        )
    return {"total": report.total, "components": components}


def _matches_out(report: ScoreReport | None) -> list[dict]:
    matches = report.matches if report else ()
    return [
        {"skill": m.skill, "covered": m.covered, "similarity": m.similarity, "node_ids": list(m.node_ids)}
        for m in matches
    ]


class RunQueries:
    """Builds the run list, run detail and raw snapshot views of docs/api-contract.md."""

    def __init__(self, repos: Repositories, store: SnapshotStore, progress: RunProgress):
        self._repos = repos
        self._store = store
        self._progress = progress

    def list_runs(self, limit: int = 50) -> list[dict]:
        runs = sorted(self._repos.runs.list_by(), key=lambda r: r.started_at, reverse=True)[: max(0, limit)]
        return [self._summary(run) for run in runs]

    def run_detail(self, run_id: str) -> dict:
        run = self._repos.runs.get(run_id)
        candidate = self._repos.candidates.get(run.candidate_id) if run else None
        if candidate is None:
            raise ValidationError("run not found", code="RUN_NOT_FOUND", context={"run_id": run_id})
        job = self._repos.job_requirements.get(run.job_id)
        report = self._repos.score_reports.get(run_id)
        accounts = sorted(self._repos.source_accounts.list_by(run_id=run_id), key=lambda a: (a.source, a.handle))
        linked = {(a.source, a.handle) for a in accounts if a.linked}
        nodes = sorted(self._repos.evidence_nodes.list_by(run_id=run_id), key=lambda n: (n.source, n.kind, n.id))
        progress = self._progress.events(run_id)
        return {
            "run": self._run_out(run, progress),
            "progress": progress,
            "candidate": {
                "id": candidate.id,
                "name": candidate.name,
                "email_masked": mask_email(candidate.email),
                "handles": dict(candidate.handles),
                "resume_text": candidate.resume_text,
            },
            "job": {"id": job.id, "title": job.title, "text": job.text, "required_skills": list(job.required_skills)},
            "accounts": [_account_out(a) for a in accounts],
            "snapshots": [snapshot_out(s) for s in self._store.list_for_run(run_id)],
            "evidence": [_evidence_out(n, linked) for n in nodes],
            "claims": self._claims_out(run_id, candidate.id),
            "matches": _matches_out(report),
            "coverage": round(_coverage(report), 4),
            "report": _report_out(report),
        }

    def snapshot_raw(self, snapshot_id: str) -> dict:
        """The frozen payload, hash-verified on read (SnapshotError HASH_MISMATCH otherwise)."""
        snapshot, payload = self._store.load(snapshot_id)
        try:
            parsed = json.loads(payload)
        except ValueError:
            parsed = payload.decode("utf-8", errors="replace")
        return {"snapshot": snapshot_out(snapshot), "verified": True, "payload": parsed}

    def _summary(self, run) -> dict:
        candidate = self._repos.candidates.get(run.candidate_id)
        job = self._repos.job_requirements.get(run.job_id)
        report = self._repos.score_reports.get(run.id)
        return {
            "run_id": run.id,
            "candidate_id": run.candidate_id,
            "candidate_name": candidate.name if candidate else None,
            "job_id": run.job_id,
            "job_title": job.title if job else None,
            "status": run.status,
            "started_at": _iso(run.started_at),
            "finished_at": _iso(run.finished_at),
            "total": report.total if report else None,
            "sources": sorted(candidate.handles) if candidate else [],
        }

    @staticmethod
    def _run_out(run, progress: list[dict]) -> dict:
        stage = progress[-1]["stage"] if progress else "collect"
        if run.status != "running":
            stage = FINISHED
        return {
            "id": run.id,
            "status": run.status,
            "stage": stage,
            "started_at": _iso(run.started_at),
            "finished_at": _iso(run.finished_at),
            "failures": [{"source": source, "code": code} for source, code in run.failures],
            "config": dict(run.config),
        }

    def _claims_out(self, run_id: str, candidate_id: str) -> list[dict]:
        verdicts = {v.claim_id: v for v in self._repos.verdicts.list_by(run_id=run_id)}
        claims = sorted(self._repos.claims.list_by(candidate_id=candidate_id), key=lambda c: c.id)
        return [{**_claim_out(c), "verdict": _verdict_out(verdicts.get(c.id))} for c in claims]


def _claim_out(claim: Claim) -> dict:
    fields = ("id", "text", "kind", "subject", "years", "rating", "solved")
    return {f: getattr(claim, f) for f in fields}


def _verdict_out(verdict: Verdict | None) -> dict | None:
    if verdict is None:
        return None
    return {
        "label": verdict.label,
        "rationale": verdict.rationale,
        "evidence_node_ids": list(verdict.evidence_node_ids),
    }


def _coverage(report: ScoreReport | None) -> float:
    if report is None or not report.matches:
        return 0.0
    return sum(1 for m in report.matches if m.covered) / len(report.matches)

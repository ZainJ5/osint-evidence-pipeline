"""REST API (FR-15, docs/api-contract.md): thin entry points that call the orchestrator. No business logic here."""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pipeline.adapters.resume_reader import MAX_BYTES, read_resume
from pipeline.core.errors import PipelineError, ValidationError
from pipeline.core.inputs import CandidateInput, JobRequirementInput
from pipeline.core.intake import detect_email, detect_handles, extract_links, guess_name
from pipeline.core.log import configure_logging
from pipeline.core.queries import RunProgress, RunQueries
from pipeline.interface.composition import build_pipeline, storage_name

CONFLICT_CODES = {"JOB_CONFLICT", "HASH_MISMATCH"}
CLAIM_FIELDS = ("text", "kind", "subject", "years", "rating", "solved")


class CandidateBody(BaseModel):
    """Candidate part of a run request."""

    name: str
    email: str
    resume_text: str
    handles: dict[str, str] = Field(default_factory=dict, examples=[{"github": "octocat"}])


class JobBody(BaseModel):
    """Job part of a run request."""

    id: str
    title: str
    text: str = ""
    required_skills: list[str]


class RunBody(BaseModel):
    """Request body for POST /runs."""

    candidate: CandidateBody
    job: JobBody


class ComponentOut(BaseModel):
    """Score component in a response."""

    name: str
    weight: float
    value: float
    evidence_node_ids: list[str]


class VerdictOut(BaseModel):
    """Claim verdict in a response."""

    claim_id: str
    label: str
    evidence_node_ids: list[str]
    rationale: str


class ReportOut(BaseModel):
    """Score report response."""

    run_id: str
    candidate_id: str
    job_id: str
    total: float
    components: list[ComponentOut]
    verdicts: list[VerdictOut]


class ReplayOut(BaseModel):
    """Replay response."""

    report: ReportOut
    evidence_identical: bool
    score_identical: bool


def _inputs(body: RunBody) -> tuple[CandidateInput, JobRequirementInput]:
    candidate = CandidateInput(**body.candidate.model_dump())
    job = JobRequirementInput(**{**body.job.model_dump(), "required_skills": tuple(body.job.required_skills)})
    return candidate, job


def _status(exc: PipelineError) -> int:
    if exc.code in CONFLICT_CODES:
        return 409
    if exc.code.endswith("NOT_FOUND"):
        return 404
    return 422 if isinstance(exc, ValidationError) else 502


class Runtime:
    """What the endpoints share: the pipeline, the read side, run progress and the background runs."""

    def __init__(self, pipeline, storage: str):
        self.pipeline = pipeline
        self.storage = storage
        self.progress = RunProgress()
        self.queries = RunQueries(pipeline.repos, pipeline.snapshot_store, self.progress)
        self._tasks: set[asyncio.Task] = set()  # strong references, so background runs are not garbage-collected

    async def start(self, candidate: CandidateInput, job: JobRequirementInput) -> str:
        self.pipeline.register_job(job)  # JOB_CONFLICT is answered now, not discovered by the background run
        run_id = str(uuid.uuid4())
        task = asyncio.create_task(self.pipeline.execute(candidate, job, run_id=run_id, observer=self.progress))
        self._tasks.add(task)
        task.add_done_callback(self._forget)
        await asyncio.sleep(0)  # the run writes its record before its first await, so the id is readable at once
        return run_id

    def _forget(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        if not task.cancelled():
            task.exception()  # already logged and recorded as a failed run; retrieved so asyncio does not warn

    async def close(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await self.pipeline.aclose()  # INS-11: release the HTTP connection pool


def _runtime(request: Request) -> Runtime:
    return request.app.state.runtime


App = Annotated[Runtime, Depends(_runtime)]
router = APIRouter()


@router.get("/health")
async def health(rt: App):
    return {"status": "ok", "storage": rt.storage, "extractor": rt.pipeline.extractor_name}


@router.post("/resumes/parse")
async def parse_resume(rt: App, file: UploadFile):
    text = read_resume(file.filename or "", await file.read(MAX_BYTES + 1))
    claims = await asyncio.to_thread(rt.pipeline.preview_claims, text)  # a real LLM call must not block the loop
    return {
        "filename": file.filename,
        "text": text,
        "name": guess_name(text),
        "email": detect_email(text),
        "handles": detect_handles(text),
        "links": extract_links(text),
        "claims": [{f: getattr(c, f) for f in CLAIM_FIELDS} for c in claims],
        "extractor": rt.pipeline.extractor_name,
    }


@router.post("/runs", response_model=ReportOut)
async def run(rt: App, body: RunBody):
    return asdict(await rt.pipeline.execute(*_inputs(body)))


@router.post("/runs/start", status_code=202)
async def start_run(rt: App, body: RunBody):
    return {"run_id": await rt.start(*_inputs(body))}


@router.get("/runs")
async def list_runs(rt: App, limit: int = Query(50, ge=1, le=500)):
    return rt.queries.list_runs(limit)


@router.get("/runs/{run_id}")
async def run_detail(rt: App, run_id: str):
    return rt.queries.run_detail(run_id)


@router.get("/snapshots/{snapshot_id}/raw")
async def snapshot_raw(rt: App, snapshot_id: str):
    return rt.queries.snapshot_raw(snapshot_id)


@router.post("/runs/{run_id}/replay", response_model=ReplayOut)
async def replay(rt: App, run_id: str):
    return asdict(await rt.pipeline.replay(run_id))


@router.get("/runs/{run_id}/report", response_model=ReportOut)
async def report(rt: App, run_id: str):
    found = rt.pipeline.report(run_id)
    if found is None:
        raise HTTPException(status_code=404, detail="report not found")
    return asdict(found)


@router.delete("/candidates/{candidate_id}", status_code=204)
async def delete_candidate(rt: App, candidate_id: str):
    rt.pipeline.delete_candidate(candidate_id)


async def _pipeline_error(_request, exc: PipelineError):
    return JSONResponse(status_code=_status(exc), content={"code": exc.code, "message": exc.message})


def create_app(pipeline=None, storage: str | None = None) -> FastAPI:
    configure_logging()
    runtime = Runtime(pipeline or build_pipeline(), storage or storage_name())

    @asynccontextmanager
    async def lifespan(_app):
        yield
        await runtime.close()

    application = FastAPI(title="OSINT Evidence Pipeline", version="0.3.0", lifespan=lifespan)
    application.state.runtime = runtime
    application.state.pipeline = runtime.pipeline
    origins = [o.strip() for o in os.environ.get("UI_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
    application.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
    application.add_exception_handler(PipelineError, _pipeline_error)
    application.include_router(router)
    return application


app = create_app()

"""Composition root: the only place concrete adapters are chosen and injected (DIP)."""

import os

from pipeline.adapters.fakes import (
    HashingEmbedder,
    InMemoryBlobStore,
    in_memory_eraser,
    in_memory_repositories,
)
from pipeline.adapters.http import HttpAdapter
from pipeline.core.inputs import RunConfig
from pipeline.core.pipeline import PipelineRun, Repositories
from pipeline.core.ports import LLMProvider

# pylint: disable=import-outside-toplevel  # optional adapters are imported only when they are chosen


def storage_name() -> str:
    return "postgres" if os.environ.get("DATABASE_URL") else "memory"


def build_claim_provider() -> LLMProvider:
    """Claude when ANTHROPIC_API_KEY is set, otherwise the deterministic rule-based extractor."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from pipeline.adapters.claude_llm import ClaudeClaimProvider

            return ClaudeClaimProvider()
        except ImportError:
            pass
    from pipeline.adapters.rule_claims import RuleBasedClaimProvider

    return RuleBasedClaimProvider()


def build_pipeline(config: RunConfig | None = None) -> PipelineRun:
    """PostgreSQL + MinIO when DATABASE_URL is set, otherwise in-memory storage (local demo)."""
    if storage_name() == "postgres":
        from pipeline.adapters.minio_store import MinioBlobStore
        from pipeline.adapters.postgres import Database, PostgresEraser, build_repositories

        db = Database.from_env()
        repos = Repositories(**build_repositories(db))
        blobs = MinioBlobStore.from_env()
        eraser = PostgresEraser(db, blobs)
    else:
        repos = in_memory_repositories()
        blobs = InMemoryBlobStore()
        eraser = in_memory_eraser(repos, blobs)
    return PipelineRun(repos, blobs, HttpAdapter(), build_claim_provider(), eraser, HashingEmbedder(), config)

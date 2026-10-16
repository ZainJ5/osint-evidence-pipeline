"""PostgreSQL adapters: one generic Repository configured per table, plus the candidate eraser."""

import dataclasses
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from pipeline.core.errors import PipelineError, SnapshotError, ValidationError
from pipeline.core.inputs import JobRequirementInput
from pipeline.core.models import (
    AccountLink,
    CandidateRecord,
    Claim,
    EvidenceNode,
    RunRecord,
    ScoreComponent,
    ScoreReport,
    SkillMatch,
    Snapshot,
    Verdict,
)
from pipeline.core.ports import BlobStore, CandidateEraser, Repository


class Database:
    """One shared autocommit connection guarded by a lock; reconnects if it was closed."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._conn: psycopg.Connection | None = None
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls) -> "Database":
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise PipelineError("DATABASE_URL is not set", code="CONFIG_ERROR")
        return cls(dsn)

    def query(self, statement, params=(), error: type[PipelineError] = PipelineError) -> list[dict]:
        with self._lock:
            try:
                if self._conn is None or self._conn.closed:
                    self._conn = psycopg.connect(
                        self._dsn, autocommit=True, row_factory=dict_row, options="-c TimeZone=UTC"
                    )
                with self._conn.cursor() as cur:
                    cur.execute(statement, params)
                    return cur.fetchall() if cur.description else []
            except psycopg.Error as exc:
                # Parameters are deliberately left out of the context: they may hold personal data.
                raise error(
                    f"database error: {type(exc).__name__}", code="DB_ERROR", context={"sqlstate": exc.sqlstate}
                ) from exc

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()


@dataclass(frozen=True)
class Table:
    """How one model maps onto one SQL table."""

    name: str
    columns: tuple[str, ...]
    key: tuple[str, ...] = ("id",)
    json_columns: tuple[str, ...] = ()
    upsert: bool = False  # only runs: their status changes; every other table is insert-only
    error: type[PipelineError] = PipelineError


def to_json(value):
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    return value


class PostgresRepository(Repository):
    """Repository for one frozen dataclass. Composite keys are passed to get() joined with ':'."""

    def __init__(self, db: Database, table: Table, from_row: Callable[[dict], object]):
        self._db = db
        self.table = table
        self.from_row = from_row

    def to_row(self, item) -> dict:
        row = {c: getattr(item, c) for c in self.table.columns}
        for column in self.table.json_columns:
            row[column] = Jsonb(to_json(row[column]))
        return row

    def add(self, item) -> None:
        columns = self.table.columns
        if self.table.upsert:
            updates = [c for c in columns if c not in self.table.key]
            conflict = sql.SQL("DO UPDATE SET {}").format(
                sql.SQL(", ").join(sql.SQL("{0} = EXCLUDED.{0}").format(sql.Identifier(c)) for c in updates)
            )
        else:
            conflict = sql.SQL("DO NOTHING")  # deterministic ids: re-adding the same row is a no-op
        statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) {}").format(
            sql.Identifier(self.table.name),
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder(c) for c in columns),
            sql.SQL(", ").join(map(sql.Identifier, self.table.key)),
            conflict,
        )
        self._db.query(statement, self.to_row(item), error=self.table.error)

    def get(self, item_id: str):
        parts = item_id.split(":", len(self.table.key) - 1)
        if len(parts) != len(self.table.key):
            return None
        rows = self._select(dict(zip(self.table.key, parts, strict=True)))
        return rows[0] if rows else None

    def list_by(self, **filters) -> list:
        unknown = set(filters) - set(self.table.columns)
        if unknown:
            raise ValidationError(f"cannot filter {self.table.name} by {sorted(unknown)}", context={"field": "filters"})
        return self._select(filters)

    def _select(self, filters: dict) -> list:
        where = sql.SQL(" AND ").join(sql.SQL("{} = %s").format(sql.Identifier(c)) for c in filters)
        statement = sql.SQL("SELECT * FROM {} WHERE {} ORDER BY {}").format(
            sql.Identifier(self.table.name),
            where if filters else sql.SQL("TRUE"),
            sql.SQL(", ").join(map(sql.Identifier, self.table.key)),
        )
        rows = self._db.query(statement, tuple(filters.values()), error=self.table.error)
        return [self.from_row(row) for row in rows]


def _verdict(row: dict) -> Verdict:
    return Verdict(**{**row, "evidence_node_ids": tuple(row["evidence_node_ids"])})


def _component(row: dict) -> ScoreComponent:
    return ScoreComponent(**{**row, "evidence_node_ids": tuple(row["evidence_node_ids"])})


def _run(row: dict) -> RunRecord:
    return RunRecord(**{**row, "failures": tuple(tuple(f) for f in row["failures"])})


def _job(row: dict) -> JobRequirementInput:
    return JobRequirementInput(**{**row, "required_skills": tuple(row["required_skills"])})


def _account(row: dict) -> AccountLink:
    return AccountLink(**{**row, "rationale": tuple(row["rationale"])})


def _match(row: dict) -> SkillMatch:
    return SkillMatch(**{**row, "node_ids": tuple(row["node_ids"])})


def _score_report(row: dict) -> ScoreReport:
    return ScoreReport(
        **{
            **row,
            "components": tuple(_component(c) for c in row["components"]),
            "verdicts": tuple(_verdict(v) for v in row["verdicts"]),
            "matches": tuple(_match(m) for m in row.get("matches") or ()),
        }
    )


def _fields(cls) -> tuple[str, ...]:
    return tuple(f.name for f in dataclasses.fields(cls))


TABLES = {
    "candidates": Table("candidates", _fields(CandidateRecord), json_columns=("handles",)),
    "job_requirements": Table("job_requirements", _fields(JobRequirementInput), json_columns=("required_skills",)),
    "runs": Table("runs", _fields(RunRecord), json_columns=("config", "failures"), upsert=True),
    "source_accounts": Table(
        "source_accounts", _fields(AccountLink), key=("run_id", "source", "handle"), json_columns=("rationale",)
    ),
    "snapshots": Table("snapshots", _fields(Snapshot), error=SnapshotError),
    "evidence_nodes": Table("evidence_nodes", _fields(EvidenceNode), json_columns=("value",)),
    "claims": Table("claims", _fields(Claim)),
    "verdicts": Table("verdicts", _fields(Verdict), key=("claim_id", "run_id"), json_columns=("evidence_node_ids",)),
    "score_reports": Table(
        "score_reports", _fields(ScoreReport), key=("run_id",), json_columns=("components", "verdicts", "matches")
    ),
}

FROM_ROW = {
    "candidates": lambda row: CandidateRecord(**row),
    "job_requirements": _job,
    "runs": _run,
    "source_accounts": _account,
    "snapshots": lambda row: Snapshot(**row),
    "evidence_nodes": lambda row: EvidenceNode(**row),
    "claims": lambda row: Claim(**row),
    "verdicts": _verdict,
    "score_reports": _score_report,
}


def build_repositories(db: Database) -> dict[str, PostgresRepository]:
    """One repository per table, keyed by table name (e.g. repos["snapshots"])."""
    return {name: PostgresRepository(db, table, FROM_ROW[name]) for name, table in TABLES.items()}


class PostgresEraser(CandidateEraser):
    """Deletes the candidate row (FKs cascade to every other table) and blobs no other candidate uses."""

    def __init__(self, db: Database, blob_store: BlobStore):
        self._db = db
        self._blobs = blob_store

    def delete_candidate(self, candidate_id: str) -> None:
        unshared = self._db.query(
            "SELECT DISTINCT s.object_key FROM snapshots s WHERE s.candidate_id = %s AND NOT EXISTS "
            "(SELECT 1 FROM snapshots o WHERE o.object_key = s.object_key AND o.candidate_id <> %s)",
            (candidate_id, candidate_id),
        )
        self._db.query("DELETE FROM candidates WHERE id = %s", (candidate_id,))
        for row in unshared:  # rows first: a failed blob delete leaves an orphan blob, never a dangling row
            self._blobs.delete(row["object_key"])

-- 001: initial schema. Runs are the only mutable rows (status lifecycle); everything else is insert-only.
-- Every table hangs off candidates with ON DELETE CASCADE so one DELETE erases a candidate (right to erasure).
-- Embedding vectors (pgvector) are deferred to M3/M4 and are not stored yet.

CREATE TABLE candidates (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,          -- needed for identity resolution; never logged
    resume_text TEXT NOT NULL,
    handles     JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE job_requirements (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    text            TEXT NOT NULL,
    required_skills JSONB NOT NULL
);

CREATE TABLE runs (
    id           TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidates (id) ON DELETE CASCADE,
    job_id       TEXT NOT NULL,         -- no FK: a run keeps its job id even if the job is replaced
    status       TEXT NOT NULL CHECK (status IN ('running', 'partial', 'done', 'failed')),
    started_at   TIMESTAMPTZ NOT NULL,
    finished_at  TIMESTAMPTZ,
    config       JSONB NOT NULL DEFAULT '{}',
    failures     JSONB NOT NULL DEFAULT '[]',
    replay_of    TEXT
);
CREATE INDEX runs_candidate_idx ON runs (candidate_id);

CREATE TABLE source_accounts (
    run_id       TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES candidates (id) ON DELETE CASCADE,
    source       TEXT NOT NULL,
    handle       TEXT NOT NULL,
    confidence   DOUBLE PRECISION NOT NULL,
    linked       BOOLEAN NOT NULL,
    rationale    JSONB NOT NULL DEFAULT '[]',
    PRIMARY KEY (run_id, source, handle)
);

-- Refinement of the M1 design's UNIQUE (source, sha256): metadata is one row per run, while the bytes are
-- deduplicated by the content-addressed object_key (snapshots/{source}/{sha256}). Two endpoints may return
-- identical bytes (e.g. two empty "[]" commit lists), hence the key includes the endpoint.
CREATE TABLE snapshots (
    id           TEXT PRIMARY KEY,
    run_id       TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES candidates (id) ON DELETE CASCADE,
    source       TEXT NOT NULL,
    handle       TEXT NOT NULL,
    endpoint     TEXT NOT NULL,
    object_key   TEXT NOT NULL,
    sha256       CHAR(64) NOT NULL,
    fetched_at   TIMESTAMPTZ NOT NULL,
    size         BIGINT NOT NULL,
    UNIQUE (run_id, endpoint, sha256)
);
CREATE INDEX snapshots_object_key_idx ON snapshots (object_key);

CREATE TABLE evidence_nodes (
    id           TEXT PRIMARY KEY,
    run_id       TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES candidates (id) ON DELETE CASCADE,
    snapshot_id  TEXT NOT NULL REFERENCES snapshots (id) ON DELETE CASCADE,
    source       TEXT NOT NULL,
    handle       TEXT NOT NULL,
    kind         TEXT NOT NULL CHECK (kind IN ('skill', 'project', 'contribution', 'achievement')),
    value        JSONB NOT NULL,
    locator      TEXT NOT NULL
);
CREATE INDEX evidence_nodes_run_idx ON evidence_nodes (run_id);

CREATE TABLE claims (
    id           TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidates (id) ON DELETE CASCADE,
    text         TEXT NOT NULL,
    kind         TEXT NOT NULL,
    subject      TEXT NOT NULL,
    years        DOUBLE PRECISION,
    rating       INTEGER
);

CREATE TABLE verdicts (
    claim_id          TEXT NOT NULL REFERENCES claims (id) ON DELETE CASCADE,
    run_id            TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    candidate_id      TEXT NOT NULL REFERENCES candidates (id) ON DELETE CASCADE,
    label             TEXT NOT NULL CHECK (label IN ('supported', 'partially_supported', 'unsupported')),
    evidence_node_ids JSONB NOT NULL DEFAULT '[]',
    rationale         TEXT NOT NULL,
    PRIMARY KEY (claim_id, run_id)
);

CREATE TABLE score_reports (
    run_id       TEXT PRIMARY KEY REFERENCES runs (id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES candidates (id) ON DELETE CASCADE,
    job_id       TEXT NOT NULL,
    total        DOUBLE PRECISION NOT NULL,
    components   JSONB NOT NULL,
    verdicts     JSONB NOT NULL DEFAULT '[]'
);

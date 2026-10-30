"""Integration fixtures: real PostgreSQL and MinIO (docker compose up). Skipped when env vars are missing."""

import os
import uuid

import pytest

from pipeline.adapters.migrate import migrate
from pipeline.adapters.minio_store import MinioBlobStore
from pipeline.adapters.postgres import Database, build_repositories


@pytest.fixture(scope="session")
def database():
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    migrate(os.environ["DATABASE_URL"])
    db = Database.from_env()
    yield db
    db.close()


@pytest.fixture
def repos(database):
    return build_repositories(database)


@pytest.fixture
def minio_store():
    if not os.environ.get("MINIO_ENDPOINT"):
        pytest.skip("MINIO_ENDPOINT not set")
    return MinioBlobStore.from_env()


@pytest.fixture
def uid():
    """Unique ids per test so tests never collide in a shared database."""
    return lambda prefix: f"{prefix}-{uuid.uuid4()}"

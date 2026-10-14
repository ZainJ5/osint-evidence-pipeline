"""Tiny migration runner: applies migrations/NNN_*.sql in order, once each. Run: python -m pipeline.adapters.migrate"""

import os
import sys
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def migrate(dsn: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations, each in its own transaction. Returns the versions applied now."""
    applied_now = []
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(directory.glob("[0-9][0-9][0-9]_*.sql")):
            if path.stem in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
            applied_now.append(path.stem)
    return applied_now


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1
    applied = migrate(dsn)
    print(f"applied {len(applied)} migration(s): {', '.join(applied) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

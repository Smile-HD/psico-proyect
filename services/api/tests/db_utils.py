"""Shared DB helpers for the test suite.

The integration tests run against a REAL PostgreSQL (the compose stack, or any
reachable PSICO_DATABASE_URL). When no database is reachable they skip with an
explicit message — running the full suite locally without Docker is
deliberately not a false green.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text


def db_url() -> str:
    return os.environ.get("PSICO_DATABASE_URL", "").strip()


def db_reachable(url: str) -> bool:
    if not url:
        return False
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


SKIP_MESSAGE = (
    "PSICO_DATABASE_URL not reachable — requires PostgreSQL (e.g. the compose "
    "stack: docker compose up -d --build, then run pytest inside the api "
    "container). Skipping database-backed tests."
)


def maintenance_url(url: str) -> str:
    """Same server URL but connected to the `postgres` maintenance database."""
    base, _, _ = url.rpartition("/")
    return f"{base}/postgres"

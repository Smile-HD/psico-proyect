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


def reset_database(url: str) -> None:
    """Drop and recreate the target database for a repeatable test run.

    F2 idempotency records persist across runs; tests use fixed keys, so a
    second run would replay stale records against old resources. Resetting
    the database makes the whole suite repeatable (CI-style fresh state).
    Only databases whose name starts with `psico` are touched, so an
    accidentally misconfigured URL can never drop unrelated data.
    """
    base, _, dbname = url.rpartition("/")
    if not dbname or not dbname.startswith("psico"):
        return
    # Name is allowlisted (prefix check above); only safe characters can reach
    # the DDL, so interpolation is confined to a psico*_test-style identifier.
    if not dbname.replace("_", "").isalnum():
        return
    maint = create_engine(maintenance_url(url), isolation_level="AUTOCOMMIT")
    with maint.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    maint.dispose()

"""RED test — schema (F1): nine-family upgrade, idempotency, F5/F6 empty.

Runs against a REAL PostgreSQL; skips when unreachable (see tests/db_utils).

Covered scenarios (data-schema spec):
  - Fresh upgrade creates all families (all expected tables + columns).
  - Idempotent upgrade: running `upgrade head` again executes nothing.
  - Linear history: one head, no branches or merge points.
  - Empty-but-migrated F5/F6: tables exist with zero rows before any seed.
  - Append-only trigger is installed at schema level.
"""

from __future__ import annotations

import uuid

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

from tests.db_utils import SKIP_MESSAGE, db_reachable, db_url, maintenance_url
from tests.conftest import alembic_config

EXPECTED_TABLES = {
    # identity
    "users", "roles", "user_roles",
    # institutions
    "institutions", "campuses", "faculties", "programs",
    # instruments
    "instruments", "instrument_versions", "instrument_items",
    # sessions
    "sessions", "responses",
    # scoring
    "reference_sets", "reference_values", "score_runs",
    # recommendation (F5) + reporting (F6) — empty-but-migrated
    "recommendation_rules", "recommendation_results",
    "reports", "report_templates",
    # audit + consent + seed bookkeeping
    "audit_log", "consent_versions", "consent_grants", "seed_manifest",
}

F5_F6_TABLES = {
    "recommendation_rules",
    "recommendation_results",
    "reports",
    "report_templates",
}

KEY_COLUMNS = {
    "users": {"username", "password_hash", "synthetic", "source"},
    "roles": {"name", "synthetic", "source"},
    "instruments": {"key"},
    "instrument_versions": {"version_no", "status", "is_immutable"},
    "instrument_items": {"scale", "scale_order", "text"},
    "sessions": {"user_id", "consent_grant_id", "status"},
    "responses": {"session_id", "item_id", "value"},
    "reference_sets": {"key", "reference_status", "use", "norm_note"},
    "audit_log": {"event_type", "actor_user_id", "metadata", "occurred_at"},
    "consent_versions": {"version_no", "title", "body", "is_active"},
    "consent_grants": {"state", "signed_at"},
    "seed_manifest": {"seed_version", "counts", "checksum", "executed_at"},
}


def _new_test_database(url: str) -> tuple[str, str]:
    """Create a throwaway database on the same server; return (name, url)."""
    dbname = f"psico_schema_test_{uuid.uuid4().hex[:12]}"
    maint = create_engine(maintenance_url(url), isolation_level="AUTOCOMMIT")
    with maint.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    maint.dispose()
    base, _, _ = url.rpartition("/")
    return dbname, f"{base}/{dbname}"


def _schema_engine(url: str):
    """Engine against a throwaway schema DB. NullPool so every connection is
    released immediately, letting the fixture drop the database at teardown."""
    return create_engine(url, poolclass=NullPool)


@pytest.fixture(scope="module")
def schema_url():
    url = db_url()
    if not db_reachable(url):
        pytest.skip(SKIP_MESSAGE)
    dbname, test_url = _new_test_database(url)
    command.upgrade(alembic_config(test_url), "head")
    yield test_url
    engine = create_engine(test_url, poolclass=NullPool)
    engine.dispose()
    maint = create_engine(maintenance_url(url), isolation_level="AUTOCOMMIT")
    with maint.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)'))
    maint.dispose()


def test_fresh_upgrade_creates_all_families(schema_url: str) -> None:
    inspector = inspect(_schema_engine(schema_url))
    tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"missing tables: {sorted(missing)}"
    for table, columns in KEY_COLUMNS.items():
        present = {col["name"] for col in inspector.get_columns(table)}
        assert columns <= present, f"{table} missing columns: {columns - present}"


def test_unique_constraints_present(schema_url: str) -> None:
    inspector = inspect(_schema_engine(schema_url))
    uniques = {
        "roles": {"name"},
        "instruments": {"key"},
        "reference_sets": {"key"},
    }
    for table, expected_cols in uniques.items():
        uq_cols = {
            tuple(uc.get("column_names") or [])
            for uc in inspector.get_unique_constraints(table)
        }
        assert any(
            set(cols) == expected_cols for cols in uq_cols
        ), f"{table} missing unique on {expected_cols}; got {uq_cols}"


def test_check_constraints_present(schema_url: str) -> None:
    inspector = inspect(_schema_engine(schema_url))
    checks = {
        "responses": ["ck_value_1_to_5"],
        "instrument_items": ["ck_scale_order_1_to_5"],
        "instrument_versions": ["ck_published_versions_immutable"],
        "consent_grants": ["ck_consent_state"],
        "sessions": ["ck_session_status"],
        "audit_log": ["ck_audit_outcome"],
    }
    for table, expected in checks.items():
        names = [c["name"] for c in inspector.get_check_constraints(table)]
        assert set(expected) <= set(names), f"{table} checks {expected} not in {names}"


def test_upgrade_is_idempotent(schema_url: str) -> None:
    # Already at head from the fixture; running upgrade head again must not
    # execute any migration and must not raise.
    command.upgrade(alembic_config(schema_url), "head")
    engine = _schema_engine(schema_url)
    with engine.connect() as conn:
        revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    engine.dispose()
    assert revision == "0004_audit_append_only_trigger"


def test_linear_history() -> None:
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = script.get_heads()
    assert len(heads) == 1, f"expected a single head, got {heads}"
    # Every revision except the head must have exactly one child.
    for revision in script.walk_revisions():
        if revision.revision not in heads:
            children = [
                r for r in script.walk_revisions() if r.down_revision == revision.revision
            ]
            assert len(children) == 1, (
                f"branch at {revision.revision}: {[c.revision for c in children]}"
            )


def test_f5_f6_empty_but_migrated(schema_url: str) -> None:
    engine = _schema_engine(schema_url)
    with engine.connect() as conn:
        for table in sorted(F5_F6_TABLES):
            count = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            assert count == 0, f"{table} expected empty, found {count}"
    engine.dispose()


def test_append_only_trigger_installed(schema_url: str) -> None:
    engine = _schema_engine(schema_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT tgname FROM pg_trigger WHERE tgrelid = 'audit_log'::regclass"
                " AND NOT tgisinternal"
            )
        ).fetchall()
        names = {row[0] for row in rows}
    engine.dispose()
    assert "trg_audit_append_only" in names

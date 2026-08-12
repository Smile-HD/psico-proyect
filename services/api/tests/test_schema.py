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
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from app.models.reporting import Report, ReportArtifact, ReportTemplate
from tests.db_utils import SKIP_MESSAGE, db_reachable, db_url, maintenance_url
from tests.conftest import alembic_config

EXPECTED_TABLES = {
    # identity
    "users",
    "roles",
    "user_roles",
    # institutions
    "institutions",
    "campuses",
    "faculties",
    "programs",
    # instruments
    "instruments",
    "instrument_versions",
    "scales",
    "instrument_items",
    "response_options",
    "idempotency_records",
    # sessions
    "sessions",
    "responses",
    # scoring
    "reference_sets",
    "reference_values",
    "score_runs",
    # recommendation (F5) + reporting (F6) — empty-but-migrated
    "recommendation_rules",
    "recommendation_results",
    "reports",
    "report_templates",
    "report_artifacts",
    # audit + consent + seed bookkeeping
    "audit_log",
    "consent_versions",
    "consent_grants",
    "seed_manifest",
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
    "instrument_versions": {
        "version_no",
        "status",
        "is_immutable",
        "response_type",
        "adaptation_metadata",
        "created_at",
        "updated_at",
        "archived_at",
    },
    "scales": {"version_id", "label", "locale", "display_order", "synthetic", "source"},
    "instrument_items": {"scale_id", "item_order", "locale", "required", "text"},
    "response_options": {
        "item_id",
        "label",
        "locale",
        "display_order",
        "value",
        "synthetic",
        "source",
    },
    "idempotency_records": {
        "actor_user_id",
        "operation",
        "resource_scope",
        "idempotency_key",
        "request_hash",
        "response_status",
        "response_body",
        "created_at",
    },
    "sessions": {"user_id", "consent_grant_id", "status"},
    "responses": {"session_id", "item_id", "value"},
    "reference_sets": {"key", "reference_status", "use", "norm_note"},
    "score_runs": {
        "session_id",
        "reference_set_id",
        "status",
        "raw",
        "computed_at",
        "synthetic",
        "source",
    },
    "report_templates": {
        "key",
        "name",
        "description",
        "template_body",
        "version_no",
        "status",
        "synthetic",
        "source",
    },
    "reports": {
        "session_id",
        "score_run_id",
        "template_id",
        "template_version_no",
        "recommendation_snapshot",
        "format",
        "status",
        "storage_key",
        "sha256",
        "byte_size",
        "media_type",
        "renderer_version",
        "generated_at",
        "created_at",
        "updated_at",
        "failed_at",
        "synthetic",
        "source",
    },
    "report_artifacts": {
        "storage_key",
        "report_id",
        "payload",
        "sha256",
        "byte_size",
        "media_type",
        "created_at",
    },
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
        "scales": {"version_id", "display_order"},
        "response_options": {"item_id", "display_order"},
    }
    for table, expected_cols in uniques.items():
        uq_cols = {
            tuple(uc.get("column_names") or [])
            for uc in inspector.get_unique_constraints(table)
        }
        assert any(set(cols) == expected_cols for cols in uq_cols), (
            f"{table} missing unique on {expected_cols}; got {uq_cols}"
        )

    template_uq = {
        tuple(uc.get("column_names") or [])
        for uc in inspector.get_unique_constraints("report_templates")
    }
    assert ("key", "version_no") in template_uq
    assert ("key",) not in template_uq


def test_reporting_models_match_migrated_columns(schema_url: str) -> None:
    inspector = inspect(_schema_engine(schema_url))
    for model in (ReportTemplate, Report, ReportArtifact):
        database_columns = {column["name"] for column in inspector.get_columns(model.__tablename__)}
        model_columns = set(model.__table__.columns.keys())
        assert model_columns == database_columns, (
            f"{model.__tablename__} model/schema drift: "
            f"model-only={sorted(model_columns - database_columns)}, "
            f"schema-only={sorted(database_columns - model_columns)}"
        )

    report_foreign_keys = inspector.get_foreign_keys("reports")
    assert any(
        foreign_key["constrained_columns"] == ["score_run_id"]
        and foreign_key["referred_table"] == "score_runs"
        and foreign_key["referred_columns"] == ["id"]
        for foreign_key in report_foreign_keys
    )
    assert not any(
        set(foreign_key["constrained_columns"]) == {"session_id"}
        and foreign_key.get("referred_table") == "report_templates"
        for foreign_key in report_foreign_keys
    )


def test_report_check_constraints_use_ratified_vocabularies(schema_url: str) -> None:
    inspector = inspect(_schema_engine(schema_url))
    checks = {
        constraint["name"]: str(constraint.get("sqltext", ""))
        for table in ("reports", "report_templates")
        for constraint in inspector.get_check_constraints(table)
    }
    assert "ck_report_status" in checks
    assert all(value in checks["ck_report_status"] for value in ("pending", "processing", "ready", "failed"))
    assert "ck_report_format" in checks
    assert "pdf" in checks["ck_report_format"]
    assert "ck_report_template_status" in checks
    assert all(value in checks["ck_report_template_status"] for value in ("draft", "published", "retired"))
    assert "ck_report_ready_artifact" in checks
    assert "ck_report_failed_without_artifact" in checks


def test_report_template_published_rows_are_immutable(schema_url: str) -> None:
    engine = _schema_engine(schema_url)
    template_id = uuid.uuid4()
    template_key = f"schema-template-{template_id}"
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO report_templates "
                "(id, key, name, template_body, version_no, status, synthetic, source) "
                "VALUES (:id, :key, 'Schema template', 'original', 1, 'published', false, 'runtime')"
            ),
            {"id": template_id, "key": template_key},
        )

    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE report_templates SET template_body = 'changed' WHERE id = :id"),
                {"id": template_id},
            )

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE report_templates SET status = 'retired' WHERE id = :id"),
            {"id": template_id},
        )
        body = conn.execute(
            text("SELECT template_body FROM report_templates WHERE id = :id"),
            {"id": template_id},
        ).scalar_one()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE reports, report_templates"))
    engine.dispose()
    assert body == "original"


def test_check_constraints_present(schema_url: str) -> None:
    inspector = inspect(_schema_engine(schema_url))
    checks = {
        "responses": ["ck_value_1_to_5"],
        "instrument_items": ["ck_item_order_positive"],
        "instrument_versions": [
            "ck_instrument_version_status",
            "ck_published_versions_immutable",
        ],
        "scales": ["ck_scale_display_order_positive"],
        "response_options": [
            "ck_option_display_order_1_to_5",
            "ck_option_value_1_to_5",
        ],
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
        revision = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
    engine.dispose()
    assert revision == "0006_reports_pdf"


def test_linear_history() -> None:
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = script.get_heads()
    assert len(heads) == 1, f"expected a single head, got {heads}"
    reporting_revision = script.get_revision("0006_reports_pdf")
    assert reporting_revision.down_revision == "0005_catalog_four_level"
    # Every revision except the head must have exactly one child.
    for revision in script.walk_revisions():
        if revision.revision not in heads:
            children = [
                r
                for r in script.walk_revisions()
                if r.down_revision == revision.revision
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


def test_report_template_immutability_trigger_installed(schema_url: str) -> None:
    engine = _schema_engine(schema_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT tgname FROM pg_trigger "
                "WHERE tgrelid = 'report_templates'::regclass AND NOT tgisinternal"
            )
        ).fetchall()
    engine.dispose()
    assert "trg_report_template_published_immutability" in {row[0] for row in rows}

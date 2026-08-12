"""RED test — audit (F1): append-only enforced, deny-list clean.

Pure tests: event catalog matches the contract; deny-list rejects forbidden
metadata keys/values.
DB tests (skip without PostgreSQL): UPDATE/DELETE on audit_log rejected by
the trigger; no audit row in the whole log violates the deny-list.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core import audit as audit_core
from app.models.audit import AuditLog

EXPECTED_CATALOG = {
    "auth.login",
    "auth.denied",
    "user.role_changed",
    "instrument.draft_created",
    "instrument.draft_updated",
    "instrument.published",
    "instrument.archived",
    "consent.granted",
    "consent.revoked",
    "session.started",
    "session.completed",
    "session.blocked_without_consent",
    "seed.executed",
    "scoring.run",
    "recommendation.generated",
    "report.generated",
}


# --------------------------------------------------------------------------- #
# Pure: catalog + deny-list
# --------------------------------------------------------------------------- #


def test_event_catalog_matches_contract() -> None:
    assert audit_core.EVENT_CATALOG == EXPECTED_CATALOG


@pytest.mark.parametrize(
    "bad_metadata",
    [
        {"responses": [1, 2, 3]},  # raw response values
        {"token": "abc123"},  # tokens
        {"password": "hunter2"},  # passwords
        {"item_text": "Prefiero actividades..."},  # item content
        {"pii": {"email": "x@psico.test"}},  # PII beyond actor id
    ],
)
def test_deny_list_rejects_forbidden_metadata(bad_metadata: dict) -> None:
    with pytest.raises(ValueError):
        audit_core.assert_deny_list(bad_metadata)


def test_deny_list_allows_clean_metadata() -> None:
    # Counts, durations, checksums are fine — they never leak content.
    audit_core.assert_deny_list(
        {"response_count": 20, "duration_s": 300, "seed_version": "1.0.0"}
    )


def test_unknown_event_type_rejected() -> None:
    class _DB:
        def add(self, *_a):
            pass

    with pytest.raises(ValueError):
        audit_core.record(_DB(), "made.up.event")


def test_report_generated_event_contract_is_aggregate_only() -> None:
    class _DB:
        def __init__(self):
            self.rows = []

        def add(self, row):
            self.rows.append(row)

    metadata = {
        "session_id": str(uuid.uuid4()),
        "report_id": str(uuid.uuid4()),
        "template_id": str(uuid.uuid4()),
        "template_version_no": 1,
        "transition": "processing->ready",
        "sha256": "a" * 64,
        "byte_size": 1234,
        "created_at": "2026-08-11T12:00:00+00:00",
        "generated_at": "2026-08-11T12:30:00+00:00",
    }
    db = _DB()

    row = audit_core.record(
        db,
        "report.generated",
        actor_user_id=uuid.uuid4(),
        actor_role="psicólogo",
        resource_type="report",
        resource_id=metadata["report_id"],
        action="generate",
        metadata=metadata,
    )

    assert row.event_type == "report.generated"
    assert row.metadata_ == metadata
    assert set(row.metadata_) == {
        "session_id",
        "report_id",
        "template_id",
        "template_version_no",
        "transition",
        "sha256",
        "byte_size",
        "created_at",
        "generated_at",
    }
    serialized = str(row.metadata_).lower()
    assert not any(
        forbidden in serialized
        for forbidden in (
            "body",
            "score",
            "justification",
            "pdf",
            "storage_key",
            "token",
            "path",
        )
    )


# --------------------------------------------------------------------------- #
# DB: trigger enforcement + deny-list sweep
# --------------------------------------------------------------------------- #


def test_update_on_audit_log_rejected(engine, db_session) -> None:
    row = audit_core.record(db_session, "auth.login", actor_role="admin", commit=True)
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE audit_log SET event_type = 'auth.denied' WHERE id = :rid"),
                {"rid": row.id},
            )


def test_delete_on_audit_log_rejected(engine, db_session) -> None:
    row = audit_core.record(
        db_session, "auth.denied", actor_role=None, outcome="denied", commit=True
    )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM audit_log WHERE id = :rid"),
                {"rid": row.id},
            )


def test_deny_list_clean_across_whole_log(db_session) -> None:
    rows = db_session.execute(
        text("SELECT metadata FROM audit_log WHERE metadata IS NOT NULL")
    ).fetchall()
    for (metadata,) in rows:
        audit_core.assert_deny_list(metadata)  # raises on any violation

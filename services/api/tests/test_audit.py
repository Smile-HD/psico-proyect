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

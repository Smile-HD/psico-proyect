"""PostgreSQL-backed artifact storage contracts for the F6 reporting boundary."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.models.reporting import Report
from app.models.sessions import Session as SessionRow
from app.modules.reporting.storage import (
    ArtifactConflictError,
    ArtifactNotFoundError,
    PostgresReportStorage,
)
from app.seed.loader import seed_id


@pytest.fixture
def storage_db(seeded_db_session):
    seeded_db_session.rollback()
    yield seeded_db_session
    seeded_db_session.rollback()


def _report(db) -> Report:
    session = db.get(SessionRow, seed_id("session:evaluado_08"))
    assert session is not None
    report = Report(
        id=uuid4(),
        session_id=session.id,
        format="pdf",
        status="processing",
        synthetic=False,
        source="runtime",
    )
    db.add(report)
    db.flush()
    return report


def test_storage_put_open_delete_is_opaque_idempotent_and_persists_checksum(storage_db) -> None:
    db = storage_db
    report = _report(db)
    payload = b"%PDF-1.7\nsynthetic report artifact\n"
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    storage = PostgresReportStorage()

    stored = storage.put(
        db,
        report_id=report.id,
        payload=payload,
        media_type="application/pdf",
    )
    replay = storage.put(
        db,
        report_id=report.id,
        payload=payload,
        media_type="application/pdf",
    )

    assert UUID(stored.storage_key).version == 4
    assert "/" not in stored.storage_key
    assert "\\" not in stored.storage_key
    assert stored.sha256 == expected_sha256
    assert stored.byte_size == len(payload)
    assert stored.media_type == "application/pdf"
    assert replay == stored

    row = db.execute(
        text(
            "SELECT report_id, payload, sha256, byte_size, media_type "
            "FROM report_artifacts WHERE storage_key = :storage_key"
        ),
        {"storage_key": stored.storage_key},
    ).one()
    assert row.report_id == report.id
    assert bytes(row.payload) == payload
    assert row.sha256 == expected_sha256
    assert row.byte_size == len(payload)
    assert row.media_type == "application/pdf"

    stream = storage.open(db, stored.storage_key)
    assert stream.metadata == stored
    assert stream.read() == payload
    stream.close()

    assert storage.delete(db, stored.storage_key) is True
    assert storage.delete(db, stored.storage_key) is False
    with pytest.raises(ArtifactNotFoundError):
        storage.open(db, stored.storage_key)


def test_storage_rejects_conflicting_put_and_cleans_orphans_idempotently(storage_db) -> None:
    db = storage_db
    report = _report(db)
    storage = PostgresReportStorage()
    stored = storage.put(db, report_id=report.id, payload=b"first")

    with pytest.raises(ArtifactConflictError):
        storage.put(db, report_id=report.id, payload=b"different")

    orphan = storage.put(db, report_id=uuid4(), payload=b"orphan")
    assert storage.cleanup_orphans(db) == 1
    assert storage.cleanup_orphans(db) == 0
    with pytest.raises(ArtifactNotFoundError):
        storage.open(db, orphan.storage_key)

    # The report-owned artifact is not an orphan and remains available.
    assert storage.open(db, stored.storage_key).read() == b"first"


def test_storage_missing_and_path_like_keys_are_never_exposed(storage_db) -> None:
    storage = PostgresReportStorage()

    with pytest.raises(ArtifactNotFoundError):
        storage.open(storage_db, str(uuid4()))
    assert storage.delete(storage_db, str(uuid4())) is False
    with pytest.raises(ValueError, match="opaque"):
        storage.open(storage_db, "..\\internal\\report.pdf")

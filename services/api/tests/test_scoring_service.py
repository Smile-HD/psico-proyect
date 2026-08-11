"""PostgreSQL-backed orchestration contracts for the F4 scoring service."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update

from app.core.errors import ApiError, CONFLICT, FORBIDDEN, NOT_FOUND
from app.models.audit import AuditLog
from app.models.scoring import ScoreRun
from app.models.sessions import Session as SessionRow
from app.modules.scoring.service import ScoringService
from app.seed.loader import seed_id


def _user(key: str, role: str = "evaluado") -> SimpleNamespace:
    return SimpleNamespace(id=seed_id(key), roles=[role])


def _completed_session(db, profile: str = "evaluado_01") -> SessionRow:
    row = db.get(SessionRow, seed_id(f"session:{profile}"))
    assert row is not None
    assert row.status == "completed"
    return row


def _runtime_session(db, user: SimpleNamespace, status: str) -> SessionRow:
    row = SessionRow(
        id=uuid4(),
        user_id=user.id,
        instrument_version_id=seed_id("TP-S-01:v1"),
        status=status,
        completed_at=datetime.now(timezone.utc) if status == "completed" else None,
        synthetic=False,
        source="runtime",
    )
    db.add(row)
    db.commit()
    return row


def _run_count(db, session_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(ScoreRun).where(ScoreRun.session_id == session_id)
        )
        or 0
    )


def _event_rows(db, session_id: UUID) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.event_type == "scoring.run",
                AuditLog.resource_id == str(session_id),
            )
            .order_by(AuditLog.occurred_at, AuditLog.id)
        ).all()
    )


def test_score_persists_completed_runtime_run_and_aggregate_audit(seeded_db_session) -> None:
    db = seeded_db_session
    user = _user("evaluado_01")
    session = _completed_session(db)
    service = ScoringService()

    status, result = service.score_session(db, user, session.id, {}, f"score-{uuid4().hex}")

    assert status == 200
    assert result["session_id"] == str(session.id)
    assert len(result["scales"]) == 5
    assert result["overall"]["raw"] in range(1, 21)
    run = db.get(ScoreRun, UUID(result["run"]["id"]))
    assert run is not None
    assert run.status == "completed"
    assert run.computed_at is not None
    assert run.synthetic is False
    assert run.source == "runtime"
    assert set(run.raw) == {"scales", "overall"}

    events = _event_rows(db, session.id)
    assert len(events) == 1
    assert events[0].metadata_ == {
        "session_id": str(session.id),
        "instrument_version_id": str(session.instrument_version_id),
        "reference_set_id": result["reference_set_id"],
        "run_id": result["run"]["id"],
        "response_count": 20,
        "scale_count": 5,
        "computed_at": result["run"]["computed_at"],
    }


def test_audit_failure_rolls_back_the_pending_score_run(seeded_db_session, monkeypatch) -> None:
    db = seeded_db_session
    user = _user("evaluado_02")
    session = _completed_session(db, "evaluado_02")
    before = _run_count(db, session.id)

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.modules.scoring.service.audit.record", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        ScoringService().score_session(db, user, session.id, {}, f"audit-{uuid4().hex}")

    db.expire_all()
    assert _run_count(db, session.id) == before
    assert _event_rows(db, session.id) == []


def test_score_rejects_in_progress_missing_and_foreign_sessions(seeded_db_session) -> None:
    db = seeded_db_session
    service = ScoringService()
    owner = _user("evaluado_03")
    in_progress = _runtime_session(db, owner, "in_progress")

    with pytest.raises(ApiError) as incomplete:
        service.score_session(db, owner, in_progress.id, {}, f"in-progress-{uuid4().hex}")
    assert (incomplete.value.code, incomplete.value.message) == (
        CONFLICT,
        "session_not_completed",
    )
    assert incomplete.value.details == {}
    assert _run_count(db, in_progress.id) == 0

    with pytest.raises(ApiError) as missing:
        service.score_session(db, owner, uuid4(), {}, f"missing-{uuid4().hex}")
    assert (missing.value.code, missing.value.message) == (NOT_FOUND, "resource_not_found")

    foreign_session = _completed_session(db, "evaluado_04")
    before = _run_count(db, foreign_session.id)
    with pytest.raises(ApiError) as foreign:
        service.score_session(db, owner, foreign_session.id, {}, f"foreign-{uuid4().hex}")
    assert foreign.value.code == FORBIDDEN
    assert _run_count(db, foreign_session.id) == before


def test_score_idempotency_replays_conflicts_and_allows_a_new_key(seeded_db_session) -> None:
    db = seeded_db_session
    user = _user("evaluado_05")
    session = _completed_session(db, "evaluado_05")
    service = ScoringService()
    key = f"replay-{uuid4().hex}"
    body = {"reference_set": "RS-TP-S-01"}

    first = service.score_session(db, user, session.id, body, key)
    replay = service.score_session(db, user, session.id, {"reference_set": "RS-TP-S-01"}, key)
    assert replay == first
    assert _run_count(db, session.id) == 1
    assert len(_event_rows(db, session.id)) == 1

    with pytest.raises(ApiError) as reused:
        service.score_session(db, user, session.id, {"reference_set": "other"}, key)
    assert (reused.value.code, reused.value.message) == (CONFLICT, "idempotency_key_reused")
    assert _run_count(db, session.id) == 1
    assert len(_event_rows(db, session.id)) == 1

    second = service.score_session(db, user, session.id, body, f"new-{uuid4().hex}")
    assert second[0] == 200
    assert _run_count(db, session.id) == 2
    assert len(_event_rows(db, session.id)) == 2


def test_latest_result_orders_by_computed_at_then_run_id(seeded_db_session) -> None:
    db = seeded_db_session
    user = _user("evaluado_06")
    session = _completed_session(db, "evaluado_06")
    service = ScoringService()
    first = service.score_session(db, user, session.id, {}, f"latest-1-{uuid4().hex}")[1]
    second = service.score_session(db, user, session.id, {}, f"latest-2-{uuid4().hex}")[1]
    first_id = UUID(first["run"]["id"])
    second_id = UUID(second["run"]["id"])
    tie = datetime(2026, 8, 10, 22, 0, tzinfo=timezone.utc)
    db.execute(
        update(ScoreRun)
        .where(ScoreRun.id.in_([first_id, second_id]))
        .values(computed_at=tie)
    )
    db.commit()

    expected = db.scalar(
        select(ScoreRun)
        .where(ScoreRun.session_id == session.id, ScoreRun.status == "completed")
        .order_by(ScoreRun.computed_at.desc(), ScoreRun.id.desc())
        .limit(1)
    )
    latest = service.latest_result(db, user, session.id)
    assert expected is not None
    assert latest["run"]["id"] == str(expected.id)

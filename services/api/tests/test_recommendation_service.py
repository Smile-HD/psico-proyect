"""PostgreSQL-backed orchestration contracts for the F5 recommendation service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import ApiError, CONFLICT, FORBIDDEN, INTERNAL_ERROR, NOT_FOUND
from app.models.audit import AuditLog
from app.models.recommendation import RecommendationResult, RecommendationRule
from app.models.sessions import Session as SessionRow
from app.modules.scoring.service import ScoringService
from app.seed.loader import seed_id
from app.modules.recommendation.service import RecommendationService


SERVICE_PROFILE_PRIMARY = "evaluado_29"
SERVICE_PROFILE_SECONDARY = "evaluado_30"


def _user(profile: str, role: str = "evaluado") -> SimpleNamespace:
    return SimpleNamespace(id=seed_id(profile), roles=[role])


def _completed_session(db, profile: str) -> SessionRow:
    session = db.get(SessionRow, seed_id(f"session:{profile}"))
    assert session is not None
    assert session.status == "completed"
    return session


def _runtime_session(db, profile: str, status: str) -> SessionRow:
    session = SessionRow(
        id=uuid4(),
        user_id=seed_id(profile),
        instrument_version_id=seed_id("TP-S-01:v1"),
        status=status,
        completed_at=(datetime.now(timezone.utc) if status == "completed" else None),
        synthetic=False,
        source="runtime",
    )
    db.add(session)
    db.commit()
    return session


def _score_reserved_session(db, profile: str) -> SessionRow:
    session = _completed_session(db, profile)
    status, payload = ScoringService().score_session(
        db,
        _user(profile),
        session.id,
        {},
        f"recommendation-service-score-{profile}-{uuid4().hex}",
    )
    assert status == 200
    assert payload["session_id"] == str(session.id)
    return session


def _count_results(db, session_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationResult)
            .where(RecommendationResult.session_id == session_id)
        )
        or 0
    )


def _recommendation_events(db, session_id: UUID) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.event_type == "recommendation.generated",
                AuditLog.resource_id == str(session_id),
            )
            .order_by(AuditLog.occurred_at, AuditLog.id)
        ).all()
    )


def _denial_events(db, session_id: UUID) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.event_type == "auth.denied",
                AuditLog.resource_id == str(session_id),
            )
            .order_by(AuditLog.occurred_at, AuditLog.id)
        ).all()
    )


def _error_signature(error: ApiError) -> tuple[str, str, dict]:
    return error.code, error.message, error.details


def test_generation_persists_rows_and_one_aggregate_audit_event(
    seeded_db_session,
) -> None:
    db = seeded_db_session
    session = _score_reserved_session(db, SERVICE_PROFILE_PRIMARY)
    user = _user(SERVICE_PROFILE_PRIMARY)
    service = RecommendationService()
    before_rows = _count_results(db, session.id)
    before_events = len(_recommendation_events(db, session.id))
    active_rule_count = int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationRule)
            .where(RecommendationRule.is_active.is_(True))
        )
        or 0
    )

    status, payload = service.generate_recommendations(
        db, user, session.id, {}, f"recommendation-generate-{uuid4().hex}"
    )

    assert status == 200
    assert set(payload) == {"session_id", "generated_at", "disclaimer", "items"}
    assert payload["session_id"] == str(session.id)
    assert payload["generated_at"]
    assert payload["disclaimer"] == (
        "Recomendaciones orientativas sobre datos sintéticos (research-only). "
        "No constituyen una norma UAGRM ni asesoramiento profesional."
    )
    assert payload["items"]
    assert all(
        set(item) == {
            "program_id",
            "program_name",
            "program_code",
            "fit_score",
            "justification",
        }
        for item in payload["items"]
    )

    rows = list(
        db.scalars(
            select(RecommendationResult).where(
                RecommendationResult.session_id == session.id
            )
        ).all()
    )
    assert len(rows) == before_rows + active_rule_count
    assert len(rows) > 0
    assert all(row.synthetic is False and row.source == "runtime" for row in rows)

    events = _recommendation_events(db, session.id)
    assert len(events) == before_events + 1
    metadata = events[-1].metadata_
    assert set(metadata) == {
        "session_id",
        "program_ids",
        "rule_ids",
        "program_count",
        "rule_count",
        "result_count",
        "generated_at",
    }
    assert metadata["session_id"] == str(session.id)
    assert metadata["program_count"] == len(payload["items"])
    assert metadata["rule_count"] == metadata["result_count"] == len(rows)
    assert set(metadata["rule_ids"]) == {str(row.rule_id) for row in rows}
    assert set(metadata["program_ids"]) == {str(row.program_id) for row in rows}
    serialized = json.dumps(metadata, ensure_ascii=False).lower()
    assert not any(
        forbidden in serialized
        for forbidden in ("fit_score", "justification", "response", "option", "item_content")
    )


def test_audit_failure_rolls_back_rows_and_fails_closed(
    seeded_db_session,
    monkeypatch,
) -> None:
    db = seeded_db_session
    session = _score_reserved_session(db, SERVICE_PROFILE_SECONDARY)
    user = _user(SERVICE_PROFILE_SECONDARY)
    before_rows = _count_results(db, session.id)
    before_events = len(_recommendation_events(db, session.id))

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.modules.recommendation.service.audit.record", fail_audit)
    with pytest.raises(ApiError) as error:
        RecommendationService().generate_recommendations(
            db, user, session.id, {}, f"recommendation-audit-{uuid4().hex}"
        )

    assert error.value.code == INTERNAL_ERROR
    db.expire_all()
    assert _count_results(db, session.id) == before_rows
    assert len(_recommendation_events(db, session.id)) == before_events


def test_generation_idempotency_replays_conflicts_and_allows_new_key(
    seeded_db_session,
) -> None:
    db = seeded_db_session
    session = _score_reserved_session(db, SERVICE_PROFILE_PRIMARY)
    user = _user(SERVICE_PROFILE_PRIMARY)
    service = RecommendationService()
    key = f"recommendation-replay-{uuid4().hex}"
    body = {"mode": "default"}
    before_rows = _count_results(db, session.id)
    before_events = len(_recommendation_events(db, session.id))
    first = service.generate_recommendations(db, user, session.id, body, key)
    after_first_rows = _count_results(db, session.id)
    after_first_events = len(_recommendation_events(db, session.id))
    replay = service.generate_recommendations(
        db, user, session.id, {"mode": "default"}, key
    )
    assert replay == first
    assert _count_results(db, session.id) == after_first_rows
    assert len(_recommendation_events(db, session.id)) == after_first_events

    with pytest.raises(ApiError) as reused:
        service.generate_recommendations(
            db, user, session.id, {"mode": "different"}, key
        )
    assert _error_signature(reused.value)[:2] == (CONFLICT, "idempotency_key_reused")
    assert _count_results(db, session.id) == after_first_rows
    assert len(_recommendation_events(db, session.id)) == after_first_events

    second = service.generate_recommendations(
        db,
        user,
        session.id,
        body,
        f"recommendation-new-{uuid4().hex}",
    )
    assert second[0] == 200
    generation_rows = after_first_rows - before_rows
    generation_events = after_first_events - before_events
    assert generation_rows > 0
    assert generation_events == 1
    assert _count_results(db, session.id) == after_first_rows + generation_rows
    assert len(_recommendation_events(db, session.id)) == after_first_events + generation_events


def test_generation_access_and_availability_errors_are_stable(
    seeded_db_session,
) -> None:
    db = seeded_db_session
    service = RecommendationService()

    foreign_session = _completed_session(db, SERVICE_PROFILE_PRIMARY)
    foreign_user = _user(SERVICE_PROFILE_SECONDARY)
    before_foreign_rows = _count_results(db, foreign_session.id)
    with pytest.raises(ApiError) as foreign:
        service.generate_recommendations(
            db,
            foreign_user,
            foreign_session.id,
            {},
            f"recommendation-foreign-{uuid4().hex}",
        )
    assert foreign.value.code == FORBIDDEN
    assert _count_results(db, foreign_session.id) == before_foreign_rows
    assert _denial_events(db, foreign_session.id)[-1].outcome == "denied"

    unscored = _runtime_session(db, SERVICE_PROFILE_SECONDARY, "completed")
    owner = _user(SERVICE_PROFILE_SECONDARY)
    with pytest.raises(ApiError) as unscored_error:
        service.generate_recommendations(
            db, owner, unscored.id, {}, f"recommendation-unscored-{uuid4().hex}"
        )
    with pytest.raises(ApiError) as missing_error:
        service.generate_recommendations(
            db, owner, uuid4(), {}, f"recommendation-missing-{uuid4().hex}"
        )
    assert _error_signature(unscored_error.value) == _error_signature(missing_error.value)
    assert _error_signature(unscored_error.value) == (
        NOT_FOUND,
        "resource_not_found",
        {},
    )

    in_progress = _runtime_session(db, SERVICE_PROFILE_PRIMARY, "in_progress")
    before_in_progress_rows = _count_results(db, in_progress.id)
    with pytest.raises(ApiError) as incomplete:
        service.generate_recommendations(
            db,
            _user(SERVICE_PROFILE_PRIMARY),
            in_progress.id,
            {},
            f"recommendation-in-progress-{uuid4().hex}",
        )
    assert _error_signature(incomplete.value) == (
        CONFLICT,
        "session_not_completed",
        {},
    )
    assert _count_results(db, in_progress.id) == before_in_progress_rows


def test_latest_recommendations_uses_latest_generation_and_deterministic_item_order(
    seeded_db_session,
) -> None:
    db = seeded_db_session
    session = _score_reserved_session(db, SERVICE_PROFILE_SECONDARY)
    user = _user(SERVICE_PROFILE_SECONDARY)
    service = RecommendationService()

    first = service.generate_recommendations(
        db, user, session.id, {}, f"recommendation-latest-1-{uuid4().hex}"
    )
    second = service.generate_recommendations(
        db, user, session.id, {}, f"recommendation-latest-2-{uuid4().hex}"
    )
    latest = service.latest_recommendations(db, user, session.id)

    assert first[0] == second[0] == 200
    assert latest["generated_at"] == second[1]["generated_at"]
    assert latest["items"] == sorted(
        latest["items"], key=lambda item: (-item["fit_score"], item["program_name"])
    )
    assert all(
        current["fit_score"] >= following["fit_score"]
        or current["program_name"] <= following["program_name"]
        for current, following in zip(latest["items"], latest["items"][1:])
    )


def test_get_no_generation_and_foreign_read_are_safe(
    seeded_db_session,
) -> None:
    db = seeded_db_session
    service = RecommendationService()
    no_generation = _runtime_session(db, SERVICE_PROFILE_PRIMARY, "completed")
    owner = _user(SERVICE_PROFILE_PRIMARY)

    with pytest.raises(ApiError) as no_generation_error:
        service.latest_recommendations(db, owner, no_generation.id)
    with pytest.raises(ApiError) as missing_error:
        service.latest_recommendations(db, owner, uuid4())
    assert _error_signature(no_generation_error.value) == _error_signature(missing_error.value)
    assert _error_signature(no_generation_error.value) == (
        NOT_FOUND,
        "resource_not_found",
        {},
    )

    generated = _score_reserved_session(db, SERVICE_PROFILE_SECONDARY)
    service.generate_recommendations(
        db,
        _user(SERVICE_PROFILE_SECONDARY),
        generated.id,
        {},
        f"recommendation-owner-read-{uuid4().hex}",
    )
    with pytest.raises(ApiError) as foreign:
        service.latest_recommendations(db, _user(SERVICE_PROFILE_PRIMARY), generated.id)
    assert foreign.value.code == FORBIDDEN
    assert _denial_events(db, generated.id)[-1].outcome == "denied"

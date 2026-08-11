"""PostgreSQL-backed HTTP contracts for the F4 results surface."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.core.config import settings
from app.main import app
from app.models.audit import AuditLog
from app.models.instruments import InstrumentItem
from app.models.scoring import ReferenceSet, ScoreRun
from app.models.sessions import Session as SessionRow
from app.seed.loader import seed_id


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _password(username: str) -> str:
    return {
        "admin": settings.dev_password_admin,
        "psicologo": settings.dev_password_psicologo,
        "evaluado": settings.dev_password_evaluado,
    }.get(username, f"psico-seed-{username}")


def _login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": _password(username)}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _signature(response) -> tuple[str, str, dict]:
    error = response.json()["error"]
    return error["code"], error["message"], error["details"]


def _score(client, token: str, session_id: str, key: str | None, body=None):
    return client.post(
        f"/api/v1/results/{session_id}/score",
        json={} if body is None else body,
        headers=_headers(token, key),
    )


def _runtime_session(db_session, profile: str, status: str) -> str:
    row = SessionRow(
        id=uuid4(),
        user_id=seed_id(profile),
        instrument_version_id=seed_id("TP-S-01:v1"),
        status=status,
        completed_at=datetime.now(timezone.utc) if status == "completed" else None,
        synthetic=False,
        source="runtime",
    )
    db_session.add(row)
    db_session.commit()
    return str(row.id)


def _seeded_session(profile: str) -> str:
    return str(seed_id(f"session:{profile}"))


def _count(db_session, model, session_id: str, *, event_type: str | None = None) -> int:
    statement = select(func.count()).select_from(model)
    if model is ScoreRun:
        statement = statement.where(ScoreRun.session_id == UUID(session_id))
    else:
        statement = statement.where(
            AuditLog.event_type == event_type, AuditLog.resource_id == session_id
        )
    return int(db_session.scalar(statement) or 0)


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def test_score_completed_session_persists_public_result(
    client, seeded_db_session, db_session
) -> None:
    token = _login(client, "evaluado_01")
    session_id = _seeded_session("evaluado_01")
    before_runs = _count(db_session, ScoreRun, session_id)
    before_events = _count(db_session, AuditLog, session_id, event_type="scoring.run")

    response = _score(client, token, session_id, f"results-score-{uuid4().hex}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "session_id", "run", "reference_set_id", "norm_note", "scales", "overall"
    }
    assert body["session_id"] == session_id
    assert body["run"]["status"] == "completed" and body["run"]["computed_at"]
    assert len(body["scales"]) == 5 and body["overall"]["raw"] in range(1, 21)
    assert _count(db_session, ScoreRun, session_id) == before_runs + 1
    assert _count(db_session, AuditLog, session_id, event_type="scoring.run") == before_events + 1
    run = db_session.get(ScoreRun, UUID(body["run"]["id"]))
    assert run is not None and run.status == "completed" and run.raw is not None
    assert run.synthetic is False and run.source == "runtime"


def test_score_error_boundaries_are_stable_and_non_leaking(
    client, seeded_db_session, db_session
) -> None:
    evaluator = _login(client, "evaluado_09")
    in_progress = _runtime_session(db_session, "evaluado_09", "in_progress")
    incomplete = _score(client, evaluator, in_progress, f"results-in-progress-{uuid4().hex}")
    assert incomplete.status_code == 409
    assert _signature(incomplete) == ("CONFLICT", "session_not_completed", {})
    assert _count(db_session, ScoreRun, in_progress) == 0
    assert "response" not in incomplete.json()["error"]

    missing = _score(client, _login(client, "admin"), str(uuid4()), f"results-missing-{uuid4().hex}")
    assert missing.status_code == 404
    assert _signature(missing) == ("NOT_FOUND", "resource_not_found", {})

    foreign_session = _seeded_session("evaluado_11")
    foreign = _score(
        client, evaluator, foreign_session, f"results-foreign-{uuid4().hex}"
    )
    assert foreign.status_code == 403 and foreign.json()["error"]["code"] == "FORBIDDEN"
    assert "scales" not in foreign.json()

    no_key = _score(client, _login(client, "admin"), _seeded_session("evaluado_12"), None)
    assert no_key.status_code == 422
    assert _signature(no_key)[:2] == ("VALIDATION_ERROR", "idempotency_key_required")


def test_score_replay_key_reuse_and_new_key_are_run_safe(
    client, seeded_db_session, db_session
) -> None:
    token = _login(client, "evaluado_13")
    session_id = _seeded_session("evaluado_13")
    key = f"results-replay-{uuid4().hex}"
    body = {"reference_set": "RS-TP-S-01"}
    first = _score(client, token, session_id, key, body)
    replay = _score(client, token, session_id, key, body)
    conflict = _score(client, token, session_id, key, {"reference_set": "other"})
    second = _score(client, token, session_id, f"results-new-key-{uuid4().hex}", body)

    assert first.status_code == 200, first.text
    assert replay.status_code == 200 and replay.json() == first.json()
    assert _signature(conflict)[:2] == ("CONFLICT", "idempotency_key_reused")
    assert second.status_code == 200, second.text
    assert _count(db_session, ScoreRun, session_id) == 2
    assert _count(db_session, AuditLog, session_id, event_type="scoring.run") == 2


def test_get_latest_result_pins_expected_run_and_preserves_norm_note(
    client, seeded_db_session, db_session
) -> None:
    token = _login(client, "evaluado_14")
    session_id = _seeded_session("evaluado_14")
    first = _score(client, token, session_id, f"results-latest-1-{uuid4().hex}")
    second = _score(client, token, session_id, f"results-latest-2-{uuid4().hex}")
    assert first.status_code == second.status_code == 200
    expected_run_id = second.json()["run"]["id"]

    # Pin the expected id explicitly instead of duplicating the repository ORDER BY.
    db_session.execute(
        update(ScoreRun)
        .where(ScoreRun.id == UUID(expected_run_id))
        .values(computed_at=datetime(2030, 1, 1, tzinfo=timezone.utc))
    )
    db_session.commit()
    reference = db_session.scalar(
        select(ReferenceSet).where(ReferenceSet.key == "RS-TP-S-01")
    )
    assert reference is not None
    response = client.get(f"/api/v1/results/{session_id}", headers=_headers(token))
    assert response.status_code == 200, response.text
    assert response.json()["run"]["id"] == expected_run_id
    assert response.json()["norm_note"] == reference.norm_note


def test_get_unscored_and_missing_results_share_not_found_signature(
    client, seeded_db_session, db_session
) -> None:
    token = _login(client, "evaluado_15")
    unscored = _runtime_session(db_session, "evaluado_15", "completed")
    unscored_response = client.get(f"/api/v1/results/{unscored}", headers=_headers(token))
    missing_response = client.get(f"/api/v1/results/{uuid4()}", headers=_headers(token))
    assert unscored_response.status_code == missing_response.status_code == 404
    assert _signature(unscored_response) == _signature(missing_response) == (
        "NOT_FOUND", "resource_not_found", {}
    )


def test_foreign_evaluado_cannot_read_results(client, seeded_db_session) -> None:
    admin = _login(client, "admin")
    foreign = _login(client, "evaluado_17")
    session_id = _seeded_session("evaluado_16")
    scored = _score(client, admin, session_id, f"results-owner-read-{uuid4().hex}")
    assert scored.status_code == 200, scored.text
    response = client.get(f"/api/v1/results/{session_id}", headers=_headers(foreign))
    assert response.status_code == 403 and response.json()["error"]["code"] == "FORBIDDEN"
    assert "scales" not in response.json()


def test_results_payload_is_scores_only_and_session_boundary_stays_intact(
    client, seeded_db_session, db_session
) -> None:
    admin = _login(client, "admin")
    session_id = _seeded_session("evaluado_18")
    scored = _score(client, admin, session_id, f"results-no-leak-{uuid4().hex}")
    assert scored.status_code == 200, scored.text
    response = client.get(f"/api/v1/results/{session_id}", headers=_headers(admin))
    assert response.status_code == 200, response.text
    payload = response.json()
    keys = {key.lower() for key in _keys(payload)}
    assert keys == {
        "session_id", "run", "id", "status", "computed_at", "reference_set_id",
        "norm_note", "scales", "label", "raw", "direct", "z", "transformed",
        "percentile", "t_score", "eneatype", "overall"
    }
    forbidden = {
        "value", "response_option_id", "item_id", "response_options", "mapping",
        "fixture_projection", "projection"
    }
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert not forbidden.intersection(keys) and "option" not in serialized
    items = db_session.scalars(
        select(InstrumentItem)
        .where(InstrumentItem.version_id == seed_id("TP-S-01:v1"))
        .order_by(InstrumentItem.item_order)
    ).all()
    for item in items:
        assert str(item.id) not in serialized and item.text.lower() not in serialized
        for option in item.response_options:
            assert str(option.id) not in serialized

    session_detail = client.get(f"/api/v1/sessions/{session_id}", headers=_headers(admin))
    assert session_detail.status_code == 200
    assert not any(
        term in str(session_detail.json()).lower()
        for term in ("score", "percentile", "eneatype", "reference")
    )

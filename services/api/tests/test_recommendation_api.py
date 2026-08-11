"""PostgreSQL-backed HTTP contracts for the F5 recommendation surface."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.main import app
from app.models.audit import AuditLog
from app.models.instruments import InstrumentItem
from app.models.recommendation import RecommendationResult, RecommendationRule
from app.models.scoring import ReferenceSet
from app.models.sessions import Response, Session as SessionRow
from app.seed.loader import seed_id


DISCLAIMER = (
    "Recomendaciones orientativas sobre datos sintéticos (research-only). "
    "No constituyen una norma UAGRM ni asesoramiento profesional."
)


@pytest.fixture
def client() -> Iterator[TestClient]:
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
        "/api/v1/auth/login",
        json={"username": username, "password": _password(username)},
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


def _seeded_session(profile: str) -> str:
    return str(seed_id(f"session:{profile}"))


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


def _score(client: TestClient, token: str, session_id: str, key: str):
    return client.post(
        f"/api/v1/results/{session_id}/score",
        json={},
        headers=_headers(token, key),
    )


def _generate(
    client: TestClient,
    token: str,
    session_id: str,
    key: str | None,
    body: dict | None = None,
):
    return client.post(
        f"/api/v1/recommendations/{session_id}/generate",
        json={} if body is None else body,
        headers=_headers(token, key),
    )


def _result_count(db_session, session_id: str) -> int:
    return int(
        db_session.scalar(
            select(func.count())
            .select_from(RecommendationResult)
            .where(RecommendationResult.session_id == UUID(session_id))
        )
        or 0
    )


def _events(db_session, session_id: str, event_type: str) -> list[AuditLog]:
    return list(
        db_session.scalars(
            select(AuditLog)
            .where(
                AuditLog.event_type == event_type,
                AuditLog.resource_id == session_id,
            )
            .order_by(AuditLog.occurred_at, AuditLog.id)
        ).all()
    )


def _keys(value) -> Iterator[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def _numeric_paths(value, path: tuple[str | int, ...] = ()):
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _numeric_paths(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _numeric_paths(child, (*path, index))


def test_generate_api_persists_rows_audit_and_exact_safe_payload(
    client, seeded_db_session, db_session
) -> None:
    token = _login(client, "evaluado_21")
    session_id = _seeded_session("evaluado_21")
    score = _score(client, token, session_id, f"recommendation-score-{uuid4().hex}")
    assert score.status_code == 200, score.text

    before_rows = _result_count(db_session, session_id)
    before_events = len(_events(db_session, session_id, "recommendation.generated"))
    active_rules = int(
        db_session.scalar(
            select(func.count())
            .select_from(RecommendationRule)
            .where(RecommendationRule.is_active.is_(True))
        )
        or 0
    )

    response = _generate(
        client,
        token,
        session_id,
        f"recommendation-generate-{uuid4().hex}",
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"session_id", "generated_at", "disclaimer", "items"}
    assert payload["session_id"] == session_id
    assert payload["generated_at"]
    assert payload["disclaimer"] == DISCLAIMER
    assert payload["items"]
    assert all(
        set(item)
        == {"program_id", "program_name", "program_code", "fit_score", "justification"}
        for item in payload["items"]
    )

    rows = list(
        db_session.scalars(
            select(RecommendationResult).where(
                RecommendationResult.session_id == UUID(session_id)
            )
        ).all()
    )
    assert _result_count(db_session, session_id) == before_rows + active_rules
    assert len(rows) == active_rules and len(rows) > 0
    assert all(row.synthetic is False and row.source == "runtime" for row in rows)

    grouped_rows: dict[str, list[RecommendationResult]] = {}
    for row in rows:
        grouped_rows.setdefault(str(row.program_id), []).append(row)
    for item in payload["items"]:
        item_rows = sorted(
            grouped_rows[item["program_id"]],
            key=lambda row: (str(row.rule_id), str(row.id)),
        )
        assert item["justification"] == "; ".join(
            row.justification for row in item_rows if row.justification is not None
        )
        assert " ≥ " in item["justification"]
        assert ">=" not in item["justification"]
        assert item["fit_score"] == pytest.approx(
            float(sum((row.fit_score for row in item_rows), 0))
        )

    events = _events(db_session, session_id, "recommendation.generated")
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
    assert metadata["session_id"] == session_id
    assert metadata["rule_count"] == metadata["result_count"] == len(rows)
    assert metadata["program_count"] == len(payload["items"])
    assert set(metadata["rule_ids"]) == {str(row.rule_id) for row in rows}
    assert set(metadata["program_ids"]) == {str(row.program_id) for row in rows}
    assert not any(
        term in json.dumps(metadata, ensure_ascii=False).lower()
        for term in ("fit_score", "justification", "response", "option", "item_content")
    )

    allowed_keys = {
        "session_id",
        "generated_at",
        "disclaimer",
        "items",
        "program_id",
        "program_name",
        "program_code",
        "fit_score",
        "justification",
    }
    assert set(_keys(payload)) == allowed_keys
    numeric_paths = list(_numeric_paths(payload))
    assert numeric_paths and all(path[-1] == "fit_score" for path, _ in numeric_paths)

    serialized = json.dumps(payload, ensure_ascii=False)
    reference = db_session.get(ReferenceSet, UUID(score.json()["reference_set_id"]))
    assert reference is not None
    assert reference.norm_note not in serialized
    assert "norm_note" not in serialized.lower()

    items = db_session.scalars(
        select(InstrumentItem).where(
            InstrumentItem.version_id == seed_id("TP-S-01:v1")
        )
    ).all()
    responses = db_session.scalars(
        select(Response).where(Response.session_id == UUID(session_id))
    ).all()
    for item in items:
        assert item.text not in serialized
        assert str(item.id) not in serialized
        for option in item.response_options:
            assert str(option.id) not in serialized
    for answer in responses:
        assert str(answer.id) not in serialized
        assert str(answer.item_id) not in serialized


def test_generation_api_replay_key_reuse_and_new_key_are_run_safe(
    client, seeded_db_session, db_session
) -> None:
    token = _login(client, "evaluado_22")
    session_id = _seeded_session("evaluado_22")
    score = _score(client, token, session_id, f"recommendation-score-{uuid4().hex}")
    assert score.status_code == 200, score.text

    key = f"recommendation-replay-{uuid4().hex}"
    body = {"mode": "default"}
    before_rows = _result_count(db_session, session_id)
    before_events = len(_events(db_session, session_id, "recommendation.generated"))

    first = _generate(client, token, session_id, key, body)
    after_first_rows = _result_count(db_session, session_id)
    replay = _generate(client, token, session_id, key, body)
    conflict = _generate(client, token, session_id, key, {"mode": "different"})
    second = _generate(
        client,
        token,
        session_id,
        f"recommendation-new-{uuid4().hex}",
        body,
    )

    assert first.status_code == 200, first.text
    assert replay.status_code == 200 and replay.json() == first.json()
    assert _signature(conflict)[:2] == ("CONFLICT", "idempotency_key_reused")
    assert second.status_code == 200, second.text
    assert _result_count(db_session, session_id) > before_rows
    assert _result_count(db_session, session_id) == before_rows + 2 * (
        after_first_rows - before_rows
    )
    assert len(_events(db_session, session_id, "recommendation.generated")) == before_events + 2


def test_generation_and_read_missing_unscored_and_ungenerated_share_not_found(
    client, seeded_db_session, db_session
) -> None:
    owner = _login(client, "evaluado_23")
    unscored = _runtime_session(db_session, "evaluado_23", "completed")
    unscored_response = _generate(
        client, owner, unscored, f"recommendation-unscored-{uuid4().hex}"
    )
    missing_post = _generate(
        client, _login(client, "admin"), str(uuid4()), f"recommendation-missing-{uuid4().hex}"
    )
    assert _signature(unscored_response) == _signature(missing_post) == (
        "NOT_FOUND",
        "resource_not_found",
        {},
    )

    scored_owner = _login(client, "evaluado_24")
    scored_session = _seeded_session("evaluado_24")
    score = _score(
        client, scored_owner, scored_session, f"recommendation-score-{uuid4().hex}"
    )
    assert score.status_code == 200, score.text
    no_generation = client.get(
        f"/api/v1/recommendations/{scored_session}",
        headers=_headers(scored_owner),
    )
    missing_get = client.get(
        f"/api/v1/recommendations/{uuid4()}",
        headers=_headers(scored_owner),
    )
    assert _signature(no_generation) == _signature(missing_get) == (
        "NOT_FOUND",
        "resource_not_found",
        {},
    )


def test_generation_api_rejects_in_progress_and_missing_idempotency_key(
    client, seeded_db_session, db_session
) -> None:
    owner = _login(client, "evaluado_25")
    in_progress = _runtime_session(db_session, "evaluado_25", "in_progress")
    incomplete = _generate(
        client, owner, in_progress, f"recommendation-in-progress-{uuid4().hex}"
    )
    assert _signature(incomplete) == (
        "CONFLICT",
        "session_not_completed",
        {},
    )
    assert "response" not in incomplete.json()["error"]
    assert "score" not in incomplete.json()["error"]

    missing_key = _generate(client, owner, _seeded_session("evaluado_25"), None)
    assert missing_key.status_code == 422
    assert _signature(missing_key)[:2] == (
        "VALIDATION_ERROR",
        "idempotency_key_required",
    )


def test_get_latest_recommendations_returns_ordered_items_and_pinned_disclaimer(
    client, seeded_db_session
) -> None:
    token = _login(client, "evaluado_26")
    session_id = _seeded_session("evaluado_26")
    score = _score(client, token, session_id, f"recommendation-score-{uuid4().hex}")
    assert score.status_code == 200, score.text
    first = _generate(
        client, token, session_id, f"recommendation-latest-1-{uuid4().hex}"
    )
    second = _generate(
        client, token, session_id, f"recommendation-latest-2-{uuid4().hex}"
    )
    assert first.status_code == second.status_code == 200

    response = client.get(
        f"/api/v1/recommendations/{session_id}",
        headers=_headers(token),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload == second.json()
    assert payload["disclaimer"] == DISCLAIMER
    assert payload["items"] == sorted(
        payload["items"],
        key=lambda item: (-item["fit_score"], item["program_name"]),
    )
    assert "norm_note" not in json.dumps(payload, ensure_ascii=False).lower()


def test_foreign_evaluado_cannot_generate_or_read_recommendations(
    client, seeded_db_session, db_session
) -> None:
    admin = _login(client, "admin")
    owner = _login(client, "evaluado_27")
    foreign = _login(client, "evaluado_28")
    session_id = _seeded_session("evaluado_27")
    score = _score(client, admin, session_id, f"recommendation-score-{uuid4().hex}")
    assert score.status_code == 200, score.text
    generated = _generate(
        client, admin, session_id, f"recommendation-owner-{uuid4().hex}"
    )
    assert generated.status_code == 200, generated.text
    before_rows = _result_count(db_session, session_id)
    before_events = len(_events(db_session, session_id, "recommendation.generated"))
    before_denials = len(_events(db_session, session_id, "auth.denied"))

    foreign_generate = _generate(
        client, foreign, session_id, f"recommendation-foreign-{uuid4().hex}"
    )
    foreign_read = client.get(
        f"/api/v1/recommendations/{session_id}", headers=_headers(foreign)
    )

    assert foreign_generate.status_code == 403
    assert foreign_generate.json()["error"]["code"] == "FORBIDDEN"
    assert foreign_read.status_code == 403
    assert foreign_read.json()["error"]["code"] == "FORBIDDEN"
    assert "items" not in foreign_generate.json()
    assert "items" not in foreign_read.json()
    assert _result_count(db_session, session_id) == before_rows
    assert len(_events(db_session, session_id, "recommendation.generated")) == before_events
    assert len(_events(db_session, session_id, "auth.denied")) == before_denials + 2

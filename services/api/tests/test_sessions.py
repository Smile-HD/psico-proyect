"""F3 integration tests — Evaluation Session & Delivery.

All tests require a reachable PostgreSQL + seeded database
(``PSICO_DATABASE_URL`` env var + compose stack).  They skip cleanly when
the database is not available.

Coverage:
  - Session creation: consent-gated, version must be published, status locked.
  - Session resume: saved responses + server-calculated remaining time.
  - Response autosave: idempotent via Idempotency-Key, value validation.
  - Submit: freeze responses → completed; editing completed session → 409.
  - Ownership: evaluado cannot access another user's session.
  - Audit trail: session.started, session.resumed, session.response_saved,
    session.completed written correctly.
  - Error envelope shape: {error: {code, message, request_id, details}}.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models.audit import AuditLog
from app.models.sessions import Response, Session
from app.seed.loader import seed_id


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, username: str) -> str:
    password = {
        "admin": settings.dev_password_admin,
        "psicologo": settings.dev_password_psicologo,
        "evaluado": settings.dev_password_evaluado,
    }[username]
    resp = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _grant_consent(client: TestClient, token: str) -> None:
    """Grant the active consent for the dev evaluado account."""
    consent_id = str(seed_id("consent:v1"))
    resp = client.post(f"/api/v1/consent/{consent_id}/grant", headers=_auth(token))
    assert resp.status_code == 200, f"consent grant failed: {resp.text}"


def _revoke_consent(client: TestClient, token: str) -> None:
    consent_id = str(seed_id("consent:v1"))
    client.post(f"/api/v1/consent/{consent_id}/revoke", headers=_auth(token))


def _audit_count(db_session, event_type: str, resource_id: str | None = None) -> int:
    db_session.rollback()
    q = select(AuditLog).where(AuditLog.event_type == event_type)
    if resource_id:
        q = q.where(AuditLog.resource_id == resource_id)
    return len(db_session.scalars(q).all())


# ---------------------------------------------------------------------------
# Helper: create a session for the evaluado (handles consent grant internally)
# ---------------------------------------------------------------------------


def _create_session(client: TestClient, token: str) -> dict:
    version_id = str(seed_id("TP-S-01:v1"))
    resp = client.post(
        "/api/v1/sessions",
        json={"instrument_version_id": version_id},
        headers=_auth(token),
    )
    return resp


# ---------------------------------------------------------------------------
# 1. Session creation
# ---------------------------------------------------------------------------


def test_session_create_requires_consent(client, seeded_db_session) -> None:
    """Evaluado without consent → 409 CONFLICT."""
    token = _login(client, "evaluado")
    _revoke_consent(client, token)  # ensure no grant
    resp = _create_session(client, token)
    assert resp.status_code == 409
    body = resp.json()
    assert set(body["error"].keys()) == {"code", "message", "request_id", "details"}
    assert body["error"]["code"] == "CONFLICT"


def test_session_create_success(client, seeded_db_session, db_session) -> None:
    """Happy path: grant consent then create session → 201, in_progress."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    resp = _create_session(client, token)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "in_progress"
    assert "id" in body
    assert body["instrument_version_id"] == str(seed_id("TP-S-01:v1"))
    assert "started_at" in body
    # audit
    assert _audit_count(db_session, "session.started", body["id"]) >= 1


def test_session_create_accepts_version_key_string(client, seeded_db_session) -> None:
    """Session create accepts version key string like TP-S-01:v1."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    resp = client.post(
        "/api/v1/sessions",
        json={"instrument_version_id": "TP-S-01:v1"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["instrument_version_id"] == str(seed_id("TP-S-01:v1"))


def test_session_create_invalid_version(client, seeded_db_session) -> None:
    """Non-existent instrument_version_id → 404."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    resp = client.post(
        "/api/v1/sessions",
        json={"instrument_version_id": str(uuid.uuid4())},
        headers=_auth(token),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_session_create_unpublished_version_rejected(
    client, seeded_db_session, db_session
) -> None:
    """A draft instrument version must be rejected with VALIDATION_ERROR."""
    # Create a draft via catalog API (admin creates, does NOT publish)
    admin_token = _login(client, "admin")
    created = client.post(
        "/api/v1/catalog/admin/instruments",
        headers=_auth(admin_token, "f3-draft-inst"),
        json={"key": "F3-DRAFT-01", "title": "F3 Draft Instrument"},
    )
    assert created.status_code == 201, created.text
    draft_version_id = created.json()["draft"]["instrument_version_id"]

    eval_token = _login(client, "evaluado")
    _grant_consent(client, eval_token)
    resp = client.post(
        "/api/v1/sessions",
        json={"instrument_version_id": draft_version_id},
        headers=_auth(eval_token),
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_session_create_locked_version(client, seeded_db_session, db_session) -> None:
    """Session stores the exact instrument_version_id at creation."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    resp = _create_session(client, token)
    assert resp.status_code == 201
    session_id = resp.json()["id"]
    row = db_session.get(Session, uuid.UUID(session_id))
    assert row is not None
    assert str(row.instrument_version_id) == str(seed_id("TP-S-01:v1"))


def test_session_create_unauthenticated(client, seeded_db_session) -> None:
    """No JWT → 401."""
    resp = client.post(
        "/api/v1/sessions",
        json={"instrument_version_id": str(seed_id("TP-S-01:v1"))},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Resume endpoint
# ---------------------------------------------------------------------------


def test_session_resume_returns_saved_responses(
    client, seeded_db_session, db_session
) -> None:
    """Resume must echo back every saved response + server timer."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    session_resp = _create_session(client, token)
    assert session_resp.status_code == 201
    session_id = session_resp.json()["id"]

    # Save two responses first
    item1_id = str(seed_id("TP-S-01:i1"))
    item2_id = str(seed_id("TP-S-01:i2"))
    client.post(
        f"/api/v1/sessions/{session_id}/responses",
        json={"item_id": item1_id, "value": 3},
        headers=_auth(token, "res-i1"),
    )
    client.post(
        f"/api/v1/sessions/{session_id}/responses",
        json={"item_id": item2_id, "value": 5},
        headers=_auth(token, "res-i2"),
    )

    # Resume
    resume = client.get(f"/api/v1/sessions/{session_id}/resume", headers=_auth(token))
    assert resume.status_code == 200, resume.text
    body = resume.json()
    assert body["id"] == session_id
    assert body["status"] == "in_progress"
    assert body["instrument_version_id"] == str(seed_id("TP-S-01:v1"))
    assert "started_at" in body
    # remaining_seconds is None since no duration_minutes on the model yet
    assert body["remaining_seconds"] is None
    saved = {str(r["item_id"]): r["value"] for r in body["saved_responses"]}
    assert saved[item1_id] == 3
    assert saved[item2_id] == 5
    # audit
    assert _audit_count(db_session, "session.resumed", session_id) >= 1


def test_session_resume_not_found(client, seeded_db_session) -> None:
    """Unknown session id → 404."""
    token = _login(client, "evaluado")
    resp = client.get(
        f"/api/v1/sessions/{uuid.uuid4()}/resume", headers=_auth(token)
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_session_resume_ownership(client, seeded_db_session, db_session) -> None:
    """Evaluado cannot resume another user's session (403)."""
    eval_token = _login(client, "evaluado")
    _grant_consent(client, eval_token)
    sess = _create_session(client, eval_token)
    assert sess.status_code == 201
    session_id = sess.json()["id"]

    # Psicologo tries to access evaluado's session
    psico_token = _login(client, "psicologo")
    resp = client.get(
        f"/api/v1/sessions/{session_id}/resume", headers=_auth(psico_token)
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 3. Response autosave — idempotency
# ---------------------------------------------------------------------------


def test_response_save_requires_idempotency_key(client, seeded_db_session) -> None:
    """Missing Idempotency-Key header → 422 VALIDATION_ERROR."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    sess = _create_session(client, token)
    session_id = sess.json()["id"]

    resp = client.post(
        f"/api/v1/sessions/{session_id}/responses",
        json={"item_id": str(seed_id("TP-S-01:i1")), "value": 2},
        headers=_auth(token),  # no Idempotency-Key
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_response_save_first_call_created_true(
    client, seeded_db_session, db_session
) -> None:
    """First autosave returns created=true."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    session_id = _create_session(client, token).json()["id"]

    resp = client.post(
        f"/api/v1/sessions/{session_id}/responses",
        json={"item_id": str(seed_id("TP-S-01:i3")), "value": 4},
        headers=_auth(token, "save-i3-first"),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["created"] is True
    assert body["value"] == 4
    assert body["item_id"] == str(seed_id("TP-S-01:i3"))
    assert "response_id" in body
    # audit
    assert _audit_count(db_session, "session.response_saved", session_id) >= 1


def test_response_save_idempotent_replay(
    client, seeded_db_session, db_session
) -> None:
    """Replay with same (session, item) returns existing record and created=false."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    session_id = _create_session(client, token).json()["id"]

    item_id = str(seed_id("TP-S-01:i4"))
    first = client.post(
        f"/api/v1/sessions/{session_id}/responses",
        json={"item_id": item_id, "value": 1},
        headers=_auth(token, "idemp-i4"),
    )
    assert first.status_code == 201
    first_resp_id = first.json()["response_id"]

    # Replay (same item, same value)
    replay = client.post(
        f"/api/v1/sessions/{session_id}/responses",
        json={"item_id": item_id, "value": 1},
        headers=_auth(token, "idemp-i4"),
    )
    assert replay.status_code == 201
    body = replay.json()
    assert body["created"] is False
    assert body["response_id"] == first_resp_id

    # Only one row in DB
    responses = db_session.scalars(
        select(Response).where(
            Response.session_id == uuid.UUID(session_id),
            Response.item_id == uuid.UUID(item_id),
        )
    ).all()
    assert len(responses) == 1


def test_response_save_value_out_of_range(client, seeded_db_session) -> None:
    """Value outside [1,5] → 422 VALIDATION_ERROR before hitting DB."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    session_id = _create_session(client, token).json()["id"]

    resp = client.post(
        f"/api/v1/sessions/{session_id}/responses",
        json={"item_id": str(seed_id("TP-S-01:i5")), "value": 6},
        headers=_auth(token, "out-of-range"),
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_response_save_item_not_in_version(client, seeded_db_session) -> None:
    """item_id that does not belong to the session's version → 404."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    session_id = _create_session(client, token).json()["id"]

    resp = client.post(
        f"/api/v1/sessions/{session_id}/responses",
        json={"item_id": str(uuid.uuid4()), "value": 3},
        headers=_auth(token, "bad-item"),
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_response_save_on_completed_session(client, seeded_db_session) -> None:
    """Autosave on a completed session → 409 CONFLICT."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    session_id = _create_session(client, token).json()["id"]

    # Submit first
    client.post(f"/api/v1/sessions/{session_id}/submit", headers=_auth(token))

    resp = client.post(
        f"/api/v1/sessions/{session_id}/responses",
        json={"item_id": str(seed_id("TP-S-01:i1")), "value": 2},
        headers=_auth(token, "after-submit"),
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


# ---------------------------------------------------------------------------
# 4. Submit endpoint
# ---------------------------------------------------------------------------


def test_submit_transitions_to_completed(
    client, seeded_db_session, db_session
) -> None:
    """Submit: status → completed, completed_at set, response_count accurate."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    session_id = _create_session(client, token).json()["id"]

    # Save two responses
    for idx, val in [(6, 2), (7, 4)]:
        client.post(
            f"/api/v1/sessions/{session_id}/responses",
            json={"item_id": str(seed_id(f"TP-S-01:i{idx}")), "value": val},
            headers=_auth(token, f"submit-save-i{idx}"),
        )

    resp = client.post(f"/api/v1/sessions/{session_id}/submit", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == session_id
    assert body["status"] == "completed"
    assert body["response_count"] == 2
    assert "completed_at" in body

    # DB row check
    db_session.rollback()
    row = db_session.get(Session, uuid.UUID(session_id))
    db_session.refresh(row)
    assert row.status == "completed"
    assert row.completed_at is not None

    # audit
    assert _audit_count(db_session, "session.completed", session_id) >= 1


def test_submit_already_completed_returns_conflict(client, seeded_db_session) -> None:
    """Submitting an already-completed session → 409 CONFLICT."""
    token = _login(client, "evaluado")
    _grant_consent(client, token)
    session_id = _create_session(client, token).json()["id"]

    first = client.post(
        f"/api/v1/sessions/{session_id}/submit", headers=_auth(token)
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/sessions/{session_id}/submit", headers=_auth(token)
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


def test_submit_not_found(client, seeded_db_session) -> None:
    """Unknown session id → 404."""
    token = _login(client, "evaluado")
    resp = client.post(
        f"/api/v1/sessions/{uuid.uuid4()}/submit", headers=_auth(token)
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_submit_ownership(client, seeded_db_session) -> None:
    """Psicólogo cannot submit evaluado's session (403)."""
    eval_token = _login(client, "evaluado")
    _grant_consent(client, eval_token)
    session_id = _create_session(client, eval_token).json()["id"]

    psico_token = _login(client, "psicologo")
    resp = client.post(
        f"/api/v1/sessions/{session_id}/submit", headers=_auth(psico_token)
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 5. Admin override
# ---------------------------------------------------------------------------


def test_admin_can_access_any_session(client, seeded_db_session) -> None:
    """Admin can resume any session regardless of ownership."""
    eval_token = _login(client, "evaluado")
    _grant_consent(client, eval_token)
    session_id = _create_session(client, eval_token).json()["id"]

    admin_token = _login(client, "admin")
    resp = client.get(
        f"/api/v1/sessions/{session_id}/resume", headers=_auth(admin_token)
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 6. Error envelope shape
# ---------------------------------------------------------------------------


def test_error_envelope_shape_on_404(client, seeded_db_session) -> None:
    """All 404 errors return the canonical error envelope."""
    token = _login(client, "evaluado")
    resp = client.get(
        f"/api/v1/sessions/{uuid.uuid4()}/resume", headers=_auth(token)
    )
    assert resp.status_code == 404
    body = resp.json()
    assert set(body["error"].keys()) == {"code", "message", "request_id", "details"}
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["request_id"]  # non-empty


def test_error_envelope_shape_on_conflict(client, seeded_db_session) -> None:
    """Conflict errors return the canonical error envelope."""
    token = _login(client, "evaluado")
    _revoke_consent(client, token)
    resp = _create_session(client, token)
    assert resp.status_code == 409
    body = resp.json()
    assert set(body["error"].keys()) == {"code", "message", "request_id", "details"}

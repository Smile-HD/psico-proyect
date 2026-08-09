"""PostgreSQL-backed session-runtime service contracts."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.consent import grant_consent
from app.core.errors import ApiError
from app.models.audit import AuditLog
from app.models.consent import ConsentVersion
from app.models.sessions import Response, Session
from app.modules.session_runtime.repository import SessionRepository
from app.modules.session_runtime.service import SessionService
from app.seed.loader import seed_id


def _user(key: str, role: str = "evaluado"):
    return SimpleNamespace(id=seed_id(key), roles=[role])


def _grant(db, user) -> None:
    version = db.scalar(select(ConsentVersion).where(ConsentVersion.is_active.is_(True)))
    grant_consent(db, user.id, version.id)


def test_create_is_gate_first_and_actor_key_replays(seeded_db_session) -> None:
    db, service, user = seeded_db_session, SessionService(), _user("user:evaluado")
    version, key = str(seed_id("TP-S-01:v1")), f"create-{uuid4()}"
    with pytest.raises(ApiError, match="resource_not_found"):
        service.create_session(db, user, {"instrument_version_id": "bad"}, key)
    with pytest.raises(ApiError, match="consent_required"):
        service.create_session(db, user, {"instrument_version_id": version}, key)
    _grant(db, user)
    first = service.create_session(db, user, {"instrument_version_id": version}, key)
    assert first == service.create_session(db, user, {"instrument_version_id": version}, key)
    assert db.scalar(select(func.count()).select_from(Session).where(Session.id == first[1]["id"])) == 1
    assert db.scalar(select(func.count()).where(
        AuditLog.event_type == "session.started", AuditLog.resource_id == first[1]["id"])) == 1


def test_save_is_owner_scoped_and_completion_is_required_and_idempotent(seeded_db_session) -> None:
    db, service, user = seeded_db_session, SessionService(), _user("evaluado_02")
    _grant(db, user)
    _, created = service.create_session(db, user, {"instrument_version_id": str(seed_id("TP-S-01:v1"))}, str(uuid4()))
    session_id = created["id"]
    with pytest.raises(ApiError, match="insufficient_role"):
        service.get_session(db, _user("evaluado_03"), session_id)
    assert service.list_sessions(db, user)["sessions"][0]["id"] == session_id
    with pytest.raises(ApiError, match="validation_error"):
        service.complete_session(db, user, session_id, str(uuid4()))
    allowed = SessionRepository().response_option_map(db, seed_id("TP-S-01:v1"))
    body = {"responses": [{"item_id": str(item), "response_option_id": str(next(iter(options)))}
                           for item, options in allowed.items()]}
    save_key = f"save-{uuid4()}"
    service.save_responses(db, user, session_id, body, save_key)
    assert service.save_responses(db, user, session_id, body, save_key)[1]["saved_count"] == len(body["responses"])
    assert db.scalar(select(func.count()).select_from(Response).where(Response.session_id == session_id)) == len(body["responses"])
    assert db.scalar(select(func.count()).where(AuditLog.resource_id == session_id, AuditLog.action == "save")) == 0
    admin, complete_key = _user("user:admin", "admin"), f"complete-{uuid4()}"
    result = service.complete_session(db, admin, session_id, complete_key)
    assert result == service.complete_session(db, admin, session_id, complete_key)
    event = db.scalar(select(AuditLog).where(AuditLog.resource_id == session_id, AuditLog.event_type == "session.completed"))
    assert event.metadata_ == {"response_count": len(body["responses"])}

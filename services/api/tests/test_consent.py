"""RED test — consent (F1): consent-gated sessions, grant/revoke lifecycle.

DB tests (skip without PostgreSQL + seed):
  - Session without granted consent -> CONFLICT + session.blocked_without_consent.
  - Grant lifecycle: grant -> granted row + consent.granted audited.
  - Revoke lifecycle: revoke -> state revoked + consent.revoked audited.
  - Granted session starts: session created + session.started audited.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.main import app
from app.models.audit import AuditLog
from app.models.consent import ConsentGrant, ConsentVersion
from app.seed.loader import seed_id


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, username: str) -> str:
    password = {
        "admin": settings.dev_password_admin,
        "psicologo": settings.dev_password_psicologo,
        "evaluado": settings.dev_password_evaluado,
    }[username]
    return client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    ).json()["access_token"]


def _auth(token: str, key: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _audit_event_count(db_session, event_type: str) -> int:
    return db_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.event_type == event_type)
    ) or 0


def test_consent_version_seeded(seeded_db_session, db_session) -> None:
    versions = db_session.scalars(select(ConsentVersion)).all()
    assert len(versions) >= 1
    assert any(v.is_active for v in versions)


def test_session_blocked_without_consent(client, seeded_db_session, db_session) -> None:
    # Dev `evaluado` account has NO consent grant (only the 30 profiles do).
    token = _login(client, "evaluado")
    version_id = str(seed_id("TP-S-01:v1"))
    resp = client.post(
        "/api/v1/sessions",
        json={"instrument_version_id": version_id},
        headers=_auth(token, "consent-session-blocked"),
    )
    assert resp.status_code == 409
    body = resp.json()
    assert set(body["error"].keys()) == {"code", "message", "request_id", "details"}
    assert body["error"]["code"] == "CONFLICT"
    # blocked_without_consent audited
    assert _audit_event_count(db_session, "session.blocked_without_consent") >= 1


def test_grant_then_session_starts(client, seeded_db_session, db_session) -> None:
    token = _login(client, "evaluado")
    version_id = str(seed_id("TP-S-01:v1"))
    consent_id = str(seed_id("consent:v1"))

    grant_resp = client.post(
        f"/api/v1/consent/{consent_id}/grant",
        headers=_auth(token, "legacy-grant-session"),
    )
    assert grant_resp.status_code == 200
    assert grant_resp.json()["state"] == "granted"
    assert _audit_event_count(db_session, "consent.granted") >= 1

    resp = client.post(
        "/api/v1/sessions",
        json={"instrument_version_id": version_id},
        headers=_auth(token, "consent-session-start"),
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "in_progress"
    assert _audit_event_count(db_session, "session.started") >= 1

    # registry state is granted
    grant = db_session.scalars(
        select(ConsentGrant).where(
            ConsentGrant.user_id == seed_id("user:evaluado"),
            ConsentGrant.consent_version_id == seed_id("consent:v1"),
        )
    ).first()
    assert grant is not None and grant.state == "granted"


def test_revoke_lifecycle(client, seeded_db_session, db_session) -> None:
    token = _login(client, "evaluado")
    consent_id = str(seed_id("consent:v1"))

    client.post(
        f"/api/v1/consent/{consent_id}/grant",
        headers=_auth(token, "legacy-grant-revoke"),
    )
    revoke_resp = client.post(
        f"/api/v1/consent/{consent_id}/revoke",
        headers=_auth(token, "legacy-revoke"),
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["state"] == "revoked"
    assert _audit_event_count(db_session, "consent.revoked") >= 1

    grant = db_session.scalars(
        select(ConsentGrant).where(
            ConsentGrant.user_id == seed_id("user:evaluado"),
            ConsentGrant.consent_version_id == seed_id("consent:v1"),
        )
    ).first()
    assert grant is not None and grant.state == "revoked"


def test_session_blocked_again_after_revoke(client, seeded_db_session, db_session) -> None:
    token = _login(client, "evaluado")
    consent_id = str(seed_id("consent:v1"))
    version_id = str(seed_id("TP-S-01:v1"))

    client.post(
        f"/api/v1/consent/{consent_id}/grant",
        headers=_auth(token, "legacy-grant-blocked"),
    )
    client.post(
        f"/api/v1/consent/{consent_id}/revoke",
        headers=_auth(token, "legacy-revoke-blocked"),
    )

    resp = client.post(
        "/api/v1/sessions",
        json={"instrument_version_id": version_id},
        headers=_auth(token, "consent-session-revoked"),
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"

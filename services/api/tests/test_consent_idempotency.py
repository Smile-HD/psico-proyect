"""F3 consent mutation idempotency contracts."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.main import app
from app.models.audit import AuditLog
from app.models.consent import ConsentGrant
from app.seed.loader import seed_id


def _login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "evaluado", "password": settings.dev_password_evaluado},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str, key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": key,
    }


def _event_count(db_session, event_type: str) -> int:
    return (
        db_session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.event_type == event_type)
        )
        or 0
    )


def _grant_count(db_session) -> int:
    return (
        db_session.scalar(
            select(func.count())
            .select_from(ConsentGrant)
            .where(
                ConsentGrant.user_id == seed_id("user:evaluado"),
                ConsentGrant.consent_version_id == seed_id("consent:v1"),
            )
        )
        or 0
    )


def test_grant_retry_replays_without_duplicate_registry_or_audit(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        token = _login(client)
        consent_id = str(seed_id("consent:v1"))
        before_events = _event_count(db_session, "consent.granted")

        first = client.post(
            f"/api/v1/consent/{consent_id}/grant",
            headers=_headers(token, "consent-grant-replay"),
        )
        replay = client.post(
            f"/api/v1/consent/{consent_id}/grant",
            headers=_headers(token, "consent-grant-replay"),
        )

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert _grant_count(db_session) == 1
    assert _event_count(db_session, "consent.granted") == before_events + 1


def test_revoke_retry_replays_without_duplicate_registry_or_audit(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        token = _login(client)
        consent_id = str(seed_id("consent:v1"))
        granted = client.post(
            f"/api/v1/consent/{consent_id}/grant",
            headers=_headers(token, "consent-revoke-setup"),
        )
        assert granted.status_code == 200, granted.text
        before_events = _event_count(db_session, "consent.revoked")

        first = client.post(
            f"/api/v1/consent/{consent_id}/revoke",
            headers=_headers(token, "consent-revoke-replay"),
        )
        replay = client.post(
            f"/api/v1/consent/{consent_id}/revoke",
            headers=_headers(token, "consent-revoke-replay"),
        )

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert replay.json()["state"] == "revoked"
    assert _grant_count(db_session) == 1
    assert _event_count(db_session, "consent.revoked") == before_events + 1


def test_same_consent_key_with_different_body_conflicts_without_side_effect(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        token = _login(client)
        consent_id = str(seed_id("consent:v1"))
        before_events = _event_count(db_session, "consent.granted")

        first = client.post(
            f"/api/v1/consent/{consent_id}/grant",
            headers=_headers(token, "consent-body-conflict"),
            json={"confirmation": "accepted"},
        )
        conflict = client.post(
            f"/api/v1/consent/{consent_id}/grant",
            headers=_headers(token, "consent-body-conflict"),
            json={"confirmation": "changed"},
        )

    assert first.status_code == 200, first.text
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["message"] == "idempotency_key_reused"
    assert _grant_count(db_session) == 1
    assert _event_count(db_session, "consent.granted") == before_events + 1


def test_consent_grant_and_revoke_require_idempotency_key(
    seeded_db_session,
) -> None:
    with TestClient(app) as client:
        token = _login(client)
        consent_id = str(seed_id("consent:v1"))
        grant_missing = client.post(
            f"/api/v1/consent/{consent_id}/grant",
            headers={"Authorization": f"Bearer {token}"},
        )
        revoke_missing = client.post(
            f"/api/v1/consent/{consent_id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert grant_missing.status_code == 422
    assert grant_missing.json()["error"]["message"] == "idempotency_key_required"
    assert revoke_missing.status_code == 422
    assert revoke_missing.json()["error"]["message"] == "idempotency_key_required"

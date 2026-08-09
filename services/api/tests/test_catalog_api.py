"""F2 API and lifecycle integration scenarios."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models.audit import AuditLog
from app.models.instruments import InstrumentVersion


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _content() -> dict:
    return {
        "response_type": "likert_1_5",
        "scales": [
            {
                "display_order": 1,
                "label": "Intereses",
                "locale": "es",
                "items": [
                    {
                        "item_order": 1,
                        "text": "Ítem sintético de prueba",
                        "locale": "es",
                        "required": True,
                        "options": [
                            {"display_order": index, "label": label, "locale": "es"}
                            for index, label in enumerate(
                                [
                                    "Nunca",
                                    "Casi nunca",
                                    "A veces",
                                    "Casi siempre",
                                    "Siempre",
                                ],
                                start=1,
                            )
                        ],
                    }
                ],
            }
        ],
    }


def _create_and_save(
    client: TestClient, token: str, suffix: str = "01"
) -> tuple[str, str]:
    created = client.post(
        "/api/v1/catalog/admin/instruments",
        headers=_headers(token, f"create-{suffix}"),
        json={"key": f"CAT-API-{suffix}", "title": "Catálogo sintético"},
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    instrument_id = payload["instrument"]["id"]
    version_id = payload["draft"]["instrument_version_id"]
    saved = client.put(
        f"/api/v1/catalog/admin/versions/{version_id}/content",
        headers=_headers(token, f"save-{suffix}"),
        json=_content(),
    )
    assert saved.status_code == 200, saved.text
    return instrument_id, version_id


def test_create_save_publish_read_archive_and_payload_secrecy(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        psychologist = _login(client, "psicologo", settings.dev_password_psicologo)
        admin = _login(client, "admin", settings.dev_password_admin)
        evaluator = _login(client, "evaluado", settings.dev_password_evaluado)
        _instrument_id, version_id = _create_and_save(client, psychologist)

        denied = client.post(
            f"/api/v1/catalog/admin/versions/{version_id}/publish",
            headers=_headers(psychologist, "publish-denied"),
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "FORBIDDEN"

        published = client.post(
            f"/api/v1/catalog/admin/versions/{version_id}/publish",
            headers=_headers(admin, "publish-01"),
        )
        assert published.status_code == 200
        assert published.json()["status"] == "published"

        read = client.get(
            f"/api/v1/catalog/published-versions/{version_id}",
            headers=_headers(evaluator),
        )
        assert read.status_code == 200, read.text
        body = read.json()
        serialized = str(body).lower()
        assert "value" not in serialized
        assert body["scales"][0]["items"][0]["response_options"][0]["label"] == "Nunca"

        replay = client.post(
            f"/api/v1/catalog/admin/versions/{version_id}/publish",
            headers=_headers(admin, "publish-01"),
        )
        assert replay.status_code == 200
        published_events = db_session.scalars(
            select(AuditLog).where(
                AuditLog.event_type == "instrument.published",
                AuditLog.resource_id == version_id,
            )
        ).all()
        assert len(published_events) == 1

        archived = client.post(
            f"/api/v1/catalog/admin/versions/{version_id}/archive",
            headers=_headers(psychologist, "archive-01"),
        )
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"
        assert (
            client.get(
                f"/api/v1/catalog/published-versions/{version_id}",
                headers=_headers(evaluator),
            ).json()["error"]["code"]
            == "NOT_FOUND"
        )


def test_invalid_publish_rolls_back_and_non_published_read_does_not_leak(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin", settings.dev_password_admin)
        evaluator = _login(client, "evaluado", settings.dev_password_evaluado)
        created = client.post(
            "/api/v1/catalog/admin/instruments",
            headers=_headers(admin, "invalid-create"),
            json={"key": "CAT-INVALID-01", "title": "Inválido"},
        )
        version_id = created.json()["draft"]["instrument_version_id"]
        publish = client.post(
            f"/api/v1/catalog/admin/versions/{version_id}/publish",
            headers=_headers(admin, "invalid-publish"),
        )
        assert publish.status_code == 422
        assert publish.json()["error"]["code"] == "VALIDATION_ERROR"
        assert (
            db_session.get(InstrumentVersion, uuid.UUID(version_id)).status == "draft"
        )
        hidden = client.get(
            f"/api/v1/catalog/published-versions/{version_id}",
            headers=_headers(evaluator),
        )
        assert hidden.status_code == 404
        assert hidden.json()["error"]["code"] == "NOT_FOUND"


def test_same_key_different_body_conflicts_without_second_instrument(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        psychologist = _login(client, "psicologo", settings.dev_password_psicologo)
        first = client.post(
            "/api/v1/catalog/admin/instruments",
            headers=_headers(psychologist, "same-key"),
            json={"key": "CAT-IDEMP-01", "title": "Primero"},
        )
        assert first.status_code == 201
        second = client.post(
            "/api/v1/catalog/admin/instruments",
            headers=_headers(psychologist, "same-key"),
            json={"key": "CAT-IDEMP-01", "title": "Distinto"},
        )
        assert second.status_code == 409
        assert second.json()["error"]["message"] == "idempotency_key_reused"


def test_admin_list_rows_carry_instrument_identity(seeded_db_session) -> None:
    """The authoring list must render key/title per row (web catalog table)."""
    with TestClient(app) as client:
        admin = _login(client, "admin", settings.dev_password_admin)
        resp = client.get(
            "/api/v1/catalog/admin/instruments",
            headers=_headers(admin),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"items", "page", "page_size", "total"}
        assert body["items"], "seed must provide at least one instrument row"
        for row in body["items"]:
            # Web InstrumentRow contract: instrument identity + version summary.
            for field in (
                "key",
                "title",
                "instrument_id",
                "instrument_version_id",
                "status",
                "version_no",
                "source",
                "synthetic",
            ):
                assert field in row, f"list row missing {field}"
            assert "id" not in row, "legacy web field must not appear"


def test_admin_version_detail_flat_contract(seeded_db_session) -> None:
    """The web editor reads status/title/key at the top level of the detail."""
    with TestClient(app) as client:
        psychologist = _login(client, "psicologo", settings.dev_password_psicologo)
        created = client.post(
            "/api/v1/catalog/admin/instruments",
            headers=_headers(psychologist, "detail-shape"),
            json={"key": "CAT-DETAIL-01", "title": "Detalle plano"},
        )
        assert created.status_code == 201
        version_id = created.json()["draft"]["instrument_version_id"]
        detail = client.get(
            f"/api/v1/catalog/admin/versions/{version_id}",
            headers=_headers(psychologist),
        )
        assert detail.status_code == 200
        body = detail.json()
        # Web editor contract: flat fields, no nested summary envelope.
        assert "summary" not in body, "detail must not wrap fields in summary"
        assert body["status"] == "draft"
        assert body["title"] == "Detalle plano"
        assert body["instrument_key"] == "CAT-DETAIL-01"
        assert body["version_no"] == 1
        assert body["source"] == "runtime"
        assert isinstance(body["scales"], list)


def test_evaluado_can_fetch_published_version_by_key_or_uuid(seeded_db_session) -> None:
    """Evaluado can read published version using seed key e.g. TP-S-01:v1 or UUID."""
    with TestClient(app) as client:
        evaluator = _login(client, "evaluado", settings.dev_password_evaluado)
        
        # Fetch by seed key string "TP-S-01:v1"
        resp_key = client.get(
            "/api/v1/catalog/published-versions/TP-S-01:v1",
            headers=_headers(evaluator),
        )
        assert resp_key.status_code == 200
        data_key = resp_key.json()
        assert data_key["instrument_key"] == "TP-S-01"

        # Fetch by UUID string
        version_id = data_key["instrument_version_id"]
        resp_uuid = client.get(
            f"/api/v1/catalog/published-versions/{version_id}",
            headers=_headers(evaluator),
        )
        assert resp_uuid.status_code == 200
        assert resp_uuid.json()["instrument_version_id"] == version_id

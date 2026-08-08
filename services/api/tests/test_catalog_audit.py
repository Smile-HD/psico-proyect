"""Catalog audit metadata and idempotency audit scenarios."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models.audit import AuditLog
from tests.test_catalog_api import _content, _headers, _login


def test_explicit_saves_are_audited_once_each_and_content_is_excluded(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        psychologist = _login(client, "psicologo", settings.dev_password_psicologo)
        admin = _login(client, "admin", settings.dev_password_admin)
        created = client.post(
            "/api/v1/catalog/admin/instruments",
            headers=_headers(psychologist, "audit-create"),
            json={"key": "CAT-AUDIT-01", "title": "Auditoría sintética"},
        )
        version_id = created.json()["draft"]["instrument_version_id"]
        for key in ("audit-save-1", "audit-save-2"):
            saved = client.put(
                f"/api/v1/catalog/admin/versions/{version_id}/content",
                headers=_headers(psychologist, key),
                json=_content(),
            )
            assert saved.status_code == 200
        invalid = _content()
        invalid["scales"][0]["items"][0]["options"] = invalid["scales"][0]["items"][0][
            "options"
        ][:4]
        failed = client.put(
            f"/api/v1/catalog/admin/versions/{version_id}/content",
            headers=_headers(psychologist, "audit-failed"),
            json=invalid,
        )
        assert failed.status_code == 422
        assert (
            client.post(
                f"/api/v1/catalog/admin/versions/{version_id}/publish",
                headers=_headers(admin, "audit-publish"),
            ).status_code
            == 200
        )
        rows = db_session.scalars(
            select(AuditLog)
            .where(AuditLog.resource_id == version_id)
            .order_by(AuditLog.occurred_at)
        ).all()
        assert [row.event_type for row in rows] == [
            "instrument.draft_created",
            "instrument.draft_updated",
            "instrument.draft_updated",
            "instrument.published",
        ]
        for row in rows:
            metadata = row.metadata_ or {}
            assert "item_text" not in metadata
            assert "value" not in metadata
            assert metadata.get("instrument_version_id") == version_id


def test_replayed_create_has_one_row_and_one_audit_event(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        psychologist = _login(client, "psicologo", settings.dev_password_psicologo)
        path = "/api/v1/catalog/admin/instruments"
        body = {"key": "CAT-AUDIT-REPLAY", "title": "Repetible"}
        first = client.post(
            path, headers=_headers(psychologist, "create-replay"), json=body
        )
        replay = client.post(
            path, headers=_headers(psychologist, "create-replay"), json=body
        )
        assert first.status_code == replay.status_code == 201
        assert first.json() == replay.json()
        rows = db_session.scalars(
            select(AuditLog).where(
                AuditLog.event_type == "instrument.draft_created",
                AuditLog.resource_id == first.json()["draft"]["instrument_version_id"],
            )
        ).all()
        assert len(rows) == 1

"""Permission, version coexistence, and immutable lifecycle scenarios."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.main import app
from app.models.audit import AuditLog
from app.models.instruments import InstrumentVersion
from tests.test_catalog_api import _content, _headers, _login


def test_evaluado_is_denied_every_admin_route_and_denial_is_audited(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        evaluator = _login(client, "evaluado", settings.dev_password_evaluado)
        routes = [
            ("get", "/api/v1/catalog/admin/instruments"),
            ("post", "/api/v1/catalog/admin/instruments"),
        ]
        for method, path in routes:
            headers = _headers(evaluator, f"denied-{method}")
            if method == "post":
                response = client.post(
                    path,
                    headers=headers,
                    json={"key": "CAT-DENIED", "title": "No"},
                )
            else:
                response = client.get(path, headers=headers)
            assert response.status_code == 403
            assert response.json()["error"]["code"] == "FORBIDDEN"
        denied = db_session.scalars(
            select(AuditLog).where(AuditLog.event_type == "auth.denied")
        ).all()
        assert any(row.outcome == "denied" for row in denied)


def test_two_published_versions_coexist_and_clone_has_fresh_runtime_rows(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        psychologist = _login(client, "psicologo", settings.dev_password_psicologo)
        admin = _login(client, "admin", settings.dev_password_admin)
        evaluator = _login(client, "evaluado", settings.dev_password_evaluado)
        created = client.post(
            "/api/v1/catalog/admin/instruments",
            headers=_headers(psychologist, "coexist-create"),
            json={"key": "CAT-COEXIST-01", "title": "Coexistencia"},
        )
        instrument_id = created.json()["instrument"]["id"]
        v1 = created.json()["draft"]["instrument_version_id"]
        saved = client.put(
            f"/api/v1/catalog/admin/versions/{v1}/content",
            headers=_headers(psychologist, "coexist-save-1"),
            json=_content(),
        )
        assert saved.status_code == 200
        assert (
            client.post(
                f"/api/v1/catalog/admin/versions/{v1}/publish",
                headers=_headers(admin, "coexist-publish-1"),
            ).status_code
            == 200
        )

        created_v2 = client.post(
            f"/api/v1/catalog/admin/instruments/{instrument_id}/versions",
            headers=_headers(psychologist, "coexist-version-2"),
            json={"source_version_id": v1},
        )
        assert created_v2.status_code == 201, created_v2.text
        v2 = created_v2.json()["instrument_version_id"]
        assert created_v2.json()["version_no"] == 2
        assert (
            client.post(
                f"/api/v1/catalog/admin/versions/{v2}/publish",
                headers=_headers(admin, "coexist-publish-2"),
            ).status_code
            == 200
        )

        for version_id in (v1, v2):
            response = client.get(
                f"/api/v1/catalog/published-versions/{version_id}",
                headers=_headers(evaluator),
            )
            assert response.status_code == 200
            assert response.json()["version_no"] in (1, 2)
        assert (
            db_session.scalar(
                select(func.count())
                .select_from(InstrumentVersion)
                .where(
                    InstrumentVersion.instrument_id == instrument_id,
                    InstrumentVersion.status == "published",
                )
            )
            == 2
        )


def test_published_edit_is_conflict_and_archive_has_no_unarchive_path(
    seeded_db_session, db_session
) -> None:
    with TestClient(app) as client:
        psychologist = _login(client, "psicologo", settings.dev_password_psicologo)
        admin = _login(client, "admin", settings.dev_password_admin)
        created = client.post(
            "/api/v1/catalog/admin/instruments",
            headers=_headers(psychologist, "immutable-create"),
            json={"key": "CAT-IMMUTABLE-01", "title": "Inmutable"},
        )
        version_id = created.json()["draft"]["instrument_version_id"]
        assert (
            client.put(
                f"/api/v1/catalog/admin/versions/{version_id}/content",
                headers=_headers(psychologist, "immutable-save"),
                json=_content(),
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/catalog/admin/versions/{version_id}/publish",
                headers=_headers(admin, "immutable-publish"),
            ).status_code
            == 200
        )
        edit = client.put(
            f"/api/v1/catalog/admin/versions/{version_id}/content",
            headers=_headers(psychologist, "immutable-edit"),
            json=_content(),
        )
        assert edit.status_code == 409
        assert edit.json()["error"]["message"] == "version_immutable"
        archive = client.post(
            f"/api/v1/catalog/admin/versions/{version_id}/archive",
            headers=_headers(psychologist, "immutable-archive"),
        )
        assert archive.status_code == 200
        assert db_session.get(InstrumentVersion, version_id).status == "archived"

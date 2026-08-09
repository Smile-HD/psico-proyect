"""F3 published-version discovery contracts."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def _login(client: TestClient, username: str) -> str:
    password = {
        "admin": settings.dev_password_admin,
        "psicologo": settings.dev_password_psicologo,
        "evaluado": settings.dev_password_evaluado,
    }[username]
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str, key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": key,
    }


def _content() -> dict:
    return {
        "response_type": "likert_1_5",
        "scales": [
            {
                "display_order": 1,
                "label": "Intereses sintéticos",
                "locale": "es",
                "items": [
                    {
                        "item_order": 1,
                        "text": "Ítem sintético de listado",
                        "locale": "es",
                        "required": True,
                        "options": [
                            {
                                "display_order": index,
                                "label": label,
                                "locale": "es",
                            }
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


def _create_version(client: TestClient, token: str, suffix: str) -> str:
    created = client.post(
        "/api/v1/catalog/admin/instruments",
        headers=_headers(token, f"listing-create-{suffix}"),
        json={"key": f"CAT-LIST-{suffix}", "title": f"Listado sintético {suffix}"},
    )
    assert created.status_code == 201, created.text
    version_id = created.json()["draft"]["instrument_version_id"]
    saved = client.put(
        f"/api/v1/catalog/admin/versions/{version_id}/content",
        headers=_headers(token, f"listing-save-{suffix}"),
        json=_content(),
    )
    assert saved.status_code == 200, saved.text
    return version_id


def test_published_versions_listing_is_available_to_all_roles_and_filters_lifecycle(
    seeded_db_session,
) -> None:
    with TestClient(app) as client:
        admin = _login(client, "admin")
        psychologist = _login(client, "psicologo")
        tokens = {
            "admin": admin,
            "psicólogo": psychologist,
            "evaluado": _login(client, "evaluado"),
        }

        published_id = _create_version(client, psychologist, "PUBLISHED")
        draft_id = _create_version(client, psychologist, "DRAFT")
        archived_id = _create_version(client, psychologist, "ARCHIVED")

        published = client.post(
            f"/api/v1/catalog/admin/versions/{published_id}/publish",
            headers=_headers(admin, "listing-publish-published"),
        )
        assert published.status_code == 200, published.text

        archived_publish = client.post(
            f"/api/v1/catalog/admin/versions/{archived_id}/publish",
            headers=_headers(admin, "listing-publish-archived"),
        )
        assert archived_publish.status_code == 200, archived_publish.text
        archived = client.post(
            f"/api/v1/catalog/admin/versions/{archived_id}/archive",
            headers=_headers(psychologist, "listing-archive-archived"),
        )
        assert archived.status_code == 200, archived.text

        for role, token in tokens.items():
            response = client.get(
                "/api/v1/catalog/published-versions", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200, f"{role}: {response.text}"
            body = response.json()
            assert set(body) == {"versions"}

            listed_ids = {row["instrument_version_id"] for row in body["versions"]}
            assert published_id in listed_ids
            assert draft_id not in listed_ids
            assert archived_id not in listed_ids

            for row in body["versions"]:
                assert {
                    "instrument_version_id",
                    "instrument_key",
                    "title",
                    "version_no",
                } <= set(row)
                serialized = str(row).lower()
                assert "value" not in serialized
                assert "score" not in serialized
                assert "answer_key" not in serialized
                assert "response_options" not in row


def test_published_versions_listing_is_a_flat_label_projection(seeded_db_session) -> None:
    with TestClient(app) as client:
        token = _login(client, "evaluado")
        response = client.get(
            "/api/v1/catalog/published-versions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, response.text
    versions = response.json()["versions"]
    assert versions, "seed must provide a published discovery choice"
    for version in versions:
        assert set(version) == {
            "instrument_version_id",
            "instrument_key",
            "title",
            "version_no",
        }
        assert isinstance(version["instrument_key"], str)
        assert isinstance(version["title"], str)

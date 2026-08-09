"""PostgreSQL-backed HTTP contracts for evaluation sessions."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.config import settings
from app.main import app
from app.models.audit import AuditLog
from app.models.consent import ConsentGrant
from app.models.instruments import (
    Instrument,
    InstrumentItem,
    InstrumentVersion,
    ResponseOption,
    Scale,
)
from app.models.sessions import Response, Session as SessionRow
from app.schemas.sessions import BatchResponseRequest, SessionDetail, StartRequest
from app.seed.loader import seed_id


def test_start_request_defers_missing_ids_to_the_not_found_gate() -> None:
    assert StartRequest().instrument_version_id is None


def test_batch_dto_accepts_option_ids_but_not_numeric_values() -> None:
    item_id, option_id = uuid4(), uuid4()
    request = BatchResponseRequest(
        responses=[{"item_id": item_id, "response_option_id": option_id}]
    )
    assert request.responses[0].response_option_id == option_id
    with pytest.raises(ValidationError):
        BatchResponseRequest(
            responses=[
                {"item_id": item_id, "response_option_id": option_id, "value": 5}
            ]
        )


def test_detail_dto_contains_progress_and_stable_answer_ids_only() -> None:
    item_id, option_id, version_id = uuid4(), uuid4(), uuid4()
    detail = SessionDetail.model_validate(
        {
            "id": uuid4(),
            "status": "in_progress",
            "instrument_version_id": version_id,
            "progress": {"answered": 1, "total": 1},
            "projection": {
                "instrument_version_id": version_id,
                "version_no": 1,
                "response_type": "likert_1_5",
                "scales": [
                    {
                        "id": uuid4(),
                        "display_order": 1,
                        "label": "Intereses",
                        "locale": "es",
                        "items": [
                            {
                                "id": item_id,
                                "item_order": 1,
                                "text": "Ítem sintético",
                                "locale": "es",
                                "required": True,
                                "response_options": [],
                                "response_option_id": option_id,
                            }
                        ],
                    }
                ],
            },
        }
    ).model_dump(mode="json")
    assert detail["progress"] == {"answered": 1, "total": 1}
    assert detail["projection"]["scales"][0]["items"][0]["response_option_id"] == str(
        option_id
    )
    assert "value" not in str(detail).lower()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def restore_dev_consent(request):
    """Keep the shared legacy service test's no-consent precondition intact."""

    yield
    if "seeded_db_session" not in request.fixturenames:
        return
    db_session = request.getfixturevalue("db_session")
    grant = db_session.scalar(
        select(ConsentGrant).where(
            ConsentGrant.user_id == seed_id("user:evaluado"),
            ConsentGrant.consent_version_id == seed_id("consent:v1"),
        )
    )
    if grant is not None and grant.state != "revoked":
        grant.state = "revoked"
        db_session.commit()


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
    result = {"Authorization": f"Bearer {token}"}
    if key is not None:
        result["Idempotency-Key"] = key
    return result


def _grant(client: TestClient, token: str) -> None:
    response = client.post(
        f"/api/v1/consent/{seed_id('consent:v1')}/grant", headers=_headers(token)
    )
    assert response.status_code == 200, response.text


def _start(client: TestClient, token: str, version_id: str, key: str | None = None):
    return client.post(
        "/api/v1/sessions",
        json={"instrument_version_id": version_id},
        headers=_headers(token, key),
    )


def _signature(response) -> tuple[str, str, dict]:
    error = response.json()["error"]
    return error["code"], error["message"], error["details"]


def _runtime_version(db_session, status: str = "published", *, with_item: bool = False):
    instrument = Instrument(key=f"SESSION-{uuid4().hex[:12].upper()}", title="Sintético")
    version = InstrumentVersion(
        instrument=instrument,
        version_no=1,
        status=status,
        is_immutable=status != "draft",
    )
    if with_item:
        scale = Scale(version=version, label="Escala sintética", locale="es", display_order=1)
        item = InstrumentItem(
            version=version,
            scale=scale,
            item_order=1,
            text="Ítem sintético",
            locale="es",
            required=True,
        )
        item.response_options = [
            ResponseOption(
                item=item,
                display_order=index,
                value=index,
                label=f"Opción {index}",
                locale="es",
            )
            for index in range(1, 6)
        ]
    db_session.add(version)
    db_session.commit()
    return str(version.id)


def _seed_items(db_session) -> list[InstrumentItem]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(InstrumentItem)
            .where(InstrumentItem.version_id == seed_id("TP-S-01:v1"))
            .order_by(InstrumentItem.item_order)
        ).all()
    )


def _answers(db_session, limit: int | None = None) -> dict:
    items = _seed_items(db_session)
    return {
        item.id: sorted(item.response_options, key=lambda option: option.display_order)[0].id
        for item in items[:limit]
    }


def _answer_body(db_session, limit: int | None = None) -> dict:
    return {
        "responses": [
            {"item_id": str(item_id), "response_option_id": str(option_id)}
            for item_id, option_id in _answers(db_session, limit).items()
        ]
    }


def test_invalid_ids_are_indistinguishable_and_gate_precedes_consent(
    client, seeded_db_session, db_session
) -> None:
    evaluator = _login(client, "evaluado")
    draft = _runtime_version(db_session, "draft")
    archived = _runtime_version(db_session, "archived")
    published = _runtime_version(db_session)
    invalid = [
        ("absent", {}),
        ("null", {"instrument_version_id": None}),
        ("malformed", {"instrument_version_id": "not-a-uuid"}),
        ("missing", {"instrument_version_id": str(uuid4())}),
        ("draft", {"instrument_version_id": draft}),
        ("archived", {"instrument_version_id": archived}),
    ]
    user_id = seed_id("user:evaluado")
    before = db_session.scalar(
        select(func.count()).select_from(SessionRow).where(SessionRow.user_id == user_id)
    )
    signatures = []
    for label, body in invalid:
        response = client.post(
            "/api/v1/sessions",
            json=body,
            headers=_headers(evaluator, f"invalid-{label}-{uuid4().hex}"),
        )
        assert response.status_code == 404, response.text
        signatures.append(_signature(response))
    assert all(signature == signatures[0] for signature in signatures)
    assert signatures[0] == ("NOT_FOUND", "resource_not_found", {})
    db_session.expire_all()
    assert (
        db_session.scalar(
            select(func.count()).select_from(SessionRow).where(SessionRow.user_id == user_id)
        )
        == before
    )

    _grant(client, evaluator)
    revoked = client.post(
        f"/api/v1/consent/{seed_id('consent:v1')}/revoke", headers=_headers(evaluator)
    )
    assert revoked.status_code == 200
    draft_response = _start(client, evaluator, draft, f"draft-gate-{uuid4().hex}")
    published_response = _start(client, evaluator, published, f"published-gate-{uuid4().hex}")
    assert draft_response.status_code == 404
    assert _signature(published_response)[:2] == ("CONFLICT", "consent_required")


def test_list_is_owned_detail_is_owner_or_admin_and_bad_session_ids_do_not_leak(
    client, seeded_db_session, db_session
) -> None:
    owner, foreign, admin = (_login(client, name) for name in ("evaluado", "evaluado_02", "admin"))
    _grant(client, owner)
    created = _start(client, owner, str(seed_id("TP-S-01:v1")), f"scope-{uuid4().hex}")
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]

    listing = client.get("/api/v1/sessions", headers=_headers(owner))
    assert listing.status_code == 200 and listing.json()["sessions"]
    for row in listing.json()["sessions"]:
        assert db_session.get(SessionRow, row["id"]).user_id == seed_id("user:evaluado")
    foreign_detail = client.get(f"/api/v1/sessions/{session_id}", headers=_headers(foreign))
    admin_detail = client.get(f"/api/v1/sessions/{session_id}", headers=_headers(admin))
    assert foreign_detail.status_code == 403 and "projection" not in foreign_detail.json()
    assert admin_detail.status_code == 200 and admin_detail.json()["id"] == session_id

    bad = "not-a-session-id"
    responses = [
        client.get(f"/api/v1/sessions/{bad}", headers=_headers(owner)),
        client.put(
            f"/api/v1/sessions/{bad}/responses",
            headers=_headers(owner, f"bad-save-{uuid4().hex}"),
            json={"responses": []},
        ),
        client.post(
            f"/api/v1/sessions/{bad}/complete",
            headers=_headers(owner, f"bad-complete-{uuid4().hex}"),
        ),
    ]
    assert all(response.status_code == 404 for response in responses)
    assert all(_signature(response) == ("NOT_FOUND", "resource_not_found", {}) for response in responses)


def test_batch_upserts_maps_options_rejects_foreign_items_and_requires_keys(
    client, seeded_db_session, db_session
) -> None:
    evaluator = _login(client, "evaluado")
    _grant(client, evaluator)
    missing_key = _start(client, evaluator, str(seed_id("TP-S-01:v1")))
    assert _signature(missing_key)[:2] == ("VALIDATION_ERROR", "idempotency_key_required")
    created = _start(client, evaluator, str(seed_id("TP-S-01:v1")), f"batch-{uuid4().hex}")
    session_id = created.json()["id"]
    items = _seed_items(db_session)[:3]
    options = [sorted(item.response_options, key=lambda row: row.display_order) for item in items]
    body = {
        "responses": [
            {"item_id": str(item.id), "response_option_id": str(option[0].id)}
            for item, option in zip(items, options)
        ]
    }
    audit_count = db_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.resource_id == session_id)
    )
    saved = client.put(
        f"/api/v1/sessions/{session_id}/responses",
        headers=_headers(evaluator, f"save-{uuid4().hex}"),
        json=body,
    )
    assert saved.status_code == 200 and saved.json()["saved_count"] == 3
    replacement = {"responses": [{"item_id": str(items[0].id), "response_option_id": str(options[0][-1].id)}]}
    replaced = client.put(
        f"/api/v1/sessions/{session_id}/responses",
        headers=_headers(evaluator, f"replace-{uuid4().hex}"),
        json=replacement,
    )
    assert replaced.status_code == 200
    db_session.expire_all()
    rows = db_session.scalars(select(Response).where(Response.session_id == session_id)).all()
    assert len(rows) == 3 and next(row for row in rows if row.item_id == items[0].id).value == 5
    assert db_session.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.resource_id == session_id)) == audit_count
    assert "value" not in str(saved.json()).lower()

    foreign = client.put(
        f"/api/v1/sessions/{session_id}/responses",
        headers=_headers(evaluator, f"foreign-{uuid4().hex}"),
        json={"responses": body["responses"] + [{"item_id": str(uuid4()), "response_option_id": str(options[0][0].id)}]},
    )
    assert foreign.status_code == 422 and _signature(foreign)[:2] == ("VALIDATION_ERROR", "validation_error")
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(Response).where(Response.session_id == session_id)) == 3


def test_completion_requires_all_items_admin_override_and_aggregate_audit(
    client, seeded_db_session, db_session
) -> None:
    evaluator, admin = _login(client, "evaluado"), _login(client, "admin")
    _grant(client, evaluator)
    created = _start(client, evaluator, str(seed_id("TP-S-01:v1")), f"complete-{uuid4().hex}")
    session_id = created.json()["id"]
    blocked = client.post(
        f"/api/v1/sessions/{session_id}/complete",
        headers=_headers(evaluator, f"blocked-{uuid4().hex}"),
    )
    assert _signature(blocked)[:2] == ("VALIDATION_ERROR", "validation_error")
    db_session.expire_all()
    assert db_session.get(SessionRow, session_id).status == "in_progress"
    saved = client.put(
        f"/api/v1/sessions/{session_id}/responses",
        headers=_headers(evaluator, f"all-answers-{uuid4().hex}"),
        json=_answer_body(db_session),
    )
    assert saved.status_code == 200
    key = f"admin-complete-{uuid4().hex}"
    completed = client.post(f"/api/v1/sessions/{session_id}/complete", headers=_headers(admin, key))
    replay = client.post(f"/api/v1/sessions/{session_id}/complete", headers=_headers(admin, key))
    assert completed.status_code == replay.status_code == 200 and replay.json() == completed.json()
    assert not any(term in str(completed.json()).lower() for term in ("score", "percentile", "eneatype", "reference"))
    db_session.expire_all()
    events = db_session.scalars(select(AuditLog).where(AuditLog.event_type == "session.completed", AuditLog.resource_id == session_id)).all()
    assert len(events) == 1 and events[0].metadata_ == {"response_count": len(_seed_items(db_session))}
    detail = client.get(f"/api/v1/sessions/{session_id}", headers=_headers(admin))
    assert detail.status_code == 200 and "value" not in str(detail.json()).lower()


def test_archived_version_keeps_the_session_projection(client, seeded_db_session, db_session) -> None:
    evaluator, psychologist = _login(client, "evaluado"), _login(client, "psicologo")
    _grant(client, evaluator)
    version_id = _runtime_version(db_session, with_item=True)
    created = _start(client, evaluator, version_id, f"archive-{uuid4().hex}")
    session_id = created.json()["id"]
    db_session.expire_all()
    item = db_session.scalar(select(InstrumentItem).where(InstrumentItem.version_id == version_id))
    option = sorted(item.response_options, key=lambda row: row.display_order)[-1]
    saved = client.put(
        f"/api/v1/sessions/{session_id}/responses",
        headers=_headers(evaluator, f"archive-save-{uuid4().hex}"),
        json={"responses": [{"item_id": str(item.id), "response_option_id": str(option.id)}]},
    )
    assert saved.status_code == 200
    archived = client.post(
        f"/api/v1/catalog/admin/versions/{version_id}/archive",
        headers=_headers(psychologist, f"archive-version-{uuid4().hex}"),
    )
    assert archived.status_code == 200
    detail = client.get(f"/api/v1/sessions/{session_id}", headers=_headers(evaluator))
    body = detail.json()
    assert detail.status_code == 200 and body["instrument_version_id"] == version_id
    assert body["projection"]["scales"][0]["items"][0]["response_option_id"] == str(option.id)
    assert "status" not in body["projection"] and "value" not in str(body).lower()
    assert client.get(f"/api/v1/catalog/published-versions/{version_id}", headers=_headers(evaluator)).status_code == 404


def test_create_and_response_idempotency_replay_or_conflict_without_duplicates(
    client, seeded_db_session, db_session
) -> None:
    evaluator = _login(client, "evaluado")
    _grant(client, evaluator)
    version = str(seed_id("TP-S-01:v1"))
    key = f"create-replay-{uuid4().hex}"
    before = db_session.scalar(select(func.count()).select_from(SessionRow).where(SessionRow.user_id == seed_id("user:evaluado")))
    first = _start(client, evaluator, version, key)
    replay = _start(client, evaluator, version, key)
    conflict = _start(client, evaluator, str(uuid4()), key)
    assert first.status_code == replay.status_code == 201 and first.json() == replay.json()
    assert _signature(conflict)[:2] == ("CONFLICT", "idempotency_key_reused")
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(SessionRow).where(SessionRow.user_id == seed_id("user:evaluado"))) == before + 1

    item = _seed_items(db_session)[0]
    options = sorted(item.response_options, key=lambda row: row.display_order)
    body = {"responses": [{"item_id": str(item.id), "response_option_id": str(options[0].id)}]}
    response_key = f"response-replay-{uuid4().hex}"
    saved = client.put(f"/api/v1/sessions/{first.json()['id']}/responses", headers=_headers(evaluator, response_key), json=body)
    saved_replay = client.put(f"/api/v1/sessions/{first.json()['id']}/responses", headers=_headers(evaluator, response_key), json=body)
    saved_conflict = client.put(
        f"/api/v1/sessions/{first.json()['id']}/responses",
        headers=_headers(evaluator, response_key),
        json={"responses": [{"item_id": str(item.id), "response_option_id": str(options[-1].id)}]},
    )
    assert saved.status_code == saved_replay.status_code == 200 and saved.json() == saved_replay.json()
    assert _signature(saved_conflict)[:2] == ("CONFLICT", "idempotency_key_reused")
    db_session.expire_all()
    rows = db_session.scalars(select(Response).where(Response.session_id == first.json()["id"])).all()
    assert len(rows) == 1 and rows[0].value == 1

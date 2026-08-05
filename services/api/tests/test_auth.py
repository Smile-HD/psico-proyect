"""RED test — auth (F1): 3-role matrix, deny-by-default, safe denials.

Pure tests (no DB): capability matrix, require_roles semantics, envelope
shape, JWT + password hashing.
DB tests (skip when PSICO_DATABASE_URL unreachable): login happy path,
identical 401s, admin allowed / role denied, denials audited.

Scenarios covered (identity-auth + contracts specs):
  - Happy login: JWT carries the role, audit logs auth.login.
  - No default-allow / undeclared role: 403, no partial data.
  - No account disclosure: identical generic 401 text.
  - Denial audited: auth.denied with actor id and outcome denied.
  - Envelope shape + unique request_id.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.core.config import settings
from app.core.errors import ApiError, FORBIDDEN, build_envelope
from app.core.permissions import (
    ADMIN,
    CAPABILITIES,
    EVALUADO,
    PSICOLOGO,
    ROLES,
    require_roles,
)
from app.main import app
from app.models.audit import AuditLog

EXPECTED_MATRIX = {
    "manage_users_roles": {ADMIN},
    "manage_institutions": {ADMIN},
    "publish_instruments": {ADMIN},
    "read_catalog": {ADMIN, PSICOLOGO, EVALUADO},
    "run_sessions": {ADMIN, PSICOLOGO, EVALUADO},
    "sign_consent": {ADMIN, PSICOLOGO, EVALUADO},
    "view_results": {ADMIN, PSICOLOGO, EVALUADO},
    "view_audit": {ADMIN},
    "manage_seed": {ADMIN},
}


class FakeUser:
    def __init__(self, user_id: uuid.UUID, username: str, roles: list[str]):
        self.id = user_id
        self.username = username
        self.roles = roles


class FakeDB:
    def add(self, *_args):
        pass

    def commit(self):
        pass


def _make_user(role: str) -> FakeUser:
    return FakeUser(uuid.uuid4(), "synthetic.user", [role])


# --------------------------------------------------------------------------- #
# Pure: access matrix and require_roles (no database)
# --------------------------------------------------------------------------- #


def test_capability_matrix_matches_contract() -> None:
    assert CAPABILITIES == EXPECTED_MATRIX
    assert set(ROLES) == {ADMIN, PSICOLOGO, EVALUADO}


def test_require_roles_admin_allowed() -> None:
    user = _make_user(ADMIN)
    assert require_roles(ADMIN)(user, FakeDB()) is user


def test_require_roles_role_denied() -> None:
    user = _make_user(EVALUADO)
    with pytest.raises(ApiError) as exc_info:
        require_roles(ADMIN)(user, FakeDB())
    assert exc_info.value.code == FORBIDDEN


def test_require_roles_undeclared_role_denied() -> None:
    """No default-allow: a role not declared for the endpoint is denied 403."""
    user = _make_user(PSICOLOGO)
    with pytest.raises(ApiError) as exc_info:
        require_roles(ADMIN)(user, FakeDB())
    assert exc_info.value.code == FORBIDDEN
    assert exc_info.value.message == "insufficient_role"


def test_require_roles_empty_declaration_denies_everyone() -> None:
    for role in ROLES:
        with pytest.raises(ApiError):
            require_roles()(_make_user(role), FakeDB())


def test_require_roles_multiple_roles_allows_any_member() -> None:
    user = _make_user(PSICOLOGO)
    assert require_roles(ADMIN, PSICOLOGO)(user, FakeDB()) is user


# --------------------------------------------------------------------------- #
# Pure: envelope and credentials
# --------------------------------------------------------------------------- #


class _FakeRequest:
    def __init__(self, rid: str):
        self.state = type("State", (), {"request_id": rid})()


def test_envelope_shape() -> None:
    env = build_envelope(_FakeRequest("rid-1"), FORBIDDEN, "insufficient_role")
    assert set(env.keys()) == {"error"}
    assert set(env["error"].keys()) == {"code", "message", "request_id", "details"}
    assert env["error"]["code"] == FORBIDDEN
    assert env["error"]["request_id"] == "rid-1"


def test_envelope_request_ids_differ() -> None:
    e1 = build_envelope(_FakeRequest("a"), FORBIDDEN, "x")
    e2 = build_envelope(_FakeRequest("b"), FORBIDDEN, "x")
    assert e1["error"]["request_id"] != e2["error"]["request_id"]


def test_password_hash_roundtrip() -> None:
    stored = hash_password("s3cret")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("s3cret", stored)
    assert not verify_password("wrong", stored)


def test_jwt_roundtrip_carries_role() -> None:
    secret = "test-secret-0123456789abcdef-0123456789abcdef"
    token = create_access_token(uuid.uuid4(), "psicologo", [PSICOLOGO], secret)
    payload = decode_access_token(token, secret)
    assert payload["roles"] == [PSICOLOGO]
    assert payload["username"] == "psicologo"


# --------------------------------------------------------------------------- #
# Integration (needs PostgreSQL + seeded dev accounts)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def seeded_db_session(engine, db_session):
    from app.seed.loader import run_seed

    run_seed(db_session)
    return db_session


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


def test_login_happy_psicologo(client, seeded_db_session, db_session) -> None:
    resp = _login(client, "psicologo", settings.dev_password_psicologo)
    assert resp.status_code == 200
    body = resp.json()
    token = body["access_token"]
    assert body["token_type"] == "bearer"
    payload = decode_access_token(token, settings.jwt_secret)
    assert payload["roles"] == [PSICOLOGO]
    # audit auth.login recorded
    rows = db_session.scalars(
        select(AuditLog).where(AuditLog.event_type == "auth.login")
    ).all()
    assert any(r.actor_role == PSICOLOGO for r in rows)


def test_login_identical_401_no_account_disclosure(client, seeded_db_session) -> None:
    unknown = _login(client, "nobody", "whatever")
    wrong_pw = _login(client, "psicologo", "wrong-password")
    assert unknown.status_code == wrong_pw.status_code == 401
    u_env = unknown.json()["error"]
    w_env = wrong_pw.json()["error"]
    # Generic text only; nothing reveals account existence or role.
    assert u_env["code"] == w_env["code"] == "UNAUTHORIZED"
    assert u_env["message"] == w_env["message"]
    assert u_env["details"] == w_env["details"] == {}
    assert "psicologo" not in u_env["message"].lower()
    # request_id is unique per request
    assert u_env["request_id"] != w_env["request_id"]


def test_admin_allowed_audit_endpoint(client, seeded_db_session) -> None:
    token = _login(client, "admin", settings.dev_password_admin).json()["access_token"]
    resp = client.get(
        "/api/v1/audit", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert "events" in resp.json()


def test_evaluado_denied_audit_endpoint(client, seeded_db_session, db_session) -> None:
    token = _login(client, "evaluado", settings.dev_password_evaluado).json()["access_token"]
    resp = client.get(
        "/api/v1/audit", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    body = resp.json()
    assert set(body["error"].keys()) == {"code", "message", "request_id", "details"}
    assert body["error"]["code"] == "FORBIDDEN"
    assert "events" not in body  # no partial data leaked
    # denial audited with outcome denied
    denied = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.event_type == "auth.denied")
        .order_by(AuditLog.occurred_at.desc())
        .limit(3)
    ).all()
    assert any(d.outcome == "denied" for d in denied)


def test_seed_status_public(client, seeded_db_session) -> None:
    resp = client.get("/api/v1/seed/status")
    assert resp.status_code == 200
    counts = resp.json()["seed"]
    assert counts["items"] == 20
    assert counts["reference_sets"] == 1
    assert counts["profiles"] == 30

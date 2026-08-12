"""PostgreSQL-backed HTTP contracts for the F6 reports surface."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.main import app
from app.models.audit import AuditLog
from app.models.recommendation import RecommendationResult, RecommendationRule
from app.models.reporting import Report, ReportArtifact, ReportTemplate
from app.models.scoring import ReferenceSet, ScoreRun
from app.models.sessions import Session as SessionRow
from app.modules.reporting.service import service
from app.seed.loader import seed_id


SOURCE_TIME = datetime(2026, 8, 11, 12, 30, tzinfo=timezone.utc)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _password(username: str) -> str:
    return {
        "admin": settings.dev_password_admin,
        "psicologo": settings.dev_password_psicologo,
        "evaluado": settings.dev_password_evaluado,
    }.get(username, f"psico-seed-{username}")


def _login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": _password(username)},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _signature(response) -> tuple[str, str, dict]:
    error = response.json()["error"]
    return error["code"], error["message"], error["details"]


def _score_snapshot() -> dict:
    return {
        "scales": [
            {
                "label": "Intereses",
                "raw": 14,
                "direct": {"z": 1.0},
                "transformed": {"percentile": 84, "t_score": 60, "eneatype": 6},
            }
        ],
        "overall": {
            "raw": 14,
            "transformed": {"percentile": 84, "t_score": 60, "eneatype": 6},
        },
        "norm_note": "Synthetic research-only norm note.",
    }


def _runtime_sources(db_session, *, status: str = "completed", with_score: bool = True):
    session = SessionRow(
        id=uuid4(),
        user_id=seed_id("user:evaluado"),
        instrument_version_id=seed_id("TP-S-01:v1"),
        status=status,
        completed_at=SOURCE_TIME if status == "completed" else None,
        synthetic=False,
        source="runtime",
    )
    db_session.add(session)
    db_session.flush()

    reference = db_session.scalar(
        select(ReferenceSet).where(ReferenceSet.key == "RS-TP-S-01")
    )
    rule = db_session.scalar(
        select(RecommendationRule)
        .where(RecommendationRule.is_active.is_(True))
        .order_by(RecommendationRule.id)
    )
    assert reference is not None and rule is not None

    score_run = None
    if with_score:
        score_run = ScoreRun(
            id=uuid4(),
            session_id=session.id,
            reference_set_id=reference.id,
            status="completed",
            raw=_score_snapshot(),
            computed_at=SOURCE_TIME,
            synthetic=False,
            source="runtime",
        )
        db_session.add(score_run)

    recommendation = RecommendationResult(
        id=uuid4(),
        session_id=session.id,
        rule_id=rule.id,
        program_id=rule.program_id,
        fit_score=72.5,
        justification="Synthetic recommendation justification.",
        created_at=SOURCE_TIME,
        synthetic=False,
        source="runtime",
    )
    db_session.add(recommendation)
    db_session.commit()
    return session


def _report_count(db_session, session_id: UUID) -> int:
    return int(
        db_session.scalar(
            select(func.count()).select_from(Report).where(Report.session_id == session_id)
        )
        or 0
    )


def _artifact_count(db_session, session_id: UUID) -> int:
    report_ids = select(Report.id).where(Report.session_id == session_id)
    return int(
        db_session.scalar(
            select(func.count())
            .select_from(ReportArtifact)
            .where(ReportArtifact.report_id.in_(report_ids))
        )
        or 0
    )


def _report_events(db_session, session_id: UUID) -> list[AuditLog]:
    rows = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.event_type == "report.generated")
        .order_by(AuditLog.occurred_at, AuditLog.id)
    ).all()
    return [row for row in rows if row.metadata_.get("session_id") == str(session_id)]


def _generate(client: TestClient, token: str, session_id: UUID, key: str, body=None):
    return client.post(
        f"/api/v1/reports/{session_id}/generate",
        json={} if body is None else body,
        headers=_headers(token, key),
    )


def test_report_api_generates_exact_metadata_and_streams_pdf(
    client, seeded_db_session, db_session
) -> None:
    session = _runtime_sources(db_session)
    token = _login(client, "admin")
    before = (_report_count(db_session, session.id), _artifact_count(db_session, session.id))

    generated = _generate(client, token, session.id, f"reports-api-{uuid4().hex}")

    assert generated.status_code == 200, generated.text
    payload = generated.json()
    assert set(payload) == {
        "id",
        "session_id",
        "template_id",
        "template_version_no",
        "status",
        "format",
        "generated_at",
        "checksum",
        "byte_size",
    }
    assert payload["session_id"] == str(session.id)
    assert payload["status"] == "ready"
    assert payload["format"] == "pdf"
    assert payload["byte_size"] > 0
    assert len(payload["checksum"]) == 64
    assert _report_count(db_session, session.id) == before[0] + 1
    assert _artifact_count(db_session, session.id) == before[1] + 1

    metadata = client.get(
        f"/api/v1/reports/{session.id}", headers=_headers(token)
    )
    assert metadata.status_code == 200, metadata.text
    assert metadata.json() == payload

    report = db_session.get(Report, UUID(payload["id"]))
    assert report is not None and report.storage_key is not None
    before_read = (_report_count(db_session, session.id), _artifact_count(db_session, session.id))
    assert client.get(f"/api/v1/reports/{session.id}", headers=_headers(token)).json() == payload
    assert (_report_count(db_session, session.id), _artifact_count(db_session, session.id)) == before_read

    download = client.get(
        f"/api/v1/reports/{report.id}/download", headers=_headers(token)
    )
    assert download.status_code == 200, download.text
    assert download.headers["content-type"] == "application/pdf"
    assert int(download.headers["content-length"]) == payload["byte_size"]
    assert download.headers["x-checksum-sha256"] == payload["checksum"]
    assert hashlib.sha256(download.content).hexdigest() == payload["checksum"]
    assert report.storage_key not in download.text
    assert "file://" not in download.text.lower()


def test_report_api_replay_new_key_and_strict_request_body(
    client, seeded_db_session, db_session
) -> None:
    session = _runtime_sources(db_session)
    token = _login(client, "psicologo")
    key = f"reports-replay-{uuid4().hex}"

    first = _generate(client, token, session.id, key)
    replay = _generate(client, token, session.id, key)
    second = _generate(client, token, session.id, f"reports-new-{uuid4().hex}")

    assert first.status_code == replay.status_code == second.status_code == 200
    assert replay.json() == first.json()
    assert second.json()["id"] != first.json()["id"]
    assert _report_count(db_session, session.id) == 2
    assert _artifact_count(db_session, session.id) == 2
    assert len(_report_events(db_session, session.id)) == 2

    latest = client.get(f"/api/v1/reports/{session.id}", headers=_headers(token))
    assert latest.status_code == 200
    assert latest.json() == second.json()

    before = (_report_count(db_session, session.id), len(_report_events(db_session, session.id)))
    invalid = _generate(
        client,
        token,
        session.id,
        f"reports-invalid-{uuid4().hex}",
        {"template_id": "client-cannot-select-templates"},
    )
    assert invalid.status_code == 422
    assert _signature(invalid)[0:2] == ("VALIDATION_ERROR", "validation_error")
    assert (_report_count(db_session, session.id), len(_report_events(db_session, session.id))) == before


def test_report_api_availability_errors_are_stable_and_side_effect_free(
    client, seeded_db_session, db_session
) -> None:
    token = _login(client, "admin")
    unscored = _runtime_sources(db_session, with_score=False)
    in_progress = _runtime_sources(db_session, status="in_progress", with_score=False)

    missing = _generate(client, token, uuid4(), f"reports-missing-{uuid4().hex}")
    incomplete = _generate(
        client, token, in_progress.id, f"reports-in-progress-{uuid4().hex}"
    )
    unscored_response = _generate(
        client, token, unscored.id, f"reports-unscored-{uuid4().hex}"
    )

    assert _signature(missing) == _signature(unscored_response) == (
        "NOT_FOUND",
        "resource_not_found",
        {},
    )
    assert _signature(incomplete) == ("CONFLICT", "session_not_completed", {})
    assert _report_count(db_session, unscored.id) == 0
    assert _report_count(db_session, in_progress.id) == 0

    no_report = client.get(f"/api/v1/reports/{unscored.id}", headers=_headers(token))
    missing_metadata = client.get(
        f"/api/v1/reports/{uuid4()}", headers=_headers(token)
    )
    assert _signature(no_report) == _signature(missing_metadata) == (
        "NOT_FOUND",
        "resource_not_found",
        {},
    )

    template = db_session.scalar(
        select(ReportTemplate).where(ReportTemplate.key == "informe-basico")
    )
    assert template is not None
    pending = Report(
        id=uuid4(),
        session_id=unscored.id,
        template_id=template.id,
        template_version_no=template.version_no,
        format="pdf",
        status="pending",
        synthetic=False,
        source="runtime",
    )
    db_session.add(pending)
    db_session.commit()
    pending_metadata = client.get(
        f"/api/v1/reports/{unscored.id}", headers=_headers(token)
    )
    assert pending_metadata.status_code == 200
    assert set(pending_metadata.json()) == {
        "id",
        "session_id",
        "template_id",
        "template_version_no",
        "status",
        "format",
        "generated_at",
    }
    missing_download = client.get(
        f"/api/v1/reports/{uuid4()}/download", headers=_headers(token)
    )
    pending_download = client.get(
        f"/api/v1/reports/{pending.id}/download", headers=_headers(token)
    )
    assert _signature(missing_download) == _signature(pending_download) == (
        "NOT_FOUND",
        "resource_not_found",
        {},
    )
    assert _artifact_count(db_session, unscored.id) == 0


def test_report_api_requires_idempotency_key(client, seeded_db_session, db_session) -> None:
    session = _runtime_sources(db_session)
    token = _login(client, "admin")
    response = client.post(
        f"/api/v1/reports/{session.id}/generate",
        json={},
        headers=_headers(token),
    )
    assert response.status_code == 422
    assert _signature(response)[:2] == ("VALIDATION_ERROR", "idempotency_key_required")
    assert _report_count(db_session, session.id) == 0


def test_report_api_streams_in_chunks_without_exposing_storage_key(
    client, seeded_db_session, db_session, monkeypatch
) -> None:
    session = _runtime_sources(db_session)
    token = _login(client, "admin")
    generated = _generate(client, token, session.id, f"reports-chunks-{uuid4().hex}")
    assert generated.status_code == 200, generated.text
    report_id = generated.json()["id"]
    report = db_session.get(Report, UUID(report_id))
    assert report is not None and report.storage_key is not None

    class ChunkedStream:
        def __init__(self, payload: bytes):
            self.payload = payload
            self.offset = 0
            self.read_sizes: list[int] = []
            self.closed = False

        def read(self, size: int = -1) -> bytes:
            self.read_sizes.append(size)
            if self.offset >= len(self.payload):
                return b""
            end = self.offset + min(size, 3) if size >= 0 else len(self.payload)
            chunk = self.payload[self.offset:end]
            self.offset = end
            return chunk

        def close(self) -> None:
            self.closed = True

    # The TestClient uses a separate request DB session, so keep the contract
    # assertion at the HTTP boundary while exercising the stream abstraction.
    original_open = service.storage.open
    stream_holder: dict[str, ChunkedStream] = {}

    def open_chunked(db, storage_key):
        artifact = original_open(db, storage_key)
        payload = artifact.read()
        artifact.close()
        stream = ChunkedStream(payload)
        stream_holder["stream"] = stream
        return type(artifact)(artifact.metadata, stream)

    monkeypatch.setattr(service.storage, "open", open_chunked)
    response = client.get(
        f"/api/v1/reports/{report_id}/download", headers=_headers(token)
    )
    assert response.status_code == 200
    assert hashlib.sha256(response.content).hexdigest() == generated.json()["checksum"]
    assert stream_holder["stream"].read_sizes
    assert all(size == 64 * 1024 for size in stream_holder["stream"].read_sizes)
    assert stream_holder["stream"].closed is True
    assert report.storage_key not in response.text


def test_report_api_denies_evaluado_before_lookup_and_audits_denial(
    client, seeded_db_session, db_session
) -> None:
    session = _runtime_sources(db_session)
    admin = _login(client, "admin")
    generated = _generate(client, admin, session.id, f"reports-auth-{uuid4().hex}")
    assert generated.status_code == 200, generated.text
    report_id = generated.json()["id"]
    evaluator = _login(client, "evaluado")
    before_reports = _report_count(db_session, session.id)
    before_denials = int(
        db_session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.event_type == "auth.denied")
        )
        or 0
    )

    denied_generate = _generate(client, evaluator, session.id, f"reports-denied-{uuid4().hex}")
    denied_read = client.get(
        f"/api/v1/reports/{session.id}", headers=_headers(evaluator)
    )
    denied_download = client.get(
        f"/api/v1/reports/{report_id}/download", headers=_headers(evaluator)
    )

    assert denied_generate.status_code == denied_read.status_code == denied_download.status_code == 403
    assert all(response.json()["error"]["code"] == "FORBIDDEN" for response in (denied_generate, denied_read, denied_download))
    assert all("id" not in response.json() for response in (denied_generate, denied_read, denied_download))
    assert _report_count(db_session, session.id) == before_reports
    assert (
        int(
            db_session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.event_type == "auth.denied")
            )
            or 0
        )
        >= before_denials + 3
    )

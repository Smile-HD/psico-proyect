"""PostgreSQL-backed orchestration contracts for the F6 reporting service."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update

from app.core.errors import ApiError, CONFLICT, FORBIDDEN, INTERNAL_ERROR, NOT_FOUND
from app.models.audit import AuditLog
from app.models.idempotency import IdempotencyRecord
from app.models.recommendation import RecommendationResult, RecommendationRule
from app.models.reporting import Report, ReportArtifact, ReportTemplate
from app.models.scoring import ReferenceSet, ScoreRun
from app.models.sessions import Session as SessionRow
from app.modules.reporting.pdf_renderer import RenderedReport
from app.modules.reporting.service import ReportingService
from app.modules.reporting.storage import PostgresReportStorage
from app.seed.loader import seed_id


REPORT_TEMPLATE_KEY = "informe-basico"
GENERATED_AT = datetime(2026, 8, 11, 12, 30, tzinfo=timezone.utc)


def _professional(role: str = "psicólogo") -> SimpleNamespace:
    username = "admin" if role == "admin" else "psicologo"
    return SimpleNamespace(id=seed_id(f"user:{username}"), roles=[role])


def _evaluado() -> SimpleNamespace:
    return SimpleNamespace(id=seed_id("user:evaluado"), roles=["evaluado"])


def _score_snapshot() -> dict:
    return {
        "scales": [
            {
                "label": "Intereses",
                "raw": 14,
                "direct": {"z": 1.0},
                "transformed": {
                    "percentile": 84,
                    "t_score": 60,
                    "eneatype": 6,
                },
            }
        ],
        "overall": {
            "raw": 14,
            "transformed": {
                "percentile": 84,
                "t_score": 60,
                "eneatype": 6,
            },
        },
        "norm_note": "Synthetic research-only norm note.",
    }


def _ensure_template(db) -> ReportTemplate:
    template = db.scalar(
        select(ReportTemplate)
        .where(ReportTemplate.key == REPORT_TEMPLATE_KEY)
        .order_by(ReportTemplate.version_no.desc(), ReportTemplate.id.desc())
        .limit(1)
    )
    if template is None:
        template = ReportTemplate(
            id=seed_id("report-template:informe-basico"),
            key=REPORT_TEMPLATE_KEY,
            name="Synthetic report template",
            template_body=(
                "{{session_id}} {{scores}} {{overall}} {{recommendations}} "
                "{{norm_note}} {{disclaimer}}"
            ),
            version_no=1,
            status="published",
            synthetic=True,
            source="seed",
        )
        db.add(template)
        db.commit()
    return template


def _sources(
    db,
    *,
    status: str = "completed",
    with_score: bool = True,
    with_recommendation: bool = True,
) -> tuple[SessionRow, ScoreRun | None, RecommendationResult | None]:
    session = SessionRow(
        id=uuid4(),
        user_id=seed_id("user:evaluado"),
        instrument_version_id=seed_id("TP-S-01:v1"),
        status=status,
        completed_at=GENERATED_AT if status == "completed" else None,
        synthetic=False,
        source="runtime",
    )
    db.add(session)
    db.flush()
    score_run = None
    result = None
    reference = db.scalar(select(ReferenceSet).where(ReferenceSet.key == "RS-TP-S-01"))
    assert reference is not None
    rule = db.scalar(
        select(RecommendationRule)
        .where(RecommendationRule.is_active.is_(True))
        .order_by(RecommendationRule.id)
    )
    assert rule is not None
    if with_score:
        score_run = ScoreRun(
            id=uuid4(),
            session_id=session.id,
            reference_set_id=reference.id,
            status="completed",
            raw=_score_snapshot(),
            computed_at=GENERATED_AT,
            synthetic=False,
            source="runtime",
        )
        db.add(score_run)
    if with_recommendation:
        result = RecommendationResult(
            id=uuid4(),
            session_id=session.id,
            rule_id=rule.id,
            program_id=rule.program_id,
            fit_score=72.5,
            justification="Synthetic recommendation justification.",
            created_at=GENERATED_AT,
            synthetic=False,
            source="runtime",
        )
        db.add(result)
    db.commit()
    _ensure_template(db)
    return session, score_run, result


def _count_reports(db, session_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Report)
            .where(Report.session_id == session_id)
        )
        or 0
    )


def _count_artifacts(db, session_id: UUID) -> int:
    report_ids = select(Report.id).where(Report.session_id == session_id)
    return int(
        db.scalar(
            select(func.count())
            .select_from(ReportArtifact)
            .where(ReportArtifact.report_id.in_(report_ids))
        )
        or 0
    )


def _report_events(db, session_id: UUID) -> list[AuditLog]:
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.event_type == "report.generated")
        .order_by(AuditLog.occurred_at, AuditLog.id)
    ).all()
    return [row for row in rows if row.metadata_.get("session_id") == str(session_id)]


def _error_signature(error: ApiError) -> tuple[str, str, dict]:
    return error.code, error.message, error.details


class _ControlledRenderer:
    def __init__(self, db, *, failures: int = 0):
        self.db = db
        self.failures = failures
        self.calls = 0
        self.transaction_states: list[bool] = []

    def render(self, _document):
        self.calls += 1
        self.transaction_states.append(self.db.in_transaction())
        if self.failures:
            self.failures -= 1
            raise RuntimeError("synthetic renderer failure")
        return RenderedReport(
            payload=b"%PDF-synthetic-report%",
            media_type="application/pdf",
            renderer_version="renderer-test",
            metadata={"generated_at": GENERATED_AT.isoformat()},
        )


class _FailingStorage:
    def __init__(self):
        self.put_calls = 0

    def put(self, *_args, **_kwargs):
        self.put_calls += 1
        raise RuntimeError("synthetic storage failure")

    def delete(self, *_args, **_kwargs):
        return False


class _LookupBombRepository:
    def get_session(self, *_args, **_kwargs):
        raise AssertionError("evaluado authorization must precede resource lookup")


def test_generate_stages_outside_io_and_persists_pins_artifact_and_aggregate_audit(
    seeded_db_session,
):
    db = seeded_db_session
    session, score_run, _result = _sources(db)
    renderer = _ControlledRenderer(db)
    service = ReportingService(renderer=renderer, storage=PostgresReportStorage())

    status, payload = service.generate_report(
        db, _professional(), session.id, {}, f"report-success-{uuid4().hex}"
    )

    assert status == 200
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
    assert payload["status"] == "ready"
    assert payload["format"] == "pdf"
    assert payload["session_id"] == str(session.id)
    assert renderer.transaction_states == [False]
    report = db.get(Report, UUID(payload["id"]))
    assert report is not None
    assert report.status == "ready"
    assert report.score_run_id == score_run.id
    assert report.storage_key is not None
    assert report.sha256 == payload["checksum"]
    assert report.byte_size == payload["byte_size"]
    assert _count_artifacts(db, session.id) == 1

    events = _report_events(db, session.id)
    assert len(events) == 1
    assert events[0].metadata_ == {
        "session_id": str(session.id),
        "report_id": str(report.id),
        "template_id": str(report.template_id),
        "template_version_no": report.template_version_no,
        "transition": "processing->ready",
        "sha256": report.sha256,
        "byte_size": report.byte_size,
        "created_at": report.created_at.isoformat(),
        "generated_at": report.generated_at.isoformat(),
    }


def test_renderer_failure_marks_failed_and_same_key_retry_converges(
    seeded_db_session,
):
    db = seeded_db_session
    session, _score_run, _result = _sources(db)
    key = f"report-retry-{uuid4().hex}"
    renderer = _ControlledRenderer(db, failures=1)
    service = ReportingService(renderer=renderer, storage=PostgresReportStorage())

    with pytest.raises(ApiError) as first_error:
        service.generate_report(db, _professional(), session.id, {}, key)
    assert _error_signature(first_error.value) == (
        INTERNAL_ERROR,
        "report_generation_failed",
        {},
    )
    failed = db.scalar(
        select(Report).where(Report.session_id == session.id).order_by(Report.created_at.desc())
    )
    assert failed is not None
    assert failed.status == "failed"
    assert failed.storage_key is None
    assert failed.sha256 is None
    assert failed.byte_size is None
    assert _count_artifacts(db, session.id) == 0
    assert _report_events(db, session.id) == []

    status, replayed = service.generate_report(db, _professional(), session.id, {}, key)

    assert status == 200
    assert replayed["id"] == str(failed.id)
    assert db.get(Report, failed.id).status == "ready"
    assert _count_reports(db, session.id) == 1
    assert _count_artifacts(db, session.id) == 1
    assert len(_report_events(db, session.id)) == 1
    assert renderer.calls == 2


def test_storage_failure_marks_failed_without_artifact(seeded_db_session):
    db = seeded_db_session
    session, _score_run, _result = _sources(db)
    storage = _FailingStorage()
    service = ReportingService(renderer=_ControlledRenderer(db), storage=storage)

    with pytest.raises(ApiError) as error:
        service.generate_report(
            db, _professional(), session.id, {}, f"report-storage-{uuid4().hex}"
        )

    assert _error_signature(error.value) == (
        INTERNAL_ERROR,
        "report_generation_failed",
        {},
    )
    report = db.scalar(select(Report).where(Report.session_id == session.id))
    assert report is not None
    assert report.status == "failed"
    assert _count_artifacts(db, session.id) == 0
    assert _report_events(db, session.id) == []
    assert storage.put_calls == 1


def test_audit_failure_cleans_orphan_and_fails_closed(seeded_db_session, monkeypatch):
    db = seeded_db_session
    session, _score_run, _result = _sources(db)

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("app.modules.reporting.service.audit.record", fail_audit)
    service = ReportingService(renderer=_ControlledRenderer(db), storage=PostgresReportStorage())

    with pytest.raises(ApiError) as error:
        service.generate_report(
            db, _professional(), session.id, {}, f"report-audit-{uuid4().hex}"
        )

    assert _error_signature(error.value) == (
        INTERNAL_ERROR,
        "report_generation_failed",
        {},
    )
    report = db.scalar(select(Report).where(Report.session_id == session.id))
    assert report is not None
    assert report.status == "failed"
    assert report.storage_key is None
    assert _count_artifacts(db, session.id) == 0
    assert _report_events(db, session.id) == []


def test_idempotency_replays_conflicts_and_creates_historical_report(
    seeded_db_session,
):
    db = seeded_db_session
    session, _score_run, _result = _sources(db)
    renderer = _ControlledRenderer(db)
    service = ReportingService(renderer=renderer, storage=PostgresReportStorage())
    key = f"report-idempotency-{uuid4().hex}"
    body = {"mode": "default"}

    first = service.generate_report(db, _professional(), session.id, body, key)
    first_report = db.get(Report, UUID(first[1]["id"]))
    assert first_report is not None
    first_artifact = (first_report.storage_key, first_report.sha256, first_report.byte_size)
    claim = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.actor_user_id == _professional().id,
            IdempotencyRecord.operation == "report.generated",
            IdempotencyRecord.idempotency_key == key,
        )
    )
    assert claim is not None
    assert claim.resource_scope == f"session:{session.id}"
    assert claim.response_body == first[1]

    replay = service.generate_report(db, _professional(), session.id, dict(body), key)
    assert replay == first
    assert _count_reports(db, session.id) == 1
    assert _count_artifacts(db, session.id) == 1
    assert len(_report_events(db, session.id)) == 1

    with pytest.raises(ApiError) as reused:
        service.generate_report(db, _professional(), session.id, {"mode": "other"}, key)
    assert _error_signature(reused.value)[:2] == (CONFLICT, "idempotency_key_reused")
    assert _count_reports(db, session.id) == 1
    assert _count_artifacts(db, session.id) == 1
    assert len(_report_events(db, session.id)) == 1

    second = service.generate_report(
        db,
        _professional(),
        session.id,
        body,
        f"report-new-key-{uuid4().hex}",
    )
    assert second[0] == 200
    assert second[1]["id"] != first[1]["id"]
    assert _count_reports(db, session.id) == 2
    assert _count_artifacts(db, session.id) == 2
    assert len(_report_events(db, session.id)) == 2
    assert (first_report.storage_key, first_report.sha256, first_report.byte_size) == first_artifact


def test_prerequisites_are_indistinguishable_and_engines_are_never_called(
    seeded_db_session,
    monkeypatch,
):
    db = seeded_db_session
    service = ReportingService(renderer=_ControlledRenderer(db), storage=PostgresReportStorage())
    user = _professional()
    unscored, _score_run, _result = _sources(db, with_score=False, with_recommendation=False)
    ungenerated, _score_run, _result = _sources(db, with_score=True, with_recommendation=False)
    in_progress, _score_run, _result = _sources(db, status="in_progress", with_score=False, with_recommendation=False)

    def forbidden_engine(*_args, **_kwargs):
        raise AssertionError("F4/F5 engines must not be invoked by reporting")

    monkeypatch.setattr("app.modules.scoring.service.ScoringService.score_session", forbidden_engine)
    monkeypatch.setattr(
        "app.modules.recommendation.service.RecommendationService.generate_recommendations",
        forbidden_engine,
    )

    cases = [
        uuid4(),
        unscored.id,
        ungenerated.id,
    ]
    errors = []
    for index, session_id in enumerate(cases):
        with pytest.raises(ApiError) as error:
            service.generate_report(
                db, user, session_id, {}, f"report-prerequisite-{index}-{uuid4().hex}"
            )
        errors.append(error.value)

    assert [_error_signature(error) for error in errors] == [
        (NOT_FOUND, "resource_not_found", {}),
        (NOT_FOUND, "resource_not_found", {}),
        (NOT_FOUND, "resource_not_found", {}),
    ]
    for session in (unscored, ungenerated):
        assert _count_reports(db, session.id) == 0
        assert _count_artifacts(db, session.id) == 0
        assert _report_events(db, session.id) == []

    before = _count_reports(db, in_progress.id)
    with pytest.raises(ApiError) as incomplete:
        service.generate_report(
            db, user, in_progress.id, {}, f"report-in-progress-{uuid4().hex}"
        )
    assert _error_signature(incomplete.value) == (
        CONFLICT,
        "session_not_completed",
        {},
    )
    assert _count_reports(db, in_progress.id) == before == 0


def test_evaluado_is_denied_before_lookup_and_denial_is_audited(seeded_db_session):
    db = seeded_db_session
    service = ReportingService(repository=_LookupBombRepository())

    with pytest.raises(ApiError) as error:
        service.generate_report(
            db,
            _evaluado(),
            uuid4(),
            {},
            f"report-denied-{uuid4().hex}",
        )

    assert _error_signature(error.value) == (FORBIDDEN, "insufficient_role", {})
    denial = db.scalar(
        select(AuditLog)
        .where(
            AuditLog.event_type == "auth.denied",
            AuditLog.resource_type == "session",
            AuditLog.action == "report_access",
        )
        .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
    )
    assert denial is not None
    assert denial.outcome == "denied"


def test_latest_metadata_is_deterministic_and_side_effect_free(seeded_db_session):
    db = seeded_db_session
    session, _score_run, _result = _sources(db)
    service = ReportingService(renderer=_ControlledRenderer(db), storage=PostgresReportStorage())
    service.generate_report(db, _professional(), session.id, {}, f"report-latest-1-{uuid4().hex}")
    service.generate_report(db, _professional(), session.id, {}, f"report-latest-2-{uuid4().hex}")
    reports = list(
        db.scalars(
            select(Report).where(Report.session_id == session.id).order_by(Report.id)
        ).all()
    )
    assert len(reports) == 2
    tie = datetime(2026, 8, 11, 14, 0, tzinfo=timezone.utc)
    db.execute(update(Report).where(Report.id.in_([row.id for row in reports])).values(created_at=tie))
    db.commit()
    expected = db.scalar(
        select(Report)
        .where(Report.session_id == session.id)
        .order_by(Report.created_at.desc(), Report.id.desc())
        .limit(1)
    )
    before = (_count_reports(db, session.id), _count_artifacts(db, session.id), len(_report_events(db, session.id)))

    first = service.latest_metadata(db, _professional(), session.id)
    second = service.latest_metadata(db, _professional(), session.id)

    assert expected is not None
    assert first == second
    assert first["id"] == str(expected.id)
    assert first["status"] == "ready"
    assert set(first) == {
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
    assert (_count_reports(db, session.id), _count_artifacts(db, session.id), len(_report_events(db, session.id))) == before


def test_latest_metadata_without_report_matches_missing_session(seeded_db_session):
    db = seeded_db_session
    session, _score_run, _result = _sources(db)
    service = ReportingService()

    with pytest.raises(ApiError) as no_report:
        service.latest_metadata(db, _professional(), session.id)
    with pytest.raises(ApiError) as missing:
        service.latest_metadata(db, _professional(), uuid4())

    assert _error_signature(no_report.value) == _error_signature(missing.value)
    assert _error_signature(no_report.value) == (
        NOT_FOUND,
        "resource_not_found",
        {},
    )
    assert _count_reports(db, session.id) == 0
    assert _count_artifacts(db, session.id) == 0
    assert _report_events(db, session.id) == []

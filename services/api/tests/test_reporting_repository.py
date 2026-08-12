"""PostgreSQL-backed repository contracts for the F6 reporting boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.models.institutions import Program
from app.models.recommendation import RecommendationResult, RecommendationRule
from app.models.reporting import Report, ReportTemplate
from app.models.scoring import ReferenceSet, ScoreRun
from app.models.sessions import Session as SessionRow
from app.modules.reporting.repository import ReportingRepository
from app.seed.loader import seed_id


REPORTING_PROFILE = "evaluado_07"
REPORTING_TEMPLATE_KEY = "runtime-report-template"


@pytest.fixture
def reporting_db(seeded_db_session):
    """Keep runtime reporting fixtures inside the test's caller-owned transaction."""

    seeded_db_session.rollback()
    yield seeded_db_session
    seeded_db_session.rollback()


def _completed_session(db, profile: str = REPORTING_PROFILE) -> SessionRow:
    session = db.get(SessionRow, seed_id(f"session:{profile}"))
    assert session is not None
    assert session.status == "completed"
    return session


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


def _runtime_inputs(db, *, profile: str = REPORTING_PROFILE):
    session = _completed_session(db, profile)
    reference = db.scalar(select(ReferenceSet).where(ReferenceSet.key == "RS-TP-S-01"))
    assert reference is not None
    score_run = ScoreRun(
        session_id=session.id,
        reference_set_id=reference.id,
        status="completed",
        raw=_score_snapshot(),
        computed_at=datetime.now(timezone.utc),
        synthetic=False,
        source="runtime",
    )
    db.add(score_run)

    rule = db.scalar(select(RecommendationRule).order_by(RecommendationRule.id))
    assert rule is not None
    program = db.get(Program, rule.program_id)
    assert program is not None
    generated_at = datetime.now(timezone.utc)
    result = RecommendationResult(
        session_id=session.id,
        rule_id=rule.id,
        program_id=program.id,
        fit_score=Decimal("72.50"),
        justification="Synthetic recommendation justification.",
        created_at=generated_at,
        synthetic=False,
        source="runtime",
    )
    db.add(result)

    template = ReportTemplate(
        id=uuid4(),
        key=f"{REPORTING_TEMPLATE_KEY}-{uuid4().hex}",
        name="Runtime report",
        template_body="Report {{session_id}} {{scores}} {{overall}} {{recommendations}} {{norm_note}} {{disclaimer}}",
        version_no=1,
        status="published",
        synthetic=False,
        source="runtime",
    )
    db.add(template)
    db.flush()
    return session, score_run, result, template, program


def _report_count(db, session_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(Report).where(Report.session_id == session_id)
        )
        or 0
    )


def test_repository_reads_latest_sources_and_template_for_pinning(reporting_db) -> None:
    db = reporting_db
    session, score_run, result, template, program = _runtime_inputs(db)
    repository = ReportingRepository()

    context = repository.get_reporting_context(db, session.id, template_key=template.key)

    assert context.session.id == session.id
    assert context.score_run.id == score_run.id
    assert context.score_run.raw == _score_snapshot()
    assert context.template.id == template.id
    assert context.template.version_no == 1
    assert context.recommendation_snapshot["items"] == [
        {
            "program_id": str(program.id),
            "program_name": program.name,
            "program_code": program.code,
            "fit_score": 72.5,
            "justification": result.justification,
        }
    ]
    assert context.recommendation_snapshot["generated_at"] == result.created_at.isoformat()
    assert context.recommendation_snapshot["disclaimer"]


def test_repository_creates_pending_report_with_pins_and_runtime_flags(reporting_db) -> None:
    db = reporting_db
    session, score_run, _result, template, _program = _runtime_inputs(db)
    repository = ReportingRepository()
    context = repository.get_reporting_context(db, session.id, template_key=template.key)
    before = _report_count(db, session.id)

    report = repository.create_report(db, context=context, created_at=datetime(2026, 8, 11, tzinfo=timezone.utc))

    assert _report_count(db, session.id) == before + 1
    assert report.id.version == 4
    assert report.session_id == session.id
    assert report.score_run_id == score_run.id
    assert report.recommendation_snapshot == context.recommendation_snapshot
    assert report.template_id == template.id
    assert report.template_version_no == template.version_no
    assert report.status == "pending"
    assert report.format == "pdf"
    assert report.synthetic is False
    assert report.source == "runtime"
    assert report.created_at == datetime(2026, 8, 11, tzinfo=timezone.utc)
    assert report.updated_at == report.created_at


def test_repository_transitions_processing_to_ready_and_failed(reporting_db) -> None:
    db = reporting_db
    session, _score_run, _result, template, _program = _runtime_inputs(db)
    repository = ReportingRepository()
    context = repository.get_reporting_context(db, session.id, template_key=template.key)
    ready_report = repository.create_report(db, context=context)
    failed_report = repository.create_report(db, context=context)
    db.flush()

    repository.transition_to_processing(db, ready_report)
    generated_at = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
    repository.transition_to_ready(
        db,
        ready_report,
        storage_key="artifact-key",
        sha256="a" * 64,
        byte_size=128,
        media_type="application/pdf",
        renderer_version="reportlab-test",
        generated_at=generated_at,
        updated_at=generated_at,
    )

    repository.transition_to_processing(db, failed_report)
    failed_at = generated_at + timedelta(minutes=1)
    repository.transition_to_failed(db, failed_report, failed_at=failed_at, updated_at=failed_at)
    db.flush()

    assert ready_report.status == "ready"
    assert ready_report.storage_key == "artifact-key"
    assert ready_report.sha256 == "a" * 64
    assert ready_report.byte_size == 128
    assert ready_report.media_type == "application/pdf"
    assert ready_report.renderer_version == "reportlab-test"
    assert ready_report.generated_at == generated_at
    assert ready_report.failed_at is None
    assert failed_report.status == "failed"
    assert failed_report.storage_key is None
    assert failed_report.sha256 is None
    assert failed_report.byte_size is None
    assert failed_report.media_type is None
    assert failed_report.renderer_version is None
    assert failed_report.generated_at is None
    assert failed_report.failed_at == failed_at


def test_repository_ready_transition_requires_complete_artifact_metadata(reporting_db) -> None:
    db = reporting_db
    session, _score_run, _result, template, _program = _runtime_inputs(db)
    repository = ReportingRepository()
    context = repository.get_reporting_context(db, session.id, template_key=template.key)
    report = repository.create_report(db, context=context)
    repository.transition_to_processing(db, report)

    with pytest.raises(ValueError, match="artifact"):
        repository.transition_to_ready(
            db,
            report,
            storage_key="artifact-key",
            sha256=None,
            byte_size=128,
            media_type="application/pdf",
            renderer_version="reportlab-test",
            generated_at=datetime.now(timezone.utc),
        )


def test_repository_leaves_commit_and_rollback_to_caller(reporting_db) -> None:
    db = reporting_db
    session, _score_run, _result, template, _program = _runtime_inputs(db)
    repository = ReportingRepository()
    context = repository.get_reporting_context(db, session.id, template_key=template.key)
    before = _report_count(db, session.id)

    repository.create_report(db, context=context)
    assert _report_count(db, session.id) == before + 1
    db.rollback()

    assert _report_count(db, session.id) == before


def test_repository_allows_multiple_historical_reports_and_selects_latest(reporting_db) -> None:
    db = reporting_db
    session, _score_run, _result, template, _program = _runtime_inputs(db)
    repository = ReportingRepository()
    context = repository.get_reporting_context(db, session.id, template_key=template.key)
    first_at = datetime(2026, 8, 11, 12, 1, tzinfo=timezone.utc)
    second_at = datetime(2026, 8, 11, 12, 2, tzinfo=timezone.utc)

    first = repository.create_report(db, context=context, created_at=first_at)
    second = repository.create_report(db, context=context, created_at=second_at)
    db.flush()

    assert first.id != second.id
    assert _report_count(db, session.id) == 2
    assert repository.latest_report(db, session.id).id == second.id

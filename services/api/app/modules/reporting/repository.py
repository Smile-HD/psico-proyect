"""PostgreSQL adapters for pinned F4/F5 reporting inputs and report rows."""

from __future__ import annotations

import uuid
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.recommendation import RecommendationResult
from app.models.reporting import Report, ReportTemplate
from app.models.scoring import ScoreRun
from app.models.sessions import Session
from app.modules.recommendation.errors import recommendation_integrity_error, resource_not_found
from app.modules.recommendation.repository import RecommendationRepository
from app.modules.scoring.repository import ScoringRepository


RECOMMENDATION_DISCLAIMER = (
    "Recomendaciones orientativas sobre datos sintéticos (research-only). "
    "No constituyen una norma UAGRM ni asesoramiento profesional."
)


@dataclass(frozen=True)
class ReportingContext:
    """All persisted inputs selected for one report generation attempt."""

    session: Session
    score_run: ScoreRun
    recommendation_snapshot: dict[str, Any]
    template: ReportTemplate


class ReportingRepository:
    """Load and stage report data; the caller owns transaction boundaries."""

    def __init__(
        self,
        scoring_repository: ScoringRepository | None = None,
        recommendation_repository: RecommendationRepository | None = None,
    ) -> None:
        self.scoring_repository = scoring_repository or ScoringRepository()
        self.recommendation_repository = (
            recommendation_repository or RecommendationRepository(self.scoring_repository)
        )

    @staticmethod
    def _uuid(value: Any) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (AttributeError, TypeError, ValueError) as error:
            raise resource_not_found() from error

    def get_session(
        self,
        db: DbSession,
        session_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> Session | None:
        return self.scoring_repository.get_session(db, self._uuid(session_id), lock=lock)

    def get_score_run(self, db: DbSession, session_id: uuid.UUID) -> ScoreRun | None:
        """Return the latest completed F4 run without recalculating scoring."""

        return self.scoring_repository.latest_completed_run(db, self._uuid(session_id))

    @staticmethod
    def get_template(
        db: DbSession,
        key: str,
        *,
        version_no: int | None = None,
    ) -> ReportTemplate | None:
        """Select a published template version deterministically."""

        statement = select(ReportTemplate).where(ReportTemplate.key == key)
        if version_no is not None:
            # A retry may need to resolve the exact version after it was
            # retired; a new generation without an explicit pin uses only the
            # current published version below.
            statement = statement.where(
                ReportTemplate.version_no == version_no,
                ReportTemplate.status.in_(["published", "retired"]),
            )
        else:
            statement = statement.where(ReportTemplate.status == "published")
        statement = statement.order_by(
            ReportTemplate.version_no.desc(), ReportTemplate.id.desc()
        ).limit(1)
        return db.scalar(statement)

    @staticmethod
    def _fit_score(row: RecommendationResult) -> Decimal:
        try:
            value = Decimal(str(row.fit_score))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise recommendation_integrity_error(
                {"reason": "result_fit_score_unavailable", "result_id": str(row.id)}
            ) from error
        if not value.is_finite():
            raise recommendation_integrity_error(
                {"reason": "result_fit_score_unavailable", "result_id": str(row.id)}
            )
        return value

    def get_recommendation_snapshot(
        self,
        db: DbSession,
        session_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Project the latest persisted F5 generation into a JSON-safe snapshot."""

        sid = self._uuid(session_id)
        anchor = self.recommendation_repository.latest_generation_anchor(db, sid)
        if anchor is None:
            return None
        rows = self.recommendation_repository.list_generation_rows(db, sid, anchor.created_at)
        if not rows:
            return None

        programs = {
            str(program.id): program
            for program in self.recommendation_repository.list_programs(db)
        }
        grouped: dict[str, list[RecommendationResult]] = defaultdict(list)
        for row in rows:
            grouped[str(row.program_id)].append(row)

        items: list[dict[str, Any]] = []
        for program_id, program_rows in grouped.items():
            program = programs.get(program_id)
            if program is None:
                raise recommendation_integrity_error(
                    {"reason": "result_program_unavailable", "program_id": program_id}
                )
            ordered_rows = sorted(program_rows, key=lambda row: (str(row.rule_id), str(row.id)))
            fit_score = sum((self._fit_score(row) for row in ordered_rows), Decimal("0.00"))
            items.append(
                {
                    "program_id": program_id,
                    "program_name": program.name,
                    "program_code": program.code,
                    "fit_score": float(fit_score),
                    "justification": "; ".join(
                        row.justification for row in ordered_rows if row.justification is not None
                    ),
                }
            )

        items.sort(
            key=lambda item: (-item["fit_score"], item["program_name"], item["program_id"])
        )
        return {
            "session_id": str(sid),
            "generated_at": anchor.created_at.isoformat(),
            "disclaimer": RECOMMENDATION_DISCLAIMER,
            "items": items,
        }

    def get_reporting_context(
        self,
        db: DbSession,
        session_id: uuid.UUID,
        *,
        template_key: str,
        template_version_no: int | None = None,
    ) -> ReportingContext:
        """Load all source rows before the service starts composition or I/O."""

        sid = self._uuid(session_id)
        session = self.get_session(db, sid)
        if session is None:
            raise resource_not_found()
        score_run = self.get_score_run(db, sid)
        if score_run is None or score_run.raw is None:
            raise resource_not_found()
        recommendation_snapshot = self.get_recommendation_snapshot(db, sid)
        if recommendation_snapshot is None:
            raise resource_not_found()
        template = self.get_template(
            db,
            template_key,
            version_no=template_version_no,
        )
        if template is None:
            raise resource_not_found()
        return ReportingContext(
            session=session,
            score_run=score_run,
            recommendation_snapshot=deepcopy(recommendation_snapshot),
            template=template,
        )

    @staticmethod
    def create_report(
        db: DbSession,
        *,
        context: ReportingContext,
        created_at: datetime | None = None,
    ) -> Report:
        """Stage a pending report with value-pinned F4/F5/template inputs."""

        timestamp = created_at or datetime.now(timezone.utc)
        report = Report(
            session_id=context.session.id,
            score_run_id=context.score_run.id,
            recommendation_snapshot=deepcopy(context.recommendation_snapshot),
            template_id=context.template.id,
            template_version_no=context.template.version_no,
            format="pdf",
            status="pending",
            synthetic=False,
            source="runtime",
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(report)
        db.flush()
        return report

    @staticmethod
    def transition_to_processing(
        db: DbSession,
        report: Report,
        *,
        updated_at: datetime | None = None,
    ) -> Report:
        if report.status not in {"pending", "failed"}:
            raise ValueError(f"report cannot enter processing from {report.status!r}")
        report.status = "processing"
        report.storage_key = None
        report.sha256 = None
        report.byte_size = None
        report.media_type = None
        report.renderer_version = None
        report.generated_at = None
        report.failed_at = None
        report.updated_at = updated_at or datetime.now(timezone.utc)
        db.flush()
        return report

    @staticmethod
    def transition_to_ready(
        db: DbSession,
        report: Report,
        *,
        storage_key: str | None,
        sha256: str | None,
        byte_size: int | None,
        media_type: str | None,
        renderer_version: str | None,
        generated_at: datetime | None,
        updated_at: datetime | None = None,
    ) -> Report:
        if report.status != "processing":
            raise ValueError(f"report cannot become ready from {report.status!r}")
        if any(
            value is None
            for value in (
                storage_key,
                sha256,
                byte_size,
                media_type,
                renderer_version,
                generated_at,
            )
        ):
            raise ValueError("ready report artifact metadata is required")
        if byte_size < 0:
            raise ValueError("ready report artifact byte_size must be non-negative")
        report.status = "ready"
        report.storage_key = storage_key
        report.sha256 = sha256
        report.byte_size = byte_size
        report.media_type = media_type
        report.renderer_version = renderer_version
        report.generated_at = generated_at
        report.failed_at = None
        report.updated_at = updated_at or datetime.now(timezone.utc)
        db.flush()
        return report

    @staticmethod
    def transition_to_failed(
        db: DbSession,
        report: Report,
        *,
        failed_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> Report:
        if report.status not in {"pending", "processing"}:
            raise ValueError(f"report cannot fail from {report.status!r}")
        failure_time = failed_at or datetime.now(timezone.utc)
        report.status = "failed"
        report.storage_key = None
        report.sha256 = None
        report.byte_size = None
        report.media_type = None
        report.renderer_version = None
        report.generated_at = None
        report.failed_at = failure_time
        report.updated_at = updated_at or failure_time
        db.flush()
        return report

    @staticmethod
    def latest_report(db: DbSession, session_id: uuid.UUID) -> Report | None:
        statement = (
            select(Report)
            .where(Report.session_id == session_id)
            .order_by(Report.created_at.desc(), Report.id.desc())
            .limit(1)
        )
        return db.scalar(statement)

    # Compatibility aliases keep repository vocabulary parallel with F4/F5.
    load_session = get_session
    load_score_run = get_score_run
    load_recommendation_snapshot = get_recommendation_snapshot
    load_template = get_template
    load_context = get_reporting_context
    create = create_report
    mark_processing = transition_to_processing
    mark_ready = transition_to_ready
    mark_failed = transition_to_failed
    get_latest_report = latest_report


repository = ReportingRepository()

"""Transactional orchestration for persisted F6 report generations."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core import audit
from app.core.errors import (
    ApiError,
    CONFLICT,
    FORBIDDEN,
    NOT_FOUND,
    VALIDATION_ERROR,
)
from app.core.permissions import has_capability
from app.models.idempotency import IdempotencyRecord
from app.models.reporting import Report, ReportTemplate
from app.models.scoring import ScoreRun
from app.modules.assessment_authoring.idempotency import canonical_request_hash
from app.modules.reporting.domain import ReportDomainError, ReportInput, compose_report
from app.modules.reporting.errors import report_generation_failed, report_integrity_error
from app.modules.reporting.pdf_renderer import ReportLabRenderer, RenderedReport
from app.modules.reporting.repository import ReportingRepository
from app.modules.reporting.storage import (
    ArtifactMetadata,
    ArtifactNotFoundError,
    ArtifactStream,
    PostgresReportStorage,
)


REPORT_TEMPLATE_KEY = "informe-basico"
REPORT_STATUS_PROCESSING = "processing"
REPORT_STATUS_READY = "ready"
REPORT_STATUS_FAILED = "failed"
REPORT_OPERATION = "report.generated"
REPORT_RESOURCE_SCOPE = "session:{session_id}"
REPORT_CLAIM_FIELD = "_report_claim"


@dataclass(frozen=True)
class _GenerationClaim:
    """The committed T1 claim and the immutable inputs used after the commit."""

    report_id: uuid.UUID
    request_body: dict[str, Any]
    idempotency_key: str
    report_input: ReportInput | None
    replay: tuple[int, dict[str, Any]] | None = None


def _resource_not_found() -> ApiError:
    return ApiError(NOT_FOUND, "resource_not_found")


def _session_not_completed() -> ApiError:
    return ApiError(CONFLICT, "session_not_completed")


def _idempotency_key_required() -> ApiError:
    return ApiError(VALIDATION_ERROR, "idempotency_key_required")


class ReportingService:
    """Coordinate report generation without invoking F4 or F5 engines.

    T1 claims and pins a report, commits it as ``processing``, and releases all
    database locks before composition, rendering, and artifact storage. T2 then
    commits the ready report, aggregate audit event, and final idempotency body
    together. A failure uses a compensating transaction to remove the artifact
    and persist ``failed`` so the same key can converge on the same row later.
    """

    OPERATION = REPORT_OPERATION
    TEMPLATE_KEY = REPORT_TEMPLATE_KEY

    def __init__(
        self,
        repository: ReportingRepository | None = None,
        renderer: Any | None = None,
        storage: Any | None = None,
    ) -> None:
        self.repository = repository or ReportingRepository()
        self.renderer = renderer or ReportLabRenderer()
        self.storage = storage or PostgresReportStorage()

    @staticmethod
    def _uuid(value: Any) -> uuid.UUID:
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        except (AttributeError, TypeError, ValueError) as error:
            raise _resource_not_found() from error

    @staticmethod
    def _request_body(body: Any) -> dict[str, Any]:
        if body is None:
            return {}
        if hasattr(body, "model_dump"):
            return body.model_dump(mode="json")
        if isinstance(body, Mapping):
            return dict(body)
        raise ApiError(VALIDATION_ERROR, "validation_error")

    @staticmethod
    def _key(key: str | None) -> str:
        if not isinstance(key, str) or not key.strip():
            raise _idempotency_key_required()
        return key

    @staticmethod
    def _actor_role(user: Any) -> str:
        return ",".join(getattr(user, "roles", []))

    @classmethod
    def _authorize(cls, db: DbSession, user: Any, session_id: Any) -> None:
        """Deny evaluado before any session/report lookup and audit the denial."""

        roles = set(getattr(user, "roles", []))
        if has_capability(roles, "view_reports"):
            return
        audit.record(
            db,
            "auth.denied",
            actor_user_id=getattr(user, "id", None),
            actor_role=cls._actor_role(user),
            resource_type="session",
            resource_id=str(session_id),
            action="report_access",
            outcome="denied",
            commit=True,
        )
        raise ApiError(FORBIDDEN, "insufficient_role")

    @staticmethod
    def _claim_query(
        *,
        actor_user_id: uuid.UUID,
        operation: str,
        resource_scope: str,
        idempotency_key: str,
    ):
        return (
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.actor_user_id == actor_user_id,
                IdempotencyRecord.operation == operation,
                IdempotencyRecord.resource_scope == resource_scope,
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
            .with_for_update()
        )

    @staticmethod
    def _claim_marker(report_id: uuid.UUID, status: str) -> dict[str, str]:
        return {REPORT_CLAIM_FIELD: str(report_id), "status": status}

    @staticmethod
    def _report_input_from_context(context: Any) -> ReportInput:
        return ReportInput(
            session_id=context.session.id,
            score_run_id=context.score_run.id,
            score_snapshot=deepcopy(context.score_run.raw),
            f5_snapshot=deepcopy(context.recommendation_snapshot),
            template_id=context.template.id,
            template_version_no=context.template.version_no,
            template_body=context.template.template_body,
        )

    @staticmethod
    def _report_input_from_row(db: DbSession, report: Report) -> ReportInput:
        if report.score_run_id is None or report.template_id is None:
            raise report_integrity_error()
        score_run = db.get(ScoreRun, report.score_run_id)
        template = db.get(ReportTemplate, report.template_id)
        if (
            score_run is None
            or score_run.status != "completed"
            or score_run.raw is None
            or template is None
            or report.template_version_no is None
            or template.version_no != report.template_version_no
            or report.recommendation_snapshot is None
        ):
            raise report_integrity_error()
        return ReportInput(
            session_id=report.session_id,
            score_run_id=report.score_run_id,
            score_snapshot=deepcopy(score_run.raw),
            f5_snapshot=deepcopy(report.recommendation_snapshot),
            template_id=report.template_id,
            template_version_no=report.template_version_no,
            template_body=template.template_body,
        )

    @staticmethod
    def _metadata_payload(report: Report) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": str(report.id),
            "session_id": str(report.session_id),
            "template_id": str(report.template_id),
            "template_version_no": report.template_version_no,
            "status": report.status,
            "format": report.format,
            "generated_at": report.generated_at.isoformat()
            if report.generated_at is not None
            else None,
        }
        if report.status == REPORT_STATUS_READY:
            payload["checksum"] = report.sha256
            payload["byte_size"] = report.byte_size
        return payload

    @staticmethod
    def _generated_at(rendered: RenderedReport) -> datetime:
        value = getattr(rendered, "metadata", {}).get("generated_at")
        if isinstance(value, datetime):
            timestamp = value
        elif isinstance(value, str) and value.strip():
            try:
                timestamp = datetime.fromisoformat(value)
            except ValueError as error:
                raise ValueError("renderer generated_at metadata is invalid") from error
        else:
            timestamp = datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)

    @staticmethod
    def _rendered_payload(rendered: RenderedReport) -> bytes:
        payload = getattr(rendered, "payload", None)
        if payload is None:
            payload = getattr(rendered, "content", None)
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError("renderer payload must be bytes-like")
        return bytes(payload)

    @staticmethod
    def _artifact_value(artifact: ArtifactMetadata, name: str) -> Any:
        if isinstance(artifact, Mapping):
            return artifact.get(name)
        return getattr(artifact, name, None)

    def _load_existing_claim(
        self,
        db: DbSession,
        *,
        user_id: uuid.UUID,
        resource_scope: str,
        key: str,
        body: dict[str, Any],
    ) -> _GenerationClaim | None:
        row = db.scalar(
            self._claim_query(
                actor_user_id=user_id,
                operation=self.OPERATION,
                resource_scope=resource_scope,
                idempotency_key=key,
            )
        )
        if row is None:
            return None
        if row.request_hash != canonical_request_hash(body):
            raise ApiError(CONFLICT, "idempotency_key_reused")

        stored_body = dict(row.response_body)
        marker = stored_body.get(REPORT_CLAIM_FIELD)
        if marker is None:
            response_status = row.response_status
            db.commit()
            return _GenerationClaim(
                report_id=uuid.UUID(str(stored_body["id"])),
                request_body=body,
                idempotency_key=key,
                report_input=None,
                replay=(response_status, stored_body),
            )

        report_id = self._uuid(marker)
        db.commit()
        report = db.get(Report, report_id)
        if report is None:
            db.rollback()
            raise report_generation_failed()
        if report.status == REPORT_STATUS_READY:
            replay = self._metadata_payload(report)
            claim = db.scalar(
                self._claim_query(
                    actor_user_id=user_id,
                    operation=self.OPERATION,
                    resource_scope=resource_scope,
                    idempotency_key=key,
                )
            )
            if claim is None:
                db.rollback()
                raise report_generation_failed()
            claim.response_status = 200
            claim.response_body = replay
            db.commit()
            return _GenerationClaim(
                report_id=report.id,
                request_body=body,
                idempotency_key=key,
                report_input=None,
                replay=(200, replay),
            )
        try:
            report_input = self._report_input_from_row(db, report)
        finally:
            db.rollback()
        return _GenerationClaim(
            report_id=report_id,
            request_body=body,
            idempotency_key=key,
            report_input=report_input,
        )

    def _claim_new_generation(
        self,
        db: DbSession,
        *,
        user: Any,
        session_id: uuid.UUID,
        key: str,
        body: dict[str, Any],
    ) -> _GenerationClaim:
        resource_scope = REPORT_RESOURCE_SCOPE.format(session_id=session_id)
        try:
            existing = self._load_existing_claim(
                db,
                user_id=user.id,
                resource_scope=resource_scope,
                key=key,
                body=body,
            )
            if existing is not None:
                if existing.replay is None and existing.report_input is not None:
                    report = db.get(Report, existing.report_id)
                    if report is None:
                        db.rollback()
                        raise report_generation_failed()
                    if report.status in {"pending", REPORT_STATUS_FAILED}:
                        self.repository.transition_to_processing(db, report)
                        claim = db.scalar(
                            self._claim_query(
                                actor_user_id=user.id,
                                operation=self.OPERATION,
                                resource_scope=resource_scope,
                                idempotency_key=key,
                            )
                        )
                        if claim is not None:
                            claim.response_status = 202
                            claim.response_body = self._claim_marker(
                                report.id, REPORT_STATUS_PROCESSING
                            )
                        db.commit()
                    else:
                        db.rollback()
                return existing

            session = self.repository.get_session(db, session_id, lock=True)
            if session is None:
                raise _resource_not_found()
            if session.status != "completed":
                raise _session_not_completed()

            context = self.repository.get_reporting_context(
                db,
                session_id,
                template_key=self.TEMPLATE_KEY,
            )
            report = self.repository.create_report(db, context=context)
            self.repository.transition_to_processing(db, report)
            claim = IdempotencyRecord(
                actor_user_id=user.id,
                operation=self.OPERATION,
                resource_scope=resource_scope,
                idempotency_key=key,
                request_hash=canonical_request_hash(body),
                response_status=202,
                response_body=self._claim_marker(report.id, REPORT_STATUS_PROCESSING),
            )
            db.add(claim)
            db.flush()
            report_input = self._report_input_from_context(context)
            report_id = report.id
            db.commit()
            return _GenerationClaim(
                report_id=report_id,
                request_body=body,
                idempotency_key=key,
                report_input=report_input,
            )
        except Exception:
            db.rollback()
            raise

    def _cleanup_artifact(self, db: DbSession, storage_key: str | None) -> None:
        if not storage_key:
            return
        try:
            db.rollback()
            self.storage.delete(db, storage_key)
            db.commit()
        except Exception:
            db.rollback()

    def _mark_failed(self, db: DbSession, report_id: uuid.UUID) -> None:
        try:
            db.rollback()
            report = db.get(Report, report_id)
            if report is not None and report.status in {"pending", REPORT_STATUS_PROCESSING}:
                self.repository.transition_to_failed(db, report)
            db.commit()
        except Exception:
            db.rollback()

    def _fail_generation(
        self,
        db: DbSession,
        report_id: uuid.UUID,
        storage_key: str | None = None,
    ) -> None:
        self._cleanup_artifact(db, storage_key)
        self._mark_failed(db, report_id)

    def _store_artifact(
        self,
        db: DbSession,
        *,
        report_id: uuid.UUID,
        rendered: RenderedReport,
    ) -> ArtifactMetadata:
        payload = self._rendered_payload(rendered)
        artifact = self.storage.put(
            db,
            report_id=report_id,
            payload=payload,
            media_type=rendered.media_type,
        )
        db.commit()
        return artifact

    def _finalize(
        self,
        db: DbSession,
        *,
        user: Any,
        session_id: uuid.UUID,
        claim: _GenerationClaim,
        rendered: RenderedReport,
        artifact: ArtifactMetadata,
    ) -> tuple[int, dict[str, Any]]:
        storage_key = self._artifact_value(artifact, "storage_key")
        try:
            report = db.get(Report, claim.report_id)
            if report is None or report.status != REPORT_STATUS_PROCESSING:
                raise ValueError("report is not processing")
            generated_at = self._generated_at(rendered)
            self.repository.transition_to_ready(
                db,
                report,
                storage_key=storage_key,
                sha256=self._artifact_value(artifact, "sha256"),
                byte_size=self._artifact_value(artifact, "byte_size"),
                media_type=self._artifact_value(artifact, "media_type"),
                renderer_version=rendered.renderer_version,
                generated_at=generated_at,
            )
            payload = self._metadata_payload(report)
            audit.record(
                db,
                "report.generated",
                actor_user_id=user.id,
                actor_role=self._actor_role(user),
                resource_type="report",
                resource_id=str(report.id),
                action="generate",
                metadata={
                    "session_id": str(session_id),
                    "report_id": str(report.id),
                    "template_id": str(report.template_id),
                    "template_version_no": report.template_version_no,
                    "transition": "processing->ready",
                    "sha256": report.sha256,
                    "byte_size": report.byte_size,
                    "created_at": report.created_at.isoformat(),
                    "generated_at": report.generated_at.isoformat(),
                },
                commit=False,
                occurred_at=generated_at,
            )
            resource_scope = REPORT_RESOURCE_SCOPE.format(session_id=session_id)
            idempotency = db.scalar(
                self._claim_query(
                    actor_user_id=user.id,
                    operation=self.OPERATION,
                    resource_scope=resource_scope,
                    idempotency_key=claim.idempotency_key,
                )
            )
            if idempotency is None:
                raise ValueError("report idempotency claim is missing")
            idempotency.response_status = 200
            idempotency.response_body = payload
            db.commit()
            return 200, payload
        except Exception as error:
            db.rollback()
            self._fail_generation(db, claim.report_id, storage_key)
            raise report_generation_failed() from error

    def generate_report(
        self,
        db: DbSession,
        user: Any,
        session_id: Any,
        body: Any = None,
        idempotency_key: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """Generate one report using persisted F4/F5 snapshots only."""

        if idempotency_key is None and isinstance(body, str):
            idempotency_key, body = body, None
        self._authorize(db, user, session_id)
        key = self._key(idempotency_key)
        sid = self._uuid(session_id)
        request_body = self._request_body(body)
        claim = self._claim_new_generation(
            db,
            user=user,
            session_id=sid,
            key=key,
            body=request_body,
        )
        if claim.replay is not None:
            return claim.replay
        if claim.report_input is None:
            raise report_generation_failed()

        try:
            document = compose_report(claim.report_input)
            rendered = self.renderer.render(document)
        except ReportDomainError as error:
            self._fail_generation(db, claim.report_id)
            raise report_integrity_error() from error
        except Exception as error:
            self._fail_generation(db, claim.report_id)
            raise report_generation_failed() from error

        artifact: ArtifactMetadata | None = None
        try:
            artifact = self._store_artifact(
                db,
                report_id=claim.report_id,
                rendered=rendered,
            )
        except Exception as error:
            db.rollback()
            self._fail_generation(db, claim.report_id)
            raise report_generation_failed() from error

        return self._finalize(
            db,
            user=user,
            session_id=sid,
            claim=claim,
            rendered=rendered,
            artifact=artifact,
        )

    def latest_metadata(
        self,
        db: DbSession,
        user: Any,
        session_id: Any,
    ) -> dict[str, Any]:
        """Return latest report metadata without changing persisted state."""

        self._authorize(db, user, session_id)
        sid = self._uuid(session_id)
        session = self.repository.get_session(db, sid)
        if session is None:
            raise _resource_not_found()
        report = self.repository.latest_report(db, sid)
        if report is None:
            raise _resource_not_found()
        return self._metadata_payload(report)

    def download_report(
        self,
        db: DbSession,
        user: Any,
        report_id: Any,
    ) -> ArtifactStream:
        """Re-authorize and return an authenticated stream for a ready report."""

        self._authorize(db, user, report_id)
        report_uuid = self._uuid(report_id)
        report = db.scalar(select(Report).where(Report.id == report_uuid))
        if (
            report is None
            or report.status != REPORT_STATUS_READY
            or report.storage_key is None
            or report.sha256 is None
            or report.byte_size is None
            or report.media_type is None
        ):
            raise _resource_not_found()
        try:
            artifact = self.storage.open(db, report.storage_key)
        except ArtifactNotFoundError as error:
            raise _resource_not_found() from error
        if (
            artifact.metadata.sha256 != report.sha256
            or artifact.metadata.byte_size != report.byte_size
            or artifact.metadata.media_type != report.media_type
        ):
            artifact.close()
            raise report_generation_failed()
        return artifact

    download = download_report

    generate = generate_report
    generate_session = generate_report
    get_report = latest_metadata
    get_latest_report = latest_metadata
    latest_report = latest_metadata
    get_metadata = latest_metadata


service = ReportingService()

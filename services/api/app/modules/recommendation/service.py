"""Transactional orchestration for persisted F5 recommendation generations."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session as DbSession

from app.core import audit
from app.core.errors import ApiError, INTERNAL_ERROR
from app.core.permissions import ADMIN, PSICOLOGO
from app.modules.assessment_authoring.idempotency import (
    lookup_idempotency,
    store_idempotency,
)
from app.modules.recommendation import domain
from app.modules.recommendation.errors import (
    recommendation_integrity_error,
    resource_not_found,
    session_not_completed,
)
from app.modules.recommendation.repository import RecommendationRepository
from app.modules.session_runtime.errors import forbidden, idempotency_key_required


RECOMMENDATION_DISCLAIMER = (
    "Recomendaciones orientativas sobre datos sintéticos (research-only). "
    "No constituyen una norma UAGRM ni asesoramiento profesional."
)


class RecommendationService:
    """Coordinate one eager recommendation generation and its public projection."""

    OPERATION = "recommendation.generated"
    DISCLAIMER = RECOMMENDATION_DISCLAIMER

    def __init__(self, repository: RecommendationRepository | None = None) -> None:
        self.repository = repository or RecommendationRepository()

    @staticmethod
    def _uuid(value: Any) -> uuid.UUID:
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        except (AttributeError, TypeError, ValueError) as error:
            raise resource_not_found() from error

    @staticmethod
    def _request_body(body: Any) -> dict[str, Any]:
        if body is None:
            return {}
        if hasattr(body, "model_dump"):
            return body.model_dump(mode="json")
        if isinstance(body, Mapping):
            return dict(body)
        raise ValueError("recommendation request body must be an object")

    @staticmethod
    def _key(key: str | None) -> str:
        if not isinstance(key, str) or not key.strip():
            raise idempotency_key_required()
        return key

    @staticmethod
    def _actor_role(user: Any) -> str:
        return ",".join(getattr(user, "roles", []))

    @staticmethod
    def _audit_foreign_access(db: DbSession, user: Any, session: Any) -> None:
        audit.record(
            db,
            "auth.denied",
            actor_user_id=getattr(user, "id", None),
            actor_role=RecommendationService._actor_role(user),
            resource_type="session",
            resource_id=str(session.id),
            action="recommendation_access",
            outcome="denied",
            commit=True,
        )

    @classmethod
    def _owner(cls, db: DbSession, user: Any, session: Any) -> None:
        roles = set(getattr(user, "roles", []))
        if session.user_id == user.id or roles.intersection({ADMIN, PSICOLOGO}):
            return
        cls._audit_foreign_access(db, user, session)
        raise forbidden()

    @staticmethod
    def _payload(
        session_id: uuid.UUID,
        generated_at: datetime,
        recommendations: tuple[domain.RecommendationResult, ...],
    ) -> dict[str, Any]:
        return {
            "session_id": str(session_id),
            "generated_at": generated_at.isoformat(),
            "disclaimer": RECOMMENDATION_DISCLAIMER,
            "items": [
                {
                    "program_id": str(recommendation.program_id),
                    "program_name": recommendation.program_name,
                    "program_code": recommendation.program_code,
                    "fit_score": float(recommendation.fit_score),
                    "justification": recommendation.justification,
                }
                for recommendation in recommendations
            ],
        }

    @staticmethod
    def _domain_error(error: domain.RecommendationIntegrityError) -> ApiError:
        details: dict[str, Any] = {"reason": error.message}
        if error.path:
            details["path"] = error.path
        return recommendation_integrity_error(details)

    @staticmethod
    def _row_fit(row: Any) -> Decimal:
        try:
            return Decimal(str(row.fit_score))
        except Exception as error:
            raise recommendation_integrity_error(
                {"reason": "result_fit_score_unavailable", "result_id": str(row.id)}
            ) from error

    def _rows_payload(
        self,
        db: DbSession,
        session_id: uuid.UUID,
        generated_at: datetime,
        rows: tuple[Any, ...],
    ) -> dict[str, Any]:
        programs = {str(program.id): program for program in self.repository.list_programs(db)}
        grouped: dict[str, list[Any]] = defaultdict(list)
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
            items.append(
                {
                    "program_id": program_id,
                    "program_name": program.name,
                    "program_code": program.code,
                    "fit_score": float(
                        sum((self._row_fit(row) for row in ordered_rows), Decimal("0.00"))
                    ),
                    "justification": "; ".join(
                        row.justification for row in ordered_rows if row.justification is not None
                    ),
                }
            )

        items.sort(key=lambda item: (-item["fit_score"], item["program_name"], item["program_id"]))
        return {
            "session_id": str(session_id),
            "generated_at": generated_at.isoformat(),
            "disclaimer": RECOMMENDATION_DISCLAIMER,
            "items": items,
        }

    def generate_recommendations(
        self,
        db: DbSession,
        user: Any,
        session_id: Any,
        body: Any = None,
        idempotency_key: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """Generate, audit, remember, and commit one recommendation generation."""

        if idempotency_key is None and isinstance(body, str):
            idempotency_key, body = body, None
        key = self._key(idempotency_key)
        sid = self._uuid(session_id)
        request_body = self._request_body(body)
        session = self.repository.get_session(db, sid, lock=True)
        if session is None:
            raise resource_not_found()
        self._owner(db, user, session)

        replay = lookup_idempotency(
            db,
            actor_user_id=user.id,
            operation=self.OPERATION,
            resource_scope=f"session:{sid}",
            idempotency_key=key,
            request_body=request_body,
        )
        if replay is not None:
            return replay.status_code, replay.body
        if session.status != "completed":
            raise session_not_completed()

        try:
            context = self.repository.get_recommendation_context(db, sid)
            if context.session.status != "completed":
                raise session_not_completed()
            try:
                recommendations = domain.evaluate_recommendations(
                    context.score_run.raw,
                    context.programs,
                    context.rules,
                )
            except domain.RecommendationIntegrityError as error:
                raise self._domain_error(error) from error

            generated_at = datetime.now(timezone.utc)
            rows = self.repository.persist_generation(
                db,
                sid,
                recommendations,
                created_at=generated_at,
            )
            rule_ids = sorted({str(row.rule_id) for row in rows})
            program_ids = sorted({str(row.program_id) for row in rows})
            payload = self._payload(sid, generated_at, recommendations)
            audit.record(
                db,
                "recommendation.generated",
                actor_user_id=user.id,
                actor_role=self._actor_role(user),
                resource_type="session",
                resource_id=str(sid),
                action="generate",
                metadata={
                    "session_id": str(sid),
                    "program_ids": program_ids,
                    "rule_ids": rule_ids,
                    "program_count": len(program_ids),
                    "rule_count": len(rule_ids),
                    "result_count": len(rows),
                    "generated_at": generated_at.isoformat(),
                },
                commit=False,
                occurred_at=generated_at,
            )
            store_idempotency(
                db,
                actor_user_id=user.id,
                operation=self.OPERATION,
                resource_scope=f"session:{sid}",
                idempotency_key=key,
                request_body=request_body,
                response_status=200,
                response_body=payload,
            )
            db.commit()
            return 200, payload
        except ApiError:
            db.rollback()
            raise
        except Exception as error:
            db.rollback()
            raise ApiError(INTERNAL_ERROR, "internal_error") from error

    def latest_recommendations(
        self,
        db: DbSession,
        user: Any,
        session_id: Any,
    ) -> dict[str, Any]:
        """Return the latest complete generation for an owned session."""

        sid = self._uuid(session_id)
        session = self.repository.get_session(db, sid)
        if session is None:
            raise resource_not_found()
        self._owner(db, user, session)
        anchor = self.repository.latest_generation_anchor(db, sid)
        if anchor is None:
            raise resource_not_found()
        rows = self.repository.list_generation_rows(db, sid, anchor.created_at)
        if not rows:
            raise resource_not_found()
        return self._rows_payload(db, sid, anchor.created_at, rows)

    generate = generate_recommendations
    generate_session = generate_recommendations
    get_recommendations = latest_recommendations
    get_latest_recommendations = latest_recommendations
    latest = latest_recommendations


service = RecommendationService()

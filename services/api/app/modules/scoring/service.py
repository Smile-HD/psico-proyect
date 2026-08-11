"""Transactional orchestration for persisted F4 scoring runs."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session as DbSession

from app.core import audit
from app.core.permissions import ADMIN, PSICOLOGO
from app.modules.assessment_authoring.idempotency import (
    lookup_idempotency,
    store_idempotency,
)
from app.modules.scoring import domain
from app.modules.scoring.errors import (
    reference_unavailable,
    resource_not_found,
    session_not_completed,
)
from app.modules.scoring.repository import (
    REFERENCE_SET_KEY,
    ScoringContext,
    ScoringRepository,
)
from app.modules.session_runtime.errors import (
    forbidden,
    idempotency_key_required,
)


class ScoringService:
    """Coordinate one eager score without exposing the private fixture."""

    OPERATION = "scoring.run"

    def __init__(self, repository: ScoringRepository | None = None) -> None:
        self.repository = repository or ScoringRepository()

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
        raise ValueError("scoring request body must be an object")

    @staticmethod
    def _key(key: str | None) -> str:
        if not isinstance(key, str) or not key.strip():
            raise idempotency_key_required()
        return key

    @staticmethod
    def _actor_role(user: Any) -> str:
        return ",".join(getattr(user, "roles", []))

    @staticmethod
    def _owner(user: Any, session: Any) -> None:
        roles = set(getattr(user, "roles", []))
        if session.user_id != user.id and not roles.intersection({ADMIN, PSICOLOGO}):
            raise forbidden()

    @staticmethod
    def _raw_result(result: domain.ScoreResult) -> dict[str, Any]:
        return {
            "scales": [
                {
                    "label": scale.label,
                    "raw": scale.raw,
                    "direct": {"z": scale.direct.z},
                    "transformed": {
                        "percentile": scale.transformed.percentile,
                        "t_score": scale.transformed.t_score,
                        "eneatype": scale.transformed.eneatype,
                    },
                }
                for scale in result.scales
            ],
            "overall": {
                "raw": result.overall.raw,
                "transformed": {
                    "percentile": result.overall.transformed.percentile,
                    "t_score": result.overall.transformed.t_score,
                    "eneatype": result.overall.transformed.eneatype,
                },
            },
        }

    @staticmethod
    def _run_result(run: Any, reference: Any) -> dict[str, Any]:
        if run.raw is None or run.computed_at is None:
            raise ValueError("completed score run is missing its result")
        return {
            "session_id": str(run.session_id),
            "run": {
                "id": str(run.id),
                "status": run.status,
                "computed_at": run.computed_at.isoformat(),
            },
            "reference_set_id": str(run.reference_set_id),
            "norm_note": reference.norm_note,
            **dict(run.raw),
        }

    def _reference_for_run(self, db: DbSession, session: Any, run: Any) -> Any:
        reference = self.repository.get_reference_set(
            db,
            REFERENCE_SET_KEY,
            instrument_version_id=session.instrument_version_id,
        )
        if reference is None or reference.id != run.reference_set_id:
            raise reference_unavailable({"reference_set": REFERENCE_SET_KEY})
        return reference

    def score_session(
        self,
        db: DbSession,
        user: Any,
        session_id: Any,
        body: Any = None,
        idempotency_key: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """Score a completed session and atomically persist run, audit, and replay."""

        if idempotency_key is None and isinstance(body, str):
            idempotency_key, body = body, None
        key = self._key(idempotency_key)
        sid = self._uuid(session_id)
        request_body = self._request_body(body)
        session = self.repository.get_session(db, sid)
        if session is None:
            raise resource_not_found()
        self._owner(user, session)

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
            context = self.repository.get_scoring_context(db, sid)
            if context.session.status != "completed":
                raise session_not_completed()
            scoring_input = self.repository.build_scoring_input(context)
            run = self.repository.create_score_run(
                db, session_id=sid, reference_set_id=context.reference.id
            )
            result = domain.score(scoring_input)
            computed_at = datetime.now(timezone.utc)
            raw = self._raw_result(result)
            self.repository.complete_score_run(
                db, run, raw=raw, computed_at=computed_at
            )
            payload = self._run_result(run, context.reference)
            audit.record(
                db,
                "scoring.run",
                actor_user_id=user.id,
                actor_role=self._actor_role(user),
                resource_type="session",
                resource_id=str(sid),
                action="score",
                metadata={
                    "session_id": str(sid),
                    "instrument_version_id": str(context.version.id),
                    "reference_set_id": str(context.reference.id),
                    "run_id": str(run.id),
                    "response_count": len(context.response_option_ids),
                    "scale_count": len(result.scales),
                    "computed_at": computed_at.isoformat(),
                },
                commit=False,
                occurred_at=computed_at,
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
        except Exception:
            db.rollback()
            raise

    def latest_result(
        self, db: DbSession, user: Any, session_id: Any
    ) -> dict[str, Any]:
        """Return the deterministic latest completed run for an owned session."""

        sid = self._uuid(session_id)
        session = self.repository.get_session(db, sid)
        if session is None:
            raise resource_not_found()
        self._owner(user, session)
        run = self.repository.latest_completed_run(db, sid)
        if run is None:
            raise resource_not_found()
        reference = self._reference_for_run(db, session, run)
        return self._run_result(run, reference)

    get_result = latest_result
    get_latest_result = latest_result


service = ScoringService()

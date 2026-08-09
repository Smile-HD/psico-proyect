"""Application service for the consent-gated, non-scoring session runtime."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session as DbSession

from app.core import audit
from app.core.consent import require_consent
from app.modules.assessment_authoring.idempotency import lookup_idempotency, store_idempotency
from app.modules.session_runtime import domain
from app.modules.session_runtime.errors import (
    forbidden,
    idempotency_key_required,
    resource_not_found,
    state_conflict,
    validation_error,
)
from app.modules.session_runtime.repository import SessionRepository


class SessionService:
    CREATE, SAVE, COMPLETE = "session.create", "session.save_responses", "session.complete"

    def __init__(self, repository: SessionRepository | None = None) -> None:
        self.repository = repository or SessionRepository()

    @staticmethod
    def _key(key: str | None) -> str:
        if not isinstance(key, str) or not key.strip():
            raise idempotency_key_required()
        return key

    @staticmethod
    def _body(body: Any) -> dict[str, Any]:
        if hasattr(body, "model_dump"):
            return body.model_dump(mode="json")
        return dict(body) if isinstance(body, Mapping) else {"instrument_version_id": str(body)}

    @staticmethod
    def _uuid(value: Any) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except (AttributeError, TypeError, ValueError) as error:
            raise resource_not_found() from error

    @staticmethod
    def _role(user: Any) -> str:
        return ",".join(getattr(user, "roles", []))

    @staticmethod
    def _pairs(body: Any) -> list[tuple[uuid.UUID, uuid.UUID]]:
        raw, pairs = body.get("responses", []) if isinstance(body, Mapping) else body, []
        try:
            for pair in raw:
                if hasattr(pair, "model_dump"):
                    pair = pair.model_dump(mode="python")
                if isinstance(pair, Mapping):
                    item, option = pair["item_id"], pair.get("response_option_id") or pair["option_id"]
                else:
                    item, option = pair
                pairs.append((uuid.UUID(str(item)), uuid.UUID(str(option))))
        except (KeyError, TypeError, ValueError) as error:
            raise validation_error({"reason": "invalid response pair"}) from error
        return pairs

    @staticmethod
    def _owner(user: Any, row: Any, *, admin: bool = False) -> None:
        if row.user_id != user.id and not (admin and "admin" in user.roles):
            raise forbidden()

    def _replay(self, db: DbSession, user: Any, operation: str, scope: str, key: str, body: Any):
        return lookup_idempotency(
            db, actor_user_id=user.id, operation=operation, resource_scope=scope,
            idempotency_key=key, request_body=body,
        )

    @staticmethod
    def _store(db: DbSession, user: Any, operation: str, scope: str, key: str,
               request: Any, status: int, result: dict[str, Any]) -> None:
        store_idempotency(
            db, actor_user_id=user.id, operation=operation, resource_scope=scope,
            idempotency_key=key, request_body=request, response_status=status,
            response_body=result,
        )
        db.commit()

    def create_session(self, db: DbSession, user: Any, body: Any, idempotency_key: str | None):
        key, request = self._key(idempotency_key), self._body(body)
        self.repository.get_actor(db, user.id, lock=True)
        replay = self._replay(db, user, self.CREATE, "actor", key, request)
        if replay:
            return replay.status_code, replay.body
        version_id = self._uuid(request.get("instrument_version_id"))
        version = self.repository.get_version(db, version_id)
        if version is None or version.status != "published":
            raise resource_not_found()
        grant = require_consent(db, user.id)
        row = self.repository.create_session(
            db, user_id=user.id, instrument_version_id=version.id, consent_grant_id=grant.id
        )
        result = {"id": str(row.id), "status": row.status}
        audit.record(
            db, "session.started", actor_user_id=user.id, actor_role=self._role(user),
            resource_type="session", resource_id=str(row.id), action="create", metadata={},
        )
        self._store(db, user, self.CREATE, "actor", key, request, 201, result)
        return 201, result

    def list_sessions(self, db: DbSession, user: Any) -> dict[str, Any]:
        return {"sessions": [
            {"id": str(row.id), "status": row.status,
             "instrument_version_id": str(row.instrument_version_id),
             "started_at": row.started_at.isoformat() if row.started_at else None,
             "completed_at": row.completed_at.isoformat() if row.completed_at else None}
            for row in self.repository.list_for_user(db, user.id)
        ]}

    def get_session(self, db: DbSession, user: Any, session_id: Any) -> dict[str, Any]:
        row = self.repository.get_session(db, self._uuid(session_id))
        if row is None:
            raise resource_not_found()
        self._owner(user, row, admin=True)
        return self.repository.project_session(db, row)

    def save_responses(self, db: DbSession, user: Any, session_id: Any, body: Any,
                       idempotency_key: str | None):
        key, sid = self._key(idempotency_key), self._uuid(session_id)
        row = self.repository.get_session(db, sid, lock=True)
        if row is None:
            raise resource_not_found()
        self._owner(user, row)
        pairs = self._pairs(body)
        request = {"responses": [{"item_id": str(i), "response_option_id": str(o)} for i, o in pairs]}
        replay = self._replay(db, user, self.SAVE, f"session:{sid}", key, request)
        if replay:
            return replay.status_code, replay.body
        if row.status != domain.IN_PROGRESS:
            raise state_conflict()
        try:
            values = domain.validate_batch(
                pairs, self.repository.response_option_map(db, row.instrument_version_id)
            )
        except ValueError as error:
            raise validation_error({"reason": str(error)}) from error
        self.repository.upsert_responses(db, sid, values)
        result = {"id": str(sid), "status": row.status, "saved_count": len(values)}
        self._store(db, user, self.SAVE, f"session:{sid}", key, request, 200, result)
        return 200, result

    def complete_session(self, db: DbSession, user: Any, session_id: Any,
                         idempotency_key: str | None):
        key, sid = self._key(idempotency_key), self._uuid(session_id)
        row = self.repository.get_session(db, sid, lock=True)
        if row is None:
            raise resource_not_found()
        self._owner(user, row, admin=True)
        request: dict[str, Any] = {}
        replay = self._replay(db, user, self.COMPLETE, f"session:{sid}", key, request)
        if replay:
            return replay.status_code, replay.body
        if row.status != domain.IN_PROGRESS:
            raise state_conflict()
        missing = domain.required_missing(
            self.repository.required_item_ids(db, row.instrument_version_id),
            self.repository.answered_item_ids(db, sid),
        )
        if missing:
            raise validation_error({"missing_item_ids": [str(item) for item in missing]})
        row.status, row.completed_at = domain.COMPLETED, datetime.now(timezone.utc)
        count = self.repository.response_count(db, sid)
        audit.record(
            db, "session.completed", actor_user_id=user.id, actor_role=self._role(user),
            resource_type="session", resource_id=str(sid), action="complete",
            metadata={"response_count": count},
        )
        result = {"id": str(sid), "status": row.status}
        self._store(db, user, self.COMPLETE, f"session:{sid}", key, request, 200, result)
        return 200, result


service = SessionService()

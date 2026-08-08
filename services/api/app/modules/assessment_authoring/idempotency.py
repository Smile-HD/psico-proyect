"""Scoped idempotency storage for catalog mutations."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, CONFLICT
from app.models.idempotency import IdempotencyRecord


@dataclass(frozen=True)
class IdempotencyReplay:
    status_code: int
    body: dict[str, Any]


def _json_default(value: Any) -> str:
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "model_dump"):
        return json.dumps(
            value.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def canonical_request_hash(body: Any) -> str:
    """Hash canonical JSON so key ordering cannot change request identity."""

    canonical = json.dumps(
        body,
        default=_json_default,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _record_query(
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


def lookup_idempotency(
    db: Session,
    *,
    actor_user_id: uuid.UUID,
    operation: str,
    resource_scope: str,
    idempotency_key: str,
    request_body: Any,
) -> IdempotencyReplay | None:
    """Return a completed result, or raise on same-key/different-body reuse."""

    if not idempotency_key.strip():
        raise ApiError(CONFLICT, "idempotency_key_required")
    row = db.scalar(
        _record_query(actor_user_id, operation, resource_scope, idempotency_key)
    )
    if row is None:
        return None
    request_hash = canonical_request_hash(request_body)
    if row.request_hash != request_hash:
        raise ApiError(
            CONFLICT,
            "idempotency_key_reused",
            details={"operation": operation, "resource_scope": resource_scope},
        )
    return IdempotencyReplay(
        status_code=row.response_status, body=dict(row.response_body)
    )


def store_idempotency(
    db: Session,
    *,
    actor_user_id: uuid.UUID,
    operation: str,
    resource_scope: str,
    idempotency_key: str,
    request_body: Any,
    response_status: int,
    response_body: dict[str, Any],
) -> IdempotencyRecord:
    """Stage a successful mutation result in the caller's transaction."""

    if not idempotency_key.strip():
        raise ApiError(CONFLICT, "idempotency_key_required")
    row = IdempotencyRecord(
        actor_user_id=actor_user_id,
        operation=operation,
        resource_scope=resource_scope,
        idempotency_key=idempotency_key,
        request_hash=canonical_request_hash(request_body),
        response_status=response_status,
        response_body=response_body,
    )
    db.add(row)
    db.flush()
    return row

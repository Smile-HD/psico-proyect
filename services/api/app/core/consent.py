"""Versioned consent registry + consent-gated sessions (audit-consent spec).

- grant/revoke transition registry state and write audit events.
- require_consent blocks session creation without a granted consent:
  CONFLICT + session.blocked_without_consent audited.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import ApiError, CONFLICT, NOT_FOUND
from app.models.consent import ConsentGrant, ConsentVersion
from app.modules.assessment_authoring.idempotency import (
    IdempotencyReplay,
    lookup_idempotency,
    store_idempotency,
)


def get_active_consent_version(db: Session) -> ConsentVersion | None:
    return db.scalar(
        select(ConsentVersion)
        .where(ConsentVersion.is_active.is_(True))
        .order_by(ConsentVersion.version_no.desc())
    )


def get_granted_grant(db: Session, user_id: uuid.UUID) -> ConsentGrant | None:
    return db.scalar(
        select(ConsentGrant).where(
            ConsentGrant.user_id == user_id,
            ConsentGrant.state == "granted",
        )
    )


def require_consent(db: Session, user_id: uuid.UUID) -> ConsentGrant:
    """Return a granted grant or block with CONFLICT + audit."""
    grant = get_granted_grant(db, user_id)
    if grant is None:
        audit.record(
            db,
            "session.blocked_without_consent",
            actor_user_id=user_id,
            actor_role=None,
            resource_type="session",
            action="create",
            outcome="denied",
            metadata={},
            commit=True,
        )
        raise ApiError(CONFLICT, "consent_required")
    return grant


def grant_consent(
    db: Session,
    user_id: uuid.UUID,
    consent_version_id: uuid.UUID,
    ip: str | None = None,
    *,
    idempotency_key: str | None = None,
    request_body: Any | None = None,
) -> ConsentGrant | IdempotencyReplay:
    body = request_body if request_body is not None else {}
    if idempotency_key is not None:
        replay = lookup_idempotency(
            db,
            actor_user_id=user_id,
            operation="consent.grant",
            resource_scope=f"consent:{consent_version_id}",
            idempotency_key=idempotency_key,
            request_body=body,
        )
        if replay is not None:
            return replay

    version = db.get(ConsentVersion, consent_version_id)
    if version is None:
        raise ApiError(NOT_FOUND, "consent_version_not_found")
    grant = db.scalar(
        select(ConsentGrant).where(
            ConsentGrant.user_id == user_id,
            ConsentGrant.consent_version_id == consent_version_id,
        )
    )
    if grant is None:
        grant = ConsentGrant(
            user_id=user_id,
            consent_version_id=consent_version_id,
            state="granted",
            signed_at=datetime.now(timezone.utc),
            ip=ip,
            synthetic=False,
            source="runtime",
        )
        db.add(grant)
    else:
        grant.state = "granted"
        grant.signed_at = datetime.now(timezone.utc)
    audit.record(
        db,
        "consent.granted",
        actor_user_id=user_id,
        actor_role=None,
        resource_type="consent",
        resource_id=str(consent_version_id),
        action="grant",
        outcome="allowed",
        metadata={"consent_version_no": version.version_no},
        commit=idempotency_key is None,
    )
    if idempotency_key is not None:
        store_idempotency(
            db,
            actor_user_id=user_id,
            operation="consent.grant",
            resource_scope=f"consent:{consent_version_id}",
            idempotency_key=idempotency_key,
            request_body=body,
            response_status=200,
            response_body={
                "state": grant.state,
                "consent_version_id": str(consent_version_id),
            },
        )
        db.commit()
    return grant


def revoke_consent(
    db: Session,
    user_id: uuid.UUID,
    consent_version_id: uuid.UUID,
    *,
    idempotency_key: str | None = None,
    request_body: Any | None = None,
) -> ConsentGrant | IdempotencyReplay:
    body = request_body if request_body is not None else {}
    if idempotency_key is not None:
        replay = lookup_idempotency(
            db,
            actor_user_id=user_id,
            operation="consent.revoke",
            resource_scope=f"consent:{consent_version_id}",
            idempotency_key=idempotency_key,
            request_body=body,
        )
        if replay is not None:
            return replay

    grant = db.scalar(
        select(ConsentGrant).where(
            ConsentGrant.user_id == user_id,
            ConsentGrant.consent_version_id == consent_version_id,
        )
    )
    if grant is None:
        raise ApiError(NOT_FOUND, "consent_grant_not_found")
    grant.state = "revoked"
    audit.record(
        db,
        "consent.revoked",
        actor_user_id=user_id,
        actor_role=None,
        resource_type="consent",
        resource_id=str(consent_version_id),
        action="revoke",
        outcome="allowed",
        metadata={},
        commit=idempotency_key is None,
    )
    if idempotency_key is not None:
        store_idempotency(
            db,
            actor_user_id=user_id,
            operation="consent.revoke",
            resource_scope=f"consent:{consent_version_id}",
            idempotency_key=idempotency_key,
            request_body=body,
            response_status=200,
            response_body={
                "state": grant.state,
                "consent_version_id": str(consent_version_id),
            },
        )
        db.commit()
    return grant

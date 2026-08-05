"""Versioned consent registry + consent-gated sessions (audit-consent spec).

- grant/revoke transition registry state and write audit events.
- require_consent blocks session creation without a granted consent:
  CONFLICT + session.blocked_without_consent audited.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import ApiError, CONFLICT, NOT_FOUND
from app.models.consent import ConsentGrant, ConsentVersion


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
) -> ConsentGrant:
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
        commit=True,
    )
    return grant


def revoke_consent(
    db: Session,
    user_id: uuid.UUID,
    consent_version_id: uuid.UUID,
) -> ConsentGrant:
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
        commit=True,
    )
    return grant

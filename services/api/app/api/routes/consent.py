"""Consent endpoints: list versions, grant, revoke."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.consent import grant_consent, revoke_consent
from app.core.errors import ApiError, NOT_FOUND
from app.core.permissions import ADMIN, EVALUADO, PSICOLOGO, require_roles
from app.db.session import get_db
from app.models.consent import ConsentVersion
from app.modules.assessment_authoring.errors import idempotency_key_required
from app.modules.assessment_authoring.idempotency import IdempotencyReplay

router = APIRouter(prefix="/consent", tags=["consent"])


def _key_or_error(value: str | None) -> str:
    if value is None or not value.strip():
        raise idempotency_key_required()
    return value


@router.get("/versions")
def list_versions(
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> dict:
    versions = db.scalars(
        select(ConsentVersion).order_by(ConsentVersion.version_no.desc())
    ).all()
    return {
        "versions": [
            {
                "id": str(v.id),
                "version_no": v.version_no,
                "title": v.title,
                "is_active": v.is_active,
            }
            for v in versions
        ]
    }


@router.post("/{version_id}/grant")
def grant(
    version_id: str,
    body: dict[str, Any] | None = Body(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> dict:
    try:
        vid = uuid.UUID(version_id)
    except ValueError:
        raise ApiError(NOT_FOUND, "consent_version_not_found")
    result = grant_consent(
        db,
        user.id,
        vid,
        ip="127.0.0.1",
        idempotency_key=_key_or_error(idempotency_key),
        request_body=body or {},
    )
    if isinstance(result, IdempotencyReplay):
        return result.body
    return {"state": result.state, "consent_version_id": str(vid)}


@router.post("/{version_id}/revoke")
def revoke(
    version_id: str,
    body: dict[str, Any] | None = Body(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> dict:
    try:
        vid = uuid.UUID(version_id)
    except ValueError:
        raise ApiError(NOT_FOUND, "consent_grant_not_found")
    result = revoke_consent(
        db,
        user.id,
        vid,
        idempotency_key=_key_or_error(idempotency_key),
        request_body=body or {},
    )
    if isinstance(result, IdempotencyReplay):
        return result.body
    return {"state": result.state, "consent_version_id": str(vid)}

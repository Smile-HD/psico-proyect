"""Consent endpoints: list versions, grant, revoke."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.consent import grant_consent, revoke_consent
from app.core.errors import ApiError, NOT_FOUND
from app.core.permissions import ADMIN, EVALUADO, PSICOLOGO, require_roles
from app.db.session import get_db
from app.models.consent import ConsentVersion

router = APIRouter(prefix="/consent", tags=["consent"])


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
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> dict:
    try:
        vid = uuid.UUID(version_id)
    except ValueError:
        raise ApiError(NOT_FOUND, "consent_version_not_found")
    grant = grant_consent(db, user.id, vid, ip="127.0.0.1")
    return {"state": grant.state, "consent_version_id": version_id}


@router.post("/{version_id}/revoke")
def revoke(
    version_id: str,
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> dict:
    try:
        vid = uuid.UUID(version_id)
    except ValueError:
        raise ApiError(NOT_FOUND, "consent_grant_not_found")
    grant = revoke_consent(db, user.id, vid)
    return {"state": grant.state, "consent_version_id": version_id}

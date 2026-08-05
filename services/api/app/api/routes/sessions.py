"""Session endpoints — consent-gated (audit-consent spec).

POST /sessions requires a granted consent for the caller; without it the
request fails CONFLICT and session.blocked_without_consent is audited.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.consent import require_consent
from app.core.errors import ApiError, FORBIDDEN, NOT_FOUND
from app.core.permissions import ADMIN, EVALUADO, PSICOLOGO, require_roles
from app.db.session import get_db
from app.models.instruments import InstrumentVersion
from app.models.sessions import Response, Session
from app.schemas.auth import SessionStartRequest

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", status_code=201)
def create_session(
    body: SessionStartRequest,
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> dict:
    try:
        version_id = uuid.UUID(body.instrument_version_id)
    except ValueError:
        raise ApiError(NOT_FOUND, "instrument_version_not_found")
    version = db.get(InstrumentVersion, version_id)
    if version is None:
        raise ApiError(NOT_FOUND, "instrument_version_not_found")

    grant = require_consent(db, user.id)  # raises CONFLICT + audit when absent

    session = Session(
        user_id=user.id,
        instrument_version_id=version.id,
        consent_grant_id=grant.id,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
        synthetic=False,
        source="runtime",
    )
    db.add(session)
    db.flush()
    audit.record(
        db,
        "session.started",
        actor_user_id=user.id,
        actor_role=",".join(user.roles),
        resource_type="session",
        resource_id=str(session.id),
        action="create",
        outcome="allowed",
        metadata={},
        commit=True,
    )
    return {"id": str(session.id), "status": session.status}


@router.post("/{session_id}/complete")
def complete_session(
    session_id: str,
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> dict:
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise ApiError(NOT_FOUND, "session_not_found")
    session = db.get(Session, sid)
    if session is None:
        raise ApiError(NOT_FOUND, "session_not_found")
    # Own-session rule: evaluados/psicólogos only their own sessions.
    if session.user_id != user.id and ADMIN not in user.roles:
        raise ApiError(FORBIDDEN, "insufficient_role")

    response_count = db.scalar(
        select(func.count()).select_from(Response).where(Response.session_id == session.id)
    ) or 0
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    audit.record(
        db,
        "session.completed",
        actor_user_id=user.id,
        actor_role=",".join(user.roles),
        resource_type="session",
        resource_id=str(session.id),
        action="complete",
        outcome="allowed",
        # Deny-list: counts only, never response values or item content.
        metadata={"response_count": response_count},
        commit=True,
    )
    return {"id": str(session.id), "status": session.status}

"""Session delivery endpoints — F3 (Sesión de Evaluación).

Lifecycle:
    POST   /sessions              create + start (consent-gated)
    GET    /sessions/{id}/resume  progress + server-calculated remaining time
    POST   /sessions/{id}/responses  idempotent autosave (Idempotency-Key)
    POST   /sessions/{id}/submit  freeze responses → completed

Ownership rule: evaluados/psicólogos may only touch their own sessions;
admins may access any session.

Idempotency-Key header for POST /responses:
    First request: saves the response and returns ``created=true``.
    Replay (same key):  returns the existing record and ``created=false``.
    Key is stored per (session_id, item_id) — see ``Response.idempotency_key``
    (added as a nullable column if supported) or implemented via the
    database UniqueConstraint on (session_id, item_id) with a lookup before
    insert.  The current Response model already enforces uniqueness per
    (session, item), so the idempotency logic is: try to load the existing
    row first; if found return it.  The ``Idempotency-Key`` header is
    validated to be present (not empty) but not persisted — the duplicate
    prevention is enforced by the DB unique constraint.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app.api.routes.catalog import resolve_published_version_id
from app.core import audit
from app.core.consent import require_consent
from app.core.errors import (
    CONFLICT,
    FORBIDDEN,
    NOT_FOUND,
    VALIDATION_ERROR,
    ApiError,
)
from app.core.permissions import ADMIN, EVALUADO, PSICOLOGO, require_roles
from app.db.session import get_db
from app.models.instruments import InstrumentItem, InstrumentVersion
from app.models.sessions import Response, Session
from app.schemas.sessions import (
    ResponseCreate,
    ResponseSaveResponse,
    SavedResponseRead,
    SessionCreate,
    SessionCreateResponse,
    SessionResumeResponse,
    SessionSubmitResponse,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_session_or_404(db: DBSession, session_id: str) -> Session:
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise ApiError(NOT_FOUND, "session_not_found")
    session = db.get(Session, sid)
    if session is None:
        raise ApiError(NOT_FOUND, "session_not_found")
    return session


def _assert_owner(session: Session, user) -> None:
    """Evaluados and psicólogos may only access their own sessions."""
    if session.user_id != user.id and ADMIN not in user.roles:
        raise ApiError(FORBIDDEN, "insufficient_role")


def _assert_in_progress(session: Session) -> None:
    """Reject mutations on already-completed or cancelled sessions."""
    if session.status != "in_progress":
        raise ApiError(
            CONFLICT,
            "session_not_in_progress",
            details={"status": session.status},
        )


def _remaining_seconds(session: Session, version: InstrumentVersion) -> float | None:
    """Server-side remaining time.

    The InstrumentVersion model currently has no ``duration_minutes``
    column (F4 domain).  Until that column is added, every session is
    treated as unbounded (returns None).  When the column exists, change
    this function accordingly — the timer is always computed from
    ``started_at`` stored in the DB, never from a client value.
    """
    duration_minutes: int | None = getattr(version, "duration_minutes", None)
    if duration_minutes is None:
        return None
    elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds()
    remaining = duration_minutes * 60.0 - elapsed
    return max(remaining, 0.0)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201, response_model=SessionCreateResponse)
def create_session(
    body: SessionCreate,
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: DBSession = Depends(get_db),
) -> dict:
    """Create and immediately start an evaluation session.

    Locks the provided ``instrument_version_id``.  The version MUST be
    published (status='published').  Requires a granted consent.
    """
    try:
        vid = resolve_published_version_id(db, str(body.instrument_version_id))
    except ApiError:
        raise ApiError(NOT_FOUND, "instrument_version_not_found")

    version = db.get(InstrumentVersion, vid)
    if version is None:
        raise ApiError(NOT_FOUND, "instrument_version_not_found")
    if version.status != "published":
        raise ApiError(
            VALIDATION_ERROR,
            "instrument_version_not_published",
            details={"status": version.status},
        )

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
    return {
        "id": session.id,
        "status": session.status,
        "instrument_version_id": session.instrument_version_id,
        "started_at": session.started_at,
    }


@router.get("/{session_id}/resume", response_model=SessionResumeResponse)
def resume_session(
    session_id: str,
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: DBSession = Depends(get_db),
) -> dict:
    """Return saved responses and server-calculated remaining time.

    Safe to call at any point (not just in_progress): allows the client to
    display a read-only summary of completed sessions too.
    """
    session = _get_session_or_404(db, session_id)
    _assert_owner(session, user)

    version = db.get(InstrumentVersion, session.instrument_version_id)

    saved = db.scalars(
        select(Response).where(Response.session_id == session.id)
    ).all()

    audit.record(
        db,
        "session.resumed",
        actor_user_id=user.id,
        actor_role=",".join(user.roles),
        resource_type="session",
        resource_id=str(session.id),
        action="resume",
        outcome="allowed",
        metadata={"saved_count": len(saved)},
        commit=True,
    )
    return {
        "id": session.id,
        "status": session.status,
        "instrument_version_id": session.instrument_version_id,
        "started_at": session.started_at,
        "remaining_seconds": _remaining_seconds(session, version),
        "saved_responses": [{"item_id": r.item_id, "value": r.value} for r in saved],
    }


@router.post("/{session_id}/responses", status_code=201, response_model=ResponseSaveResponse)
def save_response(
    session_id: str,
    body: ResponseCreate,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: DBSession = Depends(get_db),
) -> dict:
    """Idempotent item-level autosave.

    The ``Idempotency-Key`` header MUST be provided.  Duplicate requests
    with the same (session_id, item_id) are safe: the existing response is
    returned with ``created=false`` — no second row is inserted.

    The ``item_id`` must belong to the locked instrument version of this
    session.  A Likert value outside [1, 5] is rejected at the Pydantic
    layer before reaching the DB.

    Timer enforcement: if the server calculates remaining_seconds == 0 the
    request is rejected with CONFLICT (session_expired).
    """
    if not idempotency_key:
        raise ApiError(
            VALIDATION_ERROR,
            "idempotency_key_required",
            details={"header": "Idempotency-Key"},
        )

    session = _get_session_or_404(db, session_id)
    _assert_owner(session, user)
    _assert_in_progress(session)

    # Timer check (no-op when duration_minutes is not set on the model)
    version = db.get(InstrumentVersion, session.instrument_version_id)
    remaining = _remaining_seconds(session, version)
    if remaining is not None and remaining <= 0:
        # Auto-submit expired session before rejecting
        _do_submit(db, session, user, auto=True)
        raise ApiError(CONFLICT, "session_expired")

    # Verify the item belongs to the session's locked instrument version
    item = db.get(InstrumentItem, body.item_id)
    if item is None or item.version_id != session.instrument_version_id:
        raise ApiError(NOT_FOUND, "item_not_found")

    # Idempotency: check for existing response first
    existing = db.scalar(
        select(Response).where(
            Response.session_id == session.id,
            Response.item_id == body.item_id,
        )
    )
    if existing is not None:
        return {
            "response_id": existing.id,
            "item_id": existing.item_id,
            "value": existing.value,
            "created": False,
        }

    # First save
    try:
        response = Response(
            session_id=session.id,
            item_id=body.item_id,
            value=body.value,
            synthetic=False,
            source="runtime",
        )
        db.add(response)
        db.flush()
    except IntegrityError:
        db.rollback()
        # Race condition: another concurrent request won; reload and return
        existing = db.scalar(
            select(Response).where(
                Response.session_id == session.id,
                Response.item_id == body.item_id,
            )
        )
        if existing is None:
            raise ApiError(CONFLICT, "response_conflict")
        return {
            "response_id": existing.id,
            "item_id": existing.item_id,
            "value": existing.value,
            "created": False,
        }

    audit.record(
        db,
        "session.response_saved",
        actor_user_id=user.id,
        actor_role=",".join(user.roles),
        resource_type="session",
        resource_id=str(session.id),
        action="save_response",
        outcome="allowed",
        # Audit-safe: counts + IDs only, never item text or response values
        metadata={"item_count": 1},
        commit=True,
    )
    return {
        "response_id": response.id,
        "item_id": response.item_id,
        "value": response.value,
        "created": True,
    }


@router.post("/{session_id}/submit", response_model=SessionSubmitResponse)
def submit_session(
    session_id: str,
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: DBSession = Depends(get_db),
) -> dict:
    """Freeze session responses and transition to completed.

    Idempotent on the status transition: submitting an already-completed
    session returns CONFLICT so callers know they already submitted.
    """
    session = _get_session_or_404(db, session_id)
    _assert_owner(session, user)
    _assert_in_progress(session)

    return _do_submit(db, session, user, auto=False)


# ---------------------------------------------------------------------------
# Internal submit logic (shared by manual submit + timer-expired auto-submit)
# ---------------------------------------------------------------------------


def _do_submit(db: DBSession, session: Session, user, *, auto: bool) -> dict:
    """Transition session to completed and write audit. Returns the response dict."""
    response_count = db.scalar(
        select(func.count()).select_from(Response).where(Response.session_id == session.id)
    ) or 0

    now = datetime.now(timezone.utc)
    session.status = "completed"
    session.completed_at = now

    audit.record(
        db,
        "session.completed",
        actor_user_id=user.id,
        actor_role=",".join(user.roles),
        resource_type="session",
        resource_id=str(session.id),
        action="submit" if not auto else "auto_submit_expired",
        outcome="allowed",
        # Deny-list: counts only, never response values or item content
        metadata={"response_count": response_count},
        commit=True,
    )
    return {
        "id": session.id,
        "status": session.status,
        "completed_at": now,
        "response_count": response_count,
    }

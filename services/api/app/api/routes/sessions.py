"""Thin HTTP adapters for the consent-gated session runtime."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.permissions import ADMIN, EVALUADO, PSICOLOGO, require_roles
from app.db.session import get_db
from app.modules.session_runtime.service import service
from app.schemas.sessions import (
    BatchResponseRequest,
    SessionCreatedResponse,
    SessionDetail,
    SessionListResponse,
    SessionSaveResponse,
    StartRequest,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _json_result(
    model: type[BaseModel], status_code: int, payload: dict
) -> JSONResponse:
    """Validate service/replay payloads before returning the public DTO."""

    body = model.model_validate(payload).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=body)


@router.post("", status_code=201)
def create_session(
    body: StartRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> JSONResponse:
    status_code, payload = service.create_session(db, user, body, idempotency_key)
    return _json_result(SessionCreatedResponse, status_code, payload)


@router.get("")
def list_sessions(
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> SessionListResponse:
    return SessionListResponse.model_validate(service.list_sessions(db, user))


@router.get("/{session_id}")
def get_session(
    session_id: str,
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> SessionDetail:
    return SessionDetail.model_validate(service.get_session(db, user, session_id))


@router.put("/{session_id}/responses")
def save_responses(
    session_id: str,
    body: BatchResponseRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> JSONResponse:
    status_code, payload = service.save_responses(
        db,
        user,
        session_id,
        body.model_dump(mode="python"),
        idempotency_key,
    )
    return _json_result(SessionSaveResponse, status_code, payload)


@router.post("/{session_id}/complete")
def complete_session(
    session_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> JSONResponse:
    status_code, payload = service.complete_session(
        db, user, session_id, idempotency_key
    )
    # The ADMIN role remains an operational owner override inside the service.
    return _json_result(SessionCreatedResponse, status_code, payload)

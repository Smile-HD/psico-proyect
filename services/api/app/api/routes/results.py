"""Thin HTTP adapters for persisted scoring results."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.permissions import ADMIN, EVALUADO, PSICOLOGO, require_roles
from app.db.session import get_db
from app.schemas.results import ResultsResponse
from app.modules.scoring.service import service


router = APIRouter(prefix="/results", tags=["results"])


def _json_result(
    model: type[BaseModel], status_code: int, payload: dict[str, Any]
) -> JSONResponse:
    """Validate service and idempotency replay payloads before returning them."""

    body = model.model_validate(payload).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=body)


@router.post("/{session_id}/score")
def score_results(
    session_id: str,
    body: dict[str, Any] | None = Body(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> JSONResponse:
    status_code, payload = service.score_session(
        db, user, session_id, body, idempotency_key
    )
    return _json_result(ResultsResponse, status_code, payload)


@router.get("/{session_id}")
def get_results(
    session_id: str,
    user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
) -> ResultsResponse:
    return ResultsResponse.model_validate(service.latest_result(db, user, session_id))

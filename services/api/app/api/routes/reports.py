"""Thin HTTP adapters for authorized F6 report generation and delivery."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.permissions import ADMIN, PSICOLOGO, require_roles
from app.db.session import get_db
from app.modules.reporting.service import service
from app.schemas.reports import ReportGenerateRequest, ReportMetadata


router = APIRouter(prefix="/reports", tags=["reports"])


def _json_result(
    model: type[BaseModel], status_code: int, payload: dict[str, Any]
) -> JSONResponse:
    """Validate service/replay payloads before returning the public DTO."""

    body = model.model_validate(payload).model_dump(mode="json")
    for field in ("checksum", "byte_size"):
        if body.get(field) is None:
            body.pop(field, None)
    return JSONResponse(status_code=status_code, content=body)


@router.post("/{session_id}/generate")
def generate_report(
    session_id: str,
    body: ReportGenerateRequest | None = Body(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO)),
    db: Session = Depends(get_db),
) -> JSONResponse:
    status_code, payload = service.generate_report(
        db, user, session_id, body, idempotency_key
    )
    return _json_result(ReportMetadata, status_code, payload)


@router.get("/{session_id}")
def get_report_metadata(
    session_id: str,
    user=Depends(require_roles(ADMIN, PSICOLOGO)),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return _json_result(ReportMetadata, 200, service.latest_metadata(db, user, session_id))


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    user=Depends(require_roles(ADMIN, PSICOLOGO)),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    artifact = service.download_report(db, user, report_id)

    def chunks():
        try:
            while True:
                chunk = artifact.read(64 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            artifact.close()

    return StreamingResponse(
        chunks(),
        media_type=artifact.metadata.media_type,
        headers={
            "Content-Length": str(artifact.metadata.byte_size),
            "X-Checksum-SHA256": artifact.metadata.sha256,
        },
    )

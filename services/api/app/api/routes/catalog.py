"""Catalog administration and published-read HTTP adapters."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, NOT_FOUND
from app.core.permissions import ADMIN, EVALUADO, PSICOLOGO, require_roles
from app.db.session import get_db
from app.models.instruments import Instrument, InstrumentVersion
from app.modules.assessment_authoring.errors import idempotency_key_required
from app.modules.assessment_authoring.service import service
from app.schemas.catalog import (
    CreateDraftVersionRequest,
    CreateInstrumentRequest,
    SaveDraftContentRequest,
)
from app.seed.loader import seed_id

router = APIRouter(prefix="/catalog", tags=["catalog"])


def resolve_published_version_id(db: Session, raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError):
        pass

    try:
        sid = seed_id(raw)
        ver = db.get(InstrumentVersion, sid)
        if ver is not None and ver.status == "published":
            return sid
    except Exception:
        pass

    key = raw.split(":")[0]
    stmt = (
        select(InstrumentVersion.id)
        .join(Instrument, InstrumentVersion.instrument_id == Instrument.id)
        .where(Instrument.key == key)
        .where(InstrumentVersion.status == "published")
        .order_by(InstrumentVersion.version_no.desc())
    )
    res = db.scalar(stmt)
    if res is not None:
        return res

    raise ApiError(NOT_FOUND, "resource_not_found")


def _uuid_or_not_found(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError):
        raise ApiError(NOT_FOUND, "resource_not_found")


def _key_or_error(value: str | None) -> str:
    if value is None or not value.strip():
        raise idempotency_key_required()
    return value


@router.get("/published-versions/{version_id}")
def published_version_read(
    version_id: str,
    _user=Depends(require_roles(ADMIN, PSICOLOGO, EVALUADO)),
    db: Session = Depends(get_db),
):
    vid = resolve_published_version_id(db, version_id)
    return service.published_read(db, vid)


@router.get("/admin/instruments")
def admin_list_instruments(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    key: str | None = None,
    status: str | None = None,
    _user=Depends(require_roles(ADMIN, PSICOLOGO)),
    db: Session = Depends(get_db),
):
    return service.admin_list(db, page, page_size, key, status)


@router.get("/admin/instruments/{instrument_id}")
def admin_instrument_detail(
    instrument_id: str,
    _user=Depends(require_roles(ADMIN, PSICOLOGO)),
    db: Session = Depends(get_db),
):
    return service.admin_instrument(db, _uuid_or_not_found(instrument_id))


@router.post("/admin/instruments", status_code=201)
def create_instrument(
    body: CreateInstrumentRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO)),
    db: Session = Depends(get_db),
):
    status_code, payload = service.create_instrument(
        db, user, body, _key_or_error(idempotency_key)
    )
    return JSONResponse(status_code=status_code, content=payload)


@router.post("/admin/instruments/{instrument_id}/versions", status_code=201)
def create_draft_version(
    instrument_id: str,
    body: CreateDraftVersionRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO)),
    db: Session = Depends(get_db),
):
    status_code, payload = service.create_version(
        db,
        user,
        _uuid_or_not_found(instrument_id),
        body,
        _key_or_error(idempotency_key),
    )
    return JSONResponse(status_code=status_code, content=payload)


@router.get("/admin/versions/{version_id}")
def admin_version_detail(
    version_id: str,
    _user=Depends(require_roles(ADMIN, PSICOLOGO)),
    db: Session = Depends(get_db),
):
    return service.admin_version(db, _uuid_or_not_found(version_id))


@router.put("/admin/versions/{version_id}/content")
def save_draft_content(
    version_id: str,
    body: SaveDraftContentRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO)),
    db: Session = Depends(get_db),
):
    status_code, payload = service.save_content(
        db,
        user,
        _uuid_or_not_found(version_id),
        body,
        _key_or_error(idempotency_key),
    )
    return JSONResponse(status_code=status_code, content=payload)


@router.post("/admin/versions/{version_id}/publish")
def publish_version(
    version_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN)),
    db: Session = Depends(get_db),
):
    status_code, payload = service.publish(
        db, user, _uuid_or_not_found(version_id), _key_or_error(idempotency_key)
    )
    return JSONResponse(status_code=status_code, content=payload)


@router.post("/admin/versions/{version_id}/archive")
def archive_version(
    version_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user=Depends(require_roles(ADMIN, PSICOLOGO)),
    db: Session = Depends(get_db),
):
    status_code, payload = service.archive(
        db, user, _uuid_or_not_found(version_id), _key_or_error(idempotency_key)
    )
    return JSONResponse(status_code=status_code, content=payload)

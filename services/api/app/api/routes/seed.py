"""Seed endpoints.

- GET  /api/v1/seed/status — public, live counts from the database.
- POST /api/v1/seed/run    — admin only (seed engine, idempotent).
- POST /api/v1/seed/reset  — admin only (wipe seed-owned rows, re-seed).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import ADMIN, require_roles
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.consent import ConsentGrant
from app.models.instruments import InstrumentItem
from app.models.scoring import ReferenceSet
from app.models.sessions import Response, Session
from app.models.seed import SeedManifest
from app.models.identity import User

router = APIRouter(prefix="/seed", tags=["seed"])


@router.get("/status")
def seed_status(db: Session = Depends(get_db)) -> dict:
    """Live counts — never hardcoded, always reflects the database."""
    profiles = db.scalar(
        select(func.count()).select_from(User).where(User.username.like(r"evaluado\_%"))
    )
    return {
        "seed": {
            "items": db.scalar(select(func.count()).select_from(InstrumentItem)) or 0,
            "reference_sets": db.scalar(select(func.count()).select_from(ReferenceSet)) or 0,
            "profiles": profiles or 0,
            "sessions": db.scalar(select(func.count()).select_from(Session)) or 0,
            "responses": db.scalar(select(func.count()).select_from(Response)) or 0,
            "consent_grants": db.scalar(select(func.count()).select_from(ConsentGrant)) or 0,
        },
        "manifest": _latest_manifest(db),
    }


@router.post("/run", dependencies=[Depends(require_roles(ADMIN))])
def seed_run(db: Session = Depends(get_db)) -> dict:
    from app.seed.loader import run_seed  # lazy: seed engine lives in F1 unit 4

    manifest = run_seed(db)
    return {"status": "seeded", "manifest": manifest}


@router.post("/reset", dependencies=[Depends(require_roles(ADMIN))])
def seed_reset(db: Session = Depends(get_db)) -> dict:
    from app.seed.loader import reset_seed  # lazy: seed engine lives in F1 unit 4

    manifest = reset_seed(db)
    return {"status": "reset_and_seeded", "manifest": manifest}


def _latest_manifest(db: Session) -> dict | None:
    row = db.scalar(select(SeedManifest).order_by(SeedManifest.executed_at.desc()))
    if row is None:
        return None
    return {
        "seed_version": row.seed_version,
        "checksum": row.checksum,
        "executed_at": row.executed_at.isoformat() if row.executed_at else None,
    }

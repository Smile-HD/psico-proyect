"""GET /api/v1/audit — admin-only view of the append-only audit log."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import ADMIN, require_roles
from app.db.session import get_db
from app.models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    _=Depends(require_roles(ADMIN)),
) -> dict:
    rows = db.scalars(
        select(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(limit)
    ).all()
    return {
        "count": len(rows),
        "events": [
            {
                "event_type": row.event_type,
                "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
                "actor_role": row.actor_role,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "action": row.action,
                "outcome": row.outcome,
                "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
                "metadata": row.metadata_ or {},
            }
            for row in rows
        ],
    }

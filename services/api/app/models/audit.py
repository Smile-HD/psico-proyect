"""Audit family: audit_log (append-only, enforced by DB trigger + role grants)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, func
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_event_occurred", "event_type", "occurred_at"),
        CheckConstraint("outcome IN ('allowed','denied')", name="ck_audit_outcome"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    # null actor_user_id = system (seed, migration, background)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(64))
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[str | None] = mapped_column(String(64))
    outcome: Mapped[str | None] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # `metadata` is a reserved-ish name on Base; map to "metadata" column.
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

"""Sessions family: sessions, responses.

Sessions are consent-gated: consent_grant_id references a granted consent
(enforced in app code via require_consent + audit). Responses carry a 1-5
Likert CHECK constraint and are unique per (session, item).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import SyntheticMixin


class Session(Base, SyntheticMixin):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_started", "user_id", "started_at"),
        CheckConstraint(
            "status IN ('in_progress','completed','blocked','cancelled')",
            name="ck_session_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    instrument_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instrument_versions.id"), index=True, nullable=False
    )
    consent_grant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("consent_grants.id"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="in_progress"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Response(Base, SyntheticMixin):
    __tablename__ = "responses"
    __table_args__ = (
        UniqueConstraint("session_id", "item_id", name="uq_response_per_session_item"),
        CheckConstraint("value BETWEEN 1 AND 5", name="ck_value_1_to_5"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id"), index=True, nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instrument_items.id"), index=True, nullable=False
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)

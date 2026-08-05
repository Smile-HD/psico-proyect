"""Consent family: consent_versions, consent_grants.

Versioned registry; grants transition pending -> granted -> revoked/expired.
Sessions MUST reference a grant in state 'granted'.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import SyntheticMixin


class ConsentVersion(Base, SyntheticMixin):
    __tablename__ = "consent_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version_no: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)  # markdown
    effective_from: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False
    )


class ConsentGrant(Base, SyntheticMixin):
    __tablename__ = "consent_grants"
    __table_args__ = (
        UniqueConstraint("user_id", "consent_version_id", name="uq_grant_per_user_version"),
        CheckConstraint(
            "state IN ('pending','granted','revoked','expired')",
            name="ck_consent_state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    consent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consent_versions.id"), index=True, nullable=False
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(64))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

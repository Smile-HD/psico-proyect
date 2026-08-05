"""Instruments family: instruments, instrument_versions, instrument_items.

Published versions are immutable (schema-enforced): a row with status
'published' MUST have is_immutable = true.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import SyntheticMixin


class Instrument(Base, SyntheticMixin):
    __tablename__ = "instruments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InstrumentVersion(Base, SyntheticMixin):
    __tablename__ = "instrument_versions"
    __table_args__ = (
        UniqueConstraint("instrument_id", "version_no", name="uq_version_no_per_instrument"),
        CheckConstraint(
            "(status <> 'published') OR is_immutable",
            name="ck_published_versions_immutable",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id"), index=True, nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_immutable: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )


class InstrumentItem(Base, SyntheticMixin):
    __tablename__ = "instrument_items"
    __table_args__ = (
        UniqueConstraint("version_id", "scale", "scale_order", name="uq_item_per_scale"),
        CheckConstraint("scale_order BETWEEN 1 AND 5", name="ck_scale_order_1_to_5"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instrument_versions.id"), index=True, nullable=False
    )
    scale: Mapped[str] = mapped_column(String(64), nullable=False)
    scale_order: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

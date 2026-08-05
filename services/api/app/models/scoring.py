"""Scoring family: reference_sets, reference_values, score_runs.

The seeded reference set is synthetic / research-only and carries an explicit
norm_note. Raw -> transformed mappings (percentile/T/eneatype) live in
reference_values for F4 to consume.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import SyntheticMixin


class ReferenceSet(Base, SyntheticMixin):
    __tablename__ = "reference_sets"
    __table_args__ = (
        CheckConstraint(
            "reference_status IN ('synthetic','real')", name="ck_reference_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    instrument_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("instrument_versions.id"), index=True
    )
    reference_status: Mapped[str] = mapped_column(String(16), nullable=False)
    use: Mapped[str] = mapped_column(
        String(32), nullable=False, default="research-only"
    )
    norm_note: Mapped[str | None] = mapped_column(Text)


class ReferenceValue(Base, SyntheticMixin):
    __tablename__ = "reference_values"
    __table_args__ = (
        UniqueConstraint(
            "reference_set_id", "scale", "value_type", "raw_value", name="uq_reference_value"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reference_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference_sets.id"), index=True, nullable=False
    )
    scale: Mapped[str] = mapped_column(String(64), nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_value: Mapped[float | None] = mapped_column(Numeric(6, 3))
    transformed_value: Mapped[float | None] = mapped_column(Numeric(6, 3))
    percentile: Mapped[int | None] = mapped_column(Integer)
    t_score: Mapped[int | None] = mapped_column(Integer)
    eneatype: Mapped[int | None] = mapped_column(Integer)


class ScoreRun(Base, SyntheticMixin):
    __tablename__ = "score_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id"), index=True, nullable=False
    )
    reference_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reference_sets.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    raw: Mapped[dict | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

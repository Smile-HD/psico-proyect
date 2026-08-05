"""Recommendation family (F5): recommendation_rules, recommendation_results.

Created empty-but-migrated in F1; F5 owns the data. Rules are declarative
(DB-driven), never LLM-driven.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import SyntheticMixin


class RecommendationRule(Base, SyntheticMixin):
    __tablename__ = "recommendation_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programs.id"), index=True, nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecommendationResult(Base, SyntheticMixin):
    __tablename__ = "recommendation_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id"), index=True, nullable=False
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendation_rules.id"), index=True, nullable=False
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programs.id"), index=True, nullable=False
    )
    fit_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    justification: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

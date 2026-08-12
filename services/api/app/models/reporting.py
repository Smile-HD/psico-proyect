"""Reporting family (F6): reports, report_templates.

Created empty-but-migrated in F1; F6 owns the data.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import SyntheticMixin


class ReportTemplate(Base, SyntheticMixin):
    __tablename__ = "report_templates"
    __table_args__ = (
        UniqueConstraint("key", "version_no", name="uq_report_template_key_version"),
        CheckConstraint(
            "status IN ('draft','published','retired')",
            name="ck_report_template_status",
        ),
        CheckConstraint(
            "version_no > 0",
            name="ck_report_template_version_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    template_body: Mapped[str | None] = mapped_column(Text)
    version_no: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )


class ReportArtifact(Base):
    """Opaque PostgreSQL BYTEA payload kept outside the report metadata row.

    ``report_id`` intentionally has no foreign key: rendering and storage are
    staged outside the report transaction, so a failed finalization can leave
    an orphan for the idempotent cleanup path to reclaim.
    """

    __tablename__ = "report_artifacts"
    __table_args__ = (
        UniqueConstraint("report_id", name="uq_report_artifact_report"),
        CheckConstraint("byte_size >= 0", name="ck_report_artifact_byte_size_nonnegative"),
    )

    storage_key: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Report(Base, SyntheticMixin):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','processing','ready','failed')",
            name="ck_report_status",
        ),
        CheckConstraint("format = 'pdf'", name="ck_report_format"),
        CheckConstraint(
            "status <> 'ready' OR ("
            "storage_key IS NOT NULL AND sha256 IS NOT NULL AND byte_size IS NOT NULL "
            "AND media_type IS NOT NULL AND renderer_version IS NOT NULL "
            "AND generated_at IS NOT NULL AND failed_at IS NULL"
            ")",
            name="ck_report_ready_artifact",
        ),
        CheckConstraint(
            "status <> 'failed' OR ("
            "storage_key IS NULL AND sha256 IS NULL AND byte_size IS NULL "
            "AND media_type IS NULL AND renderer_version IS NULL "
            "AND generated_at IS NULL AND failed_at IS NOT NULL"
            ")",
            name="ck_report_failed_without_artifact",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id"), index=True, nullable=False
    )
    score_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("score_runs.id"), index=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("report_templates.id"), index=True
    )
    template_version_no: Mapped[int | None] = mapped_column(Integer)
    recommendation_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="pdf")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    storage_key: Mapped[str | None] = mapped_column(String(255))
    sha256: Mapped[str | None] = mapped_column(String(64))
    byte_size: Mapped[int | None] = mapped_column(Integer)
    media_type: Mapped[str | None] = mapped_column(String(128))
    renderer_version: Mapped[str | None] = mapped_column(String(64))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

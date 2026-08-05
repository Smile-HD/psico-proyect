"""Reporting family (F6): reports, report_templates.

Created empty-but-migrated in F1; F6 owns the data.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import SyntheticMixin


class ReportTemplate(Base, SyntheticMixin):
    __tablename__ = "report_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    template_body: Mapped[str | None] = mapped_column(Text)


class Report(Base, SyntheticMixin):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id"), index=True, nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("report_templates.id"), index=True
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="pdf")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

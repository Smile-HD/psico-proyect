"""Four-level synthetic instrument catalog models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    versions: Mapped[list["InstrumentVersion"]] = relationship(
        back_populates="instrument", order_by="InstrumentVersion.version_no"
    )


class InstrumentVersion(Base, SyntheticMixin):
    __tablename__ = "instrument_versions"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "version_no", name="uq_version_no_per_instrument"
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_instrument_version_status",
        ),
        CheckConstraint(
            "((status = 'draft' AND is_immutable = false) OR "
            "(status IN ('published', 'archived') AND is_immutable = true))",
            name="ck_published_versions_immutable",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id"), index=True, nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    response_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="likert_1_5", server_default="likert_1_5"
    )
    adaptation_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_immutable: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )

    instrument: Mapped[Instrument] = relationship(back_populates="versions")
    scales: Mapped[list["Scale"]] = relationship(
        back_populates="version", order_by="Scale.display_order"
    )
    items: Mapped[list["InstrumentItem"]] = relationship(
        back_populates="version", order_by="InstrumentItem.item_order"
    )


class Scale(Base, SyntheticMixin):
    __tablename__ = "scales"
    __table_args__ = (
        UniqueConstraint("version_id", "display_order", name="uq_scales_version_order"),
        UniqueConstraint("id", "version_id", name="uq_scales_id_version"),
        CheckConstraint("display_order > 0", name="ck_scale_display_order_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instrument_versions.id"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="es")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)

    version: Mapped[InstrumentVersion] = relationship(back_populates="scales")
    items: Mapped[list["InstrumentItem"]] = relationship(
        back_populates="scale",
        foreign_keys="InstrumentItem.scale_id",
        order_by="InstrumentItem.item_order",
    )


class InstrumentItem(Base, SyntheticMixin):
    __tablename__ = "instrument_items"
    __table_args__ = (
        UniqueConstraint("scale_id", "item_order", name="uq_item_per_scale_order"),
        CheckConstraint("item_order > 0", name="ck_item_order_positive"),
        ForeignKeyConstraint(
            ["scale_id", "version_id"],
            ["scales.id", "scales.version_id"],
            name="fk_instrument_items_scale_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instrument_versions.id"), index=True, nullable=False
    )
    scale_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="es")
    required: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)

    version: Mapped[InstrumentVersion] = relationship(
        back_populates="items", foreign_keys=[version_id]
    )
    scale: Mapped[Scale] = relationship(back_populates="items", foreign_keys=[scale_id])
    response_options: Mapped[list["ResponseOption"]] = relationship(
        back_populates="item", order_by="ResponseOption.display_order"
    )


class ResponseOption(Base, SyntheticMixin):
    __tablename__ = "response_options"
    __table_args__ = (
        UniqueConstraint("item_id", "display_order", name="uq_option_item_order"),
        UniqueConstraint("item_id", "value", name="uq_option_item_value"),
        CheckConstraint(
            "display_order BETWEEN 1 AND 5", name="ck_option_display_order_1_to_5"
        ),
        CheckConstraint("value BETWEEN 1 AND 5", name="ck_option_value_1_to_5"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instrument_items.id"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="es")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)

    item: Mapped[InstrumentItem] = relationship(back_populates="response_options")

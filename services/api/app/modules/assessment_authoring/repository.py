"""SQLAlchemy persistence for catalog aggregates; no HTTP concerns."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.instruments import (
    Instrument,
    InstrumentItem,
    InstrumentVersion,
    ResponseOption,
    Scale,
)


class CatalogRepository:
    @staticmethod
    def get_instrument(
        db: Session, instrument_id: uuid.UUID, *, lock: bool = False
    ) -> Instrument | None:
        statement = select(Instrument).where(Instrument.id == instrument_id)
        if lock:
            statement = statement.with_for_update()
        return db.scalar(statement)

    @staticmethod
    def get_version(
        db: Session, version_id: uuid.UUID, *, lock: bool = False
    ) -> InstrumentVersion | None:
        statement = (
            select(InstrumentVersion)
            .where(InstrumentVersion.id == version_id)
            .options(
                selectinload(InstrumentVersion.instrument),
                selectinload(InstrumentVersion.scales)
                .selectinload(Scale.items)
                .selectinload(InstrumentItem.response_options),
            )
        )
        if lock:
            statement = statement.with_for_update()
        return db.scalar(statement)

    @staticmethod
    def list_instruments(
        db: Session,
        *,
        page: int,
        page_size: int,
        key: str | None = None,
        status: str | None = None,
    ) -> tuple[list[InstrumentVersion], int]:
        base = select(InstrumentVersion).join(Instrument)
        count_statement = (
            select(func.count()).select_from(InstrumentVersion).join(Instrument)
        )
        if key:
            predicate = Instrument.key.ilike(f"%{key}%")
            base = base.where(predicate)
            count_statement = count_statement.where(predicate)
        if status:
            base = base.where(InstrumentVersion.status == status)
            count_statement = count_statement.where(InstrumentVersion.status == status)
        base = (
            base.options(selectinload(InstrumentVersion.instrument))
            .order_by(Instrument.key, InstrumentVersion.version_no)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(db.scalars(base).all()), int(db.scalar(count_statement) or 0)

    @staticmethod
    def list_published_versions(db: Session) -> list[InstrumentVersion]:
        statement = (
            select(InstrumentVersion)
            .join(Instrument)
            .where(InstrumentVersion.status == "published")
            .options(selectinload(InstrumentVersion.instrument))
            .order_by(Instrument.key, InstrumentVersion.version_no)
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def create_instrument(
        db: Session,
        *,
        instrument_id: uuid.UUID,
        key: str,
        title: str,
        description: str | None,
        adaptation: dict[str, Any] | None,
    ) -> tuple[Instrument, InstrumentVersion]:
        instrument = Instrument(
            id=instrument_id,
            key=key,
            title=title,
            description=description,
            synthetic=True,
            source="runtime",
        )
        version = InstrumentVersion(
            id=uuid.uuid4(),
            instrument=instrument,
            version_no=1,
            status="draft",
            is_immutable=False,
            response_type="likert_1_5",
            adaptation_metadata=adaptation,
            synthetic=True,
            source="runtime",
        )
        db.add(instrument)
        db.flush()
        return instrument, version

    @staticmethod
    def create_version(
        db: Session,
        *,
        instrument: Instrument,
        version_no: int,
        adaptation: dict[str, Any] | None,
    ) -> InstrumentVersion:
        version = InstrumentVersion(
            id=uuid.uuid4(),
            instrument_id=instrument.id,
            version_no=version_no,
            status="draft",
            is_immutable=False,
            response_type="likert_1_5",
            adaptation_metadata=adaptation,
            synthetic=True,
            source="runtime",
        )
        db.add(version)
        db.flush()
        return version

    @staticmethod
    def next_version_no(db: Session, instrument_id: uuid.UUID) -> int:
        current = db.scalar(
            select(func.max(InstrumentVersion.version_no)).where(
                InstrumentVersion.instrument_id == instrument_id
            )
        )
        return int(current or 0) + 1

    @staticmethod
    def counts(db: Session, version_id: uuid.UUID) -> dict[str, int]:
        scale_count = (
            db.scalar(
                select(func.count())
                .select_from(Scale)
                .where(Scale.version_id == version_id)
            )
            or 0
        )
        item_count = (
            db.scalar(
                select(func.count())
                .select_from(InstrumentItem)
                .where(InstrumentItem.version_id == version_id)
            )
            or 0
        )
        option_count = (
            db.scalar(
                select(func.count())
                .select_from(ResponseOption)
                .join(InstrumentItem, ResponseOption.item_id == InstrumentItem.id)
                .where(InstrumentItem.version_id == version_id)
            )
            or 0
        )
        return {
            "scale_count": int(scale_count),
            "item_count": int(item_count),
            "option_count": int(option_count),
        }

    @staticmethod
    def is_seed_instrument(instrument: Instrument) -> bool:
        return (
            instrument.source == "seed"
            or instrument.id.version == 5
            or instrument.key == "TP-S-01"
        )

    @staticmethod
    def is_seed_version(version: InstrumentVersion) -> bool:
        return (
            version.source == "seed"
            or version.id.version == 5
            or CatalogRepository.is_seed_instrument(version.instrument)
        )

    @staticmethod
    def aggregate_mapping(version: InstrumentVersion) -> dict[str, Any]:
        scales: list[dict[str, Any]] = []
        for scale in sorted(version.scales, key=lambda row: row.display_order):
            items: list[dict[str, Any]] = []
            for item in sorted(scale.items, key=lambda row: row.item_order):
                items.append(
                    {
                        "id": item.id,
                        "scale_id": item.scale_id,
                        "version_id": item.version_id,
                        "item_order": item.item_order,
                        "text": item.text,
                        "locale": item.locale,
                        "required": item.required,
                        "options": [
                            {
                                "id": option.id,
                                "item_id": option.item_id,
                                "display_order": option.display_order,
                                "label": option.label,
                                "locale": option.locale,
                                "value": option.value,
                            }
                            for option in sorted(
                                item.response_options, key=lambda row: row.display_order
                            )
                        ],
                    }
                )
            scales.append(
                {
                    "id": scale.id,
                    "version_id": scale.version_id,
                    "display_order": scale.display_order,
                    "label": scale.label,
                    "locale": scale.locale,
                    "items": items,
                }
            )
        return {
            "version_id": version.id,
            "response_type": version.response_type,
            "adaptation": version.adaptation_metadata,
            "scales": scales,
        }

    @staticmethod
    def delete_draft_children(
        db: Session, version: InstrumentVersion, keep_ids: set[uuid.UUID]
    ) -> None:
        for scale in list(version.scales):
            for item in list(scale.items):
                if item.id not in keep_ids:
                    for option in list(item.response_options):
                        db.delete(option)
                    db.delete(item)
            if scale.id not in keep_ids:
                db.delete(scale)

    @staticmethod
    def find_scale(db: Session, scale_id: uuid.UUID) -> Scale | None:
        return db.get(Scale, scale_id)

    @staticmethod
    def find_item(db: Session, item_id: uuid.UUID) -> InstrumentItem | None:
        return db.get(InstrumentItem, item_id)

    @staticmethod
    def find_option(db: Session, option_id: uuid.UUID) -> ResponseOption | None:
        return db.get(ResponseOption, option_id)

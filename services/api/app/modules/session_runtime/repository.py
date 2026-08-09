"""SQLAlchemy persistence and safe projections for evaluation sessions."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from app.models.identity import User
from app.models.instruments import InstrumentItem, InstrumentVersion, ResponseOption, Scale
from app.models.sessions import Response, Session


def pinned_projection(
    version: InstrumentVersion, response_option_ids: Mapping[Any, Any] | None = None
) -> dict[str, Any]:
    """Project an immutable version without catalog status or numeric values."""
    answers = response_option_ids or {}
    scales = []
    for scale in sorted(version.scales, key=lambda row: row.display_order):
        items = []
        for item in sorted(scale.items, key=lambda row: row.item_order):
            projected = {
                "id": str(item.id),
                "item_order": item.item_order,
                "text": item.text,
                "locale": item.locale,
                "required": item.required,
                "response_options": [
                    {
                        "id": str(option.id),
                        "display_order": option.display_order,
                        "label": option.label,
                        "locale": option.locale,
                    }
                    for option in sorted(
                        item.response_options, key=lambda row: row.display_order
                    )
                ],
            }
            if item.id in answers:
                projected["response_option_id"] = str(answers[item.id])
            items.append(projected)
        scales.append(
            {
                "id": str(scale.id),
                "display_order": scale.display_order,
                "label": scale.label,
                "locale": scale.locale,
                "items": items,
            }
        )
    return {
        "instrument_version_id": str(version.id),
        "version_no": version.version_no,
        "response_type": version.response_type,
        "scales": scales,
    }


class SessionRepository:
    """Persistence seam; transaction ownership remains with the service."""

    @staticmethod
    def get_actor(db: DbSession, user_id: uuid.UUID, *, lock: bool = False) -> User | None:
        statement = select(User).where(User.id == user_id)
        if lock:
            statement = statement.with_for_update()
        return db.scalar(statement)

    @staticmethod
    def get_session(
        db: DbSession, session_id: uuid.UUID, *, lock: bool = False
    ) -> Session | None:
        statement = select(Session).where(Session.id == session_id)
        if lock:
            statement = statement.with_for_update()
        return db.scalar(statement)

    @staticmethod
    def get_version(
        db: DbSession, version_id: uuid.UUID, *, lock: bool = False
    ) -> InstrumentVersion | None:
        statement = (
            select(InstrumentVersion)
            .where(InstrumentVersion.id == version_id)
            .options(
                selectinload(InstrumentVersion.scales)
                .selectinload(Scale.items)
                .selectinload(InstrumentItem.response_options)
            )
        )
        if lock:
            statement = statement.with_for_update()
        return db.scalar(statement)

    @staticmethod
    def list_for_user(db: DbSession, user_id: uuid.UUID) -> list[Session]:
        return list(
            db.scalars(
                select(Session)
                .where(Session.user_id == user_id)
                .order_by(Session.started_at.desc(), Session.id.desc())
            ).all()
        )

    @staticmethod
    def required_item_ids(db: DbSession, version_id: uuid.UUID) -> list[uuid.UUID]:
        return list(
            db.scalars(
                select(InstrumentItem.id)
                .where(
                    InstrumentItem.version_id == version_id,
                    InstrumentItem.required.is_(True),
                )
                .order_by(InstrumentItem.item_order)
            ).all()
        )

    @staticmethod
    def response_option_map(
        db: DbSession, version_id: uuid.UUID
    ) -> dict[uuid.UUID, dict[uuid.UUID, int]]:
        rows = db.execute(
            select(InstrumentItem.id, ResponseOption.id, ResponseOption.value)
            .join(ResponseOption, ResponseOption.item_id == InstrumentItem.id)
            .where(InstrumentItem.version_id == version_id)
        ).all()
        result: dict[uuid.UUID, dict[uuid.UUID, int]] = {}
        for item_id, option_id, value in rows:
            result.setdefault(item_id, {})[option_id] = value
        return result

    @staticmethod
    def answered_item_ids(db: DbSession, session_id: uuid.UUID) -> set[uuid.UUID]:
        return set(
            db.scalars(
                select(Response.item_id).where(Response.session_id == session_id)
            ).all()
        )

    @staticmethod
    def response_count(db: DbSession, session_id: uuid.UUID) -> int:
        return int(
            db.scalar(
                select(func.count()).select_from(Response).where(Response.session_id == session_id)
            )
            or 0
        )

    @staticmethod
    def answer_option_ids(
        db: DbSession, session_id: uuid.UUID
    ) -> dict[uuid.UUID, uuid.UUID]:
        rows = db.execute(
            select(Response.item_id, ResponseOption.id)
            .join(
                ResponseOption,
                (ResponseOption.item_id == Response.item_id)
                & (ResponseOption.value == Response.value),
            )
            .where(Response.session_id == session_id)
        ).all()
        return {item_id: option_id for item_id, option_id in rows}

    @staticmethod
    def create_session(
        db: DbSession,
        *,
        user_id: uuid.UUID,
        instrument_version_id: uuid.UUID,
        consent_grant_id: uuid.UUID,
    ) -> Session:
        session = Session(
            user_id=user_id,
            instrument_version_id=instrument_version_id,
            consent_grant_id=consent_grant_id,
            status="in_progress",
            synthetic=False,
            source="runtime",
        )
        db.add(session)
        db.flush()
        return session

    @staticmethod
    def upsert_responses(
        db: DbSession,
        session_id: uuid.UUID,
        values: Mapping[uuid.UUID, int] | Iterable[tuple[uuid.UUID, int]],
    ) -> None:
        pairs = values.items() if isinstance(values, Mapping) else values
        rows = [
            {"session_id": session_id, "item_id": item_id, "value": value}
            for item_id, value in pairs
        ]
        if not rows:
            return
        insert = pg_insert(Response).values(rows)
        db.execute(
            insert.on_conflict_do_update(
                index_elements=[Response.session_id, Response.item_id],
                set_={"value": insert.excluded.value},
            )
        )
        db.flush()

    def project_session(self, db: DbSession, session: Session) -> dict[str, Any]:
        version = self.get_version(db, session.instrument_version_id)
        if version is None:
            return {
                "id": str(session.id),
                "status": session.status,
                "instrument_version_id": str(session.instrument_version_id),
                "progress": {"answered": 0, "total": 0},
                "projection": None,
            }
        answers = self.answer_option_ids(db, session.id)
        projection = pinned_projection(version, answers)
        total = sum(len(scale["items"]) for scale in projection["scales"])
        return {
            "id": str(session.id),
            "status": session.status,
            "instrument_version_id": str(session.instrument_version_id),
            "progress": {"answered": len(answers), "total": total},
            "projection": projection,
        }

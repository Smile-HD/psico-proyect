"""Repository contracts for locked session writes and pinned reads."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.instruments import Instrument, InstrumentItem, InstrumentVersion, ResponseOption, Scale
from app.models.sessions import Response, Session
from app.modules.session_runtime.repository import SessionRepository, pinned_projection
from app.seed.loader import seed_id


class CaptureSession:
    def scalar(self, statement):
        self.statement = statement
        return None


def test_locked_lookups_emit_for_update() -> None:
    db = CaptureSession()
    SessionRepository.get_session(db, uuid.uuid4(), lock=True)

    assert db.statement._for_update_arg is not None


def test_pinned_projection_keeps_archived_content_but_hides_values() -> None:
    instrument = Instrument(key="SESSION-PROJ", title="Synthetic")
    version = InstrumentVersion(
        instrument=instrument, version_no=1, status="archived", is_immutable=True
    )
    scale = Scale(version=version, label="Synthetic scale", display_order=1, locale="es")
    item = InstrumentItem(
        version=version,
        scale=scale,
        item_order=1,
        text="Synthetic item",
        locale="es",
        required=True,
    )
    option = ResponseOption(
        item=item,
        display_order=1,
        value=1,
        label="Never",
        locale="es",
    )

    projection = pinned_projection(version, {item.id: option.id})

    assert projection["instrument_version_id"] == str(version.id)
    assert projection["scales"][0]["items"][0]["response_option_id"] == str(option.id)
    assert "status" not in projection
    assert "value" not in str(projection).lower()


def test_upsert_replaces_a_response_without_duplicate_rows(seeded_db_session) -> None:
    db = seeded_db_session
    version_id = seed_id("TP-S-01:v1")
    item = db.scalar(
        select(InstrumentItem)
        .where(InstrumentItem.version_id == version_id)
        .order_by(InstrumentItem.item_order)
    )
    options = sorted(item.response_options, key=lambda row: row.display_order)
    session = Session(
        user_id=seed_id("user:evaluado"),
        instrument_version_id=version_id,
        status="in_progress",
    )
    db.add(session)
    db.flush()
    repository = SessionRepository()

    repository.upsert_responses(db, session.id, {item.id: options[0].value})
    db.commit()
    repository.upsert_responses(db, session.id, {item.id: options[1].value})
    db.commit()

    rows = db.scalars(select(Response).where(Response.session_id == session.id)).all()
    assert len(rows) == 1
    assert rows[0].value == options[1].value

    db.delete(rows[0])
    db.delete(session)
    db.commit()

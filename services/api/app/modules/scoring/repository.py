"""Read-only F2/F3 adapters and ScoreRun persistence for F4 scoring."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.instruments import InstrumentVersion
from app.models.scoring import ReferenceSet, ReferenceValue, ScoreRun
from app.models.sessions import Session
from app.modules.assessment_authoring.projections import fixture_projection
from app.modules.scoring.domain import OverallReference, ScaleInput, ScaleReference, ScoringInput
from app.modules.scoring.errors import reference_unavailable, resource_not_found, scoring_integrity_error
from app.modules.session_runtime.repository import SessionRepository

REFERENCE_SET_KEY = "RS-TP-S-01"


@dataclass(frozen=True)
class ScoringContext:
    session: Session
    version: InstrumentVersion
    response_option_ids: dict[uuid.UUID, uuid.UUID]
    fixture: dict[str, Any]
    reference: ReferenceSet
    reference_values: tuple[ReferenceValue, ...]


class ScoringRepository:
    def __init__(self, session_repository: SessionRepository | None = None) -> None:
        self.session_repository = session_repository or SessionRepository()

    @staticmethod
    def _uuid(value: Any) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (AttributeError, TypeError, ValueError) as error:
            raise resource_not_found() from error

    def get_session(self, db: DbSession, session_id: uuid.UUID, *, lock: bool = False) -> Session | None:
        return self.session_repository.get_session(db, self._uuid(session_id), lock=lock)

    def get_version(self, db: DbSession, version_id: uuid.UUID, *, lock: bool = False) -> InstrumentVersion | None:
        return self.session_repository.get_version(db, self._uuid(version_id), lock=lock)

    def answer_option_ids(self, db: DbSession, session_id: uuid.UUID) -> dict[uuid.UUID, uuid.UUID]:
        return self.session_repository.answer_option_ids(db, self._uuid(session_id))

    @staticmethod
    def get_reference_set(
        db: DbSession,
        key: str = REFERENCE_SET_KEY,
        *,
        instrument_version_id: uuid.UUID | None = None,
    ) -> ReferenceSet | None:
        statement = select(ReferenceSet).where(ReferenceSet.key == key)
        if instrument_version_id is not None:
            statement = statement.where(ReferenceSet.instrument_version_id == instrument_version_id)
        return db.scalar(statement)

    @staticmethod
    def list_reference_values(
        db: DbSession,
        reference_set_id: uuid.UUID,
        *,
        scale: str | None = None,
        value_type: str | None = None,
    ) -> list[ReferenceValue]:
        statement = select(ReferenceValue).where(ReferenceValue.reference_set_id == reference_set_id)
        if scale is not None:
            statement = statement.where(ReferenceValue.scale == scale)
        if value_type is not None:
            statement = statement.where(ReferenceValue.value_type == value_type)
        statement = statement.order_by(
            ReferenceValue.scale, ReferenceValue.value_type, ReferenceValue.raw_value, ReferenceValue.id
        )
        return list(db.scalars(statement).all())

    def require_reference_set(
        self,
        db: DbSession,
        key: str = REFERENCE_SET_KEY,
        *,
        instrument_version_id: uuid.UUID | None = None,
    ) -> ReferenceSet:
        if key != REFERENCE_SET_KEY:
            raise reference_unavailable({"reference_set": key})
        reference = self.get_reference_set(db, key, instrument_version_id=instrument_version_id)
        if reference is None:
            raise reference_unavailable({"reference_set": key})
        return reference

    def get_scoring_context(
        self,
        db: DbSession,
        session_id: uuid.UUID,
        *,
        reference_key: str = REFERENCE_SET_KEY,
    ) -> ScoringContext:
        session = self.get_session(db, session_id)
        if session is None:
            raise resource_not_found()
        version = self.get_version(db, session.instrument_version_id)
        if version is None:
            raise scoring_integrity_error({"reason": "instrument_version_unavailable"})
        reference = self.require_reference_set(
            db, reference_key, instrument_version_id=version.id
        )
        values = tuple(self.list_reference_values(db, reference.id))
        if not values:
            raise reference_unavailable({"reference_set": reference.key})
        return ScoringContext(
            session=session,
            version=version,
            response_option_ids=self.answer_option_ids(db, session.id),
            fixture=fixture_projection(version),
            reference=reference,
            reference_values=values,
        )

    def get_scoring_input(
        self,
        db: DbSession,
        session_id: uuid.UUID,
        *,
        reference_key: str = REFERENCE_SET_KEY,
    ) -> ScoringInput:
        context = self.get_scoring_context(db, session_id, reference_key=reference_key)
        return self.build_scoring_input(context)

    @staticmethod
    def build_scoring_input(context: ScoringContext) -> ScoringInput:
        option_values = {
            option["id"]: int(option["value"])
            for scale in context.fixture["scales"]
            for item in scale["items"]
            for option in item["response_options"]
        }
        scale_labels = {str(scale.id): scale.label for scale in context.version.scales}
        scales: list[ScaleInput] = []
        for scale in context.fixture["scales"]:
            label = scale_labels.get(scale["id"])
            if label is None:
                raise scoring_integrity_error({"reason": "scale_label_unavailable", "scale_id": scale["id"]})
            values = []
            for item in scale["items"]:
                item_id = uuid.UUID(item["id"])
                option_id = context.response_option_ids.get(item_id)
                if option_id is None or str(option_id) not in option_values:
                    raise scoring_integrity_error(
                        {"reason": "response_option_unavailable", "item_id": str(item_id)}
                    )
                values.append(option_values[str(option_id)])
            scales.append(ScaleInput(label=label, values=tuple(values)))

        scale_references: dict[str, dict[str, float]] = {}
        overall_rows: list[OverallReference] = []
        for row in context.reference_values:
            if row.scale == "overall":
                if row.raw_value is None:
                    raise scoring_integrity_error({"reason": "overall_raw_missing", "reference_value_id": str(row.id)})
                try:
                    overall_rows.append(
                        OverallReference(
                            int(row.raw_value), int(row.percentile), int(row.t_score), int(row.eneatype)
                        )
                    )
                except (TypeError, ValueError) as error:
                    raise scoring_integrity_error(
                        {"reason": "overall_reference_invalid", "reference_value_id": str(row.id)}
                    ) from error
                continue
            if row.raw_value is None:
                raise scoring_integrity_error({"reason": "scale_reference_missing", "scale": row.scale})
            stats = scale_references.setdefault(row.scale, {})
            if row.value_type in stats or row.value_type not in {"mean", "sd"}:
                raise scoring_integrity_error({"reason": "invalid_scale_reference", "scale": row.scale})
            stats[row.value_type] = float(row.raw_value)
        if any(set(stats) != {"mean", "sd"} for stats in scale_references.values()):
            raise scoring_integrity_error({"reason": "incomplete_scale_reference"})

        references = tuple(
            ScaleReference(label, stats["mean"], stats["sd"])
            for label, stats in scale_references.items()
        )
        return ScoringInput(
            version_id=context.version.id,
            reference_set_id=context.reference.id,
            scales=tuple(scales),
            overall_rows=tuple(overall_rows),
            scale_references=references,
        )

    @staticmethod
    def create_score_run(
        db: DbSession, *, session_id: uuid.UUID, reference_set_id: uuid.UUID
    ) -> ScoreRun:
        run = ScoreRun(
            session_id=session_id,
            reference_set_id=reference_set_id,
            status="pending",
            synthetic=False,
            source="runtime",
        )
        db.add(run)
        db.flush()
        return run

    @staticmethod
    def complete_score_run(
        db: DbSession,
        run: ScoreRun,
        *,
        raw: Mapping[str, Any],
        computed_at: datetime,
    ) -> ScoreRun:
        run.status = "completed"
        run.raw = dict(raw)
        run.computed_at = computed_at
        run.synthetic = False
        run.source = "runtime"
        db.flush()
        return run

    @staticmethod
    def list_score_runs(
        db: DbSession, session_id: uuid.UUID, *, status: str | None = None
    ) -> list[ScoreRun]:
        statement = select(ScoreRun).where(ScoreRun.session_id == session_id)
        if status is not None:
            statement = statement.where(ScoreRun.status == status)
        statement = statement.order_by(
            ScoreRun.computed_at.desc().nullslast(), ScoreRun.id.desc()
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def latest_completed_run(db: DbSession, session_id: uuid.UUID) -> ScoreRun | None:
        statement = (
            select(ScoreRun)
            .where(ScoreRun.session_id == session_id, ScoreRun.status == "completed")
            .order_by(ScoreRun.computed_at.desc().nullslast(), ScoreRun.id.desc())
            .limit(1)
        )
        return db.scalar(statement)

    get_latest_completed_run = latest_completed_run


repository = ScoringRepository()

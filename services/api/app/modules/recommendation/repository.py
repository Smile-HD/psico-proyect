"""Database adapters for F5 recommendation inputs and generations."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.institutions import Program
from app.models.recommendation import RecommendationResult, RecommendationRule
from app.models.scoring import ScoreRun
from app.models.sessions import Session
from app.modules.recommendation.domain import RecommendationResult as ProgramRecommendation
from app.modules.recommendation.errors import recommendation_integrity_error, resource_not_found
from app.modules.scoring.repository import ScoringRepository


@dataclass(frozen=True)
class RecommendationContext:
    """The completed score and declarative catalog used by one evaluation."""

    session: Session
    score_run: ScoreRun
    programs: tuple[Program, ...]
    rules: tuple[RecommendationRule, ...]


class RecommendationRepository:
    """Read F4 output/catalog rows and stage one recommendation generation."""

    def __init__(self, scoring_repository: ScoringRepository | None = None) -> None:
        self.scoring_repository = scoring_repository or ScoringRepository()

    @staticmethod
    def _uuid(value: Any) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (AttributeError, TypeError, ValueError) as error:
            raise resource_not_found() from error

    def get_session(
        self,
        db: DbSession,
        session_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> Session | None:
        """Reuse the F3/F4 session consumer without changing its behavior."""

        return self.scoring_repository.get_session(db, self._uuid(session_id), lock=lock)

    @staticmethod
    def list_programs(db: DbSession) -> list[Program]:
        """Return the program catalog in a deterministic order."""

        statement = select(Program).order_by(Program.name.asc(), Program.id.asc())
        return list(db.scalars(statement).all())

    @staticmethod
    def list_active_rules(db: DbSession) -> list[RecommendationRule]:
        """Return only active DB rules, ordered by their stable identifiers."""

        statement = (
            select(RecommendationRule)
            .where(RecommendationRule.is_active.is_(True))
            .order_by(RecommendationRule.id.asc())
        )
        return list(db.scalars(statement).all())

    def get_recommendation_context(
        self,
        db: DbSession,
        session_id: uuid.UUID,
    ) -> RecommendationContext:
        """Load one completed F4 run and the current declarative catalog."""

        sid = self._uuid(session_id)
        session = self.get_session(db, sid)
        if session is None:
            raise resource_not_found()

        score_run = self.scoring_repository.latest_completed_run(db, sid)
        if score_run is None:
            raise resource_not_found()
        if score_run.raw is None:
            raise recommendation_integrity_error({"reason": "score_run_raw_unavailable"})

        return RecommendationContext(
            session=session,
            score_run=score_run,
            programs=tuple(self.list_programs(db)),
            rules=tuple(self.list_active_rules(db)),
        )

    def persist_generation(
        self,
        db: DbSession,
        session_id: uuid.UUID,
        recommendations: Iterable[ProgramRecommendation],
        *,
        created_at: datetime | None = None,
    ) -> tuple[RecommendationResult, ...]:
        """Stage one row per evaluated rule; the caller owns commit/rollback."""

        sid = self._uuid(session_id)
        generation_at = created_at or datetime.now(timezone.utc)
        rows: list[RecommendationResult] = []
        for recommendation in recommendations:
            for rule_result in recommendation.rule_results:
                row = RecommendationResult(
                    session_id=sid,
                    rule_id=self._uuid(rule_result.rule_id),
                    program_id=self._uuid(rule_result.program_id),
                    fit_score=rule_result.fit_score,
                    justification=rule_result.justification,
                    synthetic=False,
                    source="runtime",
                    created_at=generation_at,
                )
                db.add(row)
                rows.append(row)

        db.flush()
        return tuple(rows)

    @staticmethod
    def list_generation_rows(
        db: DbSession,
        session_id: uuid.UUID,
        created_at: datetime,
    ) -> tuple[RecommendationResult, ...]:
        """Read all rows grouped by one shared generation timestamp."""

        statement = (
            select(RecommendationResult)
            .where(
                RecommendationResult.session_id == session_id,
                RecommendationResult.created_at == created_at,
            )
            .order_by(
                RecommendationResult.program_id.asc(),
                RecommendationResult.rule_id.asc(),
                RecommendationResult.id.asc(),
            )
        )
        return tuple(db.scalars(statement).all())

    @staticmethod
    def latest_generation_anchor(
        db: DbSession,
        session_id: uuid.UUID,
    ) -> RecommendationResult | None:
        """Select the latest result anchor by timestamp, then result id."""

        statement = (
            select(RecommendationResult)
            .where(RecommendationResult.session_id == session_id)
            .order_by(
                RecommendationResult.created_at.desc(),
                RecommendationResult.id.desc(),
            )
            .limit(1)
        )
        return db.scalar(statement)

    def latest_generation(
        self,
        db: DbSession,
        session_id: uuid.UUID,
    ) -> tuple[RecommendationResult, ...]:
        """Return every row sharing the deterministic latest anchor timestamp."""

        sid = self._uuid(session_id)
        anchor = self.latest_generation_anchor(db, sid)
        if anchor is None:
            return ()
        return self.list_generation_rows(db, sid, anchor.created_at)

    create_generation = persist_generation
    get_latest_generation_anchor = latest_generation_anchor
    get_latest_generation = latest_generation


repository = RecommendationRepository()

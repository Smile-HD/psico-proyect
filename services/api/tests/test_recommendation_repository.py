"""PostgreSQL-backed repository contracts for the F5 recommendation boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import func, select, update

from app.models.recommendation import RecommendationResult, RecommendationRule
from app.models.scoring import ScoreRun
from app.models.sessions import Session as SessionRow
from app.modules.recommendation.domain import evaluate_recommendations
from app.modules.recommendation.repository import RecommendationRepository
from app.modules.scoring.service import ScoringService
from app.seed.loader import seed_id


def _seeded_completed_session(db, profile: str) -> SessionRow:
    session = db.get(SessionRow, seed_id(f"session:{profile}"))
    assert session is not None
    assert session.status == "completed"
    return session


def _score_reserved_session(db, profile: str) -> SessionRow:
    session = _seeded_completed_session(db, profile)
    user = SimpleNamespace(id=seed_id(profile), roles=["evaluado"])
    status, payload = ScoringService().score_session(
        db,
        user,
        session.id,
        {},
        f"recommendation-repository-score-{profile}-{uuid4().hex}",
    )
    assert status == 200
    assert payload["session_id"] == str(session.id)
    return session


def _recommendations(repository: RecommendationRepository, db, session: SessionRow):
    context = repository.get_recommendation_context(db, session.id)
    recommendations = evaluate_recommendations(
        context.score_run.raw,
        context.programs,
        context.rules,
    )
    assert recommendations
    return context, recommendations


def _result_count(db, session_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationResult)
            .where(RecommendationResult.session_id == session_id)
        )
        or 0
    )


def test_repository_reads_latest_scored_run_programs_and_active_rules(seeded_db_session) -> None:
    db = seeded_db_session
    session = _score_reserved_session(db, "evaluado_21")
    repository = RecommendationRepository()
    _score_reserved_session(db, "evaluado_21")

    context = repository.get_recommendation_context(db, session.id)
    active_rules = repository.list_active_rules(db)
    programs = repository.list_programs(db)
    scored_runs = repository.scoring_repository.list_score_runs(db, session.id)

    assert context.session.id == session.id
    assert len(scored_runs) >= 2
    assert context.score_run.id == scored_runs[0].id
    assert context.score_run.status == "completed"
    persisted_run = db.get(ScoreRun, context.score_run.id)
    assert persisted_run is not None
    assert context.score_run.raw == persisted_run.raw
    assert programs
    assert active_rules
    assert all(rule.is_active for rule in active_rules)
    assert [rule.id for rule in active_rules] == sorted(
        (rule.id for rule in active_rules), key=str
    )
    assert {rule.program_id for rule in active_rules}.issubset(
        {program.id for program in programs}
    )

    disabled_rule = active_rules[0]
    db.execute(
        update(RecommendationRule)
        .where(RecommendationRule.id == disabled_rule.id)
        .values(is_active=False)
    )
    db.flush()
    filtered_rules = repository.list_active_rules(db)
    assert disabled_rule.id not in {rule.id for rule in filtered_rules}
    db.rollback()


def test_repository_persists_one_runtime_row_per_rule_with_shared_timestamp(
    seeded_db_session,
) -> None:
    db = seeded_db_session
    session = _score_reserved_session(db, "evaluado_22")
    repository = RecommendationRepository()
    _context, recommendations = _recommendations(repository, db, session)
    expected_rule_results = tuple(
        rule_result
        for recommendation in recommendations
        for rule_result in recommendation.rule_results
    )
    before = _result_count(db, session.id)
    created_at = datetime(2026, 8, 11, 12, 0, 0, 123456, tzinfo=timezone.utc)

    rows = repository.persist_generation(
        db,
        session.id,
        recommendations,
        created_at=created_at,
    )

    assert len(rows) == len(expected_rule_results)
    assert len(rows) > 0
    assert _result_count(db, session.id) == before + len(expected_rule_results)
    assert {row.created_at for row in rows} == {created_at}
    assert all(row.synthetic is False for row in rows)
    assert all(row.source == "runtime" for row in rows)
    assert all(row.fit_score.as_tuple().exponent == -2 for row in rows)
    assert RecommendationResult.__table__.c.fit_score.type.precision == 5
    assert RecommendationResult.__table__.c.fit_score.type.scale == 2

    by_rule = {row.rule_id: row for row in rows}
    assert set(by_rule) == {rule_result.rule_id for rule_result in expected_rule_results}
    for rule_result in expected_rule_results:
        row = by_rule[rule_result.rule_id]
        assert row.program_id == rule_result.program_id
        assert row.fit_score == rule_result.fit_score
        assert row.justification == rule_result.justification

    db.commit()


def test_repository_generation_writes_are_left_to_the_callers_transaction(
    seeded_db_session,
) -> None:
    db = seeded_db_session
    session = _score_reserved_session(db, "evaluado_23")
    repository = RecommendationRepository()
    _context, recommendations = _recommendations(repository, db, session)
    before = _result_count(db, session.id)

    repository.persist_generation(db, session.id, recommendations)
    assert _result_count(db, session.id) > before

    db.rollback()
    assert _result_count(db, session.id) == before


def test_repository_allows_multiple_generations_and_selects_latest_anchor(
    seeded_db_session,
) -> None:
    db = seeded_db_session
    session = _score_reserved_session(db, "evaluado_24")
    repository = RecommendationRepository()
    _context, recommendations = _recommendations(repository, db, session)
    first_at = datetime(2026, 8, 11, 12, 1, tzinfo=timezone.utc)
    second_at = datetime(2026, 8, 11, 12, 2, tzinfo=timezone.utc)

    first_rows = repository.persist_generation(
        db,
        session.id,
        recommendations,
        created_at=first_at,
    )
    db.commit()
    second_rows = repository.persist_generation(
        db,
        session.id,
        recommendations,
        created_at=second_at,
    )
    db.commit()

    assert first_rows and second_rows
    assert {row.created_at for row in first_rows} == {first_at}
    assert {row.created_at for row in second_rows} == {second_at}
    assert {row.id for row in first_rows}.isdisjoint({row.id for row in second_rows})

    anchor = repository.latest_generation_anchor(db, session.id)
    assert anchor is not None
    assert anchor.created_at == second_at
    assert anchor.id == max((row.id for row in second_rows), key=str)

    latest_rows = repository.latest_generation(db, session.id)
    assert {row.id for row in latest_rows} == {row.id for row in second_rows}
    assert {row.created_at for row in latest_rows} == {second_at}

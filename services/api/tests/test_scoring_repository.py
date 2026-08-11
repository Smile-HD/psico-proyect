"""PostgreSQL-backed repository contracts for the F4 scoring boundary."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.errors import ApiError, CONFLICT, INTERNAL_ERROR, NOT_FOUND
from app.models.scoring import ScoreRun
from app.models.sessions import Session
from app.modules.scoring.errors import (
    reference_unavailable,
    resource_not_found,
    scoring_integrity_error,
    session_not_completed,
)
from app.modules.scoring.repository import ScoringRepository
from app.seed.loader import FIXTURES_DIR, seed_id


def _seeded_completed_session(db, profile: str = "evaluado_19") -> Session:
    session = db.scalar(
        select(Session)
        .where(
            Session.user_id == seed_id(profile),
            Session.source == "seed",
            Session.status == "completed",
        )
        .order_by(Session.id)
    )
    assert session is not None
    return session


def test_scoring_error_factories_keep_stable_tokens() -> None:
    assert session_not_completed().code == CONFLICT
    assert session_not_completed().message == "session_not_completed"
    assert reference_unavailable().code == INTERNAL_ERROR
    assert reference_unavailable().message == "reference_unavailable"
    assert resource_not_found().code == NOT_FOUND
    assert resource_not_found().message == "resource_not_found"
    assert scoring_integrity_error({"path": "raw"}).message == "scoring_integrity_error"
    assert session_not_completed({"session_id": "synthetic"}).details == {
        "session_id": "synthetic"
    }


def test_reference_contract_is_available_through_repository(seeded_db_session) -> None:
    db = seeded_db_session
    repository = ScoringRepository()
    reference = repository.get_reference_set(db, "RS-TP-S-01")
    rows = repository.list_reference_values(db, reference.id)

    fixture = json.loads((FIXTURES_DIR / "reference.json").read_text(encoding="utf-8"))
    items = json.loads((FIXTURES_DIR / "items.json").read_text(encoding="utf-8"))
    scale_labels = {scale["scale"] for scale in items["scales"]}
    per_scale = [row for row in rows if row.scale != "overall"]
    overall = [row for row in rows if row.scale == "overall"]

    assert reference.key == fixture["key"]
    assert reference.norm_note == fixture["norm_note"]
    assert reference.reference_status == "synthetic"
    assert reference.use == "research-only"
    assert len(rows) == 30
    assert Counter(row.scale for row in per_scale) == Counter({label: 2 for label in scale_labels})
    assert {row.value_type for row in per_scale} == {"mean", "sd"}
    assert len(overall) == 20
    assert {int(row.raw_value) for row in overall} == set(range(1, 21))
    assert all(row.value_type == "percentile" for row in overall)


def test_repository_reads_pinned_session_fixture_and_reference(seeded_db_session) -> None:
    db = seeded_db_session
    repository = ScoringRepository()
    session = _seeded_completed_session(db)

    context = repository.get_scoring_context(db, session.id)

    assert context.session.id == session.id
    assert context.version.id == session.instrument_version_id
    assert context.reference.key == "RS-TP-S-01"
    assert len(context.response_option_ids) == 20
    assert len(context.fixture["scales"]) == 5
    assert all(
        len(item["response_options"]) == 5
        for scale in context.fixture["scales"]
        for item in scale["items"]
    )
    assert all(
        str(option_id) in {
            option["id"]
            for scale in context.fixture["scales"]
            for item in scale["items"]
            for option in item["response_options"]
        }
        for option_id in context.response_option_ids.values()
    )

    scoring_input = repository.get_scoring_input(db, session.id)
    assert len(scoring_input.scales) == 5
    assert all(len(scale.values) == 4 for scale in scoring_input.scales)
    assert all(value in range(1, 6) for scale in scoring_input.scales for value in scale.values)
    assert {row.raw for row in scoring_input.overall_rows} == set(range(1, 21))

    with pytest.raises(ApiError, match="reference_unavailable"):
        repository.require_reference_set(db, "RS-TP-S-DOES-NOT-EXIST")


def test_score_runs_transition_and_allow_multiple_runtime_rows(seeded_db_session) -> None:
    db = seeded_db_session
    repository = ScoringRepository()
    session = _seeded_completed_session(db)
    reference = repository.get_reference_set(db, "RS-TP-S-01")
    computed_at = datetime(2026, 8, 10, 22, 0, tzinfo=timezone.utc)
    raw = {"scales": [{"label": "Intereses", "raw": 14}], "overall": {"raw": 11}}

    first = repository.create_score_run(db, session_id=session.id, reference_set_id=reference.id)
    second = repository.create_score_run(db, session_id=session.id, reference_set_id=reference.id)

    assert first.status == "pending"
    assert first.synthetic is False
    assert first.source == "runtime"
    assert second.id != first.id

    repository.complete_score_run(db, first, raw=raw, computed_at=computed_at)
    db.commit()

    persisted = list(
        db.scalars(
            select(ScoreRun)
            .where(ScoreRun.session_id == session.id)
            .order_by(ScoreRun.id)
        ).all()
    )
    assert len(persisted) == 2
    completed = next(row for row in persisted if row.id == first.id)
    pending = next(row for row in persisted if row.id == second.id)
    assert completed.status == "completed"
    assert completed.raw == raw
    assert completed.computed_at == computed_at
    assert pending.status == "pending"
    assert repository.latest_completed_run(db, session.id).id == first.id

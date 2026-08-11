"""Pure recommendation-domain contracts for F5."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.core.errors import CONFLICT, INTERNAL_ERROR, NOT_FOUND
from app.modules.recommendation.domain import (
    RecommendationIntegrityError,
    RecommendationProgram,
    RecommendationRule,
    RecommendationRunResult,
    evaluate_recommendations,
)
from app.modules.recommendation.errors import (
    recommendation_integrity_error,
    resource_not_found,
    session_not_completed,
)


EXACT_SCALES = (
    "Intereses",
    "Aptitud verbal",
    "Aptitud numérica",
    "Razonamiento abstracto",
    "Valores/preferencias",
    "overall",
)


def _run(**percentiles: int) -> RecommendationRunResult:
    return RecommendationRunResult(percentiles)


def _program(program_id: str = "program-1", name: str = "Programa Uno") -> RecommendationProgram:
    return RecommendationProgram(program_id, name, "P1")


def _rule(
    rule_id: int,
    program_id: str = "program-1",
    *,
    scale: str = "Aptitud numérica",
    minimum: int = 60,
    weight: object = ...,
    rule_type: str = "percentile_min",
) -> RecommendationRule:
    params: dict[str, object] = {"scale": scale, "min_percentile": minimum}
    if weight is not ...:
        params["weight"] = weight
    return RecommendationRule(rule_id, program_id, rule_type, params)


def test_recommendation_error_factories_keep_stable_tokens() -> None:
    assert recommendation_integrity_error().code == INTERNAL_ERROR
    assert recommendation_integrity_error().message == "recommendation_integrity_error"
    assert resource_not_found().code == NOT_FOUND
    assert resource_not_found().message == "resource_not_found"
    assert session_not_completed().code == CONFLICT
    assert session_not_completed().message == "session_not_completed"
    assert recommendation_integrity_error({"path": "rule.params"}).details == {
        "path": "rule.params"
    }


def test_closed_vocabulary_accepts_only_the_pinned_scale_labels() -> None:
    program = _program()
    rules = tuple(
        _rule(index + 1, scale=scale)
        for index, scale in enumerate(EXACT_SCALES)
    )

    result = evaluate_recommendations(
        _run(**{scale: 60 for scale in EXACT_SCALES}),
        (program,),
        rules,
    )

    assert len(result) == 1
    assert len(result[0].rule_results) == len(EXACT_SCALES)
    assert all(rule_result.satisfied for rule_result in result[0].rule_results)


@pytest.mark.parametrize(
    ("rule", "match"),
    [
        (_rule(1, rule_type="percentile_max"), "rule_type"),
        (RecommendationRule(1, "program-1", [], {"scale": "Intereses", "min_percentile": 50}), "rule_type"),
        (_rule(1, scale="Unknown scale"), "scale"),
        (
            RecommendationRule(
                1,
                "program-1",
                "percentile_min",
                {"scale": [], "min_percentile": 50},
            ),
            "scale",
        ),
        (
            RecommendationRule(1, "program-1", "percentile_min", {"scale": "Intereses"}),
            "min_percentile",
        ),
        (_rule(1, minimum=0), "min_percentile"),
        (_rule(1, minimum=100), "min_percentile"),
        (_rule(1, weight=0), "weight"),
        (_rule(1, weight=-1), "weight"),
        (
            RecommendationRule(
                1,
                "program-1",
                "percentile_min",
                {"scale": "Intereses", "min_percentile": 50, "extra": 1},
            ),
            "params",
        ),
        (RecommendationRule(1, "program-1", "percentile_min", None), "params"),
    ],
)
def test_invalid_active_rule_is_a_typed_integrity_failure(
    rule: RecommendationRule, match: str
) -> None:
    with pytest.raises(RecommendationIntegrityError, match=match):
        evaluate_recommendations(
            _run(**{"Intereses": 75, "Aptitud numérica": 75}),
            (_program(),),
            (rule,),
        )


def test_missing_weight_defaults_to_one() -> None:
    result = evaluate_recommendations(
        _run(**{"Aptitud numérica": 75}),
        (_program(),),
        (_rule(1),),
    )

    assert result[0].rule_results[0].weight == Decimal("1.0")


def test_weighted_fit_rounds_each_contribution_and_keeps_unsatisfied_at_zero() -> None:
    result = evaluate_recommendations(
        _run(**{"Aptitud numérica": 72}),
        (_program(),),
        (
            _rule(1, minimum=60, weight=1),
            _rule(2, minimum=80, weight=2),
        ),
    )

    recommendation = result[0]
    assert [rule_result.fit_score for rule_result in recommendation.rule_results] == [
        Decimal("33.33"),
        Decimal("0.00"),
    ]
    assert recommendation.fit_score == Decimal("33.33")
    assert recommendation.justification == (
        "Aptitud numérica >= 60 pct: cumple (72 pct); "
        "Aptitud numérica >= 80 pct: no cumple (72 pct)"
    )


def test_satisfied_weight_vector_rounds_to_33_33_plus_66_67() -> None:
    result = evaluate_recommendations(
        _run(**{"Aptitud numérica": 90}),
        (_program(),),
        (
            _rule(1, minimum=60, weight=1),
            _rule(2, minimum=80, weight=2),
        ),
    )

    assert [rule_result.fit_score for rule_result in result[0].rule_results] == [
        Decimal("33.33"),
        Decimal("66.67"),
    ]
    assert result[0].fit_score == Decimal("100.00")


def test_zero_rule_programs_are_excluded_and_results_order_by_fit_then_name() -> None:
    programs = (
        _program("program-z", "Zulu"),
        _program("program-a", "Alpha"),
        _program("program-empty", "Empty"),
    )
    rules = (
        _rule(1, "program-z", minimum=60),
        _rule(2, "program-a", minimum=90),
    )

    result = evaluate_recommendations(
        _run(**{"Aptitud numérica": 99}),
        programs,
        rules,
    )

    assert [(item.program_name, item.fit_score) for item in result] == [
        ("Alpha", Decimal("100.00")),
        ("Zulu", Decimal("100.00")),
    ]
    assert "Empty" not in {item.program_name for item in result}


def test_threshold_is_inclusive_trace_is_rule_id_ordered_and_domain_is_pure() -> None:
    run = _run(**{"Intereses": 50, "Aptitud numérica": 75})
    program = _program()
    rules = (
        _rule(2, scale="Intereses", minimum=60),
        _rule(1, scale="Aptitud numérica", minimum=75),
    )
    before = copy.deepcopy((run, program, rules))

    first = evaluate_recommendations(run, (program,), rules)
    second = evaluate_recommendations(run, (program,), rules)

    assert first == second
    assert (run, program, rules) == before
    assert [item.rule_id for item in first[0].rule_results] == [1, 2]
    assert first[0].rule_results[0].satisfied is True
    assert first[0].rule_results[1].satisfied is False
    assert first[0].justification == (
        "Aptitud numérica >= 75 pct: cumple (75 pct); "
        "Intereses >= 60 pct: no cumple (50 pct)"
    )

    with pytest.raises(FrozenInstanceError):
        program.name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first[0].fit_score = Decimal("0.00")  # type: ignore[misc]

    import app.modules.recommendation.domain as domain

    imported = {
        getattr(value, "__name__", "").split(".", 1)[0]
        for value in vars(domain).values()
    }
    assert imported.isdisjoint({"sqlalchemy", "psycopg", "pathlib", "datetime", "time", "random"})

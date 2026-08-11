"""Pure scoring-engine contracts for F4."""

from __future__ import annotations

import copy
import math
from dataclasses import FrozenInstanceError

import pytest

from app.modules.scoring.domain import (
    OverallReference,
    ScaleInput,
    ScaleReference,
    ScoringInput,
    ScoringIntegrityError,
    normal_cdf,
    round_half_up,
    score,
)


def _rows(missing: set[int] | None = None, special: OverallReference | None = None):
    missing = missing or set()
    return tuple(
        special
        if special is not None and raw == special.raw
        else OverallReference(raw, raw * 5, raw + 40, min(7, max(1, math.ceil(raw * 7 / 20))))
        for raw in range(1, 21)
        if raw not in missing
    )


def _input(scales, rows=None, refs=()):
    return ScoringInput("version-1", "RS-TP-S-01", tuple(scales), rows or _rows(), refs)


def test_scale_raw_direct_and_transformed_chain() -> None:
    scale = score(_input((ScaleInput("Intereses", (3, 3, 4, 4), 12, 2),))).scales[0]
    assert (scale.label, scale.raw) == ("Intereses", 14)
    assert scale.direct.z == pytest.approx(1.0, abs=1e-12)
    assert (scale.transformed.percentile, scale.transformed.t_score) == (84, 60)
    assert scale.transformed.eneatype == 6


def test_zero_variance_and_transformed_bounds() -> None:
    neutral = score(_input((ScaleInput("Cero", (3, 3, 3, 3), 12, 0),))).scales[0]
    low = score(_input((ScaleInput("Low", (1, 1, 1, 1), 24, 1),))).scales[0]
    high = score(_input((ScaleInput("High", (5, 5, 5, 5), 0, 1),))).scales[0]
    assert (neutral.direct.z, neutral.transformed.percentile, neutral.transformed.t_score) == (0, 50, 50)
    assert neutral.transformed.eneatype == 4
    assert (low.transformed.percentile, low.transformed.eneatype) == (1, 1)
    assert (high.transformed.percentile, high.transformed.eneatype) == (99, 7)


@pytest.mark.parametrize(
    ("z", "expected"),
    [(-2.0, 0.02275013194817921), (-1.0, 0.15865525393145707), (0.0, 0.5),
     (1.0, 0.8413447460685429), (2.0, 0.9772498680518208)],
)
def test_normal_cdf_matches_double_precision_vectors(z: float, expected: float) -> None:
    assert normal_cdf(z) == pytest.approx(expected, abs=1e-12)


def test_half_up_ties_and_overall_rescale_lookup_and_bounds() -> None:
    assert (round_half_up(50.5), round_half_up(-1.5)) == (51, -1)
    five = tuple(ScaleInput(f"S{index}", (3, 3, 3, 3), 12, 2) for index in range(5))
    row = OverallReference(11, 73, 57, 6)
    result = score(_input(five, _rows(special=row)))
    assert (result.overall.raw, result.overall.transformed.percentile) == (11, 73)
    assert (result.overall.transformed.t_score, result.overall.transformed.eneatype) == (57, 6)
    assert score(_input(tuple(ScaleInput(f"S{i}", (1, 1, 1, 1), 12, 2) for i in range(5)))).overall.raw == 1
    assert score(_input(tuple(ScaleInput(f"S{i}", (5, 5, 5, 5), 12, 2) for i in range(5)))).overall.raw == 20


def test_missing_overall_row_and_unknown_scale_label_raise_typed_errors() -> None:
    five = tuple(ScaleInput(f"S{index}", (3, 3, 3, 3), 12, 2) for index in range(5))
    with pytest.raises(ScoringIntegrityError, match="overall.*11"):
        score(_input(five, _rows({11})))
    with pytest.raises(ScoringIntegrityError, match="scale label"):
        score(_input((ScaleInput("Unknown", (3, 3, 4, 4)),), refs=(ScaleReference("Known", 12, 2),)))


@pytest.mark.parametrize(
    "scale",
    [ScaleInput("Missing", (3, 3, 3, 3), None, 2), ScaleInput("NaN", (3, 3, 3, 3), math.nan, 2),
     ScaleInput("Infinite", (3, 3, 3, 3), 12, math.inf), ScaleInput("Value", (3, 3, 3, math.nan), 12, 2)],
)
def test_missing_or_non_finite_inputs_raise_typed_errors(scale: ScaleInput) -> None:
    with pytest.raises(ScoringIntegrityError):
        score(_input((scale,)))


def test_score_is_deterministic_immutable_and_free_of_db_io_clock_imports() -> None:
    data = _input((ScaleInput("Stable", (3, 3, 4, 4), 12, 2), ScaleInput("Stable 2", (2, 3, 4, 5), 14, 2)))
    before = copy.deepcopy(data)
    first, second = score(data), score(data)
    assert first == second and data == before
    with pytest.raises(FrozenInstanceError):
        data.version_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.scales[0].label = "changed"  # type: ignore[misc]
    import app.modules.scoring.domain as domain
    imported = {getattr(value, "__name__", "").split(".", 1)[0] for value in vars(domain).values()}
    assert imported.isdisjoint({"sqlalchemy", "psycopg", "pathlib", "datetime", "time", "random"})

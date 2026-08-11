"""Pure scoring calculations for the F4 scoring engine.

Database rows and response option ids are adapted into these plain, frozen
inputs by later layers. This module imports only the standard library and has
no I/O, clock, random, or database access.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class ScoringIntegrityError(ValueError):
    """A typed failure caused by incomplete or invalid scoring inputs."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        self.message = message
        self.path = path
        self.errors = (
            [{"path": path, "message": message}] if path else [{"message": message}]
        )
        super().__init__(f"{path}: {message}" if path else message)


@dataclass(frozen=True)
class ScaleReference:
    """Reference mean and standard deviation joined by an exact label."""

    label: str
    mean: float | None
    sd: float | None


@dataclass(frozen=True)
class ScaleInput:
    """One scale's four already-mapped Likert values and statistics."""

    label: str
    values: tuple[Any, ...]
    mean: float | None = None
    sd: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.values, tuple):
            object.__setattr__(self, "values", tuple(self.values))


@dataclass(frozen=True)
class OverallReference:
    """One exact overall-raw lookup row."""

    raw: int
    percentile: int
    t_score: int
    eneatype: int


@dataclass(frozen=True)
class ScoringInput:
    """Immutable data boundary for one deterministic scoring run."""

    version_id: Any
    reference_set_id: Any
    scales: tuple[ScaleInput, ...]
    overall_rows: Any
    scale_references: tuple[ScaleReference, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scales, tuple):
            object.__setattr__(self, "scales", tuple(self.scales))
        if self.scale_references and not isinstance(self.scale_references, tuple):
            object.__setattr__(self, "scale_references", tuple(self.scale_references))


@dataclass(frozen=True)
class DirectScore:
    z: float


@dataclass(frozen=True)
class TransformedScore:
    percentile: int
    t_score: int
    eneatype: int


@dataclass(frozen=True)
class ScaleScore:
    label: str
    raw: int
    direct: DirectScore
    transformed: TransformedScore


@dataclass(frozen=True)
class OverallScore:
    raw: int
    transformed: TransformedScore


@dataclass(frozen=True)
class ScoreResult:
    scales: tuple[ScaleScore, ...]
    overall: OverallScore


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScoringIntegrityError(f"{name} must be a finite number", path=name)
    result = float(value)
    if not math.isfinite(result):
        raise ScoringIntegrityError(f"{name} must be a finite number", path=name)
    return result


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScoringIntegrityError(f"{name} must be an integer", path=name)
    return value


def round_half_up(value: float) -> int:
    """Round using the ratified ``RH(x) = floor(x + 0.5)`` rule."""

    return math.floor(_finite(value, "value") + 0.5)


def normal_cdf(z: float) -> float:
    """Return Φ(z) with deterministic IEEE-754 double precision."""

    value = _finite(z, "z")
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _transformed(z: float) -> TransformedScore:
    percentile = max(1, min(99, round_half_up(100.0 * normal_cdf(z))))
    t_score = round_half_up(50.0 + 10.0 * z)
    eneatype = max(1, min(7, math.ceil(7.0 * percentile / 100.0)))
    return TransformedScore(percentile, t_score, eneatype)


def _reference_map(
    references: tuple[ScaleReference, ...],
) -> dict[str, ScaleReference]:
    result: dict[str, ScaleReference] = {}
    for reference in references:
        if not isinstance(reference.label, str) or not reference.label:
            raise ScoringIntegrityError("scale reference label must be non-empty")
        if reference.label in result:
            raise ScoringIntegrityError(
                f"duplicate scale reference label: {reference.label!r}"
            )
        result[reference.label] = reference
    return result


def _row_field(row: Any, name: str, *aliases: str, default: Any = None) -> Any:
    for key in (name, *aliases):
        if isinstance(row, Mapping) and key in row:
            return row[key]
        if not isinstance(row, Mapping) and hasattr(row, key):
            return getattr(row, key)
    return default


def _overall_map(rows: Any) -> dict[int, OverallReference]:
    if rows is None:
        raise ScoringIntegrityError("overall reference rows are required", path="overall_rows")
    entries = rows.items() if isinstance(rows, Mapping) else rows
    result: dict[int, OverallReference] = {}
    try:
        iterator = iter(entries)
    except TypeError as error:
        raise ScoringIntegrityError("overall reference rows must be iterable") from error
    for entry in iterator:
        key = None
        if isinstance(rows, Mapping):
            key, row = entry
        else:
            row = entry
        raw = _integer(_row_field(row, "raw", "raw_value", default=key), "overall.raw")
        if raw < 1 or raw > 20:
            raise ScoringIntegrityError("overall raw lookup must be between 1 and 20")
        if raw in result:
            raise ScoringIntegrityError(f"duplicate overall raw lookup: {raw}")
        result[raw] = OverallReference(
            raw,
            _integer(_row_field(row, "percentile"), "overall.percentile"),
            _integer(
                _row_field(row, "t_score", "transformed_value"), "overall.t_score"
            ),
            _integer(_row_field(row, "eneatype"), "overall.eneatype"),
        )
    return result


def score(scoring_input: ScoringInput) -> ScoreResult:
    """Compute raw, direct, and transformed scores without side effects."""

    if scoring_input.version_id is None:
        raise ScoringIntegrityError("missing version_id", path="version_id")
    if scoring_input.reference_set_id is None:
        raise ScoringIntegrityError("missing reference_set_id", path="reference_set_id")
    if not scoring_input.scales:
        raise ScoringIntegrityError("at least one scale is required", path="scales")

    references = _reference_map(scoring_input.scale_references)
    overall_rows = _overall_map(scoring_input.overall_rows)
    scale_results: list[ScaleScore] = []
    labels: set[str] = set()
    raw_total = 0

    for index, scale in enumerate(scoring_input.scales):
        if not isinstance(scale.label, str) or not scale.label.strip():
            raise ScoringIntegrityError(
                "scale label must be non-empty", path=f"scales[{index}].label"
            )
        if scale.label in labels:
            raise ScoringIntegrityError(
                f"duplicate scale label: {scale.label!r}",
                path=f"scales[{index}].label",
            )
        labels.add(scale.label)
        if references and scale.label not in references:
            raise ScoringIntegrityError(
                f"unknown scale label: {scale.label!r}",
                path=f"scales[{index}].label",
            )
        values = tuple(scale.values)
        if len(values) != 4:
            raise ScoringIntegrityError(
                "each scale requires exactly four values", path=f"scales[{index}].values"
            )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5
            for value in values
        ):
            raise ScoringIntegrityError(
                "mapped values must be integers between 1 and 5",
                path=f"scales[{index}].values",
            )
        reference = references.get(scale.label)
        mean = reference.mean if reference else scale.mean
        sd = reference.sd if reference else scale.sd
        mean_value = _finite(mean, f"scales[{index}].mean")
        sd_value = _finite(sd, f"scales[{index}].sd")
        if sd_value < 0:
            raise ScoringIntegrityError(
                "standard deviation must not be negative", path=f"scales[{index}].sd"
            )
        raw = sum(values)
        z = 0.0 if sd_value == 0 else _finite((raw - mean_value) / sd_value, "z")
        scale_results.append(
            ScaleScore(scale.label, raw, DirectScore(z), _transformed(z))
        )
        raw_total += raw

    count = len(scale_results)
    overall_raw = round_half_up(1.0 + 19.0 * (raw_total - 4 * count) / (16 * count))
    try:
        reference = overall_rows[overall_raw]
    except KeyError as error:
        raise ScoringIntegrityError(
            f"missing overall reference row for raw {overall_raw}",
            path="overall_rows",
        ) from error
    transformed = TransformedScore(
        reference.percentile, reference.t_score, reference.eneatype
    )
    return ScoreResult(tuple(scale_results), OverallScore(overall_raw, transformed))

"""Pure, deterministic rule evaluation for F5 recommendations.

Database rows are adapted into the frozen snapshots below by the repository.
This module deliberately imports only the standard library: it performs no
database access, I/O, clock reads, random work, or API error mapping.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


RULE_TYPES = frozenset({"percentile_min"})
SUPPORTED_SCALES = frozenset(
    {
        "Intereses",
        "Aptitud verbal",
        "Aptitud numérica",
        "Razonamiento abstracto",
        "Valores/preferencias",
        "overall",
    }
)
_RULE_PARAMS = frozenset({"scale", "min_percentile", "weight"})
_MISSING = object()
_CENT = Decimal("0.01")
_ZERO = Decimal("0.00")


class RecommendationIntegrityError(ValueError):
    """A typed failure caused by incomplete or invalid recommendation inputs."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        self.message = message
        self.path = path
        self.errors = (
            [{"path": path, "message": message}] if path else [{"message": message}]
        )
        super().__init__(f"{path}: {message}" if path else message)


@dataclass(frozen=True)
class RecommendationRule:
    """One declarative rule snapshot detached from SQLAlchemy."""

    id: Any
    program_id: Any
    rule_type: str
    params: Mapping[str, Any] | None
    is_active: bool = True


@dataclass(frozen=True)
class RecommendationRunResult:
    """Percentiles from one completed scoring run."""

    percentiles: Mapping[str, Any]


@dataclass(frozen=True)
class RecommendationProgram:
    """Program identity needed for one recommendation result."""

    id: Any
    name: str
    code: str | None = None


@dataclass(frozen=True)
class RecommendationRuleResult:
    """One rounded per-rule contribution and its explainable trace sentence."""

    rule_id: Any
    program_id: Any
    percentile: int
    min_percentile: int
    weight: Decimal
    satisfied: bool
    fit_score: Decimal
    justification: str

    @property
    def contribution(self) -> Decimal:
        """Expose the contribution vocabulary used by the domain contract."""

        return self.fit_score


@dataclass(frozen=True)
class RecommendationResult:
    """Aggregate fit plus the ordered internal rule trace for one program."""

    program_id: Any
    program_name: str
    program_code: str | None
    fit_score: Decimal
    justification: str
    rule_results: tuple[RecommendationRuleResult, ...]

    @property
    def contributions(self) -> tuple[RecommendationRuleResult, ...]:
        """Return the per-rule rows without exposing mutable state."""

        return self.rule_results


# Names used by adapters can remain explicit without creating a second model.
RuleSnapshot = RecommendationRule
ProgramSnapshot = RecommendationProgram
ScoreRunResult = RecommendationRunResult
ProgramRecommendation = RecommendationResult


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _required(source: Any, name: str, path: str) -> Any:
    value = _value(source, name, _MISSING)
    if value is _MISSING or value is None:
        raise RecommendationIntegrityError("field is required", path=path)
    return value


def _stable_id(value: Any, path: str) -> tuple[int, Any]:
    if value is None:
        raise RecommendationIntegrityError("field is required", path=path)
    if isinstance(value, bool):
        return (1, str(value))
    if isinstance(value, (int, float, Decimal)):
        return (0, value)
    return (1, str(value))


def _program_snapshot(program: Any, index: int) -> RecommendationProgram:
    if isinstance(program, RecommendationProgram):
        return program
    return RecommendationProgram(
        id=_required(program, "id", f"programs[{index}].id"),
        name=_required(program, "name", f"programs[{index}].name"),
        code=_value(program, "code"),
    )


def _rule_snapshot(rule: Any, index: int) -> RecommendationRule:
    if isinstance(rule, RecommendationRule):
        return rule
    return RecommendationRule(
        id=_required(rule, "id", f"rules[{index}].id"),
        program_id=_required(rule, "program_id", f"rules[{index}].program_id"),
        rule_type=_required(rule, "rule_type", f"rules[{index}].rule_type"),
        params=_value(rule, "params"),
        is_active=_value(rule, "is_active", True),
    )


def _decimal_weight(value: Any, path: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise RecommendationIntegrityError("weight must be a positive number", path=path)
    try:
        weight = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise RecommendationIntegrityError("weight must be a positive number", path=path) from error
    if not weight.is_finite() or weight <= 0:
        raise RecommendationIntegrityError("weight must be positive", path=path)
    return weight


def _round_fit(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _validated_rule(rule: RecommendationRule, index: int) -> tuple[Any, str, int, Decimal]:
    path = f"rules[{index}]"
    if not isinstance(rule.rule_type, str) or rule.rule_type not in RULE_TYPES:
        raise RecommendationIntegrityError(
            "rule_type must be percentile_min", path=f"{path}.rule_type"
        )
    if not isinstance(rule.params, Mapping):
        raise RecommendationIntegrityError("params must be an object", path=f"{path}.params")

    unknown = set(rule.params) - _RULE_PARAMS
    if unknown:
        raise RecommendationIntegrityError(
            f"unknown params: {sorted(map(str, unknown))}", path=f"{path}.params"
        )

    scale = rule.params.get("scale")
    if not isinstance(scale, str) or scale not in SUPPORTED_SCALES:
        raise RecommendationIntegrityError(
            "scale is not supported", path=f"{path}.params.scale"
        )

    minimum = rule.params.get("min_percentile")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or not 1 <= minimum <= 99:
        raise RecommendationIntegrityError(
            "min_percentile must be an integer between 1 and 99",
            path=f"{path}.params.min_percentile",
        )

    weight = _decimal_weight(rule.params.get("weight", 1.0), f"{path}.params.weight")
    return rule.id, scale, minimum, weight


def _percentile_value(value: Any, path: str) -> int:
    candidate = value
    if isinstance(value, (int, Decimal)) and not isinstance(value, bool):
        candidate = value
    elif isinstance(value, Mapping):
        transformed = value.get("transformed", _MISSING)
        candidate = value.get("percentile", transformed)
        if isinstance(candidate, Mapping):
            candidate = candidate.get("percentile")
    else:
        transformed = getattr(value, "transformed", _MISSING)
        candidate = getattr(value, "percentile", transformed)
        if not isinstance(candidate, (int, float, Decimal)) and transformed is not _MISSING:
            candidate = getattr(transformed, "percentile", None)
    if isinstance(candidate, bool) or not isinstance(candidate, int):
        raise RecommendationIntegrityError("percentile must be an integer", path=path)
    return candidate


def _percentiles(run: RecommendationRunResult | Mapping[str, Any] | Any) -> dict[str, int]:
    source = _value(run, "percentiles", _MISSING)
    if source is _MISSING:
        source = run
    if not isinstance(source, Mapping):
        raise RecommendationIntegrityError("percentiles must be an object", path="percentiles")

    result: dict[str, int] = {}
    raw_scales = source.get("scales")
    if raw_scales is not None:
        if not isinstance(raw_scales, Iterable) or isinstance(raw_scales, (str, bytes)):
            raise RecommendationIntegrityError("scales must be iterable", path="percentiles.scales")
        for index, raw_scale in enumerate(raw_scales):
            label = _value(raw_scale, "label", _value(raw_scale, "scale", _MISSING))
            if label is _MISSING or not isinstance(label, str):
                raise RecommendationIntegrityError(
                    "scale label is required", path=f"percentiles.scales[{index}].label"
                )
            result[label] = _percentile_value(raw_scale, f"percentiles.scales[{index}]")
    raw_overall = source.get("overall", _MISSING)
    if raw_overall is not _MISSING:
        result["overall"] = _percentile_value(raw_overall, "percentiles.overall")

    if raw_scales is None:
        for label, value in source.items():
            if label == "overall":
                continue
            result[label] = _percentile_value(value, f"percentiles.{label}")
    return result


def _rule_sort_key(rule_result: RecommendationRuleResult) -> tuple[int, Any]:
    return _stable_id(rule_result.rule_id, "rule.id")


def evaluate_recommendations(
    run: RecommendationRunResult | Mapping[str, Any] | Any,
    programs: Iterable[RecommendationProgram | Mapping[str, Any] | Any],
    rules: Iterable[RecommendationRule | Mapping[str, Any] | Any],
) -> tuple[RecommendationResult, ...]:
    """Evaluate active rules into deterministic, rounded program results."""

    percentiles = _percentiles(run)
    program_snapshots = tuple(_program_snapshot(program, index) for index, program in enumerate(programs))
    programs_by_id: dict[Any, RecommendationProgram] = {}
    for index, program in enumerate(program_snapshots):
        if program.id in programs_by_id:
            raise RecommendationIntegrityError(
                "program id must be unique", path=f"programs[{index}].id"
            )
        programs_by_id[program.id] = program

    grouped: dict[Any, list[tuple[RecommendationRule, str, int, Decimal]]] = {}
    for index, raw_rule in enumerate(rules):
        rule = _rule_snapshot(raw_rule, index)
        if not rule.is_active:
            continue
        if rule.program_id not in programs_by_id:
            raise RecommendationIntegrityError(
                "rule references an unknown program", path=f"rules[{index}].program_id"
            )
        rule_id, scale, minimum, weight = _validated_rule(rule, index)
        grouped.setdefault(rule.program_id, []).append((rule, scale, minimum, weight))

    results: list[RecommendationResult] = []
    for program in program_snapshots:
        active_rules = grouped.get(program.id, [])
        if not active_rules:
            continue
        total_weight = sum((entry[3] for entry in active_rules), _ZERO)
        rule_results: list[RecommendationRuleResult] = []
        for rule, scale, minimum, weight in active_rules:
            try:
                percentile = percentiles[scale]
            except KeyError as error:
                raise RecommendationIntegrityError(
                    "percentile is missing for rule scale",
                    path=f"rule[{rule.id}].params.scale",
                ) from error
            satisfied = percentile >= minimum
            raw_contribution = Decimal("100") * weight / total_weight if satisfied else _ZERO
            contribution = _round_fit(raw_contribution)
            outcome = "cumple" if satisfied else "no cumple"
            justification = f"{scale} >= {minimum} pct: {outcome} ({percentile} pct)"
            rule_results.append(
                RecommendationRuleResult(
                    rule_id=rule.id,
                    program_id=rule.program_id,
                    percentile=percentile,
                    min_percentile=minimum,
                    weight=weight,
                    satisfied=satisfied,
                    fit_score=contribution,
                    justification=justification,
                )
            )

        ordered_rules = tuple(sorted(rule_results, key=_rule_sort_key))
        fit_score = _round_fit(sum((item.fit_score for item in ordered_rules), _ZERO))
        results.append(
            RecommendationResult(
                program_id=program.id,
                program_name=program.name,
                program_code=program.code,
                fit_score=fit_score,
                justification="; ".join(item.justification for item in ordered_rules),
                rule_results=ordered_rules,
            )
        )

    return tuple(
        sorted(
            results,
            key=lambda item: (-item.fit_score, item.program_name, str(item.program_id)),
        )
    )


# A concise name is useful to repository/service adapters and preserves one
# implementation of the contract.
recommend = evaluate_recommendations
compute_recommendations = evaluate_recommendations

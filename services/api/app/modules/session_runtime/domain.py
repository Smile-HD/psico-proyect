"""Pure lifecycle and response-validation rules for evaluation sessions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

IN_PROGRESS = "in_progress"
COMPLETED = "completed"
RESERVED_STATES = frozenset({"blocked", "cancelled"})


def transition(current: str, target: str) -> str:
    """Return the target only for the single reachable F3 transition."""
    if current == IN_PROGRESS and target == COMPLETED:
        return target
    raise ValueError(f"invalid session transition: {current!r} -> {target!r}")


def required_missing(required_ids: Iterable[Any], answered_ids: Iterable[Any]) -> list[Any]:
    """Return unanswered required ids in their original catalog order."""
    answered = set(answered_ids)
    return [item_id for item_id in required_ids if item_id not in answered]


def map_option_id(option_id: Any, option_values: Mapping[Any, Any]) -> int:
    """Map a stable option id to its private 1–5 value."""
    try:
        value = option_values[option_id]
    except KeyError as error:
        raise ValueError("unknown response option") from error
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ValueError("response option value must be between 1 and 5")
    return value


def validate_batch(
    pairs: Iterable[Any], allowed_options: Mapping[Any, Mapping[Any, Any]]
) -> dict[Any, int]:
    """Validate every item/option pair before returning private numeric values."""
    mapped: dict[Any, int] = {}
    for pair in pairs:
        if isinstance(pair, Mapping):
            item_id = pair.get("item_id")
            option_id = pair.get("response_option_id", pair.get("option_id"))
        else:
            try:
                item_id, option_id = pair
            except (TypeError, ValueError) as error:
                raise ValueError("invalid response pair") from error
        if item_id not in allowed_options:
            raise ValueError("item does not belong to the pinned version")
        if item_id in mapped:
            raise ValueError("duplicate response item")
        mapped[item_id] = map_option_id(option_id, allowed_options[item_id])
    return mapped


option_id_to_value = map_option_id
option_value = map_option_id

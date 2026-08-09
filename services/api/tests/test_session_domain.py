"""Pure session-runtime domain contracts."""

from __future__ import annotations

import uuid

import pytest

from app.modules.session_runtime.domain import (
    COMPLETED,
    IN_PROGRESS,
    map_option_id,
    required_missing,
    transition,
    validate_batch,
)


def test_transition_allows_only_in_progress_to_completed() -> None:
    assert transition(IN_PROGRESS, COMPLETED) == COMPLETED

    with pytest.raises(ValueError, match="invalid session transition"):
        transition(COMPLETED, IN_PROGRESS)


def test_reserved_states_and_self_transitions_are_rejected() -> None:
    for current, target in (
        ("blocked", COMPLETED),
        ("cancelled", COMPLETED),
        (IN_PROGRESS, IN_PROGRESS),
        (COMPLETED, COMPLETED),
    ):
        with pytest.raises(ValueError, match="invalid session transition"):
            transition(current, target)


def test_required_missing_preserves_required_order() -> None:
    first, second, third = (uuid.uuid4() for _ in range(3))
    assert required_missing([first, second, third], {first, third}) == [second]


def test_validate_batch_maps_option_ids_and_rejects_foreign_items() -> None:
    item_id = uuid.uuid4()
    option_a, option_b = uuid.uuid4(), uuid.uuid4()
    allowed = {item_id: {option_a: 1, option_b: 5}}

    assert validate_batch([(item_id, option_b)], allowed) == {item_id: 5}

    with pytest.raises(ValueError, match="does not belong"):
        validate_batch([(uuid.uuid4(), option_a)], allowed)


def test_map_option_id_rejects_unknown_options_and_non_likert_values() -> None:
    option_id = uuid.uuid4()
    assert map_option_id(option_id, {option_id: 3}) == 3

    with pytest.raises(ValueError, match="unknown response option"):
        map_option_id(uuid.uuid4(), {option_id: 3})
    with pytest.raises(ValueError, match="between 1 and 5"):
        map_option_id(option_id, {option_id: 6})

"""Pure domain validation for the F2 catalog aggregate."""

from __future__ import annotations

import uuid

import pytest

from app.modules.assessment_authoring.domain import (
    ARCHIVED,
    DRAFT,
    PUBLISHED,
    CatalogValidationError,
    clone_hierarchy,
    validate_hierarchy,
)


def _option(order: int, label: str | None = None) -> dict:
    return {"display_order": order, "label": label or f"Opción {order}", "locale": "es"}


def _item(order: int = 1, options: list[dict] | None = None) -> dict:
    return {
        "item_order": order,
        "text": f"Ítem sintético {order}",
        "locale": "es",
        "required": True,
        "options": options
        if options is not None
        else [_option(i) for i in range(1, 6)],
    }


def _aggregate(scales: list[dict] | None = None) -> dict:
    return {
        "response_type": "likert_1_5",
        "scales": scales
        if scales is not None
        else [
            {
                "display_order": 1,
                "label": "Intereses",
                "locale": "es",
                "items": [_item()],
            }
        ],
    }


def test_valid_hierarchy_is_accepted() -> None:
    result = validate_hierarchy(_aggregate())
    assert result.scale_count == 1
    assert result.item_count == 1
    assert result.option_count == 5


@pytest.mark.parametrize(
    ("mutator", "expected_path"),
    [
        (
            lambda aggregate: aggregate["scales"][0]["items"].__setitem__(0, _item(2)),
            "scales[0].items",
        ),
        (
            lambda aggregate: aggregate["scales"][0]["items"][0]["options"].__setitem__(
                4, _option(4)
            ),
            "scales[0].items[0].options",
        ),
        (
            lambda aggregate: aggregate["scales"][0]["items"][0]["options"].__setitem__(
                1, _option(1)
            ),
            "scales[0].items[0].options",
        ),
    ],
)
def test_invalid_order_or_duplicate_options_is_rejected(
    mutator, expected_path: str
) -> None:
    aggregate = _aggregate()
    mutator(aggregate)
    with pytest.raises(CatalogValidationError) as error:
        validate_hierarchy(aggregate)
    assert expected_path in str(error.value)


def test_empty_scale_and_unsupported_response_type_are_rejected() -> None:
    empty = _aggregate(
        [{"display_order": 1, "label": "Vacía", "locale": "es", "items": []}]
    )
    with pytest.raises(CatalogValidationError, match="items"):
        validate_hierarchy(empty)

    unsupported = _aggregate()
    unsupported["response_type"] = "semantic_differential"
    with pytest.raises(CatalogValidationError, match="response_type"):
        validate_hierarchy(unsupported)


def test_parent_membership_rejects_cross_version_ids() -> None:
    aggregate = _aggregate()
    version_id = uuid.uuid4()
    other_version_id = uuid.uuid4()
    scale_id = uuid.uuid4()
    aggregate["version_id"] = version_id
    aggregate["scales"][0]["id"] = scale_id
    aggregate["scales"][0]["version_id"] = other_version_id
    with pytest.raises(CatalogValidationError, match="version"):
        validate_hierarchy(aggregate, version_id=version_id)


def test_clone_hierarchy_gets_fresh_ids_and_preserves_content() -> None:
    source = _aggregate()
    source["scales"][0]["id"] = uuid.uuid4()
    source["scales"][0]["items"][0]["id"] = uuid.uuid4()
    source["scales"][0]["items"][0]["options"][0]["id"] = uuid.uuid4()
    cloned = clone_hierarchy(source)
    assert cloned["scales"][0]["id"] != source["scales"][0]["id"]
    assert (
        cloned["scales"][0]["items"][0]["id"] != source["scales"][0]["items"][0]["id"]
    )
    assert (
        cloned["scales"][0]["items"][0]["options"][0]["id"]
        != source["scales"][0]["items"][0]["options"][0]["id"]
    )
    assert (
        cloned["scales"][0]["items"][0]["text"]
        == source["scales"][0]["items"][0]["text"]
    )


def test_lifecycle_status_constants_are_constrained() -> None:
    assert (DRAFT, PUBLISHED, ARCHIVED) == ("draft", "published", "archived")

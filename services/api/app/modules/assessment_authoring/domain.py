"""Pure catalog aggregate rules and lifecycle helpers.

This module deliberately knows nothing about SQLAlchemy, HTTP, or audit.  The
service converts request DTOs to mappings and invokes these functions before it
mutates a database aggregate.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Mapping

DRAFT = "draft"
PUBLISHED = "published"
ARCHIVED = "archived"
STATUS_VALUES = frozenset({DRAFT, PUBLISHED, ARCHIVED})
SUPPORTED_RESPONSE_TYPE = "likert_1_5"
SUPPORTED_LOCALE = "es"
OPTION_ORDERS = frozenset(range(1, 6))


class CatalogValidationError(ValueError):
    """A safe, field-oriented catalog validation failure."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        self.message = message
        self.path = path
        self.errors = (
            [{"path": path, "message": message}] if path else [{"message": message}]
        )
        super().__init__(f"{path}: {message}" if path else message)


@dataclass(frozen=True)
class HierarchyCounts:
    scale_count: int
    item_count: int
    option_count: int


def _value(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _require(value: Any, key: str, path: str) -> Any:
    result = _value(value, key)
    if result is None:
        raise CatalogValidationError("field is required", path=path)
    return result


def _check_contiguous(values: list[int], path: str, label: str) -> None:
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in values
    ):
        raise CatalogValidationError(f"{label} orders must be positive", path=path)
    if len(set(values)) != len(values):
        raise CatalogValidationError(f"{label} orders must be unique", path=path)
    expected = set(range(1, len(values) + 1))
    if set(values) != expected:
        raise CatalogValidationError(
            f"{label} orders must be contiguous from 1", path=path
        )


def _check_locale(value: Any, path: str) -> None:
    if value != SUPPORTED_LOCALE:
        raise CatalogValidationError("locale must be es", path=path)


def validate_hierarchy(
    aggregate: Any,
    *,
    version_id: uuid.UUID | None = None,
) -> HierarchyCounts:
    """Validate a complete instrument-version hierarchy without side effects."""

    response_type = _require(aggregate, "response_type", "response_type")
    if response_type != SUPPORTED_RESPONSE_TYPE:
        raise CatalogValidationError("unsupported response_type", path="response_type")

    if version_id is not None and _value(aggregate, "version_id") not in (
        None,
        version_id,
    ):
        raise CatalogValidationError(
            "aggregate belongs to another version", path="version_id"
        )

    scales = list(_value(aggregate, "scales", []) or [])
    if not scales:
        raise CatalogValidationError("at least one scale is required", path="scales")
    _check_contiguous(
        [
            _require(scale, "display_order", f"scales[{index}].display_order")
            for index, scale in enumerate(scales)
        ],
        "scales",
        "scale",
    )

    total_items = 0
    total_options = 0
    seen_scale_ids: set[uuid.UUID] = set()
    for scale_index, scale in enumerate(scales):
        scale_path = f"scales[{scale_index}]"
        _check_locale(
            _require(scale, "locale", f"{scale_path}.locale"), f"{scale_path}.locale"
        )
        label = _require(scale, "label", f"{scale_path}.label")
        if not isinstance(label, str) or not label.strip():
            raise CatalogValidationError(
                "label must not be empty", path=f"{scale_path}.label"
            )

        scale_id = _value(scale, "id")
        if scale_id is not None:
            if scale_id in seen_scale_ids:
                raise CatalogValidationError(
                    "scale id must be unique", path=f"{scale_path}.id"
                )
            seen_scale_ids.add(scale_id)
        scale_version_id = _value(scale, "version_id")
        if version_id is not None and scale_version_id not in (None, version_id):
            raise CatalogValidationError(
                "scale belongs to another version", path=f"{scale_path}.version_id"
            )

        items = list(_value(scale, "items", []) or [])
        if not items:
            raise CatalogValidationError(
                "each scale requires at least one item", path=f"{scale_path}.items"
            )
        _check_contiguous(
            [
                _require(item, "item_order", f"{scale_path}.items[{index}].item_order")
                for index, item in enumerate(items)
            ],
            f"{scale_path}.items",
            "item",
        )
        seen_item_ids: set[uuid.UUID] = set()
        for item_index, item in enumerate(items):
            item_path = f"{scale_path}.items[{item_index}]"
            _check_locale(
                _require(item, "locale", f"{item_path}.locale"), f"{item_path}.locale"
            )
            text = _require(item, "text", f"{item_path}.text")
            if not isinstance(text, str) or not text.strip():
                raise CatalogValidationError(
                    "text must not be empty", path=f"{item_path}.text"
                )
            item_id = _value(item, "id")
            if item_id is not None:
                if item_id in seen_item_ids:
                    raise CatalogValidationError(
                        "item id must be unique within its scale",
                        path=f"{item_path}.id",
                    )
                seen_item_ids.add(item_id)
            item_version_id = _value(item, "version_id")
            if version_id is not None and item_version_id not in (None, version_id):
                raise CatalogValidationError(
                    "item belongs to another version", path=f"{item_path}.version_id"
                )
            if scale_id is not None and _value(item, "scale_id") not in (
                None,
                scale_id,
            ):
                raise CatalogValidationError(
                    "item belongs to another scale", path=f"{item_path}.scale_id"
                )

            options = list(
                _value(item, "options", _value(item, "response_options", [])) or []
            )
            if len(options) != 5:
                raise CatalogValidationError(
                    "each item requires exactly five options",
                    path=f"{item_path}.options",
                )
            _check_contiguous(
                [
                    _require(
                        option,
                        "display_order",
                        f"{item_path}.options[{index}].display_order",
                    )
                    for index, option in enumerate(options)
                ],
                f"{item_path}.options",
                "option",
            )
            for option_index, option in enumerate(options):
                option_path = f"{item_path}.options[{option_index}]"
                _check_locale(
                    _require(option, "locale", f"{option_path}.locale"),
                    f"{option_path}.locale",
                )
                label = _require(option, "label", f"{option_path}.label")
                if not isinstance(label, str) or not label.strip():
                    raise CatalogValidationError(
                        "label must not be empty", path=f"{option_path}.label"
                    )
                if (
                    _value(option, "value") is not None
                    and _value(option, "value") not in OPTION_ORDERS
                ):
                    raise CatalogValidationError(
                        "option value must be between 1 and 5",
                        path=f"{option_path}.value",
                    )
                if item_id is not None and _value(option, "item_id") not in (
                    None,
                    item_id,
                ):
                    raise CatalogValidationError(
                        "option belongs to another item", path=f"{option_path}.item_id"
                    )
            total_options += len(options)
        total_items += len(items)

    return HierarchyCounts(len(scales), total_items, total_options)


def validate_transition(current_status: str, target_status: str) -> None:
    """Enforce the only two lifecycle transitions."""

    if current_status == DRAFT and target_status == PUBLISHED:
        return
    if current_status == PUBLISHED and target_status == ARCHIVED:
        return
    raise CatalogValidationError(
        f"invalid transition from {current_status} to {target_status}", path="status"
    )


def clone_hierarchy(
    aggregate: Any,
    *,
    id_factory: Callable[[], uuid.UUID] = uuid.uuid4,
) -> dict[str, Any]:
    """Return a detached hierarchy with fresh ids and stable parent links."""

    source = copy.deepcopy(
        dict(aggregate) if isinstance(aggregate, Mapping) else aggregate.__dict__
    )
    source.pop("id", None)
    source.pop("version_id", None)
    cloned_scales: list[dict[str, Any]] = []
    for raw_scale in source.get("scales", []):
        scale = dict(raw_scale)
        scale_id = id_factory()
        scale["id"] = scale_id
        scale.pop("version_id", None)
        cloned_items: list[dict[str, Any]] = []
        for raw_item in scale.get("items", []):
            item = dict(raw_item)
            item_id = id_factory()
            item["id"] = item_id
            item["scale_id"] = scale_id
            item.pop("version_id", None)
            raw_options = item.pop("response_options", None)
            options = (
                raw_options if raw_options is not None else item.get("options", [])
            )
            cloned_options: list[dict[str, Any]] = []
            for raw_option in options:
                option = dict(raw_option)
                option["id"] = id_factory()
                option["item_id"] = item_id
                cloned_options.append(option)
            item["options"] = cloned_options
            cloned_items.append(item)
        scale["items"] = cloned_items
        cloned_scales.append(scale)
    source["scales"] = cloned_scales
    return source

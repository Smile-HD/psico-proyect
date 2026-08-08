"""Public evaluator and non-public scoring-fixture projections."""

from __future__ import annotations

from typing import Any

from app.models.instruments import InstrumentVersion


def published_evaluator_projection(version: InstrumentVersion) -> dict[str, Any]:
    """Project renderable content only; numeric option values never enter it."""

    return {
        "instrument_version_id": str(version.id),
        "version_no": version.version_no,
        "status": "published",
        "response_type": version.response_type,
        "scales": [
            {
                "id": str(scale.id),
                "display_order": scale.display_order,
                "label": scale.label,
                "locale": scale.locale,
                "items": [
                    {
                        "id": str(item.id),
                        "item_order": item.item_order,
                        "text": item.text,
                        "locale": item.locale,
                        "required": item.required,
                        "response_options": [
                            {
                                "id": str(option.id),
                                "display_order": option.display_order,
                                "label": option.label,
                                "locale": option.locale,
                            }
                            for option in sorted(
                                item.response_options, key=lambda row: row.display_order
                            )
                        ],
                    }
                    for item in sorted(scale.items, key=lambda row: row.item_order)
                ],
            }
            for scale in sorted(version.scales, key=lambda row: row.display_order)
        ],
    }


def fixture_projection(version: InstrumentVersion) -> dict[str, Any]:
    """Build the internal F4 fixture with the server-side 1–5 mapping."""

    return {
        "instrument_version_id": str(version.id),
        "scales": [
            {
                "id": str(scale.id),
                "display_order": scale.display_order,
                "items": [
                    {
                        "id": str(item.id),
                        "item_order": item.item_order,
                        "response_options": [
                            {"id": str(option.id), "value": option.value}
                            for option in sorted(
                                item.response_options, key=lambda row: row.display_order
                            )
                        ],
                    }
                    for item in sorted(scale.items, key=lambda row: row.item_order)
                ],
            }
            for scale in sorted(version.scales, key=lambda row: row.display_order)
        ],
    }

"""Projection boundary tests for evaluator and F4 fixture payloads."""

from __future__ import annotations

from app.modules.assessment_authoring.projections import (
    fixture_projection,
    published_evaluator_projection,
)
from app.models.instruments import (
    Instrument,
    InstrumentItem,
    InstrumentVersion,
    ResponseOption,
    Scale,
)


def _version() -> InstrumentVersion:
    instrument = Instrument(key="CAT-PROJ-01", title="Synthetic")
    version = InstrumentVersion(
        instrument=instrument, version_no=1, status="published", is_immutable=True
    )
    scale = Scale(version=version, label="Intereses", locale="es", display_order=1)
    item = InstrumentItem(
        version=version,
        scale=scale,
        item_order=1,
        text="Ítem sintético",
        locale="es",
        required=True,
    )
    for value in range(1, 6):
        ResponseOption(
            item=item,
            display_order=value,
            value=value,
            label=f"Opción {value}",
            locale="es",
        )
    return version


def test_evaluator_projection_contains_labels_but_no_internal_values() -> None:
    payload = published_evaluator_projection(_version())
    option = payload["scales"][0]["items"][0]["response_options"][0]
    assert option["label"] == "Opción 1"
    assert "value" not in option
    assert "value" not in str(payload).lower()


def test_fixture_projection_contains_mapping_and_is_independent() -> None:
    payload = fixture_projection(_version())
    options = payload["scales"][0]["items"][0]["response_options"]
    assert [option["value"] for option in options] == [1, 2, 3, 4, 5]
    assert "response_options" in payload["scales"][0]["items"][0]

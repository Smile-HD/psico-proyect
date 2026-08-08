"""DTO contract tests for the catalog API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.catalog import (
    CreateInstrumentRequest,
    PublishedVersionRead,
    SaveDraftContentRequest,
)


def _options() -> list[dict]:
    return [
        {"display_order": index, "label": f"Opción {index}", "locale": "es"}
        for index in range(1, 6)
    ]


def _body() -> dict:
    return {
        "response_type": "likert_1_5",
        "scales": [
            {
                "display_order": 1,
                "label": "Intereses",
                "locale": "es",
                "items": [
                    {
                        "item_order": 1,
                        "text": "Prefiero explorar ideas nuevas",
                        "locale": "es",
                        "required": True,
                        "options": _options(),
                    }
                ],
            }
        ],
    }


def test_create_request_accepts_contract_key_and_rejects_dynamic_fields() -> None:
    request = CreateInstrumentRequest(
        key="CAT-SYN-01",
        title="Catálogo sintético",
        adaptation={"base_locale": "es", "target_locale": "es", "label": "Base"},
    )
    assert request.key == "CAT-SYN-01"
    with pytest.raises(ValidationError):
        CreateInstrumentRequest(key="bad key", title="Catálogo")
    with pytest.raises(ValidationError):
        CreateInstrumentRequest(key="CAT-01", title="Catálogo", runtime_rule="x")


def test_save_request_derives_option_values_from_order_and_rejects_value_input() -> (
    None
):
    request = SaveDraftContentRequest.model_validate(_body())
    option = request.scales[0].items[0].options[0]
    assert option.display_order == 1
    assert "value" not in option.model_dump()
    body = _body()
    body["scales"][0]["items"][0]["options"][0]["value"] = 1
    with pytest.raises(ValidationError):
        SaveDraftContentRequest.model_validate(body)


def test_save_request_rejects_non_spanish_and_incomplete_options() -> None:
    body = _body()
    body["scales"][0]["locale"] = "en"
    with pytest.raises(ValidationError):
        SaveDraftContentRequest.model_validate(body)

    body = _body()
    body["scales"][0]["items"][0]["options"] = _options()[:4]
    with pytest.raises(ValidationError):
        SaveDraftContentRequest.model_validate(body)


def test_published_read_model_has_no_numeric_option_field() -> None:
    payload = PublishedVersionRead(
        instrument_version_id=uuid.uuid4(),
        instrument_key="CAT-SYN-01",
        title="Catálogo sintético",
        description=None,
        version_no=1,
        status="published",
        published_at=datetime.now(timezone.utc),
        response_type="likert_1_5",
        locale="es",
        adaptation=None,
        scales=[
            {
                "id": uuid.uuid4(),
                "display_order": 1,
                "label": "Intereses",
                "locale": "es",
                "items": [
                    {
                        "id": uuid.uuid4(),
                        "item_order": 1,
                        "text": "Ítem sintético",
                        "locale": "es",
                        "required": True,
                        "response_options": [
                            {
                                "id": uuid.uuid4(),
                                "display_order": 1,
                                "label": "Nunca",
                                "locale": "es",
                            }
                        ],
                    }
                ],
            }
        ],
    )
    serialized = payload.model_dump(mode="json")
    assert "value" not in str(serialized).lower()
    assert (
        serialized["scales"][0]["items"][0]["response_options"][0]["label"] == "Nunca"
    )

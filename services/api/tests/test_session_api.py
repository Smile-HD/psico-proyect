"""HTTP contracts for the evaluation-session API."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.sessions import (
    BatchResponseRequest,
    SessionDetail,
    StartRequest,
)


def test_start_request_leaves_missing_version_for_the_not_found_gate() -> None:
    request = StartRequest()

    assert request.instrument_version_id is None


def test_batch_request_accepts_option_ids_and_forbids_numeric_values() -> None:
    item_id, option_id = uuid4(), uuid4()
    request = BatchResponseRequest(
        responses=[{"item_id": item_id, "response_option_id": option_id}]
    )

    assert request.responses[0].item_id == item_id
    assert request.responses[0].response_option_id == option_id
    with pytest.raises(ValidationError):
        BatchResponseRequest(
            responses=[
                {
                    "item_id": item_id,
                    "response_option_id": option_id,
                    "value": 5,
                }
            ]
        )


def test_detail_dto_exposes_progress_and_stable_answer_ids_only() -> None:
    item_id, option_id = uuid4(), uuid4()
    version_id = uuid4()
    detail = SessionDetail.model_validate(
        {
            "id": uuid4(),
            "status": "in_progress",
            "instrument_version_id": version_id,
            "progress": {"answered": 1, "total": 1},
            "projection": {
                "instrument_version_id": version_id,
                "version_no": 1,
                "response_type": "likert_1_5",
                "scales": [
                    {
                        "id": uuid4(),
                        "display_order": 1,
                        "label": "Intereses",
                        "locale": "es",
                        "items": [
                            {
                                "id": item_id,
                                "item_order": 1,
                                "text": "Ítem sintético",
                                "locale": "es",
                                "required": True,
                                "response_options": [],
                                "response_option_id": option_id,
                            }
                        ],
                    }
                ],
            },
        }
    )

    payload = detail.model_dump(mode="json")
    assert payload["progress"] == {"answered": 1, "total": 1}
    assert payload["projection"]["scales"][0]["items"][0]["response_option_id"] == str(
        option_id
    )
    assert "value" not in str(payload).lower()
    assert "score" not in payload

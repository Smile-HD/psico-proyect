"""Stable session-runtime error factories."""

from __future__ import annotations

import pytest

from app.modules.session_runtime.errors import (
    consent_required, forbidden, idempotency_key_reused, resource_not_found,
    state_conflict, validation_error,
)


@pytest.mark.parametrize("factory, code, message", (
    (resource_not_found, "NOT_FOUND", "resource_not_found"),
    (consent_required, "CONFLICT", "consent_required"),
    (idempotency_key_reused, "CONFLICT", "idempotency_key_reused"),
    (validation_error, "VALIDATION_ERROR", "validation_error"),
    (forbidden, "FORBIDDEN", "insufficient_role"),
    (state_conflict, "CONFLICT", "invalid_session_state"),
))
def test_factories_follow_the_shared_envelope(factory, code: str, message: str) -> None:
    error = factory({"field": "value"})
    assert (error.code, error.message, error.details) == (code, message, {"field": "value"})

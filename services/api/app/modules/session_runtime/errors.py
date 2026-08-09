"""Stable session-runtime errors mapped to the shared API envelope."""

from __future__ import annotations

from typing import Any

from app.core.errors import (
    ApiError,
    CONFLICT,
    FORBIDDEN,
    NOT_FOUND,
    VALIDATION_ERROR,
)


def resource_not_found(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(NOT_FOUND, "resource_not_found", details=details)


def consent_required(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(CONFLICT, "consent_required", details=details)


def idempotency_key_reused(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(CONFLICT, "idempotency_key_reused", details=details)


def idempotency_key_required(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(VALIDATION_ERROR, "idempotency_key_required", details=details)


def validation_error(
    message: str | dict[str, Any] = "validation_error",
    details: dict[str, Any] | None = None,
) -> ApiError:
    if isinstance(message, dict):
        details = message if details is None else details
        message = "validation_error"
    return ApiError(VALIDATION_ERROR, message, details=details)


def forbidden(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(FORBIDDEN, "insufficient_role", details=details)


def state_conflict(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(CONFLICT, "invalid_session_state", details=details)


session_state_conflict = state_conflict

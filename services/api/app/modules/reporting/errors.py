"""Stable API error factories for the F6 reporting boundary."""

from __future__ import annotations

from typing import Any

from app.core.errors import ApiError, INTERNAL_ERROR


def report_integrity_error(details: dict[str, Any] | None = None) -> ApiError:
    """Report malformed persisted snapshots or templates as an internal error."""

    return ApiError(INTERNAL_ERROR, "report_integrity_error", details=details)


def report_generation_failed(details: dict[str, Any] | None = None) -> ApiError:
    """Map renderer/storage failures to the ratified F6 error token."""

    return ApiError(INTERNAL_ERROR, "report_generation_failed", details=details)


# Keep the shorter name available to domain/service adapters.
integrity_error = report_integrity_error

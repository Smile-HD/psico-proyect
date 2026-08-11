"""Stable recommendation errors mapped to the shared API envelope."""

from __future__ import annotations

from typing import Any

from app.core.errors import ApiError, CONFLICT, INTERNAL_ERROR, NOT_FOUND


def resource_not_found(details: dict[str, Any] | None = None) -> ApiError:
    """Hide missing sessions and unavailable recommendation generations."""

    return ApiError(NOT_FOUND, "resource_not_found", details=details)


def session_not_completed(details: dict[str, Any] | None = None) -> ApiError:
    """Report that recommendations are unavailable for an unfinished session."""

    return ApiError(CONFLICT, "session_not_completed", details=details)


def recommendation_integrity_error(details: dict[str, Any] | None = None) -> ApiError:
    """Report malformed persisted recommendation rules or score data."""

    return ApiError(INTERNAL_ERROR, "recommendation_integrity_error", details=details)


# Keep the shorter name available to repository/service callers while exposing
# the stable token through the same factory.
integrity_error = recommendation_integrity_error

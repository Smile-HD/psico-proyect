"""Stable scoring errors mapped to the shared API envelope."""

from __future__ import annotations

from typing import Any

from app.core.errors import ApiError, CONFLICT, INTERNAL_ERROR, NOT_FOUND


def resource_not_found(details: dict[str, Any] | None = None) -> ApiError:
    """Hide missing sessions and unavailable result runs behind one token."""

    return ApiError(NOT_FOUND, "resource_not_found", details=details)


def session_not_completed(details: dict[str, Any] | None = None) -> ApiError:
    """Report that scoring is not available for an unfinished session."""

    return ApiError(CONFLICT, "session_not_completed", details=details)


def reference_unavailable(details: dict[str, Any] | None = None) -> ApiError:
    """Report a missing or unusable synthetic reference set."""

    return ApiError(INTERNAL_ERROR, "reference_unavailable", details=details)


def scoring_integrity_error(details: dict[str, Any] | None = None) -> ApiError:
    """Report malformed persisted scoring data as a typed server error."""

    return ApiError(INTERNAL_ERROR, "scoring_integrity_error", details=details)


# Keep the shorter name available to repository/service callers while exposing
# the stable token through the same factory.
integrity_error = scoring_integrity_error

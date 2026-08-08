"""Stable catalog error factories mapped to the F1 envelope."""

from __future__ import annotations

from typing import Any

from app.core.errors import ApiError, CONFLICT, NOT_FOUND, VALIDATION_ERROR


def catalog_validation(
    message: str = "invalid_catalog_version", details: dict[str, Any] | None = None
) -> ApiError:
    return ApiError(VALIDATION_ERROR, message, details=details)


def invalid_catalog_version(details: dict[str, Any] | None = None) -> ApiError:
    return catalog_validation("invalid_catalog_version", details)


def version_not_draft(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(CONFLICT, "version_not_draft", details=details)


def version_immutable(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(CONFLICT, "version_immutable", details=details)


def archive_requires_published(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(CONFLICT, "archive_requires_published", details=details)


def seed_catalog_read_only(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(CONFLICT, "seed_catalog_read_only", details=details)


def idempotency_key_reused(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(CONFLICT, "idempotency_key_reused", details=details)


def idempotency_key_required(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(VALIDATION_ERROR, "idempotency_key_required", details=details)


def duplicate_instrument_key(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(CONFLICT, "duplicate_instrument_key", details=details)


def resource_not_found(details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(NOT_FOUND, "resource_not_found", details=details)


def published_version_not_found() -> ApiError:
    return ApiError(NOT_FOUND, "resource_not_found")

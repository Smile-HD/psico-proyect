"""Single error envelope + request_id plumbing (contracts spec).

Every API error returns exactly:
    {"error": {"code", "message", "request_id", "details"}}
Codes are one of VALIDATION_ERROR, UNAUTHORIZED, FORBIDDEN, NOT_FOUND,
CONFLICT, INTERNAL_ERROR. Auth failures return generic message text only.
"""

from __future__ import annotations

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("psico.api.errors")

VALIDATION_ERROR = "VALIDATION_ERROR"
UNAUTHORIZED = "UNAUTHORIZED"
FORBIDDEN = "FORBIDDEN"
NOT_FOUND = "NOT_FOUND"
CONFLICT = "CONFLICT"
INTERNAL_ERROR = "INTERNAL_ERROR"

ALL_CODES = {
    VALIDATION_ERROR,
    UNAUTHORIZED,
    FORBIDDEN,
    NOT_FOUND,
    CONFLICT,
    INTERNAL_ERROR,
}

_DEFAULT_STATUS = {
    VALIDATION_ERROR: 422,
    UNAUTHORIZED: 401,
    FORBIDDEN: 403,
    NOT_FOUND: 404,
    CONFLICT: 409,
    INTERNAL_ERROR: 500,
}


class ApiError(Exception):
    """Application-level error that maps to the standard envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict | None = None,
        status_code: int | None = None,
    ) -> None:
        if code not in ALL_CODES:
            raise ValueError(f"unknown error code: {code!r}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code or _DEFAULT_STATUS[code]


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "") or uuid.uuid4().hex


def build_envelope(
    request: Request, code: str, message: str, details: dict | None = None
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id(request),
            "details": details or {},
        }
    }


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request_id to every request and echo it as a header."""

    async def dispatch(self, request: Request, call_next):
        rid = uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler: INTERNAL_ERROR envelope, traceback only server-side."""
    logger.exception("unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=build_envelope(
            request, INTERNAL_ERROR, "internal_error", {"exception_type": type(exc).__name__}
        ),
    )


def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=build_envelope(request, exc.code, exc.message, exc.details),
    )


def http_error_handler(request: Request, exc) -> JSONResponse:
    """Convert starlette HTTPException (e.g. 404 not found) to the envelope."""
    mapping = {
        400: VALIDATION_ERROR,
        401: UNAUTHORIZED,
        403: FORBIDDEN,
        404: NOT_FOUND,
        409: CONFLICT,
    }
    code = mapping.get(exc.status_code, INTERNAL_ERROR)
    return JSONResponse(
        status_code=exc.status_code,
        content=build_envelope(request, code, str(exc.detail)),
    )


def validation_handler(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=build_envelope(
            request,
            VALIDATION_ERROR,
            "validation_error",
            {"errors": exc.errors()},
        ),
    )

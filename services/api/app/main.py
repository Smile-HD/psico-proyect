"""TestPsico FastAPI application.

- request_id middleware + single error envelope on every error path.
- Public: /health, /api/v1/auth/login, /api/v1/seed/status.
- Protected routes declare require_roles(...) — deny by default.
- Startup warns when dev-only defaults are in use.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.errors import (
    ApiError,
    RequestIDMiddleware,
    api_error_handler,
    exception_handler,
    http_error_handler,
    validation_handler,
)

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger("psico.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.using_dev_defaults:
        logger.warning(
            "DEV-ONLY DEFAULTS IN USE: PSICO_JWT_SECRET has its published dev "
            "value. This is fine for local development only — never deploy it."
        )
    yield


app = FastAPI(title="TestPsico API", version="0.1.0", lifespan=lifespan)

# FastAPI's official middleware pattern; pyright cannot assign Starlette
# middleware classes to _MiddlewareFactory, hence the ignores.
app.add_middleware(RequestIDMiddleware)  # type: ignore[arg-type]

# Browser (Next.js web) calls the API directly from localhost:3000, so the
# preflight must be answered for the exact web origin. The token travels in the
# Authorization header (not cookies), but credentials stay enabled to keep the
# allow-list explicit instead of a wildcard.
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, validation_handler)
app.add_exception_handler(Exception, exception_handler)

# Root-level public health endpoint (used by the compose healthcheck).
app.include_router(health_router)

app.include_router(api_router)

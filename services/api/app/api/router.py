"""Aggregated API router under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import audit, auth, catalog, consent, results, seed, sessions

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(seed.router)
api_router.include_router(audit.router)
api_router.include_router(sessions.router)
api_router.include_router(consent.router)
api_router.include_router(catalog.router)
api_router.include_router(results.router)

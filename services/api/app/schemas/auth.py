"""Auth request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.sessions import StartRequest


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Kept as an import-compatible alias for F1 callers. The session contract now
# lives with the rest of the session DTOs rather than the auth schemas.
SessionStartRequest = StartRequest

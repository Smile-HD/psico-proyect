"""Auth dependency: single get_current_user seam gated by PSICO_AUTH_MODE.

F1 value: dev (HS256 JWT with role claims). A future OIDC provider swaps in
here without touching handlers. Safe denials: 401/403 never disclose account
existence; every denial is audited as auth.denied.
"""

from __future__ import annotations

import uuid

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.auth import decode_access_token
from app.core.config import settings
from app.core.errors import ApiError, INTERNAL_ERROR, UNAUTHORIZED
from app.db.session import get_db
from app.models.identity import User

_bearer = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    id: uuid.UUID
    username: str
    roles: list[str]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if settings.auth_mode != "dev":
        # F1 ships only dev; fail closed for anything else.
        raise ApiError(INTERNAL_ERROR, "unsupported_auth_mode")

    def deny() -> None:
        audit.record(
            db,
            "auth.denied",
            actor_role=None,
            resource_type="auth",
            action="get_current_user",
            outcome="denied",
            metadata={},
            commit=True,
        )

    if credentials is None:
        deny()
        raise ApiError(UNAUTHORIZED, "Unauthorized", status_code=401)

    try:
        payload = decode_access_token(credentials.credentials, settings.jwt_secret)
        user_id = uuid.UUID(payload["sub"])
        roles = payload.get("roles") or []
    except (jwt.PyJWTError, KeyError, ValueError):
        deny()
        raise ApiError(UNAUTHORIZED, "Unauthorized", status_code=401)

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        deny()
        raise ApiError(UNAUTHORIZED, "Unauthorized", status_code=401)

    return CurrentUser(id=user.id, username=user.username, roles=list(roles))

"""POST /api/v1/auth/login — public dev login.

Returns an HS256 JWT for seeded dev credentials. Unknown users and wrong
passwords produce IDENTICAL generic 401 envelopes (no account disclosure);
both are audited (auth.login allowed / auth.denied).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.auth import create_access_token, verify_password
from app.core.config import settings
from app.core.errors import ApiError, UNAUTHORIZED
from app.db.session import get_db
from app.models.identity import Role, User, UserRole
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_roles(db: Session, user_id) -> list[str]:
    rows = db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(
            UserRole.user_id == user_id
        )
    ).all()
    return [row[0] for row in rows]


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == body.username))

    valid = user is not None and user.is_active and verify_password(
        body.password, user.password_hash
    )
    if not valid:
        # Generic text only — identical for unknown user and wrong password.
        audit.record(
            db,
            "auth.denied",
            actor_user_id=user.id if user else None,
            actor_role=None,
            resource_type="auth",
            resource_id=body.username,
            action="login",
            outcome="denied",
            metadata={},
            commit=True,
        )
        raise ApiError(UNAUTHORIZED, "Unauthorized", status_code=401)

    roles = _user_roles(db, user.id)
    token = create_access_token(user.id, user.username, roles, settings.jwt_secret)
    audit.record(
        db,
        "auth.login",
        actor_user_id=user.id,
        actor_role=",".join(roles),
        resource_type="auth",
        action="login",
        outcome="allowed",
        metadata={},
        commit=True,
    )
    return TokenResponse(access_token=token)

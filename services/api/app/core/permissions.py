"""Role access matrix + deny-by-default require_roles (D10).

The matrix lives in code (no premature permissions table) and is the single
source of truth consumed by the contracts package and the tests.
"""

from __future__ import annotations

from fastapi import Depends

from app.api.deps import get_current_user
from app.core import audit
from app.core.errors import ApiError, FORBIDDEN
from app.db.session import get_db

# Roles are seeded exactly as these names (identity-auth spec).
ADMIN = "admin"
PSICOLOGO = "psicólogo"
EVALUADO = "evaluado"

ROLES = (ADMIN, PSICOLOGO, EVALUADO)

# capability -> roles allowed (D10 matrix)
CAPABILITIES: dict[str, set[str]] = {
    "manage_users_roles": {ADMIN},
    "manage_institutions": {ADMIN},
    "manage_instruments": {ADMIN, PSICOLOGO},
    "publish_instruments": {ADMIN},
    "read_catalog": {ADMIN, PSICOLOGO, EVALUADO},
    "run_sessions": {ADMIN, PSICOLOGO, EVALUADO},
    "sign_consent": {ADMIN, PSICOLOGO, EVALUADO},
    "view_results": {ADMIN, PSICOLOGO, EVALUADO},
    "view_recommendations": {ADMIN, PSICOLOGO, EVALUADO},
    "view_reports": {ADMIN, PSICOLOGO},
    "view_audit": {ADMIN},
    "manage_seed": {ADMIN},
}


def has_capability(user_roles: set[str], capability: str) -> bool:
    allowed = CAPABILITIES.get(capability)
    if allowed is None:
        return False  # unknown capability: deny by default
    return bool(set(user_roles) & allowed)


def require_roles(*allowed: str):
    """Dependency factory: deny-by-default role gate.

    Every protected route MUST declare require_roles(...). A user whose roles
    do not intersect the declared set is denied with 403 (never a
    default-allow) and the denial is written to audit_log as auth.denied.

    The returned function is also callable directly in tests as
    ``dependency(user, db)``.
    """

    def dependency(user=Depends(get_current_user), db=Depends(get_db)):
        if not user or not set(user.roles) & set(allowed):
            audit.record(
                db,
                "auth.denied",
                actor_user_id=user.id if user else None,
                actor_role=",".join(user.roles) if user and user.roles else None,
                resource_type="route",
                action="require_roles",
                outcome="denied",
                commit=True,
            )
            raise ApiError(FORBIDDEN, "insufficient_role")
        return user

    return dependency

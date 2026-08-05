"""Dev JWT auth: HS256 tokens + PBKDF2 password hashing.

F1 ships only PSICO_AUTH_MODE=dev. A future OIDC provider swaps in behind
app.api.deps.get_current_user without touching handlers.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid

import jwt

ALGORITHM = "HS256"
PBKDF2_SCHEME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 200_000
DEFAULT_EXPIRES_MINUTES = 480  # 8h dev session


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    """PBKDF2-HMAC-SHA256 hash, self-describing for future iteration bumps."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{PBKDF2_SCHEME}${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_hex, hash_hex = stored.split("$")
        if scheme != PBKDF2_SCHEME:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(
    user_id: uuid.UUID,
    username: str,
    roles: list[str],
    secret: str,
    expires_minutes: int = DEFAULT_EXPIRES_MINUTES,
    now: float | None = None,
) -> str:
    issued = int(now if now is not None else time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "roles": list(roles),
        "iat": issued,
        "exp": issued + expires_minutes * 60,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=[ALGORITHM])

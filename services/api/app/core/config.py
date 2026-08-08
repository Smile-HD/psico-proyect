"""Application settings.

Defaults mirror ``.env.example`` exactly (dev-environment contract: container
and host never drift). All values are safe dev-only defaults; real deployments
MUST override them via environment or ``.env``.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PSICO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App environment: dev | prod (F1 ships only dev)
    env: str = "dev"
    # Auth mode: dev (seeded accounts + HS256 JWT). Future OIDC provider swaps
    # in behind this seam without touching handlers.
    auth_mode: str = "dev"
    # DEV-ONLY default; the app logs a warning at startup when this is in use.
    jwt_secret: str = "psico-dev-jwt-secret-change-me"

    # DEV-ONLY passwords for the seeded dev accounts (hashed with PBKDF2).
    dev_password_admin: str = "psico-dev-admin"
    dev_password_psicologo: str = "psico-dev-psicologo"
    dev_password_evaluado: str = "psico-dev-evaluado"

    database_url: str = (
        "postgresql+psycopg://psico_app:psico_dev_password@db:5432/psico"
    )
    redis_url: str = "redis://redis:6379/0"

    audit_retention_days: int = 365
    log_level: str = "INFO"
    # Exact origin of the Next.js web app, for CORS (browser calls to the
    # API). Credentials are allowed, so this must not be a wildcard.
    web_origin: str = "http://localhost:3000"

    @property
    def using_dev_defaults(self) -> bool:
        """True when the dev-only JWT secret default is in use (compose warning)."""
        return self.jwt_secret == "psico-dev-jwt-secret-change-me"


settings = Settings()

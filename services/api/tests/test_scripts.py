"""RED test — scripts cross-platform parity and scaffold contract (F1).

Runs WITHOUT a database or Docker: it inspects the repository files.

Threat-matrix coverage:
  - Documentation-like paths (scripts): fixed compose strings, no eval →
    .sh <-> .ps1 parity + no-eval scan.

Dev-environment scenarios covered here (pure):
  - Cross-platform parity: each task runs the same underlying docker compose
    command through its platform wrapper.
  - Missing .env bootstrap: init-env twins create .env from .env.example.
  - No drift between Settings and example: Settings() defaults mirror
    .env.example exactly.
"""

from __future__ import annotations

import pathlib
import re

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "scripts"
SERVICE_DIR = pathlib.Path(__file__).resolve().parents[1]

PAIRS = ["init-env", "dev-up", "migrate", "seed", "clean", "test"]

# docker-compose.yml must use the ${VAR:-default} form for every variable so a
# bare `docker compose up -d --build` works without a .env file.
COMPOSE_VAR_RE = re.compile(r"\$\{[^}]*\}")


def _normalize_cmd(line: str) -> str:
    """Strip argument passthrough and whitespace; keep the docker compose base."""
    line = re.sub(r"\s+\"\$@\"", "", line)
    line = re.sub(r"\s+@args", "", line)
    return re.sub(r"\s+", " ", line.strip())


@pytest.mark.parametrize("name", PAIRS)
def test_sh_ps1_twins_exist(name: str) -> None:
    sh = SCRIPTS / f"{name}.sh"
    ps1 = SCRIPTS / f"{name}.ps1"
    assert sh.exists(), f"missing {sh}"
    assert ps1.exists(), f"missing {ps1}"


@pytest.mark.parametrize("name", ["dev-up", "migrate", "seed", "clean", "test"])
def test_docker_command_parity(name: str) -> None:
    sh_cmd = _normalize_cmd(
        next(line for line in (SCRIPTS / f"{name}.sh").read_text().splitlines() if "docker compose" in line)
    )
    ps1_cmd = _normalize_cmd(
        next(line for line in (SCRIPTS / f"{name}.ps1").read_text().splitlines() if "docker compose" in line)
    )
    assert sh_cmd == ps1_cmd, f"{name}: .sh and .ps1 diverge: {sh_cmd!r} != {ps1_cmd!r}"
    # The wrapper must be a thin fixed compose command — no eval anywhere.
    assert sh_cmd.startswith("docker compose "), f"{name}: unexpected command {sh_cmd!r}"


def test_init_env_twins_create_env() -> None:
    sh = (SCRIPTS / "init-env.sh").read_text()
    ps1 = (SCRIPTS / "init-env.ps1").read_text()
    assert "cp .env.example .env" in sh
    assert "Copy-Item .env.example .env" in ps1
    assert sh.count("cp .env.example .env") == 1


def test_no_eval_in_any_script() -> None:
    for script in SCRIPTS.glob("*"):
        assert "eval" not in script.read_text(), f"eval found in {script.name}"


def test_compose_has_required_services_and_healthchecks() -> None:
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert {"api", "db", "redis"} <= set(services)
    for svc in ("api", "db", "redis"):
        assert services[svc].get("healthcheck"), f"{svc} missing healthcheck"


def test_compose_uses_default_form_for_every_variable() -> None:
    text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for var in COMPOSE_VAR_RE.findall(text):
        assert ":-" in var, f"compose variable lacks :- default: {var}"


def test_gitignore_ignores_env() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert re.search(r"^\.env\s*$", gitignore, re.MULTILINE)


def _parse_env_example() -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in (REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        parsed[key.strip()] = value.strip()
    return parsed


def test_env_example_has_required_psico_keys() -> None:
    example = _parse_env_example()
    required = {
        "PSICO_ENV",
        "PSICO_AUTH_MODE",
        "PSICO_JWT_SECRET",
        "PSICO_DEV_PASSWORD_ADMIN",
        "PSICO_DEV_PASSWORD_PSICOLOGO",
        "PSICO_DEV_PASSWORD_EVALUADO",
        "PSICO_DATABASE_URL",
        "PSICO_REDIS_URL",
        "PSICO_AUDIT_RETENTION_DAYS",
        "PSICO_LOG_LEVEL",
    }
    assert required <= set(example), f"missing keys: {required - set(example)}"


def test_settings_mirror_env_example() -> None:
    """No drift: Settings() defaults equal the committed .env.example values."""
    import os
    from app.core.config import Settings

    # Force clean defaults (no process env / no .env file leakage), then restore.
    saved = {key: os.environ[key] for key in list(os.environ) if key.startswith("PSICO_")}
    for key in saved:
        del os.environ[key]
    try:
        settings = Settings(_env_file=None)
    finally:
        os.environ.update(saved)
    example = _parse_env_example()
    mapping = {
        "PSICO_ENV": "env",
        "PSICO_AUTH_MODE": "auth_mode",
        "PSICO_JWT_SECRET": "jwt_secret",
        "PSICO_DEV_PASSWORD_ADMIN": "dev_password_admin",
        "PSICO_DEV_PASSWORD_PSICOLOGO": "dev_password_psicologo",
        "PSICO_DEV_PASSWORD_EVALUADO": "dev_password_evaluado",
        "PSICO_DATABASE_URL": "database_url",
        "PSICO_REDIS_URL": "redis_url",
        "PSICO_AUDIT_RETENTION_DAYS": "audit_retention_days",
        "PSICO_LOG_LEVEL": "log_level",
    }
    for env_key, field in mapping.items():
        assert example.get(env_key) == str(getattr(settings, field)), (
            f"drift on {env_key}: example={example.get(env_key)!r} settings={getattr(settings, field)!r}"
        )

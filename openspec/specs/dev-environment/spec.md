# Dev Environment Specification

## Purpose

Baseline contract so a fresh clone can be up, migrated, seeded, and tested in under 10 minutes on any machine with Docker Engine + Compose v2 (Windows, macOS, Linux). Raw `docker compose` is the contract; `scripts/` wrappers are convenience.

## Requirements

### Requirement: Compose Up Contract

The system MUST provide a `docker-compose.yml` with `api` (FastAPI), `db` (PostgreSQL), and `redis` services, each with healthchecks and named volumes. All variables MUST use the `${VAR:-default}` form so `docker compose up -d --build` succeeds even without `.env`; defaults are dev-only and MUST be flagged as such.

#### Scenario: Fresh clone happy path

- GIVEN a machine with Docker Engine + Compose v2 and no `.env`
- WHEN `docker compose up -d --build` runs
- THEN `api`, `db`, and `redis` start and report healthy
- AND the terminal warns that defaults are dev-only

#### Scenario: Healthcheck gating

- GIVEN `db` not yet accepting connections
- WHEN the `api` container starts
- THEN `api` does not become healthy until `db` and `redis` pass their healthchecks

### Requirement: Env Conventions

App config variables MUST use the `PSICO_*` prefix; infrastructure variables use `POSTGRES_*`/`REDIS_*`. `.env.example` MUST be committed with safe dev-only defaults and loud comments; `.env` MUST be gitignored. `scripts/init-env` MUST create `.env` from the example when missing. API `Settings` MUST mirror `.env.example` defaults exactly.

#### Scenario: Missing .env bootstrap

- GIVEN a fresh clone with no `.env`
- WHEN the developer runs `scripts/init-env`
- THEN a `.env` is created from `.env.example`
- AND it contains no real passwords or secrets

#### Scenario: No drift between Settings and example

- GIVEN a modified `.env.example`
- WHEN `Settings` loads
- THEN defaults match the committed example, so container and host never drift

### Requirement: Official Commands

README MUST document the official commands: up (`docker compose up -d --build`), migrate (`docker compose run --rm api alembic upgrade head`), seed (`docker compose run --rm api python -m app.seed`), reset seed (`python -m app.seed --reset`), clean (`docker compose down -v`), test (`docker compose run --rm api pytest`). `scripts/` MUST provide equivalent `.sh` and `.ps1` wrappers with identical behavior.

#### Scenario: Official command sequence works

- GIVEN a running compose stack
- WHEN the README migrate then seed commands run
- THEN the schema applies and seeding succeeds

#### Scenario: Cross-platform parity

- GIVEN Windows and one Unix machine
- WHEN each runs the same task through its platform wrapper
- THEN both execute the same underlying `docker compose` command

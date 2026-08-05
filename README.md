# TestPsico

Psychotechnical test system for vocational/educational exploratory orientation
(buildings blocks for UAGRM and multi-institution deployment). Everything in the
repository is **synthetic and research-only** — no real UAGRM norms, people, or
data.

F1 (this baseline) makes a fresh clone runnable in under 10 minutes on any
machine with Docker Engine + Compose v2 (Windows, macOS, Linux): a FastAPI
service, PostgreSQL, Redis, a migrated nine-family schema, an idempotent
synthetic seed, and a minimal Spanish web page that proves the compose network.

```
psico/
├── docker-compose.yml        # api + db + redis (+ web) dev stack
├── .env.example              # PSICO_* safe dev defaults (mirrored by Settings)
├── scripts/                  # cross-platform wrappers (.sh + .ps1)
├── packages/contracts/       # binding conventions for all phases (EN)
├── services/api/             # FastAPI + SQLAlchemy 2 + Alembic
├── apps/web/                 # Next.js Spanish health/seed page
└── openspec/                 # SDD planning artifacts
```

## Prerequisites

- Docker Engine + Compose v2
- Free ports 8000 (api), 5432 (db), 6379 (redis), 3000 (web)

## Quick start

```bash
# 1. Bootstrap env (creates .env from .env.example if missing)
scripts/init-env.sh            # Windows: scripts\init-env.ps1

# 2. Build and start the stack (works with NO .env: dev-only defaults)
docker compose up -d --build

# 3. Apply the schema
docker compose run --rm api alembic upgrade head

# 4. Seed synthetic data (idempotent; run twice and counts stay identical)
docker compose run --rm api python -m app.seed

# 5. Run the test suite
docker compose run --rm api pytest
```

The web page is at http://localhost:3000 (health + seed status, Spanish UI).
The API is at http://localhost:8000 (`/health`, `/api/v1/seed/status` are public).

## Official commands

| Task | Command |
|---|---|
| Up (api + db + redis + web) | `docker compose up -d --build` |
| Migrate | `docker compose run --rm api alembic upgrade head` |
| Seed (idempotent) | `docker compose run --rm api python -m app.seed` |
| Reset seed only (seed-owned rows) | `docker compose run --rm api python -m app.seed --reset` |
| Clean dev environment (drops volumes) | `docker compose down -v` |
| Minimal tests | `docker compose run --rm api pytest` |
| Env bootstrap | `scripts/init-env` (`.sh` or `.ps1`) |

Every task above has an equivalent wrapper under `scripts/` (`.sh` + `.ps1`
twins that run the exact same `docker compose` command).

## Environment

- App config uses the `PSICO_*` prefix; infra uses `POSTGRES_*` / `REDIS_*`.
- `.env.example` holds safe dev-only defaults and is committed; `.env` is
  gitignored. `app/core/config.py` (pydantic-settings) mirrors the example
  exactly so container and host never drift.
- Compose uses `${VAR:-default}` everywhere, so bare `up` works — but the
  defaults are dev-only; the API logs a warning at startup when it detects
  them. Never ship these defaults anywhere real.
- Run `scripts/init-env` once to create a personal `.env` you can override.

## Conventions (consumed by all phases)

See `packages/contracts/README.md` — binding rules for IDs (UUID4 runtime,
UUID5 `psico-seed:` keys), the single error envelope, and the audit deny-list.

- Technical contract tokens (codes, IDs, fields) are English.
- Human-facing UI texts are Spanish.
- Published instrument versions are immutable (schema-enforced).
- `audit_log` is append-only (DB trigger rejects UPDATE/DELETE).
- No scoring/recommendation rules live in the client; no LLM in the MVP path.

## Development notes

- Migrations are schema-only and form ONE linear Alembic chain.
- The seed is deterministic (UUID5) and additive; `--reset` removes only
  seed-owned rows.
- Tests: `pytest -k scripts|schema|auth|audit|consent|seed|web` to run a
  focused slice.

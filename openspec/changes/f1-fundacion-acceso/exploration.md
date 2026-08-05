# Exploration: F1 — Fundación y acceso (Foundation & Access)

- Change: `f1-fundacion-acceso` · Owner: **Marces** · Phase F1 of TestPsico
- Goal (from working plan): *"Que las otras cinco personas puedan clonar, levantar y trabajar en menos de 10 minutos, con una base consistente y una semilla visible."*
- Mode: openspec. This artifact: `openspec/changes/f1-fundacion-acceso/exploration.md`

## Current State

- The repo is **empty**: only `.atl/` (skill registry) and `openspec/` (config.yaml, empty `specs/`, empty `changes/archive/`). No code, no git repo, no package manifests, no CI, no test runner (`strict_tdd: false`).
- `openspec/config.yaml` fixes the stack (Next.js `apps/web`, FastAPI/Pydantic v2/SQLAlchemy 2/Alembic `services/api`, PostgreSQL + Redis in Compose, R/Quarto analytics offline), the domain invariants (versioned immutable instruments, pure scoring, declarative DB rules, no LLM in MVP) and the data policy (everything synthetic, `synthetic`/`research-only`, no real UAGRM data or claims).
- F1 therefore does not "integrate with existing code" — it **defines the baseline conventions** every later phase consumes: ID format, error format, env names, seed markers, access matrix, audit/consent contract. Those must be published as contracts, not discovered later.

## Affected Areas (all planned — nothing exists yet)

| Path | Why it's affected |
|---|---|
| `docker-compose.yml` | Up in <10 min: `api` (FastAPI) + `db` (PostgreSQL) + `redis`; healthchecks; volume names for clean dev |
| `.env.example` | Safe dev defaults for every required env var; `.env` is gitignored |
| `README.md` | Official command reference (up/migrate/seed/clean/test) — the F1 "startup guide" |
| `scripts/` | Thin per-platform wrappers (`.sh` + `.ps1`) around raw `docker compose` commands |
| `services/api/pyproject.toml` | Establishes the Python runner + `pytest`; enables `strict_tdd` later |
| `services/api/alembic/` | Schema migrations — one linear `versions/` chain, `upgrade head` |
| `services/api/app/models/*` | SQLAlchemy 2 models for ALL phase table families (empty-but-migrated) |
| `services/api/app/api/deps.py` | Auth dependency + role/permission middleware (`get_current_user`, `require_roles`) |
| `services/api/app/seed/` | Idempotent seed entrypoint + JSON fixtures (20 items, reference set, 30 profiles) |
| `services/api/tests/` | Minimal test suite: auth matrix, deny-by-default, seed idempotency, audit append-only |
| `apps/web/` | Minimal Next.js scaffold (decision D2) — single page proving the vertical slice |
| `packages/contracts/` | ID convention + error format + seed manifest spec, shared by all phases |

## Investigation: Decisions & Approaches

### D1 — Repo scaffold layout (monorepo, empty repo)

Minimal reproducible monorepo:

```
psico/
├── .env.example / .gitignore / .editorconfig / README.md
├── docker-compose.yml
├── apps/web/            # Next.js (minimal)
├── services/api/        # FastAPI: pyproject.toml, alembic/, app/{core,db,models,schemas,api,seed}, tests/
├── packages/contracts/  # shared conventions (IDs, errors, seed manifest schema)
├── scripts/             # dev-up / migrate / seed / clean / test (.sh + .ps1)
└── tests/               # (optional top-level smoke, later phases)
```

Key principle: **the API runs inside Docker Compose** (no local Python/Node installs required), so any machine can `docker compose up` and be working — that is what makes "<10 min" achievable for 5 heterogeneous machines (Windows + macOS/Linux). Compose uses `${VAR:-safe_default}` so it starts even before `.env` exists, with explicit warnings.

### D2 — Web scaffold in F1: include or defer?

- **Include minimal scaffold (recommended)**: one Next.js page that calls the API `/health` + seed status. Cost is small; it validates the compose network and gives F2 (Trevor, catalog) a running skeleton.
- **Defer to F2**: F1 stays API+DB only; simpler, but "trabajar" for web-bound owners means waiting.
- Not in the F1 deliverable list either way; flag it in the proposal as a scope decision. Effort: Low.

### D3 — Dev-first auth: token login vs Keycloak/OIDC

| Approach | Pros | Cons | Effort |
|---|---|---|---|
| **A. Dev token login + roles** (recommended): `POST /api/v1/auth/login` with seeded dev accounts returns a JWT (HS256, secret from env); `deps.get_current_user` + `require_roles(...)` middleware; 3 roles from DB (`admin`/`psicólogo`/`evaluado`) | No extra container; works offline; 3 roles + permissions + audit today; single source of truth in code, exhaustively tested | Not production OIDC; later swap needs a seam | Low |
| **B. Keycloak in Compose** | Real OIDC, login UI | Heavy: extra container, realm provisioning, admin console; team spends more time on IdP than product; contradicts "no premature complexity" | High |
| **C. External IdP (Auth0/Okta)** | Zero self-hosting | Needs real secrets + network — impossible for offline synthetic dev | Med |

Recommendation: **A**, with an explicit seam: `PSICO_AUTH_MODE=dev` (F1 only value) and the auth dependency isolated behind a single `get_current_user` interface so F-later can swap to OIDC token verification without touching handlers. "Safe denials": deny-by-default (`require_roles` mandatory on every route), generic 403/401 messages that never disclose account existence, denials written to audit.

### D4 — Migration + seed strategy (Alembic)

- **Migrations = schema only.** Linear `versions/` chain; `alembic upgrade head` is naturally idempotent. Autogenerate from models as the norm.
- **Seed = application data, separate from migrations**, via `python -m app.seed`:
  - **Idempotency via deterministic keys + upsert**: seed rows get deterministic UUID5 ids (`namespace psico-seed` + stable key) and are inserted with `INSERT ... ON CONFLICT (id) DO NOTHING` (or update). Run twice → same ids, no duplicates.
  - `--reset` flag wipes seed-owned tables in FK order then re-seeds (for a clean slate without `docker compose down -v`).
  - `seed_manifest` table records every run: `seed_version`, counts, checksum, `executed_at` — visible evidence of "semilla visible" and repeatability.

### D5 — Complete initial schema (all phases' core tables, empty-but-migrated)

| Family | Tables | F1 fills? |
|---|---|---|
| Identity | `users`, `roles` (`admin`/`psicólogo`/`evaluado`), `user_roles` | ✅ 3 dev accounts (admin/psicólogo/evaluado) |
| Institutions | `institutions`, `campuses`, `faculties`, `programs` (all carry `institution_id`) | ✅ 1 synthetic institution (+ optional campus/faculty/program) |
| Instruments (F2) | `instruments`, `instrument_versions`, `instrument_items` (or items JSONB in version — F2 finalizes) | ✅ 1 test + version 1 + 20 items |
| Sessions (F3) | `sessions`, `responses` | ✅ 30 synthetic profiles → sessions + 600 responses |
| Scoring (F4) | `reference_sets`, `reference_values`, `score_runs` | ✅ 1 invented reference set |
| Recommendation (F5) | `recommendation_rules`, `recommendation_results` | ❌ empty |
| Reporting (F6) | `reports`, `report_templates` | ❌ empty |
| Audit (F1) | `audit_log` | ✅ init events |
| Consent (F1) | `consent_versions`, `consent_grants` | ✅ 1 template + grants for the 30 profiles |
| Seed bookkeeping | `seed_manifest` | ✅ every run |

F1 fills: identity, institutions (minimal), instrument+version+items, sessions/responses (from profile JSON), reference set, audit, consent, manifest. F5/F6 tables are created empty.

### D6 — Env / secret handling

- `.env.example` committed with **safe dev-only defaults** and loud comments; `.env` gitignored; `scripts/init-env` copies example→real if missing.
- Prefix convention: `PSICO_*` for app config, `POSTGRES_*`/`REDIS_*` for infra (compose defaults). Pydantic-settings reads env; `Settings` defaults mirror `.env.example` exactly so container and host never drift.
- **Never commit**: real passwords, JWT secrets, tokens, any real PII or real UAGRM data. Compose uses `${VAR:-default}` so bare `docker compose up` still works (with a printed warning that defaults are dev-only).
- Required names (no values): `PSICO_ENV`, `PSICO_AUTH_MODE`, `PSICO_JWT_SECRET`, `PSICO_DEV_PASSWORD_ADMIN`, `PSICO_DEV_PASSWORD_PSICOLOGO`, `PSICO_DEV_PASSWORD_EVALUADO`, `PSICO_DATABASE_URL`, `PSICO_REDIS_URL`, `PSICO_AUDIT_RETENTION_DAYS`, `PSICO_LOG_LEVEL`.

### D7 — Audit + consent design

**Audit (`audit_log`, append-only):**
- Minimum fields: `id`, `event_type` (catalog: `auth.login`, `auth.denied`, `user.role_changed`, `instrument.published`, `consent.granted`, `consent.revoked`, `session.started`, `session.completed`, `seed.executed`, ...), `actor_user_id` (nullable = system), `actor_role` (snapshot), `resource_type`, `resource_id`, `action`, `outcome` (allowed/denied), `occurred_at`, `metadata` JSONB.
- Append-only enforcement: DB trigger rejects `UPDATE`/`DELETE`; the app DB role gets `INSERT`+`SELECT` on `audit_log` only; no audit mutation endpoints.
- **Never log**: raw response values/answers, tokens, passwords, item content, PII beyond the actor id. Document a deny-list in the contract.
- Provisional retention: keep-all in F1; `PSICO_AUDIT_RETENTION_DAYS` (default 365) + dry-run purge job later.

**Consent (versioned registry):**
- `consent_versions`: `id`, `version_no`, `title`, `body` (markdown), `effective_from`, `is_active`.
- `consent_grants`: `id`, `user_id`, `consent_version_id`, `state` (pending|granted|revoked|expired), `signed_at`, `ip`, `metadata`.
- Mandatory events: grant/revoke → audit + registry state transition; a session MUST reference a granted consent (blocked otherwise, logged as `session.blocked_without_consent`). F1 seeds one research-only consent template; the 30 profiles get granted records.

### D8 — Seed content spec (all synthetic, all marked)

- **Instrument** `TP-S-01` "Test Psicométrico Sintético — Orientación Vocacional (research-only)": **20 items = 5 scales × 4 items** (Intereses, Aptitud verbal, Aptitud numérica, Razonamiento abstracto, Valores/preferencias), 5-point Likert (1–5), version 1 immutable.
- **Reference set** `RS-TP-S-01`: `reference_status=synthetic`, `use=research-only`, `norm_note="NO es una norma UAGRM. Datos inventados para desarrollo."`; per-scale mean/sd + raw→percentile table (T/eneatype columns for F4).
- **30 profiles**: JSON fixtures `evaluado_01..30.json` — fictional persona (name, age band), full 20-response vector, synthetic flags; loaded into `sessions` + `responses` + consent grants at seed time. Downstream phases get real-shaped data to work with.
- **Every seeded row** carries `synthetic=true` / `source='seed'` where the column exists; `seed_manifest` records counts so "semilla visible" is provable.

### D9 — ID convention + error format (contracts for downstream phases)

- **IDs**: UUID4 for runtime data; **deterministic UUID5** (`namespace psico-seed` + stable key) for seed data (this is what makes re-seed idempotent). Human-readable seed keys: `evaluado_01`, `TP-S-01`, `RS-TP-S-01`.
- **Error format** (single JSON envelope, all endpoints, all phases):
  ```json
  { "error": { "code": "FORBIDDEN", "message": "insufficient_role", "request_id": "<uuid>", "details": {} } }
  ```
  Codes: `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `INTERNAL_ERROR`. Auth failures return generic text only (safe denial).

### D10 — Access matrix (3 roles, deny-by-default)

| Capability | admin | psicólogo | evaluado |
|---|---|---|---|
| Manage users/roles | ✅ | ❌ | ❌ |
| Manage institutions/entities | ✅ | ❌ | ❌ |
| Publish instrument versions | ✅ | ❌ | ❌ |
| Read published instrument catalog | ✅ | ✅ | ✅ (own) |
| Create/run sessions | ✅ | ✅ | ✅ (own) |
| Sign / view consent | ✅ (registry) | ✅ | ✅ (own) |
| View results / scores | ✅ | ✅ | ✅ (own) |
| View audit log | ✅ | ❌ | ❌ |
| Run seeds / manage manifests | ✅ | ❌ | ❌ |

Every route MUST declare `require_roles(...)`; there is no default-allow. Permission matrix lives in code (`app/core/permissions.py`) with exhaustive tests in F1; a DB `permissions` table is deferred (not premature).

## Official commands contract (F1 publishes, README source of truth)

| Task | Command |
|---|---|
| Up (api + postgres + redis) | `docker compose up -d --build` |
| Migrate | `docker compose run --rm api alembic upgrade head` |
| Seed (idempotent) | `docker compose run --rm api python -m app.seed` |
| Reset seed only | `docker compose run --rm api python -m app.seed --reset` |
| Clean dev environment | `docker compose down -v` |
| Minimal tests | `docker compose run --rm api pytest` |
| Env bootstrap | `scripts/init-env` (or `cp .env.example .env`) |

Platform-neutral by construction (raw `docker compose` is the contract; `scripts/` wrappers are convenience).

## Recommendation

Proceed with: **Dockerized API-first monorepo** (D1) + **minimal web scaffold** (D2) + **dev token auth with role middleware and an OIDC seam** (D3-A) + **schema-only Alembic migrations with deterministic-key idempotent seed and `seed_manifest`** (D4) + **full empty-but-migrated schema across all 9 table families** (D5) + **`.env.example` with safe defaults, `PSICO_*` naming** (D6) + **append-only audit + versioned consent registry with deny-list** (D7) + **synthetic seed: 20 items / 1 reference set / 30 JSON profiles, all flagged** (D8) + **UUID5 seed ids, UUID4 runtime, single error envelope** (D9) + **code-level access matrix, deny-by-default** (D10).

This is the minimal approach that still delivers every F1 contract: 3 roles, permissions, audit, consent, repeatable schema+seed, and a <10-min onboarding path — with zero premature infrastructure.

## Risks

- **Cross-platform bootstrap**: 5 heterogeneous machines (Windows/macOS/Linux). Mitigate with compose-only commands + `.sh`/`.ps1` wrappers; verify on at least Windows + one Unix.
- **Convention freeze**: F1's ID/error/env/seed conventions become binding contracts for F2–F6. They must be written down (proposal + contracts), not just implicit in code.
- **Auth seam**: hardcoding dev-auth could make a later OIDC swap invasive. Mitigate with `PSICO_AUTH_MODE` + isolated `get_current_user` interface.
- **Seed vs F3/F4 design**: F1 pre-fills `sessions`/`responses`/`reference_sets` that F3/F4 own. All synthetic and flagged; later phases may `--reset` or extend — seed must stay additive and non-destructive of their work.
- **No git/CI yet**: no automated verify loop. Proposal should add pytest so `strict_tdd` can flip on at F2.

## Ready for Proposal

**Yes.** All decisions are enumerated with a clear recommendation and the contract surface is mapped. The proposal should formalize: official commands, env var names, access matrix, schema table list, seed manifest spec, and ID/error conventions — plus the D2 web-scaffold scope decision for the user.

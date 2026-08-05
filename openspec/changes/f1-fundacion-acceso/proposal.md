# Proposal: F1 — Fundación y acceso (Foundation & Access)

## Intent

F1 team goal: *"que las otras cinco personas puedan clonar, levantar y trabajar en menos de 10 minutos"* — a consistent baseline with visible seed. The repo is empty; F1 publishes the binding conventions every later phase consumes (IDs, error format, env names, seed markers, access matrix, audit/consent contract). Touches phase **F1 (owner: Marces)**; schema pre-creates F2–F6 table families empty-but-migrated. No edits to published instruments (immutability is encoded from day one, not amended).

## Scope

### In Scope
- Docker Compose (`api` + `db` + `redis`), healthchecks, `${VAR:-default}` so bare `up` works
- `.env.example` (safe dev-only defaults, `PSICO_*` prefix); `.env` gitignored; `scripts/init-env`
- Full schema + Alembic migrations — all 9 table families; F5/F6 tables empty-but-migrated
- Dev JWT auth: seeded `admin`/`psicólogo`/`evaluado` accounts, `require_roles` deny-by-default middleware, generic safe denials logged to audit; `PSICO_AUTH_MODE=dev` seam for future OIDC
- Append-only `audit_log` (DB trigger blocks UPDATE/DELETE; deny-list: no responses, PII, tokens) + versioned consent registry (`consent_versions`, `consent_grants`; sessions blocked without granted consent)
- Idempotent synthetic seed (deterministic UUID5 keys + upsert): 20 items (5 scales × 4), 1 invented reference set with "NO es una norma UAGRM" note, 30 JSON profiles → sessions + 600 responses + consent grants; every row flagged `synthetic`/`research-only`; `seed_manifest` records each run
- Minimal Next.js page calling API `/health` + seed status (vertical slice for F2)
- README with official commands; `scripts/` wrappers (`.sh` + `.ps1`)
- Contracts: UUID4 runtime / UUID5 seed IDs; single error envelope `{error:{code,message,request_id,details}}`
- Language: technical contract in English; UI/human-facing texts in Spanish

### Out of Scope
- Real UAGRM catalog/norms; OIDC/Keycloak; distributed queues; F5/F6 data; production deployment; real PII

## Capabilities

> Contract with sdd-spec. `openspec/specs/` is empty — all capabilities are new.

### New Capabilities
- `dev-environment`: compose up/migrate/seed/test contract, env conventions, scripts, README
- `identity-auth`: user/role schema, dev JWT login, 3-role access matrix, `require_roles`, OIDC seam
- `data-schema`: 9-family schema + linear Alembic chain, empty-but-migrated F5/F6
- `audit-consent`: append-only audit trail + versioned consent registry
- `synthetic-seed`: idempotent seed entrypoint, JSON fixtures, `seed_manifest`
- `contracts`: ID convention + single error envelope with `request_id`
- `web-scaffold`: minimal Next.js health/seed page

### Modified Capabilities
None — no existing specs.

## Approach

D1–D10 recommendations as confirmed: dockerized API-first monorepo (D1); minimal web scaffold (D2); dev token auth isolated behind `get_current_user` + `PSICO_AUTH_MODE` seam, no Keycloak (D3-A); schema-only Alembic + deterministic-key idempotent seed with `--reset` (D4); full 9-family schema (D5); `.env.example` mirrored by Pydantic `Settings` (D6); append-only audit + consent-gated sessions (D7); synthetic seed with visible markers (D8); UUID4/UUID5 + one error envelope (D9); code-level access matrix, no default-allow (D10).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `docker-compose.yml` | New | api/db/redis services, healthchecks, volumes |
| `.env.example`, `.gitignore`, `README.md` | New | env contract, startup guide, official commands |
| `scripts/*.sh` + `*.ps1` | New | init-env, dev-up, migrate, seed, clean, test wrappers |
| `services/api/` (pyproject, app/, alembic/, tests/) | New | FastAPI app, models for 9 families, auth deps, seed, pytest |
| `packages/contracts/` | New | ID + error + seed manifest conventions |
| `apps/web/` | New | Next.js health/seed page |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cross-platform bootstrap (5 machines) | Med | Compose-only commands + `.sh`/`.ps1` wrappers; verify Windows + one Unix |
| Convention freeze for F2–F6 | Med | Contracts written in `packages/contracts/` + proposal, not implicit in code |
| Auth seam hardens | Med | `PSICO_AUTH_MODE` + isolated `get_current_user`; F1 ships only `dev` |
| Seed clashes with F3/F4 data | Low | Additive seed, `--reset` only seed-owned rows, UUID5 namespace |

## Rollback Plan

- No prod data exists: `docker compose down -v` removes all volumes; delete repo to restore empty state
- Seed is non-destructive: re-run is idempotent; `--reset` touches only seed-owned rows (FK order)
- Migrations are forward-only: revert = `docker compose down -v` + fresh `upgrade head` (no data to preserve)
- F1 creates no git history; nothing published to users

## Dependencies

- Docker Engine + Compose v2 on any OS; free ports 8000/5432/6379
- No external network, IdP, or real data required (fully offline dev)

## Success Criteria

- [ ] Fresh clone → `docker compose up -d --build` + migrate + seed + pytest completes in < 10 min on Windows and one Unix machine
- [ ] `pytest` passes: auth matrix (3 roles), deny-by-default, seed idempotency (2 runs → identical counts), audit append-only enforced
- [ ] Web page renders `/health` OK + seed status (20 items / 1 reference / 30 profiles)
- [ ] `seed_manifest` records counts + checksum per run; all seeded rows flagged synthetic/research-only

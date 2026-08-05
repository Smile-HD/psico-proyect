# Design: F1 — Fundación y acceso (Foundation & Access)

## Technical Approach

Dockerized API-first monorepo: Compose runs `api`/`db`/`redis`; 9-family SQLAlchemy 2 schema, linear Alembic chain; dev JWT behind `PSICO_AUTH_MODE` seam, `require_roles` deny-by-default; UUID5 seed + `seed_manifest`; append-only audit + consent-gated sessions; Next.js page. Conventions live in `packages/contracts/`.

```
psico/
├── docker-compose.yml  .env.example  .gitignore  .editorconfig  README.md
├── scripts/  init-env dev-up migrate seed clean test (.sh+.ps1)
├── apps/web/ (ES UI) | packages/contracts/ (EN)
└── services/api/  pyproject.toml alembic/versions/
                   app/{core,db,models,schemas,api,seed} tests/
```

## Architecture Decisions

| Decision | Options | Choice | Rationale |
|---|---|---|---|
| Auth | Keycloak / IdP / JWT | Dev JWT HS256 + `PSICO_AUTH_MODE` seam | Offline; Keycloak rejected: heavy ops for synthetic dev |
| Migrations | per-family / single chain | One linear schema-only chain; seed = app data | Idempotent; F5/F6 empty-but-migrated |
| Seed IDs | UUID4 / UUID5 | UUID5 (`psico-seed:` + key) | Deterministic upsert; runtime/seed distinction |
| Permissions | DB table / code | `app/core/permissions.py` | Testable, no premature table (D10) |
| Audit | app-only / DB trigger | Trigger rejects UPDATE/DELETE; role INSERT+SELECT | Survives app bugs (D7) |
| Errors | per-endpoint / envelope | Single envelope + request_id | One parse path, F2–F6 |

## Data Flow

```
login → get_current_user (dev) → HS256 → require_roles →
   ok: handler + audit | deny: audit + 403
```

routes → deps → `core.{auth,permissions,audit}` → models → `db.session`.

Seed: fixtures (20 items = 5 scales × 4, Likert 1–5; `RS-TP-S-01` with `norm_note` "NO es una norma UAGRM. Datos inventados para desarrollo."; 30 profiles → 30 sessions + 600 responses + consent grants; all rows flagged `synthetic`/`source='seed'`) → `seed_id(key)=uuid5(NAMESPACE_URL,"psico-seed:"+key)` → `INSERT … ON CONFLICT DO NOTHING` (FK order) → `seed_manifest` (counts, sha256, executed_at). `--reset` deletes seed-owned rows in reverse FK order, then re-seeds; non-seed untouched.

## Schema

| Family | Tables | Key fields / constraints |
|---|---|---|
| identity | users, roles, user_roles | users.id UUID4 PK; roles.name UNIQUE (admin/psicólogo/evaluado); user_roles PK(user_id, role_id) |
| institutions | institutions, campuses, faculties, programs | each carries institution_id FK (isolation) |
| instruments | instruments, instrument_versions, instrument_items | key UNIQUE (TP-S-01); version_no UNIQUE per instrument; items order_idx, scale, CHECK 1–5 |
| sessions | sessions, responses | consent_grant_id FK (granted only); responses UNIQUE(session, item), value 1–5 CHECK |
| scoring | reference_sets, reference_values, score_runs | key UNIQUE (RS-TP-S-01); status/use/norm_note |
| recommendation / reporting | rules, results, reports, templates | empty-but-migrated |
| audit | audit_log | trigger `audit_append_only` (RAISE on UPDATE/DELETE); event_type, actor_user_id, actor_role, resource_type/id, action, outcome, occurred_at, metadata JSONB |
| consent | consent_versions, consent_grants | state CHECK (pending/granted/revoked/expired); UNIQUE(user_id, version_id) |
| seed | seed_manifest | seed_version, counts JSONB, checksum, executed_at |

Indexes: FK cols; sessions(user_id, started_at); audit_log(event_type, occurred_at).

## File Changes

| File | Action | Description |
|---|---|---|
| `docker-compose.yml` | Create | api/db/redis; `${VAR:-default}`; volumes; ports 8000/5432/6379; health-gated |
| `.env.example`, `.gitignore`, `.editorconfig`, `README.md` | Create | PSICO_* defaults mirrored by Settings; .env ignored |
| `scripts/*.{sh,ps1}` | Create | thin wrappers (.sh⇄.ps1 parity) |
| `services/api/pyproject.toml`, `alembic.ini`, `alembic/versions/` | Create | fastapi, sqlalchemy 2, alembic, pydantic-settings, pytest |
| `services/api/app/**` | Create | core, db, models, schemas, api deps+routes, seed |
| `apps/web/` + `packages/contracts/README.md` | Create | ES UI; EN contract; fetch `http://api:8000`; no rules in client |

## Interfaces / Contracts

```json
{"error":{"code":"FORBIDDEN","message":"insufficient_role","request_id":"<uuid4>","details":{}}}
```

Codes: VALIDATION_ERROR, UNAUTHORIZED, FORBIDDEN, NOT_FOUND, CONFLICT, INTERNAL_ERROR; auth failures: generic message only; keys `evaluado_01`, `TP-S-01`, `RS-TP-S-01`.

API: `POST /api/v1/auth/login` (public) → JWT; `/health` + `/seed/status` (public, live counts); `/seed/run|reset` + audit (admin only). Errors: request_id middleware → envelope; denials audited.

Deny-list: no raw responses, PII, tokens, item content. `require_consent` blocks consent-less sessions (CONFLICT + `session.blocked_without_consent`).

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | matrix, uuid5 determinism, envelope, Settings↔example | pure pytest |
| Integration | login ok/unknown (identical 401), 3-role × endpoints, consent gate | TestClient + migrated DB |
| E2E | seed ×2 identical; --reset keeps non-seed; audit UPDATE/DELETE rejected | compose DB |

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED test |
|---|---|---|---|
| Documentation-like paths | **Applicable** (scripts) | Fixed compose strings; no eval | .sh⇄.ps1 parity; no-eval scan |
| Git repo selection | N/A: no VCS automation | — | — |
| Commit state | N/A: no commits | — | — |
| Push state | N/A: no pushes | — | — |
| PR commands | N/A: no PR automation | — | — |

## Migration / Rollout

No data migration (empty repo). Forward-only; rollback = `down -v` + `upgrade head`. `PSICO_AUTH_MODE` dev-only; OIDC swap only in `get_current_user`.

## Open Questions

- [ ] checksum input
- [ ] seed/status visibility

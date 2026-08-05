# Tasks: F1 — Fundación y acceso

## Review Workload Forecast

Estimated changed lines: ~3500. Suggested split: 5 PRs (scaffold → schema → auth → seed → web).

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Work Units

| Unit | Goal | PR | Focused test | Harness | Rollback |
|---|---|---|---|---|---|
| 1 | Compose/env/scripts/contracts | 1 | `docker compose config` | `up -d --build` | `down -v` |
| 2 | Schema + migrations | 2 | `pytest -k schema` | `alembic upgrade head` | `down -v` |
| 3 | JWT auth + envelope | 3 | `pytest -k auth` | login→403 TestClient | revert files |
| 4 | Seed + audit/consent | 4 | `pytest -k "seed or audit or consent"` | `seed` ×2; `--reset` | re-seed |
| 5 | Web + full suite | 5 | `pytest` | web renders counts | delete apps/web |

> Apply resolution: single PR, one branch, 5 work-unit commits (05d8400, ff951d1, 6db8983, 3e1a55d, pending web). Chained PRs NOT used (ask-on-risk resolved by orchestrator).

## Phase 1: Scaffold [F1]

- [x] 1.1 `docker-compose.yml`: api/db/redis, healthchecks, `${VAR:-default}`, volumes, ports 8000/5432/6379
- [x] 1.2 `.env.example` (PSICO_* safe dev defaults), `.gitignore` (.env), `.editorconfig`
- [x] 1.3 `README.md` official commands (up/migrate/seed/reset/clean/test)
- [x] 1.4 `pyproject.toml` (fastapi, sqlalchemy 2, alembic, pydantic-settings, pytest), `alembic.ini`, `app/core/config.py` Settings mirroring example
- [x] 1.5 RED `tests/test_scripts.py`: `.sh`⇄`.ps1` parity, no eval (threat)
- [x] 1.6 `scripts/{init-env,dev-up,migrate,seed,clean,test}` `.sh`+`.ps1` twins, no eval — GREEN
- [x] 1.7 `packages/contracts/README.md` (EN): pin `uuid5(NAMESPACE_URL, "psico-seed:"+key)`, keys `evaluado_01`/`TP-S-01`/`RS-TP-S-01`, envelope, codes, deny-list

## Phase 2: Schema

- [x] 2.1 `app/models/` 9 families + `seed_manifest` (~25 tables): UNIQUE roles.name/key/version_no; CHECK 1–5 items/responses; consent state; FK indexes; synthetic/source cols
- [x] 2.2 Linear `alembic/versions/` chain + `audit_append_only` trigger; app role INSERT+SELECT audit_log
- [x] 2.3 RED `tests/test_schema.py`: upgrade head from empty DB; rerun idempotent; F5/F6 empty-but-migrated

## Phase 3: Auth [F1]

- [x] 3.1 `app/core/auth.py` HS256 JWT + `app/api/deps.py` `get_current_user` behind `PSICO_AUTH_MODE=dev`
- [x] 3.2 `app/core/permissions.py` matrix (admin/psicólogo/evaluado); `require_roles` deny-by-default
- [x] 3.3 `app/core/errors.py` envelope + request_id; login, health, seed/status public; seed/audit admin-only
- [x] 3.4 RED `tests/test_auth.py`: 3-role matrix; undeclared→403; identical 401s; denials audited

## Phase 4: Audit/Consent/Seed [F1]

- [x] 4.1 `app/core/audit.py` catalog: auth.login, auth.denied, user.role_changed, instrument.published, consent.granted/revoked, session.started/completed/blocked_without_consent, seed.executed
- [x] 4.2 RED `tests/test_audit.py`: UPDATE/DELETE rejected; deny-list clean (no responses/tokens)
- [x] 4.3 RED `tests/test_consent.py`; `require_consent`: no grant → CONFLICT + blocked_without_consent audited
- [x] 4.4 `app/seed/`: UUID5 + ON CONFLICT DO NOTHING (FK order); 20 items (5×4, Likert 1–5); RS-TP-S-01 synthetic/research-only, norm_note "NO es una norma UAGRM. Datos inventados para desarrollo."; 30 profiles → 30 sessions + 600 responses + grants; 3 dev accounts; synthetic=true/source='seed'
- [x] 4.5 `seed_manifest`: version, counts, sha256 (over fixture files), executed_at; `--reset` seed-owned only
- [x] 4.6 RED `tests/test_seed.py`: ×2 identical counts; UUID5 deterministic; reset keeps non-seed; counts match DB

## Phase 5: Web & Verify [F1]

- [x] 5.1 `apps/web` page (ES): health + seed status via compose network
- [x] 5.2 API unreachable → friendly Spanish error, no stack trace
- [ ] 5.3 Verify Win+Unix: up + migrate + seed + full `pytest`; README check

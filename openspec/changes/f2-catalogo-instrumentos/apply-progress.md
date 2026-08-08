# Apply Progress — F2 Instrument Catalog

Status: **all implementation tasks done, tests green (113 ×2), web build green.**

## PR 1 — Database (committed)

- Commits: `0f5349e` (feat db), `5f0dd36` (seed preflight), `5238816` (tests), `eef61b0` (openspec artifacts).
- Four-level models (`Scale`, `ResponseOption`, `IdempotencyRecord`), alembic `0005_catalog_four_level`
  (scales, response_options, idempotency_records, status CHECK, backfill TP-S-01 → 5/20/100),
  atomic seed `--reset` preflight.
- Lesson: rebuild the api image after touching migrations — `/app` (image copy) runs alembic
  while tests mount `/repo`; stale image → phantom `relation "scales" does not exist`.

## PR 2 — API (committed)

- Commits: `7906323` (feat api), `3bd8cf3` (tests), `dc7d640` (test infra).
- `assessment_authoring` module (domain, errors, idempotency, projections, repository, service),
  catalog routes, schemas, audit events, permission matrix, Idempotency-Key on all mutations.
- Bugs fixed during apply:
  1. `_replace_draft_graph` inserted new rows before deleting stale ones → `uq_scales_version_order`
     violation on re-save. Fix: delete-absent-first + `db.flush()` before upserts.
  2. Suite not repeatable: persistent idempotency records + fixed test keys → second run replayed
     stale creates. Fix: `reset_database()` in `tests/db_utils.py`, called from the conftest
     `engine` fixture (drop/recreate `psico*` DB per run).
  3. `except IntegrityError` masked real failures as `duplicate_instrument_key`. Fix: check
     `diag.constraint_name == "instruments_key_key"`, re-raise otherwise.
  4. Local LSP was unusable (no venv): created `services/api/.venv` + `[tool.pyright]` in
     pyproject.toml.

## PR 3 — Web UI (committed)

- Commit: `a01bc31`.
- Pages: `/login`, `/catalogo` (list + filters), `/catalogo/nuevo`, editor
  (`/catalogo/[instrumentId]/versiones/[versionId]`), evaluator view (`.../vista`).
- Imports via `@/lib/*` alias; `next build` green (7 routes).

## PR 4 — Contracts + promotion (committed)

- Commit: `429175d`.
- `packages/contracts/README.md` §7 catalog contract; 5 new specs promoted to `openspec/specs/`;
  5 deltas merged into existing specs; `AGENTS.md` added (OpenSpec-as-memory guide for devs).

## Verification evidence

- `pytest /repo/services/api/tests` → **113 passed** (twice consecutively, repeatable).
- `cd apps/web && npm run build` → **green** (7 routes).
- Verify report: `openspec/changes/f2-catalogo-instrumentos/verify-report.md`.
- Changed lines total ≈ 6,167 — exceeds the native 3,500 budget; **user-approved 4-PR
  stacked-to-main delivery** (2026-08-08) covers this with per-PR review units.

# Exploration: F5 — Perfiles / Recomendación declarativa

Change: `2026-08-10-f5-profiles-recommendation` · Owner: Piere · Phase: F5
Explored against the post-F4 state (F4 archived `2026-08-10-f4-scoring-engine`, working tree clean, no active changes).

## Current State

- **F4 delivered the consumption surface**: `score_runs` (eager persisted runs, `pending → completed`, `raw` JSONB) + `POST /api/v1/results/{session_id}/score` (Idempotency-Key scope `session:{id}`, audit `scoring.run`) + `GET /api/v1/results/{session_id}` (latest run, deterministic by `computed_at` DESC then id DESC, `NOT_FOUND`/`resource_not_found` when missing or unscored). `run.raw` JSONB holds per-scale `{label, raw, direct.z, transformed{percentile,t_score,eneatype}}` + `overall` — **exactly what a rule engine needs, with no re-scoring**.
- **F5/F6 tables ALREADY EXIST — empty-but-migrated since migration 0003** (verified in `0003_scoring_recommendation_reporting_audit_seed.py` and `app/models/recommendation.py`):
  - `recommendation_rules`: `program_id` (FK→programs.id, NOT NULL), `rule_type` String(64), `params` JSONB, `is_active`, `synthetic`/`source`, `created_at`.
  - `recommendation_results`: `session_id` (FK, NOT NULL), `rule_id` (FK→recommendation_rules.id, NOT NULL), `program_id` (FK→programs.id, NOT NULL), `fit_score` Numeric(5,2), `justification` Text, `created_at`. No unique constraint on `session_id` — multiple runs per session are schema-legal, mirroring `score_runs`.
  - **No migration needed for F5** unless the proposal adds program metadata (e.g. description) or a disclaimer column — that would be migration 0006.
- **`programs` exists since migration 0001** (institutions family): `institution_id` FK NOT NULL, `faculty_id` FK, `name`, `code`. Model `Program` at `app/models/institutions.py:55`.
- **Seed**: exactly ONE program seeded (`program:dev` — "Programa Sintético de Orientación", `PS-001`, under `institution:dev`/`faculty:dev`, `loader.py:274`). No program-catalog fixture, no `recommendation_rules`/`recommendation_results` rows (SEED_TABLES ends at `reference_values`; the data-schema spec "F5/F6 empty after seed" scenario pins count 0). The 30 profiles (`evaluado_01..30`) each have 1 completed session + 20 responses but **NO score_runs** (those are runtime rows, F4 creates them via the API).
- **Nothing F5-shaped exists in code**: no `modules/recommendation/`, no routes, no schemas, no `view_recommendations` capability (CAPABILITIES + contracts README §6 matrix has only `view_results`), no `recommendation.generated` audit event (EVENT_CATALOG ends at `scoring.run`).
- **Established patterns to mirror (F4)**: module `domain/service/repository/errors`, thin route adapters under `/api/v1`, `require_roles` deny-by-default, single error envelope, idempotency store scope `session:{id}`, audit `record(commit=False)` in the transaction, strict TDD.
- **Boundary**: percentiles/transformed scores DO cross the API (ratified by F4 via results); option values/keys, response ids, item content, and the 1–5 mapping NEVER. The results payload carries the baremo `norm_note` verbatim — F5 needs an equivalent disclaimer for recommendation output.
- **Testing**: suite is 179 collected / 177 passed / 2 inherited `test_web.py` failures (do NOT touch). Session-scoped seeded DB (conftest `seeded_db_session`). F4's remediation lesson: absolute count assertions over shared seeded profiles got contaminated — F4 now uses `evaluado_19`/`evaluado_20` for repository/service assertions; API tests use `evaluado_01..18`. **Profiles `evaluado_21..30` (10) are untouched by all existing tests** — free to reserve for F5.

## Affected Areas

| Area | Why |
| --- | --- |
| `services/api/app/modules/recommendation/` (NEW: domain/service/repository/errors) | The F5 module per the F2/F3/F4 pattern; domain holds the pure rule-evaluation + fit function |
| `services/api/app/api/routes/recommendations.py`, `app/schemas/recommendations.py` (NEW) | API surface + strict DTOs (program id/name/code, fit_score, justifications, disclaimer; never option values/keys) |
| `services/api/app/api/router.py` | Register the new router under `/api/v1` |
| `services/api/app/core/permissions.py` + `packages/contracts/README.md` §6 | Ratify a `view_recommendations` capability (admin, psicólogo, evaluado-own) |
| `services/api/app/core/audit.py` + contracts README §3 + `openspec/specs/audit-consent` + `tests/test_audit.py` | Ratify `recommendation.generated` (aggregate-only metadata: ids/counts/timestamps; never fit scores or justification text) |
| `services/api/app/seed/loader.py` + `seed/fixtures/programs.json` + `seed/fixtures/recommendation_rules.json` (NEW) | Extend the synthetic seed: small invented program catalog + declarative rules; add `recommendation_rules`/`recommendation_results` to SEED_TABLES for `--reset`; bump SEED_VERSION |
| `services/api/app/models/recommendation.py`, `models/institutions.py`, `modules/scoring/` | Consumed read-only — no changes |
| `services/api/tests/test_recommendation_{domain,repository,service}.py`, `test_recommendation_api.py` (NEW) | Strict TDD slice `-k "recommendation or program"`; use reserved profiles `evaluado_21..30` + delta counting |
| `openspec/specs/` (recommendation-api NEW domain; data-schema, synthetic-seed, audit-consent, contracts deltas) | Ratified spec deltas for the change; `data-schema` "F5/F6 empty after seed" scenario MUST be MODIFIED (reports/report_templates stay 0) |

## Approaches

### 1. Eager persisted recommendations (mirror F4 — recommended)
`POST /api/v1/recommendations/{session_id}/generate` (Idempotency-Key scope `session:{id}`, audit `recommendation.generated`) + `GET /api/v1/recommendations/{session_id}` (latest). Service reads the latest completed score run (`score_runs.raw` JSONB) + active rules for all programs, invokes the pure domain (fit per program), persists one `recommendation_results` row per rule with `fit_score` contribution + `justification`, aggregates per program in the payload. Availability mirrors F4: missing/unscored session → `NOT_FOUND`/`resource_not_found`; `in_progress` → `CONFLICT`/`session_not_completed` (reuse F4 token). New key = new run (schema-legal).
- Pros: `recommendation_results` finally used as designed ("F5 owns the data"); run history + persisted traceable justification; read path cheap; identical conventions to F4 (idempotency, audit, latest-selection).
- Cons: mutation surface (Idempotency-Key + event ratification); re-run semantics decision (new key creates a new result set — fine, no unique constraint).
- Effort: Medium–High

### 2. Lazy compute-on-read (no mutation)
Only `GET /api/v1/recommendations/{session_id}`; compute fit from latest run + rules in the service on every read; nothing persisted. No Idempotency-Key, no new audit event, smallest spec.
- Pros: zero mutation surface; idempotent reads; no event ratification.
- Cons: `recommendation_results` stays empty forever (contradicts the ratified schema intent and the "empty-but-migrated" rationale); no history; justification recomputed per read; diverges from the F4-eager precedent.
- Effort: Low–Medium

### 3. Rule representation (orthogonal decision)
- **A (recommended): rows in `recommendation_rules`** with `rule_type` + `params` JSONB — e.g. `rule_type="percentile_min"`, `params={"scale": "Aptitud numérica", "min_percentile": 60, "weight": 1.0}`, also supporting `scale="overall"`. Closed rule-type vocabulary pinned in the spec. Fit per program = `100 · Σ(w_i·satisfied_i) / Σ(w_i)`, `satisfied_i ∈ {0,1}` deterministic; justification per rule = e.g. `"Aptitud numérica ≥ 60 pct: cumple (72 pct)"`. Fits the existing schema EXACTLY — no migration.
- B: requirement columns on `programs` — needs migration 0006, denormalized, less flexible.
- C: stored SQL/expression strings — fragile, not explainable, violates invariant spirit.

### API naming / capability
`/recommendations` under `/api/v1` mirrors the `/results` convention. Ratify a new `view_recommendations` matrix row (admin ✅, psicólogo ✅, evaluado ✅ own) instead of silently reusing `view_results` — keeps the matrix explicit and deny-by-default.

## Recommendation

**Approach 1 (eager persisted) + rule representation A (DB rows, rule_type + params JSONB) + no migration.** Mirror F4 end-to-end: module `app/modules/recommendation/{domain,service,repository,errors}.py`; `POST /api/v1/recommendations/{session_id}/generate` (Idempotency-Key `session:{id}`, audit ratified `recommendation.generated`, aggregate-only) + `GET /api/v1/recommendations/{session_id}` (latest by `created_at` DESC then id DESC, `NOT_FOUND` when missing/unscored); roles via a ratified `view_recommendations` capability (evaluado own-only enforced in service). Fit math MUST be pinned in the spec like F4's (weighted satisfaction ratio, exact rounding to Numeric(5,2), tie order deterministic — e.g. fit DESC then program name). Every recommendation payload MUST carry an equivalent of `norm_note` — a pinned research-only/orientational disclaimer (decision for proposal: code constant ratified in spec, since the invariant says RULES live in DB, not disclaimers; a DB note column would force migration 0006). Seed extension: `programs.json` (4–6 invented synthetic programs under `faculty:dev`) + `recommendation_rules.json` (rules referencing the exact scale labels + overall), loader updates, SEED_TABLES += the two recommendation tables, SEED_VERSION bump. Unscored-completed → `NOT_FOUND` mirrors F4 and keeps F5 free of hidden scoring triggers.

## Risks

- **Absolute-count contamination over shared seeded profiles** (F4 was bitten and remediated): F5 tests MUST reserve untouched profiles (`evaluado_21..30`) and use delta counting from test start; never assert absolute counts over the shared seed.
- **Seed dependency for API tests**: seeded profiles have completed sessions but NO score_runs — every recommendation integration test must first trigger scoring (via the F4 API) or use a runtime-scored session; the unscored → `NOT_FOUND` case must be tested explicitly.
- **Fit-math ambiguity**: if the weighted formula, rounding, and tie-break aren't pinned in the spec, implementation and tests drift (same trap F4's exploration flagged).
- **Rule vocabulary drift**: `rule_type`/`params` are free-form JSONB — the closed vocabulary and params schema MUST be pinned in the spec and enforced by domain validation, not left to convention.
- **Event/capability ratification in lockstep**: `recommendation.generated` and `view_recommendations` touch `EVENT_CATALOG`, contracts README, permissions, audit-consent spec, and `test_audit.py` — one missing piece fails the lockstep tests.
- **PR budget**: module + routes + schemas + seed extension + ~4 spec deltas + 4 test files will likely exceed 400 lines; `sdd-tasks` should forecast chained slices (seed+fixtures → domain+unit → service/repository+persistence → API+audit+permissions).
- **Docker image staleness**: any `services/api` change requires `docker compose build api` (phantom-failure trap from AGENTS.md).
- **`data-schema` spec conflict**: the ratified "F5/F6 empty after seed" scenario becomes obsolete when F5 seeds recommendation tables — MUST be MODIFIED in the F5 delta (reports/report_templates remain 0).

## Ready for Proposal

**Yes** — scope fully verified against real code; nothing in HANDOFF-F4/config contradicts F5. What the proposal/spec must ratify: (a) fit-score formula + rounding + ordering, (b) closed rule_type/params vocabulary, (c) `recommendation.generated` event + `view_recommendations` capability ratification, (d) the recommendation disclaimer source (code constant vs migration 0006), (e) seed extension shape (program count, rule fixture). Recommend starting the change with `proposal`, keeping `exploration → proposal → spec → design → tasks → apply → verify → archive`.

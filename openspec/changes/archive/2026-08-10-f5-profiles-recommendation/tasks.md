# Tasks: F5 - Perfiles/Recomendación

## Review Workload Forecast

Estimated: ~1,300 lines (5 slices)
TDD RED->GREEN; 1 commit/unit; openspec artifacts untracked until archive.
Isolation: reserve `evaluado_21..30`; delta counts; score-trigger first (seeded: no runs).

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

| Unit | Goal | Test command | Harness | Rollback |
|------|------|--------------|---------|----------|
| 1 | Seed fixtures/loader/reset | `pytest tests/test_seed.py` | `compose run api app.seed [--reset]` | Revert fixtures/loader/test |
| 2 | Pure domain+errors | `pytest tests/test_recommendation_domain.py` | N/A (pure, no DB) | Remove domain/errors/test |
| 3 | Repository | `pytest tests/test_recommendation_repository.py` | compose run api | Remove repository/test |
| 4 | Service+ratification lockstep | `pytest tests/test_recommendation_service.py tests/test_auth.py tests/test_audit.py` | compose run api | Revert service/permissions/audit/README/tests |
| 5 | API schemas/routes | `pytest tests/test_recommendation_api.py` | TestClient+PG | Remove schemas/routes/router.py edit |

## Phase 1: Seed [F5]

- [x] 1.1 RED `tests/test_seed.py`: 4-6 programs (`program:<slug>` keys) + active `rule:<program-key>:<n>` (exact labels/`overall`), `synthetic=true`/`source='seed'`, results 0; reseed idempotent (+1 manifest row, ids/counts stable); `--reset` preflight `seed_reset_dependency_conflict` on runtime refs, no deletion; reset seed-owned only
- [x] 1.2 GREEN `app/seed/fixtures/programs.json` + `recommendation_rules.json` (weighted, incl. missing-weight)
- [x] 1.3 GREEN `app/seed/loader.py`: `SEED_TABLES += {recommendation_rules, recommendation_results}`, bump `SEED_VERSION`, manifest+reset scope; no migration

## Phase 2: Domain [F5]

- [x] 2.1 RED `tests/test_recommendation_domain.py`: vocabulary `percentile_min`; exact scales+`overall`; `min_percentile` 1-99; weight default 1.0, <=0 -> error; unknown type/scale/params -> `recommendation_integrity_error` (never skipped)
- [x] 2.2 RED same: fit = Σ RH(100·w·sat/Σw) - vector 33.33/0.00->33.33; zero-rule excluded; satisfied iff pct>=min; DESC/name ASC; trace `"{scale} ≥ {min} pct: cumple|no cumple ({pct} pct)"` rule id ASC; pure, inputs unmutated
- [x] 2.3 GREEN `app/modules/recommendation/{__init__,errors,domain}.py`

## Phase 3: Repository [F5]

- [x] 3.1 RED `tests/test_recommendation_repository.py` (reserve `evaluado_21..30`; score-trigger first): reads latest run + programs + active rules; one tx, row per rule (`fit_score` Numeric(5,2), justification, runtime flags, shared `created_at`); multi-generation legal
- [x] 3.2 GREEN `app/modules/recommendation/repository.py`

## Phase 4: Service [F5]

- [x] 4.1 RED `tests/test_recommendation_service.py`: one tx, row per rule + `recommendation.generated` (ids/counts/timestamps only); audit failure rolls back -> `INTERNAL_ERROR`
- [x] 4.2 RED same: idempotency `session:{id}` - replay -> original DTO, 0 new rows/events; diff body -> `idempotency_key_reused`; new key -> 2nd generation
- [x] 4.3 RED same: foreign evaluado -> FORBIDDEN + `auth.denied`; missing/unscored -> identical `resource_not_found`; in_progress -> `session_not_completed`; GET latest - anchor `created_at` DESC/`id` DESC, fit DESC/name ASC; no generation ≡ `resource_not_found`
- [x] 4.4 GREEN `app/modules/recommendation/service.py`
- [x] 4.5 Lockstep (one commit): `view_recommendations` -> `permissions.py` + README §6 + `tests/test_auth.py`; `recommendation.generated` -> `audit.py` EVENT_CATALOG + README §3 + `tests/test_audit.py`

## Phase 5: API [F5]

- [x] 5.1 RED `tests/test_recommendation_api.py`: POST - 200 persisted; replay/key-reuse/new-key; 404/409/403; GET - 404/403; DTO (`session_id`, `generated_at`, disclaimer, `items[{program_id,program_name,program_code,fit_score,justification}]`); disclaimer verbatim (never `norm_note`); recursive no-leak, percentiles only in justification
- [x] 5.2 GREEN `app/schemas/recommendations.py` + `app/api/routes/recommendations.py` (`require_roles`, `Idempotency-Key`) + `app/api/router.py`

## Phase 6: Verification [F5]

- [x] 6.1 Slice `-k "recommendation or program"` green; full `scripts/test.ps1` twice; diff scope: no F2-F4 edits beyond listed; 2 inherited `test_web.py` failures = debt (no fix); F6/web UI out of scope; threat matrix all-N/A

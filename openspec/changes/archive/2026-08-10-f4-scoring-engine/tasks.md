# Tasks: F4 — Scoring Engine & Results API

## Review Workload Forecast

Estimated changed lines: ~1,400 total (4 slices × 300–450; threshold 800)

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Test command | Runtime harness | Rollback boundary |
|------|------|--------------|-----------------|-------------------|
| 1 | Pure engine (domain) | `pytest tests/test_scoring_domain.py` | N/A — pure unit, no DB | Remove domain.py + test |
| 2 | Errors + repository | `pytest tests/test_scoring_repository.py` | compose run api (real PG) | Remove errors/repository + test |
| 3 | Service + audit | `pytest tests/test_scoring_service.py` | compose run api (real PG/audit) | Revert service/audit/README/test_audit |
| 4 | API routes/schemas | `pytest tests/test_results_api.py` | TestClient + PG via compose | Remove routes/schemas + router.py edit |

## Phase 1: Foundation — Errors & Repository [F4]

- [x] 1.1 Create `services/api/app/modules/scoring/errors.py`: `session_not_completed`, `reference_unavailable`, typed integrity `ApiError`s; reuse `resource_not_found` (F3 pattern)
- [x] 1.2 RED `services/api/tests/test_scoring_repository.py`: seed — RS-TP-S-01 = 30 `reference_values` (10 per-scale + 20 overall), labels = `items.json`, `norm_note` verbatim
- [x] 1.3 RED same file: ScoreRun `pending→completed`, `synthetic=False`/`source='runtime'`, multi-run legal; reads via existing consumers
- [x] 1.4 GREEN `services/api/app/modules/scoring/repository.py`: mapped session/version/option/reference/ScoreRun reads — no F2/F3 edits

## Phase 2: Core — Pure Engine [F4]

- [x] 2.1 RED `services/api/tests/test_scoring_domain.py`: per-scale — raw=Σ4 values, z=(raw−mean)/sd (sd=0→0), p=clamp(RH(100Φ),1,99) (`math.erf`, ≤1e-12), T=RH(50+10z), ene=clamp(ceil(7p/100),1,7); raw14→z1,p84,T60,ene6
- [x] 2.2 RED same file: overall RH(1+19(Σraw−4n)/16n) — Σ60→11, Σ20→1, Σ100→20; exact row lookup; unknown label/missing/non-finite → typed error
- [x] 2.3 RED same file: double-run identical, inputs unmutated, no DB/I/O/clock imports
- [x] 2.4 GREEN `services/api/app/modules/scoring/domain.py` + `__init__.py`: frozen `ScoringInput`/`ScoreResult`, pure funcs, RH=floor(x+0.5), `math.erf` Φ

## Phase 3: Service Orchestration [F4]

- [x] 3.1 RED `services/api/tests/test_scoring_service.py`: one tx `pending→completed` + `computed_at` + runtime flags; exactly one `scoring.run` (aggregate-only); audit failure rolls back run
- [x] 3.2 RED same file: `in_progress`→`session_not_completed` (no leak); missing→`resource_not_found`; foreign evaluado→FORBIDDEN, no run
- [x] 3.3 RED same file: idempotency `session:{id}` — replay same key+body→original DTO, 1 run + 1 event; diff body→`idempotency_key_reused`; new key→2nd run + 2nd event
- [x] 3.4 RED same file: latest run = `computed_at` DESC, `id` DESC (tie)
- [x] 3.5 GREEN `services/api/app/modules/scoring/service.py`: reads→domain→tx (`audit.record(..., commit=False)`), owner checks, DTO projection
- [x] 3.6 Lockstep (ADR-05): `scoring.run` → `app/core/audit.py` EVENT_CATALOG + `packages/contracts/README.md` + `tests/test_audit.py`

## Phase 4: API Integration [F4]

- [x] 4.1 RED `services/api/tests/test_results_api.py`: POST `/api/v1/results/{session_id}/score` — 200 persisted; 409 `session_not_completed`; 404 `resource_not_found`; 403 foreign; replay; key-reuse
- [x] 4.2 RED same file: GET latest 200 + `norm_note` verbatim; unscored ≡ missing 404; recursive no-leak (no 1–5 values/keys/ids/mapping/item content); `test_session_api.py:375` intact
- [x] 4.3 GREEN `services/api/app/schemas/results.py`: DTOs — per-scale label/raw/z/percentile/t_score/eneatype, overall, run{id,status,computed_at}, reference_set_id, norm_note
- [x] 4.4 GREEN `services/api/app/api/routes/results.py` + `app/api/router.py`: POST + GET, `require_roles(...)`, `Idempotency-Key` dep

## Phase 5: Verification & Debt [F4]

- [x] 5.1 Slice `-k "scoring or reference or results"` green; full suite `scripts/test.ps1` twice
- [x] 5.2 Diff scope: no F2/F3 module or seed changes; document 2 inherited `test_web.py` failures as debt (no fix)

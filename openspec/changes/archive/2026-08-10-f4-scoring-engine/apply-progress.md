# Apply Progress: F4 — Scoring Engine & Results API

## Work Unit

- Change: `2026-08-10-f4-scoring-engine`
- Slice: 1 of 4 — Pure engine (domain)
- Strategy: stacked-to-main
- Assigned tasks: 2.1 → 2.4
- Mode: Strict TDD (`pytest`)
- Boundary: create only `services/api/app/modules/scoring/domain.py`,
  `services/api/app/modules/scoring/__init__.py`, and
  `services/api/tests/test_scoring_domain.py`; later F4 slices own all other
  scoring, API, audit, seed, and F2/F3 files.

## Completed Tasks

- [x] 2.1 RED — per-scale raw/direct/transformed chain, CDF vectors, clamps,
  and pinned `raw=14 → z=1, percentile=84, T=60, eneatype=6`.
- [x] 2.2 RED — overall rescale and exact lookup, bounds, unknown labels,
  missing rows, and invalid/non-finite input errors.
- [x] 2.3 RED — deterministic repeat, input immutability, frozen dataclasses,
  and no DB/I/O/clock imports.
- [x] 2.4 GREEN — frozen dataclasses and pure scoring functions using
  `math.erf` and `floor(x + 0.5)`.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 2.1 | `tests/test_scoring_domain.py` | Unit | N/A — new file | ✅ written first; collection failed because scoring module did not exist (`1 error`) | ✅ `19 passed` | ✅ happy path, `sd=0`, CDF vectors, half-up ties, and percentile/eneatype clamps | ✅ final focused run `14 passed` |
| 2.2 | `tests/test_scoring_domain.py` | Unit | N/A — new file | ✅ written first; shared RED run (`1 error`) | ✅ `19 passed` | ✅ overall `Σraw=60→11`, minimum/maximum bounds, exact row, missing row, unknown label, and non-finite inputs | ✅ final focused run `14 passed` |
| 2.3 | `tests/test_scoring_domain.py` | Unit | N/A — new file | ✅ written first; shared RED run (`1 error`) | ✅ `19 passed` | ✅ double-run equality, deep-copy equality, frozen assignments, and forbidden-module check | ✅ final focused run `14 passed` |
| 2.4 | `tests/test_scoring_domain.py` | Unit | N/A — new file | ✅ prerequisite tests for 2.1–2.3 existed before production code | ✅ `19 passed` after implementation fixes | ✅ all preceding cases exercised the generalized implementation | ✅ simplified domain normalization; final run `14 passed` |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command | `pytest tests/test_scoring_domain.py` with `services/api/.venv/Scripts` on `PATH` → `14 passed in 0.13s` |
| Runtime harness | `N/A` — this slice is a pure function boundary; it intentionally uses no database, compose service, HTTP route, clock, or external runtime |
| Rollback boundary | Remove `services/api/app/modules/scoring/domain.py`, `services/api/app/modules/scoring/__init__.py`, and `services/api/tests/test_scoring_domain.py`; revert only tasks/progress artifact marks if required |

## Implementation Notes

- `ScoringInput` and nested score types are frozen dataclasses.
- Per-scale statistics join by exact label when `scale_references` are supplied;
  `sd=0` produces `z=0`.
- Percentile uses `math.erf` in double precision and the ratified RH rule.
- Overall transformed values come from an exact raw-keyed lookup; no
  interpolation or extrapolation is performed.
- No F2/F3 module, seed, repository, service, route, schema, or error file was
  modified.

## Review / PR Boundary

- Current PR: stacked slice 1, target `main` after the prior slice chain state
  (no prior F4 slice exists).
- Start: no scoring domain or domain tests.
- Finish: pure domain tests green and implementation independently removable.
- Follow-up: slice 2 owns scoring errors and repository integration.
- Out of scope: every database, service, audit, API, seed, and existing F2/F3
  module change.

## Status

4/18 F4 tasks complete. Ready for slice 2; not ready for final verification.

---

## Work Unit 2: Errors + Repository

- Change: `2026-08-10-f4-scoring-engine`
- Slice: 2 of 4 — Errors + repository
- Strategy: stacked-to-main
- Assigned tasks: 1.1 → 1.4
- Mode: Strict TDD (`pytest`)
- Boundary: create only `services/api/app/modules/scoring/errors.py`,
  `services/api/app/modules/scoring/repository.py`, and
  `services/api/tests/test_scoring_repository.py`; no domain, service, route,
  schema, seed, or F2/F3 module changes.

## Cumulative Completed Tasks

- [x] 2.1 RED — per-scale raw/direct/transformed chain, CDF vectors, clamps,
  and pinned `raw=14 → z=1, percentile=84, T=60, eneatype=6`.
- [x] 2.2 RED — overall rescale and exact lookup, bounds, unknown labels,
  missing rows, and invalid/non-finite input errors.
- [x] 2.3 RED — deterministic repeat, input immutability, frozen dataclasses,
  and no DB/I/O/clock imports.
- [x] 2.4 GREEN — frozen dataclasses and pure scoring functions using
  `math.erf` and `floor(x + 0.5)`.
- [x] 1.1 — stable scoring `ApiError` factories for
  `session_not_completed`, `reference_unavailable`, typed integrity failures,
  and the reused `resource_not_found` token.
- [x] 1.2 RED — PostgreSQL seed contract for exactly 30 `RS-TP-S-01`
  reference values, fixture-matching scale labels, and verbatim `norm_note`.
- [x] 1.3 RED — runtime `ScoreRun` pending/completed transition, flags,
  multi-run legality, and read-back of pinned scoring inputs.
- [x] 1.4 GREEN — repository adapters reuse `SessionRepository` and
  `fixture_projection` for session/version/response/reference reads and expose
  runtime ScoreRun persistence/latest-run reads.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | `tests/test_scoring_repository.py` | Integration + error-unit | N/A — new file | ✅ factories written first; collection failed because `errors.py` did not exist (`1 error`) | ✅ Docker run `4 passed` | ✅ conflict, internal, not-found, and details paths | ✅ stable factory aliases kept without changing tokens |
| 1.2 | `tests/test_scoring_repository.py` | PostgreSQL integration | N/A — new file | ✅ seed assertions written first; shared collection RED (`1 error`) | ✅ Docker run `4 passed` | ✅ exact row count, per-scale counts, labels, norm note, and overall raw range | ✅ UUID/string fixture assertion corrected; final run remained green |
| 1.3 | `tests/test_scoring_repository.py` | PostgreSQL integration | N/A — new file | ✅ ScoreRun assertions written first; shared collection RED (`1 error`) | ✅ Docker run `4 passed` | ✅ pending row, completed row, runtime flags, two rows, and latest read | ✅ explicit completed/pending row selection avoids UUID ordering assumptions |
| 1.4 | `tests/test_scoring_repository.py` | PostgreSQL integration | N/A — new file | ✅ repository import was absent during RED (`1 error`) | ✅ Docker run `4 passed` | ✅ delegated F3 reads, private fixture mapping, domain input adaptation, and missing-reference error | ✅ scale labels are joined from loaded immutable `Scale` rows because `fixture_projection` intentionally omits labels |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command | `pytest tests/test_scoring_repository.py` with `services/api/.venv/Scripts` available → `1 passed, 3 skipped` locally because no host `PSICO_DATABASE_URL` was reachable; no local DB result treated as acceptance evidence |
| Runtime harness command/scenario | `docker compose run --rm -v "${PWD}:/repo:ro" api pytest /repo/services/api/tests/test_scoring_repository.py` against the compose PostgreSQL; `4 passed, 1 warning` (read-only `.pytest_cache` warning only) |
| RED evidence | First collection run: `1 error`, missing `app.modules.scoring.repository`; after adding error assertions: `1 error`, missing `app.modules.scoring.errors` |
| GREEN evidence | Final authoritative integration run: `4 passed` |
| Rollback boundary | Remove `services/api/app/modules/scoring/errors.py`, `services/api/app/modules/scoring/repository.py`, and `services/api/tests/test_scoring_repository.py`; revert only this slice's task/progress marks if needed |

## Implementation Notes

- `ScoringRepository` delegates session/version/response-option reads to the
  unchanged F3 `SessionRepository` and builds the private fixture through the
  unchanged `fixture_projection` consumer.
- Scale labels are recovered from the loaded immutable version rows rather than
  added to the public/private projection contract.
- Reference rows are read-only; only `RS-TP-S-01` is accepted by the required
  reference loader, and runtime ScoreRuns are explicitly `synthetic=False` and
  `source='runtime'`.
- The repository adapts reference rows into the frozen `ScoringInput` contract
  for the next service slice while keeping domain computation outside this
  module.

## Review / PR Boundary

- Current PR: stacked slice 2 of 4, targeting the preceding/main chain state.
- Start: slice 1's pure scoring domain exists; no scoring errors or repository.
- Finish: error factories and repository integration are green against real
  PostgreSQL and independently removable.
- Follow-up: slice 3 owns service orchestration, audit, and idempotency.
- Out of scope: routes, schemas, service, audit catalog, seed changes, and all
  existing F2/F3 modules.

## Status

8/18 F4 tasks complete. Ready for slice 3; not ready for final verification.

---

## Work Unit 3: Service Orchestration + Audit Lockstep

- Change: `2026-08-10-f4-scoring-engine`
- Slice: 3 of 4 — Service orchestration + audit lockstep
- Strategy: stacked-to-main
- Assigned tasks: 3.1 → 3.6
- Mode: Strict TDD (`pytest`)
- Commit: `c8b1a97` (`feat(api): add scoring service orchestration and ratify scoring.run audit event`)
- Boundary: create only `services/api/app/modules/scoring/service.py` and
  `services/api/tests/test_scoring_service.py`; modify only the scoring audit
  catalog, contracts §3, and the audit catalog test. No routes, schemas, seed,
  repository, domain, errors, or F2/F3 modules were changed.

## Cumulative Completed Tasks

- [x] 2.1 RED — per-scale raw/direct/transformed chain, CDF vectors, clamps,
  and pinned `raw=14 → z=1, percentile=84, T=60, ene=6`.
- [x] 2.2 RED — overall rescale and exact lookup, bounds, unknown labels,
  missing rows, and invalid/non-finite input errors.
- [x] 2.3 RED — deterministic repeat, input immutability, frozen dataclasses,
  and no DB/I/O/clock imports.
- [x] 2.4 GREEN — frozen dataclasses and pure scoring functions using
  `math.erf` and `floor(x + 0.5)`.
- [x] 1.1 — stable scoring `ApiError` factories for `session_not_completed`,
  `reference_unavailable`, typed integrity failures, and `resource_not_found`.
- [x] 1.2 RED — PostgreSQL seed contract for 30 `RS-TP-S-01` reference values,
  fixture-matching labels, and verbatim `norm_note`.
- [x] 1.3 RED — runtime `ScoreRun` pending/completed transition, flags,
  multi-run legality, and pinned scoring reads.
- [x] 1.4 GREEN — repository adapters for session/version/response/reference
  reads and runtime ScoreRun persistence/latest-run reads.
- [x] 3.1 RED — transactional pending→completed scoring, computed timestamp,
  runtime flags, one aggregate-only audit event, and audit-failure rollback.
- [x] 3.2 RED — stable incomplete/missing/foreign-session behavior without run
  creation or response leakage.
- [x] 3.3 RED — `session:{id}` idempotency replay, body conflict, and distinct
  key independent-run semantics.
- [x] 3.4 RED — deterministic latest completed run selection with timestamp
  descending and UUID id descending tie-break.
- [x] 3.5 GREEN — scoring service reads context, invokes the pure domain,
  persists the run, projects the DTO, and commits audit/idempotency together.
- [x] 3.6 GREEN — `scoring.run` ratified in `EVENT_CATALOG`, contracts §3, and
  `test_audit.py` in lockstep.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 3.1 | `tests/test_scoring_service.py` | PostgreSQL integration | N/A — new file | ✅ written first; collection failed because `service.py` did not exist (`1 error`) | ✅ final focused run `5 passed` | ✅ completed run and forced audit failure rollback | ✅ transaction rollback and aggregate DTO helpers extracted |
| 3.2 | `tests/test_scoring_service.py` | PostgreSQL integration | N/A — new file | ✅ written first; shared RED collection (`1 error`) | ✅ final focused run `5 passed` | ✅ in-progress, missing, and foreign-owner branches | ✅ owner gate precedes context reads and no-leak errors |
| 3.3 | `tests/test_scoring_service.py` | PostgreSQL integration | N/A — new file | ✅ written first; shared RED collection (`1 error`) | ✅ final focused run `5 passed` | ✅ replay, same-key body conflict, and new-key second run/event | ✅ canonical request bodies delegated to the existing idempotency adapter |
| 3.4 | `tests/test_scoring_service.py` | PostgreSQL integration | N/A — new file | ✅ written first; shared RED collection (`1 error`) | ✅ final focused run `5 passed` | ✅ equal `computed_at` values exercise id descending tie-break | ✅ latest selection delegated to existing repository ordering |
| 3.5 | `services/api/tests/test_scoring_service.py` | PostgreSQL integration | N/A — new file | ✅ prerequisite RED existed before production code | ✅ `5 passed` | ✅ all service scenarios exercise real repository/domain/transaction paths | ✅ no locking added; helpers isolate projection and metadata |
| 3.6 | `services/api/tests/test_audit.py` | Pure + PostgreSQL integration | ✅ baseline `11 passed` | ✅ existing catalog equality test was extended before catalog green | ✅ `11 passed` with `scoring.run` | ➖ Structural lockstep has one deterministic catalog output | ✅ catalog/docs/test entries kept adjacent and identical |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_scoring_service.py` → `5 passed, 1 warning` (read-only `.pytest_cache` warning only) |
| Audit lockstep command | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_audit.py` → `11 passed, 1 warning` (catalog and DB audit tests green) |
| Runtime harness command/scenario | The focused commands ran against healthy Docker Compose PostgreSQL and exercised real `ScoreRun`, `IdempotencyRecord`, and `audit_log` persistence; no mocks replaced the database boundary. |
| RED evidence | `docker compose run --rm -v "${PWD}:/repo:ro" api pytest /repo/services/api/tests/test_scoring_service.py` → collection failed with `1 error`, `ModuleNotFoundError: app.modules.scoring.service`. |
| Rollback boundary | Revert `services/api/app/modules/scoring/service.py`, `services/api/tests/test_scoring_service.py`, `services/api/app/core/audit.py` catalog entry, `packages/contracts/README.md` §3 entry, and `services/api/tests/test_audit.py` catalog entry; leave domain, errors, repository, seed, routes, schemas, and F2/F3 modules untouched. |

## Implementation Notes

- The service creates a pending `ScoreRun`, computes through the existing pure
  domain, marks the row completed, records `audit.record(..., commit=False)`,
  stores the idempotency response, and commits once; any failure rolls back the
  whole transaction.
- Evaluado ownership is enforced in the service; admin and psicólogo retain
  operational read/score access for any session, while missing and unscored
  results use the same `resource_not_found` token.
- The public DTO projects only labels and score fields plus run/reference/norm
  metadata. Audit metadata contains ids, counts, and `computed_at`, never raw
  response values, option keys, item content, or computed scores.
- The API image was rebuilt before the authoritative Docker runs. The wrapper
  path without `/repo` had no tests in `/app`; the documented `/repo` mount and
  workdir command is the authoritative harness.

## Review / PR Boundary

- Current PR: stacked slice 3 of 4, targeting the preceding slice in the
  `stacked-to-main` chain.
- Start: slices 1–2 provide pure domain, errors, and repository adapters; no
  scoring service or `scoring.run` catalog entry existed.
- Finish: service tests and audit lockstep tests are green against real
  PostgreSQL, and the service/audit/catalog unit is independently removable.
- Follow-up: slice 4 owns results schemas/routes/router integration.
- Out of scope: domain, errors, repository, routes, schemas, seed, and every
  F2/F3/catalog/session module.

## Status

14/18 F4 tasks complete. Ready for slice 4; not ready for final verification.

---

## Work Unit 4: API Routes + Schemas

- Change: `2026-08-10-f4-scoring-engine`
- Slice: 4 of 4 — API routes + schemas
- Strategy: stacked-to-main
- Assigned tasks: 4.1 → 4.4
- Mode: Strict TDD (`pytest`)
- Commit: `e212f9e` (`feat(api): add results API routes and schemas`)
- Boundary: create only `services/api/app/schemas/results.py`,
  `services/api/app/api/routes/results.py`, and
  `services/api/tests/test_results_api.py`; modify only
  `services/api/app/api/router.py` to register the results router under
  `/api/v1`. Previous Work Units 1–3 and their evidence remain preserved above.

## Cumulative Completed Tasks

- [x] Work Units 1–3: tasks 1.1 → 3.6, as recorded in the preceding sections.
- [x] 4.1 RED — POST score trigger: persisted 200, stable incomplete/missing/
  foreign errors, required idempotency, replay, key reuse conflict, and new-key
  independent run.
- [x] 4.2 RED — latest GET, verbatim `norm_note`, unscored/missing no-leak,
  foreign read denial, recursive payload deny-list, and preserved session boundary.
- [x] 4.3 GREEN — strict Pydantic DTOs for per-scale, overall, run, reference,
  and norm metadata.
- [x] 4.4 GREEN — protected POST/GET routes with `require_roles(...)`,
  `Idempotency-Key`, service error mapping, and `/api/v1/results` registration.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 4.1 | `tests/test_results_api.py` | TestClient + PostgreSQL integration | N/A — new file | ✅ tests written before production; initial route-absent run `10 failed, 13 warnings` | ✅ final focused run `7 passed, 16 warnings` | ✅ completed, incomplete/missing/foreign, idempotency replay/conflict/new-key, and required-key paths | ✅ compacted tests into one bounded API unit; final run remained green |
| 4.2 | `tests/test_results_api.py` | TestClient + PostgreSQL integration | N/A — new file | ✅ same pre-route RED run `10 failed, 13 warnings` | ✅ final focused run `7 passed, 16 warnings` | ✅ latest explicit run id, verbatim note, missing/unscored equivalence, recursive deny-list, and session boundary | ✅ payload assertions use recursive keys and seeded content/option ids; final run remained green |
| 4.3 | `tests/test_results_api.py` | Pydantic response validation through HTTP | N/A — new file | ✅ response contract failed while the route/schema surface was absent | ✅ route DTO validation passed in the final `7 passed` run | ✅ exact top-level/nested DTO shape, datetime/UUID serialization, and forbidden extra payload keys | ✅ shared `ResultsModel` config and focused compatibility aliases kept the schema strict |
| 4.4 | `tests/test_results_api.py` | TestClient + PostgreSQL integration | Safety net `tests/test_session_api.py` → `9 passed, 16 warnings` | ✅ route behavior was exercised before router registration | ✅ final focused run `7 passed, 16 warnings` | ✅ role gates, own-only service enforcement, header dependency, mapper errors, and router registration | ✅ shared `_json_result` adapter mirrors the sessions route convention |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_results_api.py` → `7 passed, 16 warnings in 11.28s` |
| Runtime harness command/scenario | The same `/repo`-mounted compose command ran `TestClient` against the API and real PostgreSQL, covering persisted `ScoreRun`, audit, idempotency, role, latest-run, and no-leak paths → `7 passed, 16 warnings` |
| Safety-net command | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_session_api.py` → `9 passed, 16 warnings in 12.12s`; `test_session_api.py:375` boundary remains green |
| RED evidence | Before production code, the results suite collected and ran with the route absent → `10 failed, 13 warnings`; failures were expected contract failures, not infrastructure errors |
| GREEN evidence | Final compacted work-unit suite against compose PostgreSQL → `7 passed, 16 warnings` |
| Rollback boundary | Remove `services/api/app/schemas/results.py`, `services/api/app/api/routes/results.py`, and `services/api/tests/test_results_api.py`; revert only the results import/include edit in `services/api/app/api/router.py` |

## Implementation Notes

- `ResultsResponse` exposes only the service's public scores and metadata:
  labels, raw/direct/transformed scores, run metadata, reference id, and the
  verbatim research-only `norm_note`.
- The POST route accepts an optional JSON object, passes the `Idempotency-Key`
  through the existing `session:{id}` service scope, and validates both fresh
  and replay payloads with the same strict DTO.
- The GET route delegates latest-run selection and evaluado ownership to the
  existing scoring service; `ApiError` tokens therefore use the existing mapper
  without changes to `errors.py`.
- The latest-run API test pins the second response's explicit run id and moves
  only that run to a future timestamp; it does not duplicate the repository
  `ORDER BY` expression.
- No API image rebuild was needed because every authoritative test used the
  repository `/repo:ro` mount, as established by prior F4 integration slices.
- Expected warnings are the repository's existing Starlette/httpx deprecation,
  dev JWT key-length warnings, and read-only pytest-cache warnings.

## Review / PR Boundary

- Current PR: stacked-to-main slice 4 of 4, starting from the slice 3 commit
  `c8b1a97`.
- Start: slices 1–3 provide the pure engine, scoring errors/repository, service
  orchestration, idempotency, and `scoring.run` audit contract; no results API
  route or schema existed.
- Finish: results DTOs, protected POST/GET routes, router registration, and
  PostgreSQL-backed TestClient coverage are independently green and removable.
- Out of scope: domain, errors, repository, service, audit, seed, migrations,
  catalog, sessions, F2, F3, and verification/debt tasks 5.1–5.2.

## Status

18/18 implementation tasks complete. Ready for `sdd-verify`; Phase 5
verification/debt tasks remain pending.

---

## Remediation Work Unit: F4 Test Isolation

- Change: `2026-08-10-f4-scoring-engine`
- Scope: remediate the shared seeded-database collision in F4 scoring tests
- Mode: Strict TDD (`pytest`)
- Strategy: stacked-to-main; bounded correction slice
- Assigned tasks: `5.1` → `5.2`
- Boundary: tests-only changes in `test_scoring_repository.py` and
  `test_scoring_service.py`; no production, conftest, F2/F3, seed, or web edits

## Cumulative Completed Tasks

- [x] Work Units 1–4: implementation tasks `1.1` → `4.4`, preserved in the
  preceding sections.
- [x] 5.1 — the combined F4 selector is green after isolating the repository
  and service count assertions from profiles used by `test_results_api.py`.
- [x] 5.2 — scope remains tests-only; the two inherited `test_web.py` failures
  remain documented debt and were not changed.

## Root Cause and Fix

- The session-scoped `seeded_db_session` shares one database across the
  selector. `test_results_api.py` scores `evaluado_01` before the repository
  and service count assertions, leaving prior `score_runs` and `scoring.run`
  audit rows on that profile.
- The repository helper now selects the deterministic seeded profile
  `evaluado_19`, which is not touched by `test_results_api.py`.
- The service count/audit test now uses the deterministic seeded profile
  `evaluado_20`, which is not touched by `test_results_api.py` or the
  repository remediation test.
- All absolute assertions remain unchanged: two repository-owned rows,
  completed/pending state, runtime flags, latest-run ordering, one service
  run audit event, and aggregate-only metadata are still asserted.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 5.1 | `services/api/tests/test_scoring_repository.py`, `test_scoring_service.py` | PostgreSQL integration | ✅ isolated baselines: repository `4 passed`, service `5 passed`, results `7 passed` | ✅ existing combined regression reproduced `2 failed, 30 passed, 147 deselected` (`3` repository rows and `2` service audit events) | ✅ combined selector `32 passed, 147 deselected` | ✅ separate seeded profiles `evaluado_19` and `evaluado_20`; focused files `4 + 5 + 7 passed` | ✅ scoped helper selection and local service profile; no assertion weakened |
| 5.2 | Same files plus full-suite harness | PostgreSQL integration | ✅ pre-fix full-suite baseline was the verified F4 regression | ✅ same combined-selector RED evidence | ✅ two full-suite runs each `179 collected, 177 passed, 2 failed, 75 warnings`; only inherited `test_web.py` failures | ✅ repeatability held across both fresh full-suite database runs | ✅ no conftest, production, F2/F3, seed, or web changes |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command | `powershell -ExecutionPolicy Bypass -File scripts/test.ps1 -k "scoring or reference or results"` → `32 passed, 147 deselected, 16 warnings`; wrapper exit `0` |
| Focused file triangulation | Compose-mounted pytest runs → repository `4 passed, 1 warning`; service `5 passed, 1 warning`; results API `7 passed, 16 warnings` |
| Runtime harness command/scenario | `powershell -ExecutionPolicy Bypass -File scripts/test.ps1` run twice against the real Docker Compose PostgreSQL; each run → `179 collected, 177 passed, 2 failed, 75 warnings`, wrapper exit `0`; failures only `test_web.py::test_page_is_spanish` and `test_web.py::test_page_never_leaks_stack_trace` |
| Rollback boundary | Revert only the profile selector/import change in `services/api/tests/test_scoring_repository.py` and the `evaluado_20` setup in `services/api/tests/test_scoring_service.py`; no unrelated behavior is removed |

## Review / PR Boundary

- One tests-only remediation commit; review budget is low and autonomous.
- Start: two order-dependent absolute-count assertions reused `evaluado_01`.
- Finish: deterministic, non-overlapping seeded profiles preserve absolute
  count semantics and all required selector/full-suite evidence is repeatable.
- Out of scope: `conftest.py`, production code, all F2/F3 tests/modules, seed
  data, web files, and the inherited `test_web.py` failures.

## Status

20/20 F4 tasks complete. Ready for `sdd-verify` re-run; archive remains blocked
until the remediation evidence is consumed by verification.

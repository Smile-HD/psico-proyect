# Apply Progress: F5 — Declarative Profiles and Recommendation

**Change**: `2026-08-10-f5-profiles-recommendation`  
**Work unit**: Unit 5 of 5 — API schemas + routes  
**Artifact store**: hybrid  
**Mode**: Strict TDD (`pytest`)  
**Delivery**: stacked-to-main; one commit for this work unit  
**Commit**: `1e4e95d` (`feat(api): add recommendation API routes and schemas`)

## Completed Tasks

- [x] 1.1 RED `services/api/tests/test_seed.py`: synthetic program/rule content, exact scale vocabulary, empty runtime results, idempotency, manifest counts, reset dependency conflict, and seed-owned reset behavior.
- [x] 1.2 GREEN `services/api/app/seed/fixtures/programs.json` and `recommendation_rules.json`: five programs, ten active weighted rules, and missing-weight cases.
- [x] 1.3 GREEN `services/api/app/seed/loader.py`: recommendation table scope, seed version `1.1.0`, fixture loading, manifest counts, and reset preflight/deletion scope.
- [x] 2.1 RED `services/api/tests/test_recommendation_domain.py`: closed rule vocabulary, exact scales, percentile bounds, default/malformed weights, and typed integrity failures.
- [x] 2.2 RED `services/api/tests/test_recommendation_domain.py`: rounded weighted fit, zero-rule exclusion, threshold semantics, ordering, rule-id trace ordering, purity, and determinism.
- [x] 2.3 GREEN `services/api/app/modules/recommendation/{__init__,errors,domain}.py`: frozen snapshots, pure evaluator, contribution traces, and stable error factories.
- [x] 3.1 RED `services/api/tests/test_recommendation_repository.py`: latest completed score-run raw JSONB, program catalog, active-rule filtering/order, transactional per-rule writes, runtime flags, Numeric precision, shared generation timestamp, rollback, and multi-generation selection.
- [x] 3.2 GREEN `services/api/app/modules/recommendation/repository.py`: F4-backed reads, deterministic catalog/rule adapters, caller-owned generation transaction, runtime result persistence, and `created_at DESC, id DESC` latest-generation anchor.
- [x] 4.1 RED `services/api/tests/test_recommendation_service.py`: atomic per-rule generation, aggregate-only `recommendation.generated`, and audit-failure rollback with `INTERNAL_ERROR`.
- [x] 4.2 RED `services/api/tests/test_recommendation_service.py`: `session:{id}` idempotency replay, same-key body conflict, and independent new-key generation.
- [x] 4.3 RED `services/api/tests/test_recommendation_service.py`: ownership denial/audit, indistinguishable availability errors, in-progress conflict, and deterministic latest read projection.
- [x] 4.4 GREEN `services/api/app/modules/recommendation/service.py`: transactional orchestration, ownership checks, idempotency, domain projection, aggregate audit, and exact disclaimer DTO.
- [x] 4.5 Lockstep `permissions.py`, `packages/contracts/README.md`, `test_auth.py`, `audit.py`, and `test_audit.py`: ratified `view_recommendations` and `recommendation.generated` together.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `services/api/tests/test_seed.py` | Integration + pure fixture checks | ✅ 12 baseline tests passed | ✅ 10 passed / 8 failed before fixtures and loader | ✅ 18 passed after implementation | ✅ Programs, exact scales, missing weight, idempotent reseed, runtime dependency conflict, and seed-owned reset paths | ✅ Assertions and formatting cleaned; 18 passed afterward |
| 1.2 | `services/api/tests/test_seed.py` | Pure fixture structure | N/A (new fixture contract) | ✅ Covered by the 1.1 RED suite | ✅ Focused fixture check: 1 passed | ✅ Five distinct programs and ten rules exercise weighted and missing-weight data | ➖ None needed |
| 1.3 | `services/api/tests/test_seed.py` | PostgreSQL integration | ✅ 12 baseline tests passed | ✅ 10 passed / 8 failed before loader changes | ✅ Focused seed suite: 18 passed | ✅ Manifest, deterministic IDs, results exclusion, fail-closed reset, and scoped deletion | ✅ No production refactor required |
| 2.1 | `services/api/tests/test_recommendation_domain.py` | Pure unit | N/A (new file) | ✅ 1 collection error / 0 tests before recommendation modules | ✅ 18 passed after implementation | ✅ Exact six-scale vocabulary, boundary validation, default weight, and malformed-rule branches | ✅ Scalar/direct snapshot parsing and typed non-string validation refactored; 18 passed afterward |
| 2.2 | `services/api/tests/test_recommendation_domain.py` | Pure unit | N/A (new file) | ✅ 1 collection error / 0 tests before recommendation modules | ✅ 18 passed after implementation | ✅ 33.33/0.00→33.33, 33.33/66.67→100.00, inclusive threshold, zero-rule exclusion, fit/name ordering, and rule-id trace order | ✅ Contribution rounding helper extracted; 18 passed afterward |
| 2.3 | `services/api/tests/test_recommendation_domain.py` | Pure unit | N/A (new files) | ✅ Covered by 2.1–2.2 RED suite | ✅ 18 passed after implementation | ✅ Frozen DTOs, input immutability, deterministic double-run, and forbidden-import assertion | ✅ Final focused suite remained 18 passed |
| 3.1 | `services/api/tests/test_recommendation_repository.py` | Integration + real PostgreSQL | N/A (new file) | ✅ Written first; 1 collection error / 0 tests because `repository.py` was absent | ✅ 4 passed / 0 failed / 0 skipped after implementation | ✅ Four real-DB cases cover latest run, active catalog reads, runtime rows/precision/flags/timestamp, rollback, and multi-generation anchor selection | ✅ Assertion cleanup and deterministic checks; 4 passed afterward |
| 3.2 | `services/api/tests/test_recommendation_repository.py` | Integration + real PostgreSQL | N/A (new production file) | ✅ Covered by the 3.1 RED suite | ✅ 4 passed / 0 failed / 0 skipped | ✅ Non-empty generation, caller rollback, two generations, and timestamp/id tie-break paths exercise production logic | ✅ Repository remains focused on reads/staging; no service or route coupling |
| 4.1 | `services/api/tests/test_recommendation_service.py` | Integration + real PostgreSQL | N/A (new test file) | ✅ Written first; collection failed with `ModuleNotFoundError` for absent `service.py` (0 tests) | ✅ 6 passed in the service suite; atomic success and audit rollback exercised | ✅ Happy path plus fail-closed audit failure and aggregate metadata checks | ➖ None needed; focused service rerun remained green |
| 4.2 | `services/api/tests/test_recommendation_service.py` | Integration + real PostgreSQL | N/A (new test file) | ✅ Written first with the service RED suite | ✅ Replay/conflict/new-key behavior passed in the 6-test suite | ✅ Same body replay, materially different body conflict, and independent generation | ➖ None needed |
| 4.3 | `services/api/tests/test_recommendation_service.py` | Integration + real PostgreSQL | N/A (new test file) | ✅ Written first with the service RED suite | ✅ Ownership, availability, in-progress, latest, and no-generation cases passed | ✅ Reserved profiles `evaluado_24..30` cover foreign, missing/unscored, in-progress, latest, and foreign-read paths | ➖ None needed |
| 4.4 | `services/api/app/modules/recommendation/service.py` | Integration + real PostgreSQL | N/A (new production file) | ✅ Covered by 4.1–4.3 RED suite | ✅ 6 service tests passed; requested combined suite passed 32 tests | ✅ Repository/domain/audit/idempotency orchestration exercised against PostgreSQL | ➖ None needed |
| 4.5 | `services/api/tests/test_auth.py`, `services/api/tests/test_audit.py` | Pure contract + PostgreSQL audit integration | ✅ Existing baseline: 26 passed | ✅ Expected matrix/catalog entries written before production ratification | ✅ Combined suite: 32 passed, including capability and event-catalog lockstep | ✅ Both NEW entries match code and README contracts | ➖ None needed |

## Unit 3 Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `docker compose run --rm -w /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_recommendation_repository.py` (the requested focused command through the established Compose wrapper) → **4 passed**, 0 failed, 0 skipped, 1 read-only `/repo/.pytest_cache` warning, 13.99s |
| Runtime harness command/scenario and exact result | The same Compose command exercised all four tests against the healthy real PostgreSQL service; score-trigger helpers created completed F4 runs for reserved `evaluado_21..24` profiles before repository reads/writes → **4 passed**, 0 failed, 0 skipped |
| Rollback boundary | Remove exactly `services/api/app/modules/recommendation/repository.py` and `services/api/tests/test_recommendation_repository.py`; leave domain/errors and all F2/F3/F4, seed, service, route, schema, permission, and audit files unchanged |

## Unit 4 Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `docker compose run --rm -w /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_recommendation_service.py tests/test_auth.py tests/test_audit.py` → **32 passed**, 0 failed, 0 skipped, 8 warnings, 22.68s |
| Runtime harness command/scenario and exact result | The same Compose command exercised six service tests and the capability/event lockstep tests against real PostgreSQL; score-trigger helpers ran first for reserved `evaluado_21..30` profiles → **32 passed**, 0 failed, 0 skipped |
| Rollback boundary | Revert exactly `services/api/app/modules/recommendation/service.py`, `services/api/tests/test_recommendation_service.py`, `services/api/app/core/permissions.py`, `services/api/app/core/audit.py`, `services/api/tests/test_auth.py`, `services/api/tests/test_audit.py`, and the F5 additions in `packages/contracts/README.md`; leave domain/errors/repository, routes/schemas/router, seed, and all F2/F3/F4 modules unchanged |

## Scope and Decisions

- `recommendation_results` remains runtime-only; Unit 3 repository tests used reserved `evaluado_21..24`, while Unit 4 service tests used only reserved `evaluado_21..30` profiles and delta counts.
- No migration was created; recommendation tables remain supplied by migration `0003`.
- The repository reuses `ScoringRepository` for session lookup and latest completed `ScoreRun`, then reads `Program` and active `RecommendationRule` rows without modifying F2/F3/F4 modules.
- `persist_generation` stages one `RecommendationResult` per domain rule contribution, explicitly sets `synthetic=False` and `source='runtime'`, assigns one shared timestamp, flushes, and leaves commit/rollback to the service transaction owner.
- Latest generation selection uses an anchor ordered by `created_at DESC, id DESC`, then returns all rows sharing the anchor timestamp.
- The API image was not rebuilt for code-only Units 3 and 4: the established `/repo` mount resolved the new modules for the focused Compose pytest runs; no loader or fixture changes were made.
- Test data follows the isolation rule: only reserved `evaluado_21..30` profiles are scored and result assertions use per-session deltas rather than global counts.

## Issues and Risks

- Pytest emits the established read-only `/repo/.pytest_cache` warning from the test mount; it does not affect the passing result.
- The repository intentionally does not commit or roll back; Unit 4 service orchestration must own audit, idempotency, and the outer transaction.
- Unit 4 keeps the outer transaction fail-closed: recommendation rows, the aggregate audit event, and the idempotency replay are committed together, while audit failure rolls back all staged rows.
- Foreign evaluado access is audited as `auth.denied` by the service before returning `FORBIDDEN`; admin and psicólogo retain cross-session access as ratified.
- The public DTO projects only `session_id`, `generated_at`, the pinned code disclaimer, and aggregated program items; persisted rule traces never become structured public fields.

## Remaining Tasks

- [x] 3.1 RED recommendation repository
- [x] 3.2 GREEN recommendation repository
- [x] 5.1–5.2 RED/GREEN recommendation API
- [x] 6.1 final verification and inherited-debt accounting; remediation rerun is green for F5 and preserves only the two inherited web failures

## PR Boundary

**Start**: Unit 3 starts with Unit 2's pure domain/errors commit present and creates only the recommendation repository adapter plus its real-PostgreSQL integration test.  
**Finish**: latest F4 score-run/catalog/rule reads, caller-owned atomic generation staging, per-rule runtime rows with Numeric(5,2) contributions and shared timestamps, rollback safety, and deterministic multi-generation latest selection are green.  
**Out of scope**: service, routes, schemas, permissions, audit ratification, seed, migrations, F2/F3/F4 module edits, and web UI.

## Current PR Boundary

**Start**: Unit 4 starts with Unit 3's repository commit present and writes only the recommendation service/test plus the explicit permission, audit, contract README, and lockstep test files.  
**Finish**: service orchestration, atomic audit/idempotency behavior, ownership and availability errors, latest DTO projection, and NEW `view_recommendations`/`recommendation.generated` ratifications are green in one stacked-to-main work-unit commit.  
**Out of scope**: domain/errors/repository, routes/schemas/router (Unit 5), seed, migrations, every F2/F3/F4 module, and web UI.

## Focused Remediation — F5 Test Isolation

**Work unit**: Remediate the F5 service-test isolation defect without changing production code, `conftest.py`, or any F2/F3/F4 test.  
**Commit**: `1517ec7c5ce9df3e742279725cd792aadd8ae338` (`test(api): fix F5 recommendation test isolation with disjoint profiles`)  
**Root cause confirmed**: `seeded_db_session` is session-scoped. The API tests generated two recommendation generations for profiles shared with the service tests, so service assertions that compared absolute row counts observed 20 rows instead of 10.  
**Correction**: Service tests exclusively reserve `evaluado_29` and `evaluado_30`; repository tests use `evaluado_27` and `evaluado_28`; API tests use `evaluado_21` through `evaluado_26` and reuse only `evaluado_21`/`evaluado_22` inside its final ownership test. Service result and audit assertions now calculate before/after deltas, including idempotency's second-generation count and forbidden/in-progress no-write checks.  
**Production impact**: None. No production module, fixture loader, migration, `conftest.py`, or F2/F3/F4 test changed.

### Remediation TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 6.1 remediation | `services/api/tests/test_recommendation_service.py`, `test_recommendation_repository.py`, `test_recommendation_api.py` | Real PostgreSQL + TestClient integration | ✅ Service 6 passed, repository 4 passed, API 6 passed before edits | ✅ Prior required combined selector reproduced 38 passed / 2 failed from shared profiles | ✅ Combined selector 40 passed; both full-suite repeats 217 passed with only the two inherited web failures | ✅ Profile assignment and delta assertions stayed within the three F5 test files; no production refactor |

### Remediation Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `powershell -ExecutionPolicy Bypass -File scripts/test.ps1 -k "recommendation or program"` → **40 passed**, 179 deselected, 15 warnings; wrapper exit 0 |
| Runtime harness command/scenario and exact result | `powershell -ExecutionPolicy Bypass -File scripts/test.ps1` run twice through Docker Compose with real PostgreSQL/TestClient → Run 1: **219 collected, 217 passed, 2 failed, 88 warnings**, 121.79s; Run 2: **219 collected, 217 passed, 2 failed, 88 warnings**, 117.13s. Both failures are only `test_web.py::test_page_is_spanish` and `test_web.py::test_page_never_leaks_stack_trace`; both are inherited and unchanged. |
| Rollback boundary | Revert only `services/api/tests/test_recommendation_service.py`, `services/api/tests/test_recommendation_repository.py`, and `services/api/tests/test_recommendation_api.py`; this removes the F5 profile reassignment and delta-count assertions without touching production, fixtures, `conftest.py`, or unrelated tests. |

### Remediation Scope and Risks

- The service profile assignment is now `evaluado_29..30`, repository is `evaluado_27..28`, and API is `evaluado_21..26`; grep verification found no `evaluado_29`/`evaluado_30` references in the API or repository test files.
- The PowerShell wrapper still masks pytest failures with exit code 0; pytest's collection and failure summary remains authoritative.
- The two inherited F2b web failures remain outside this bounded remediation and were not touched.

### Current Apply Boundary

**Start**: Failed F5 verification with two reproducible service-test contamination failures and shared seeded profiles across F5 test files.  
**Finish**: F5 service tests use disjoint profiles and delta counts; the required combined selector is fully green; both full-suite runs are repeatable with only the two inherited web failures.  
**Out of scope**: production code, `conftest.py`, F2/F3/F4 tests, web tests, and any F6 work.

## Focused Correction — Spec-Pinned Justification Operator

**Defect**: Fresh-context validation found the existing recommendation domain emitted ASCII `>=` in its justification sentence, while the authoritative recommendation API specification pins Unicode `≥` (U+2265).  
**Correction**: Changed only the sentence builder and its affected domain assertions; updated task 2.2 to mirror the authoritative spec. `test_recommendation_service.py` had no affected justification assertion and remained unchanged.  
**Prior commit**: `5e1e2d5` (`feat(api): add recommendation service and ratify view_recommendations + recommendation.generated`)  
**Correction commit**: `970dc4d` (`fix(api): use spec-pinned U+2265 in recommendation justification template`)

### Correction TDD Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Validator defect | `services/api/tests/test_recommendation_domain.py` + `services/api/tests/test_recommendation_service.py` | Pure unit + real PostgreSQL integration | ✅ 24 passed before assertion updates | ✅ Updated spec assertions first; 2 failed / 22 passed with ASCII production output | ✅ 24 passed after changing only the production operator | ✅ Both cumple and no cumple sentences, plus service integration, passed | ✅ Focused rerun remained green; no unrelated refactor |

### Correction Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `docker compose run --rm -w /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_recommendation_domain.py tests/test_recommendation_service.py` → **24 passed**, 0 failed, 0 skipped, 1 read-only `/repo/.pytest_cache` warning, 14.24s |
| Runtime harness command/scenario and exact result | The same Compose command ran pure domain tests and service integration against real PostgreSQL; service scenarios exercised the corrected persisted justification path → **24 passed**, 0 failed, 0 skipped |
| Rollback boundary | Revert only `services/api/app/modules/recommendation/domain.py` and `services/api/tests/test_recommendation_domain.py`; retain the Unit 4 service, permissions, audit, contracts, and service-test changes |

## Correction Scope Decision

- The authoritative recommendation API spec takes precedence over the stale `tasks.md` 2.2 ASCII operator; task wording now uses the exact U+2265 character.
- The semantic threshold comparison remains `percentile >= minimum`; only the public justification sentence operator changed, preserving evaluation behavior.

## Unit 5 TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 5.1 | `services/api/tests/test_recommendation_api.py` | TestClient + real PostgreSQL integration | N/A (new test file) | ✅ Written first; focused run: **6 failed**, 0 passed, 13 warnings while recommendation routes were absent | ✅ Final focused rerun: **6 passed**, 0 failed, 15 warnings | ✅ Six scenarios cover persistence/audit, replay/key conflict/new key, indistinguishable availability errors, in-progress/missing key, latest ordering, ownership, and recursive no-leak | ✅ Corrected one test-only Response model field assertion; final rerun remained 6 passed |
| 5.2 | `services/api/app/schemas/recommendations.py`, `services/api/app/api/routes/recommendations.py`, `services/api/app/api/router.py` | FastAPI adapter + strict Pydantic DTO + real PostgreSQL integration | ✅ Existing `test_results_api.py`: 7 passed | ✅ Covered by the 5.1 RED suite before route/schema implementation | ✅ Final recommendation API suite: **6 passed**, 0 failed, 15 warnings | ✅ POST/GET route paths, role dependencies, header propagation, DTO projection, and service replay payload validation execute through FastAPI | ➖ None needed; implementation matches the F4 thin-adapter pattern |

## Unit 5 Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `docker compose run --rm -w /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_recommendation_api.py` → **6 passed**, 0 failed, 0 skipped, 15 warnings, 17.50s; RED baseline for the same command was **6 failed**, 0 passed, 13 warnings |
| Runtime harness command/scenario and exact result | The same Compose TestClient command exercised POST/GET routes against real PostgreSQL; score-trigger helpers ran first for reserved `evaluado_21..30`, with delta-count checks for recommendation rows and audit events → **6 passed**, 0 failed, 0 skipped |
| Rollback boundary | Remove exactly `services/api/app/schemas/recommendations.py`, `services/api/app/api/routes/recommendations.py`, and `services/api/tests/test_recommendation_api.py`; revert only the recommendations import and `include_router` line in `services/api/app/api/router.py` |

## Current PR Boundary

**Start**: Unit 5 starts with Unit 4's service, permission, audit, contract-ratification, and correction commits present; it creates only the recommendation API test, strict response schemas, and thin route adapter, then registers that router under `/api/v1`.  
**Finish**: both recommendation endpoints are reachable, protected by the same role wiring as F4 results, require the service-owned idempotency behavior, validate the exact public DTO with `extra="forbid"`, and pass the real-PostgreSQL API contract suite.  
**Out of scope**: domain/errors/repository/service/permissions/audit/seed, every F2/F3/F4 module, migrations, web UI, and inherited `test_web.py` failures.

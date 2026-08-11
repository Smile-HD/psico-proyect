```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:73851d3c058a4b163d96ccf56244bf62fda106cd0f17b9b8b684bd5174a5d250
verdict: pass
blockers: 0
critical_findings: 0
requirements: 12/12
scenarios: 39/39
test_command: "powershell -ExecutionPolicy Bypass -File scripts/test.ps1"
test_exit_code: 0
test_output_hash: sha256:73851d3c058a4b163d96ccf56244bf62fda106cd0f17b9b8b684bd5174a5d250
build_command: "npm run build (working directory: apps/web) — N/A: F4 is API-only; no web files were touched"
build_exit_code: 0
build_output_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Verification Report

**Change**: `2026-08-10-f4-scoring-engine` (F4 — Scoring Engine / Results API)  
**Version**: N/A — six delta specs are authoritative  
**Mode**: Strict TDD (`pytest`)  
**Artifact store**: hybrid (OpenSpec + Engram)  
**Verification revision**: remediation commit `47bdd2a` independently re-run; this report supersedes the previous failed report.

### Verification scope and status

- Read proposal, design, tasks, apply-progress, all six delta specs, `openspec/config.yaml`, `HANDOFF-F4.md` §8 and §12, and the previous failed verify-report before judging the change.
- Strict TDD is active (`testing.strict_tdd: true`) with pytest and real PostgreSQL/TestClient integration available through Docker Compose.
- All 20 tasks are complete: 18 implementation tasks (`1.1`–`4.4`) plus verification/debt tasks `5.1`–`5.2`. The remediation preserves absolute count assertions and isolates repository/service checks on seeded profiles `evaluado_19` and `evaluado_20`.
- Authoritative retrieved-spec totals: **12 requirements / 39 scenarios**. Runtime evidence is green for all 39 scenarios; the two full-suite failures are inherited F2b web debt and are outside F4 scope.

### Completeness

| Metric | Value |
|---|---:|
| Tasks total | 20 |
| Implementation tasks complete | 18/18 |
| Verification/debt tasks complete | 2/2 (`5.1`, `5.2`) |
| Tasks incomplete | 0 |
| Proposal/specs/design/tasks/apply-progress/previous verify-report | Present and read |

### Build & Tests Execution

**Build**: ➖ Not run — configured command is `npm run build` in `apps/web`, but F4 is API-only and the verified F4 commit range changed no web file. The envelope records exit `0` and the SHA-256 digest of exact empty output for this N/A evidence.

**Full suite repeatability** — configured command: `powershell -ExecutionPolicy Bypass -File scripts/test.ps1`

| Run | Wrapper exit | Authoritative pytest result | Output hash |
|---|---:|---|---|
| 1 | 0 (wrapper masks pytest status) | **179 collected; 177 passed; 2 failed; 75 warnings** | `sha256:73851d3c058a4b163d96ccf56244bf62fda106cd0f17b9b8b684bd5174a5d250` |
| 2 | 0 (wrapper masks pytest status) | **179 collected; 177 passed; 2 failed; 75 warnings** | `sha256:7b878ad47453b7359e4fdf19b68758e4dae11a75337104b6cfab0de1195e3a22` |

Both runs failed only these inherited tests: `services/api/tests/test_web.py::test_page_is_spanish` and `services/api/tests/test_web.py::test_page_never_leaks_stack_trace`. No F4 test failed, and both runs have identical pytest counts.

**F4 slice** — command: `powershell -ExecutionPolicy Bypass -File scripts/test.ps1 -k "scoring or reference or results"`

- **32 selected; 32 passed; 147 deselected; 16 warnings**; wrapper exit `0`.
- Output hash: `sha256:c8281d4939016d9da77cd686d281c8cf4ac3759cb42e1321053a97e7c498dd15`.
- The selector contains 30 F4 tests plus the two unchanged reference-related tests; every selected test passed, including the remediated repository and service count assertions.

**Boundary and lockstep regression evidence**

| Command / exact test | Result | Output hash |
|---|---|---|
| `powershell -ExecutionPolicy Bypass -File scripts/test.ps1 -k "session_api"` | **9 passed; 170 deselected; 16 warnings**; includes `test_session_api.py::test_completion_requires_all_items_admin_override_and_aggregate_audit`, whose line 375 no-scoring assertion passed | `sha256:2d2bc0bd11f32845069e3260245ea71fa5d179962978fc390cd19d78e787eae4` |
| `powershell -ExecutionPolicy Bypass -File scripts/test.ps1 -k "test_results_payload_is_scores_only_and_session_boundary_stays_intact"` | **1 passed; 178 deselected; 4 warnings**; exact recursive no-leak and session-boundary test passed | `sha256:598ca72ebc1020f68c71cb783c4dab697f6113d03964a2dd8bd7823b3bc4cb8e` |
| `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_audit.py` | **11 passed; 1 warning**; catalog, append-only trigger, and deny-list checks passed | `sha256:9cbabbff7a8fb3a33650c3c50c816ac20bf3d00f1fbc7b713dea522ba9fcd937` |

**Coverage**: ➖ Not available; `openspec/config.yaml` sets threshold `0` and no coverage tool is configured.

### Spec Compliance Matrix

`✅ COMPLIANT` means the covering test passed at runtime in the required F4 selector, full suite, or explicit boundary/lockstep run. All 39 retrieved scenarios are compliant.

| # | Requirement | Scenario | Covering test / evidence | Result |
|---:|---|---|---|---|
| 1 | Scoring Engine / Pure Function Contract | Deterministic pure computation | `test_scoring_domain.py::test_score_is_deterministic_immutable_and_free_of_db_io_clock_imports` — F4 slice | ✅ COMPLIANT |
| 2 | Scoring Engine / Pure Function Contract | Inputs never mutated | `test_scoring_domain.py::test_score_is_deterministic_immutable_and_free_of_db_io_clock_imports` — F4 slice | ✅ COMPLIANT |
| 3 | Scoring Engine / Per-scale Computation | Happy path scale | `test_scoring_domain.py::test_scale_raw_direct_and_transformed_chain` — F4 slice | ✅ COMPLIANT |
| 4 | Scoring Engine / Per-scale Computation | Zero variance | `test_scoring_domain.py::test_zero_variance_and_transformed_bounds` — F4 slice | ✅ COMPLIANT |
| 5 | Scoring Engine / Per-scale Computation | Bounds clamped | `test_scoring_domain.py::test_zero_variance_and_transformed_bounds` — F4 slice | ✅ COMPLIANT |
| 6 | Scoring Engine / Per-scale Computation | Unknown scale label | `test_scoring_domain.py::test_missing_overall_row_and_unknown_scale_label_raise_typed_errors` — F4 slice | ✅ COMPLIANT |
| 7 | Scoring Engine / Overall Computation | Overall happy path | `test_scoring_domain.py::test_half_up_ties_and_overall_rescale_lookup_and_bounds` — F4 slice | ✅ COMPLIANT |
| 8 | Scoring Engine / Overall Computation | Overall bounds | `test_scoring_domain.py::test_half_up_ties_and_overall_rescale_lookup_and_bounds` — F4 slice | ✅ COMPLIANT |
| 9 | Scoring Engine / Reference Input Contract | Single reference set `RS-TP-S-01` | `test_scoring_repository.py::test_repository_reads_pinned_session_fixture_and_reference` — F4 slice | ✅ COMPLIANT |
| 10 | Results API / Score Trigger | Completed session scores | `test_results_api.py::test_score_completed_session_persists_public_result` — F4 slice | ✅ COMPLIANT |
| 11 | Results API / Score Trigger | In-progress session rejected | `test_results_api.py::test_score_error_boundaries_are_stable_and_non_leaking` — F4 slice | ✅ COMPLIANT |
| 12 | Results API / Score Trigger | Missing session indistinguishable | `test_results_api.py::test_score_error_boundaries_are_stable_and_non_leaking` — F4 slice | ✅ COMPLIANT |
| 13 | Results API / Score Trigger | Foreign evaluado cannot trigger | `test_results_api.py::test_score_error_boundaries_are_stable_and_non_leaking` — F4 slice | ✅ COMPLIANT |
| 14 | Results API / Score Trigger | Retry replays without duplication | `test_results_api.py::test_score_replay_key_reuse_and_new_key_are_run_safe` — F4 slice | ✅ COMPLIANT |
| 15 | Results API / Score Trigger | Same key with different body conflicts | `test_results_api.py::test_score_replay_key_reuse_and_new_key_are_run_safe` — F4 slice | ✅ COMPLIANT |
| 16 | Results API / Score Trigger | New key creates a new run | `test_results_api.py::test_score_replay_key_reuse_and_new_key_are_run_safe` — F4 slice | ✅ COMPLIANT |
| 17 | Results API / Results Read | Owner reads own results | `test_results_api.py::test_get_latest_result_pins_expected_run_and_preserves_norm_note` — F4 slice | ✅ COMPLIANT |
| 18 | Results API / Results Read | Foreign evaluado denied | `test_results_api.py::test_foreign_evaluado_cannot_read_results` — F4 slice | ✅ COMPLIANT |
| 19 | Results API / Results Read | Unscored session is not found | `test_results_api.py::test_get_unscored_and_missing_results_share_not_found_signature` — F4 slice | ✅ COMPLIANT |
| 20 | Results API / Results Read | Multiple runs resolve deterministically | `test_results_api.py::test_get_latest_result_pins_expected_run_and_preserves_norm_note` and `test_scoring_service.py::test_latest_result_orders_by_computed_at_then_run_id` — F4 slice | ✅ COMPLIANT |
| 21 | Results API / Results Payload and No-leak Boundary | Payload exposes labels and scores only | `test_results_api.py::test_results_payload_is_scores_only_and_session_boundary_stays_intact` — explicit boundary run | ✅ COMPLIANT |
| 22 | Results API / Results Payload and No-leak Boundary | Session boundary unchanged | `test_results_api.py::test_results_payload_is_scores_only_and_session_boundary_stays_intact` and `test_session_api.py::test_completion_requires_all_items_admin_override_and_aggregate_audit` — explicit boundary runs | ✅ COMPLIANT |
| 23 | Contracts / Idempotent Mutations | Retry without duplication | `test_results_api.py::test_score_replay_key_reuse_and_new_key_are_run_safe` — F4 slice | ✅ COMPLIANT |
| 24 | Contracts / Idempotent Mutations | Replay does not duplicate audit | `test_results_api.py::test_score_replay_key_reuse_and_new_key_are_run_safe` — F4 slice | ✅ COMPLIANT |
| 25 | Contracts / Idempotent Mutations | Distinct keys are independent | `test_results_api.py::test_score_replay_key_reuse_and_new_key_are_run_safe` — F4 slice | ✅ COMPLIANT |
| 26 | Contracts / Idempotent Mutations | Same key, different body conflicts | `test_results_api.py::test_score_replay_key_reuse_and_new_key_are_run_safe` — F4 slice | ✅ COMPLIANT |
| 27 | Contracts / Idempotent Mutations | F3 session mutation rejects key reuse | `test_session_api.py::test_create_and_response_idempotency_replay_or_conflict_without_duplicates` — full suite and explicit session run | ✅ COMPLIANT |
| 28 | Contracts / Idempotent Mutations | F4 score-trigger replay is run-safe | `test_results_api.py::test_score_replay_key_reuse_and_new_key_are_run_safe` — F4 slice | ✅ COMPLIANT |
| 29 | Contracts / Idempotent Mutations | F4 new key starts an independent run | `test_results_api.py::test_score_replay_key_reuse_and_new_key_are_run_safe` — F4 slice | ✅ COMPLIANT |
| 30 | Contracts / Results Availability Errors | Missing and unscored are indistinguishable | `test_results_api.py::test_get_unscored_and_missing_results_share_not_found_signature` — F4 slice | ✅ COMPLIANT |
| 31 | Contracts / Results Availability Errors | In-progress triggers stable conflict | `test_results_api.py::test_score_error_boundaries_are_stable_and_non_leaking` — F4 slice | ✅ COMPLIANT |
| 32 | Audit & Consent / Append-only Audit Log | Append-only enforced | `test_audit.py::test_update_on_audit_log_rejected` and `test_audit.py::test_delete_on_audit_log_rejected` — explicit audit run | ✅ COMPLIANT |
| 33 | Audit & Consent / Append-only Audit Log | Deny-list respected | `test_audit.py::test_deny_list_rejects_forbidden_metadata` and `test_audit.py::test_deny_list_clean_across_whole_log` — explicit audit run | ✅ COMPLIANT |
| 34 | Audit & Consent / Append-only Audit Log | Catalog events carry aggregate metadata only | `test_catalog_audit.py::test_explicit_saves_are_audited_once_each_and_content_is_excluded` — full suite ×2 | ✅ COMPLIANT |
| 35 | Audit & Consent / Append-only Audit Log | Scoring event carries aggregates only | `test_scoring_service.py::test_score_persists_completed_runtime_run_and_aggregate_audit` — F4 slice | ✅ COMPLIANT |
| 36 | Data Schema / Score Run Persistence Shape | Multiple runs are schema-legal | `test_scoring_repository.py::test_score_runs_transition_and_allow_multiple_runtime_rows` — F4 slice | ✅ COMPLIANT |
| 37 | Data Schema / Score Run Persistence Shape | Runtime flags on runs | `test_scoring_service.py::test_score_persists_completed_runtime_run_and_aggregate_audit` and repository transition test — F4 slice | ✅ COMPLIANT |
| 38 | Synthetic Seed / Reference Set Value Shape | Seeded reference rows match the contract | `test_scoring_repository.py::test_reference_contract_is_available_through_repository` — F4 slice | ✅ COMPLIANT |
| 39 | Synthetic Seed / Reference Set Value Shape | Scale labels are the join key | `test_scoring_repository.py::test_reference_contract_is_available_through_repository` — F4 slice | ✅ COMPLIANT |

**Compliance summary**: **39/39 scenarios compliant; 12/12 requirements compliant.** No scenario is `FAILING` or `UNTESTED`.

### Requirement Verdicts

| Requirement | Verdict | Evidence |
|---|---|---|
| Pure Function Contract | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | Domain test passed in the required selector; source imports only standard-library calculation/data types. |
| Per-scale Computation | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | Happy path, zero variance, bounds, CDF vectors, and typed failures passed. |
| Overall Computation | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | Half-up ties, overall raw 1/11/20, and exact lookup tests passed. |
| Reference Input Contract | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | Repository consumed only `RS-TP-S-01` and passed pinned-input integration tests. |
| Results API / Score Trigger | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | Completed, conflict, missing, foreign, replay, conflict-key, and new-key tests passed. |
| Results API / Results Read | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | Owner, foreign, unscored, latest ordering, and `norm_note` tests passed. |
| Results Payload and No-leak Boundary | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | Recursive payload test and session line-375 boundary passed. |
| Idempotent Mutations | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | F4 replay/new-key API tests and F3 session idempotency regression passed. |
| Results Availability Errors | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | Missing/unscored equality and stable in-progress conflict passed. |
| Append-only Audit Log | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | `test_audit.py` was 11/11 green; catalog and scoring aggregate tests passed. |
| Score Run Persistence Shape | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | Two rows per session, pending/completed transition, flags, raw JSONB and timestamp passed. |
| Reference Set Value Shape | ✅ COMPLIANT — no CRITICAL/WARNING/SUGGESTION | Exactly 30 rows, synthetic/research-only metadata, and exact scale labels passed. |

### Correctness (Static Evidence)

| Requirement area | Status | Notes |
|---|---|---|
| Pure scoring engine | ✅ Implemented | `domain.py` uses frozen dataclasses, `math.erf`, ratified half-up rounding, clamps, and exact overall lookup; no DB/I/O/clock/random imports. |
| Reference and private mapping consumption | ✅ Implemented | `repository.py` reads pinned session/version/reference data and consumes `fixture_projection`; the public route/schema never returns the mapping. |
| Score-run persistence | ✅ Implemented | `ScoreRun` is created pending, completed with raw JSONB and `computed_at`, and explicitly marked `synthetic=False`, `source='runtime'`; no schema/migration change exists. |
| Results trigger/read API | ✅ Implemented | Protected `/api/v1/results` POST/GET routes, owner enforcement, stable errors, idempotency scope `session:{id}`, and deterministic latest selection are present. |
| Public no-leak boundary | ✅ Implemented | Strict DTOs expose labels/scores/run/reference/norm metadata only; recursive no-leak and F3 session-boundary tests pass. |
| Idempotency and error contracts | ✅ Implemented | Replay, same-key conflict, new-key independent run, missing/unscored equivalence, and in-progress conflict pass. |
| Audit contract | ✅ Implemented | `scoring.run` is ratified in `EVENT_CATALOG`, `packages/contracts/README.md`, and `test_audit.py`; runtime metadata is aggregate-only and atomic. |
| F2/F3/no-web scope | ✅ Implemented | Commit-range path audit found no F2/F3 module, seed, migration, or web path. |

### Design Coherence

| Decision | Followed? | Evidence |
|---|---|---|
| ADR-01: stdlib `math.erf` and RH rounding | ✅ Yes | Domain implementation and CDF/half-up runtime tests pass. |
| ADR-02: domain/service/repository layering | ✅ Yes | Pure computation is isolated from repository reads and service transaction orchestration. |
| ADR-03: thin protected `/results` adapter | ✅ Yes | Router registration, role dependencies, DTO validation, and API tests pass. |
| ADR-04: transactional pending/completed runs | ✅ Yes | Service creates, computes, completes, audits, stores replay, and commits atomically; rollback test passes. |
| ADR-05: aggregate-only `scoring.run` lockstep | ✅ Yes | Audit catalog, contracts README, catalog test, and service metadata assertions pass. |
| ADR-06: real PostgreSQL/TestClient integration | ✅ Yes | Required F4 selector, full suite, boundary runs, and explicit audit run execute against Compose PostgreSQL. |
| ADR-07: no migration/seed/web rollout | ✅ Yes | Git scope audit shows only the specified scoring/API/audit/contracts/test paths. |
| Remediation: deterministic test isolation | ✅ Yes | `evaluado_19` and `evaluado_20` avoid the shared `evaluado_01` contamination without weakening absolute assertions. |

### TDD Compliance

| Check | Result | Details |
|---|---|---|
| TDD evidence reported | ✅ | `apply-progress.md` contains cycle tables for tasks `1.1`–`5.2`. |
| All tasks have test files | ✅ | 20/20 tasks identify existing F4 test files; all files exist. |
| RED confirmed | ✅ | 20/20 task rows report tests/prerequisite RED before implementation or remediation. |
| GREEN confirmed | ✅ | 20/20 task rows have current runtime coverage; F4 slice is 32/32 and changed audit tests are 11/11. |
| Triangulation adequate | ✅ | Formula edge cases, API errors, reruns, tie-break, rollback, no-leak, audit, and boundary cases use varied assertions. |
| Safety nets for modified executable behavior | ✅ | Domain/repository/service/results baselines and audit/session boundary regressions all pass; remediation uses isolated-profile triangulation. |

**TDD Compliance**: ✅ 6/6 verification checks passed; no assertion-quality defect was found.

### Test Layer Distribution

| Layer | Tests | Files | Tools |
|---|---:|---:|---|
| Unit / contract | 23 | 3 | pytest |
| PostgreSQL / TestClient integration | 18 | 4 | pytest + Docker Compose PostgreSQL |
| E2E / browser | 0 | 0 | unavailable by project configuration |
| **Total F4-related changed tests** | **41** | **5** | |

The F4 selector additionally collected two unchanged reference-related tests, giving 32 selected cases.

### Changed File Coverage

Coverage analysis skipped — no coverage tool is configured or available; configured threshold is 0%, so this is informational and non-blocking.

### Assertion Quality

**Assertion quality**: ✅ All reviewed assertions in the five F4-related changed test files exercise production code or the intended pure boundary. No tautologies, assertion-free tests, vacuous ghost-loop failures, smoke-only tests, or mock-heavy test file were found.

### Quality Metrics

**Linter**: ➖ Not available/configured.  
**Type Checker**: ➖ API pyright is configured in project capabilities, but `services/api/.venv/Scripts/pyright.exe` and PATH `pyright` are absent; no type-check command was available to execute. Web build is not applicable because F4 touched no web files.

### Diff Scope and Checklist

The repository contains five F4 implementation/remediation commits in the verified range (`8eb59ae`, `c046840`, `c8b1a97`, `e212f9e`, `47bdd2a`); no separate verify-doc commit exists yet. `git diff --check` is clean, and all five commit subjects are conventional commits.

| Check | Result | Evidence |
|---|---|---|
| Scoring module only within F4 module boundary | ✅ | `services/api/app/modules/scoring/{__init__,domain,errors,repository,service}.py` only. |
| Results API files and router registration | ✅ | `services/api/app/api/routes/results.py`, `services/api/app/schemas/results.py`, and `services/api/app/api/router.py` only. |
| Audit lockstep | ✅ | Only `services/api/app/core/audit.py`, `packages/contracts/README.md`, and `services/api/tests/test_audit.py` changed for audit. |
| F4 test files | ✅ | Only `test_scoring_domain.py`, `test_scoring_repository.py`, `test_scoring_service.py`, `test_results_api.py`, and the lockstep `test_audit.py` changed. |
| F2/F3 modules unchanged | ✅ | No `assessment_authoring` or `session_runtime` module path appears in the commit-range diff. |
| Seed and migration unchanged | ✅ | No `services/api/app/seed` or `services/api/alembic` path appears in the commit-range diff. |
| Web unchanged | ✅ | No `apps/web` path appears in the commit-range diff; build is N/A. |
| Pure engine has no DB/side effects | ✅ | Source inspection plus `test_score_is_deterministic_immutable_and_free_of_db_io_clock_imports` passed. |
| 1–5 mapping/results stay out of API/UI | ✅ | Recursive no-leak test, session line-375 assertion, strict results DTO, and no web diff passed. |
| `norm_note` accompanies outputs | ✅ | `test_get_latest_result_pins_expected_run_and_preserves_norm_note` passed. |
| Synthetic/research-only data only | ✅ | Seed/reference test passed synthetic/research-only/disclaimer assertions; no seed or fixture file changed. |
| Mutating results endpoint requires `Idempotency-Key` | ✅ | Route declares the header; missing-key, replay, conflict, and new-key tests passed. |
| Audit aggregate-only and ratified | ✅ | `scoring.run` is in the catalog, contracts §3, and audit test; service asserts exact aggregate metadata. |
| Conventional commits and clean patch | ✅ | Five subjects match conventional-commit syntax; `git diff --check` is clean. |

### Inherited Debt

`HANDOFF-F4.md` §8 records the pre-F4 baseline as **149 collected / 147 passed / 2 inherited web failures**. The current suite is **179 collected / 177 passed / 2 failed** on both independent runs because F4 adds 30 tests and leaves the same two F2b failures untouched:

- `services/api/tests/test_web.py::test_page_is_spanish`
- `services/api/tests/test_web.py::test_page_never_leaks_stack_trace`

These failures are outside the F4 commit scope, were identical in both runs, and are documented debt rather than F4 blockers. No web file was modified.

### Issues Found

**CRITICAL**

- None. No new failure appeared; the required F4 selector is 32/32 green and both full-suite runs contain only inherited web debt.

**WARNING**

1. The two inherited F2b `test_web.py` failures remain open as documented debt and are not caused by or changed by F4.
2. `scripts/test.ps1` masks pytest's non-zero status; pytest counts and named failures are authoritative.
3. Coverage, linter, local API pyright, and browser/E2E execution are unavailable or out of scope; none is a configured F4 acceptance blocker.

**SUGGESTION**

1. Update `scripts/test.ps1` to propagate pytest's `$LASTEXITCODE` so future automation cannot treat a failing pytest run as process-successful.
2. Address the inherited F2b web assertions in their owning remediation change, not in F4.

### Final Verdict

**PASS** — remediation commit `47bdd2a` removes the shared seeded-profile contamination; the required 32/32 F4 slice is green, both full-suite runs are repeatable at 179/177/2 with only the two inherited web failures, all 12 requirements and 39 scenarios are runtime-compliant, and the verified diff stays within F4 scope.

## Key Learnings

1. Isolating repository and service assertions on evaluado_19 and evaluado_20 removes shared seeded-database contamination without weakening count assertions.
2. The F4 selector collects 32 cases, with all 32 passing after remediation and 147 cases deselected.
3. Full-suite repeatability remains 179 collected, 177 passed, and two inherited web failures on both independent runs.
4. Pytest output counts remain authoritative because scripts/test.ps1 masks the underlying non-zero test status.
5. The verified F4 commit range changes only scoring, results API, audit lockstep, tests, and allowed contracts paths.
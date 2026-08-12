```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:5f64f4f04ae3e4a981fe845e3cb48b947dc2b3b261769c7b74dc0f5b1274c59d
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 15/15
scenarios: 61/61
test_command: "powershell -ExecutionPolicy Bypass -File scripts/test.ps1"
test_exit_code: 0
test_output_hash: sha256:5c246f084581f8a1b0ba10ab6cf5dab462c27dacd435d66c3aad1682a4711c55
build_command: "npm run build (working directory: apps/web)"
build_exit_code: 0
build_output_hash: sha256:4586dd7b4367139dbb114e4f33292eeb75b12390f71229e0ebacf1cc8dba5c2b
```

## Verification Report

**Change**: `2026-08-11-f6-reports-pdf-integration` (F6 — Traceable Reports, PDF, and Authorized Download)  
**Version**: N/A — five delta specs are authoritative  
**Mode**: Strict TDD (`pytest`)  
**Artifact store**: hybrid (OpenSpec + Engram)  
**Baseline**: `master @ adc7ae6`  
**Owner**: Ivan

### Scope and completeness

Read before judging: `AGENTS.md`, `openspec/config.yaml`, `HANDOFF-F6.md`, proposal, all five delta specs, design, tasks, and the complete `apply-progress.md`. `usuarios.md` was not read, modified, staged, or deleted.

| Metric | Result |
|---|---:|
| Tasks total | 22 |
| Tasks complete | 22 |
| Tasks incomplete | 0 |
| Requirements retrieved | 15 |
| Scenarios retrieved | 61 |
| Action context | repo-local; repository root authorized |

### Build and tests execution

**Configured build**: `npm run build` in `apps/web` — exit `0`; Next.js compiled, linted, type-checked, and generated all pages. Output hash: `sha256:4586dd7b4367139dbb114e4f33292eeb75b12390f71229e0ebacf1cc8dba5c2b`.

**API image build**: `docker compose build api` — exit `0`; output hash: `sha256:b0db17ac37f396a8f8d6da0756ab2225c9eec5cbe3bec7629fadcfecce9c264e`.

**Configured test wrapper**: `powershell -ExecutionPolicy Bypass -File scripts/test.ps1` — wrapper exit `0`; output hash: `sha256:5c246f084581f8a1b0ba10ab6cf5dab462c27dacd435d66c3aad1682a4711c55`. The wrapper is known to mask pytest failures; the direct in-container summaries are authoritative.

**Authoritative full-suite regression**:

| Run | Exact command | Pytest result | Direct exit | Output hash |
|---|---|---|---:|---|
| 1 | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest -p no:cacheprovider --tb=short tests` | 264 collected; 262 passed; 2 failed; 98 warnings | 1 | `sha256:5f64f04f04ae3e4a981fe845e3cb48b947dc2b3b261769c7b74dc0f5b1274c59d` |
| 2 | same command | 264 collected; 262 passed; 2 failed; 98 warnings | 1 | `sha256:8850e9714ecef0ed04189dfb0f8f05050265c70f11adc413faae5e17c4632a9c` |

Both runs failed only on the documented inherited web debt: `services/api/tests/test_web.py::test_page_is_spanish` and `services/api/tests/test_web.py::test_page_never_leaks_stack_trace`. The earlier F6-caused migration-head failure is absent; `services/api/tests/test_catalog_migration.py::test_f1_backfill_upgrade_is_idempotent` passes in both runs. No web file changed.

**Focused F6/lockstep/schema/seed evidence**: current direct Compose execution of the 11 changed or F6-relevant test files passed `99 passed, 19 warnings`; output hash `sha256:091fd13b83f6c863be288a34e4deceb79209d6673d868bf47c18b38ab1c426d7`. Current selector `-k "report or template or pdf or seed or schema"` passed `84 passed, 180 deselected, 13 warnings`; output hash `sha256:d998af8c7ed6223d721533479e1d89ee580d0e429f829780333e47e9c8879756`. Apply evidence additionally records `31 passed, 14 warnings` for API+seed and `103 passed, 46 warnings` for the cumulative F6 gate.

**Coverage**: not available; no coverage tool is configured and threshold is `0`.

### Spec compliance matrix

`PASS` means the requirement's scenarios have passing runtime coverage. Actual totals are 15 requirements and 61 scenarios.

| Requirement | Scenario evidence — exact test names or file evidence | Result |
|---|---|---|
| **reports-api — Report Generation Trigger (5 scenarios)** | Completed chain: `services/api/tests/test_reports_api.py::test_report_api_generates_exact_metadata_and_streams_pdf`; staged pins/audit: `test_reporting_service.py::test_generate_stages_outside_io_and_persists_pins_artifact_and_aggregate_audit`. Missing/unscored/ungenerated and no hidden engines: `test_reporting_service.py::test_prerequisites_are_indistinguishable_and_engines_are_never_called`. In-progress: `test_reports_api.py::test_report_api_availability_errors_are_stable_and_side_effect_free`. Strict body: `test_reports_api.py::test_report_api_replay_new_key_and_strict_request_body`. | PASS |
| **reports-api — Report Document Content (2 scenarios)** | Sections, separate `norm_note`/disclaimer, normalized determinism, Spanish output, embedded font, and PDF no-leak: `services/api/tests/test_reporting_pdf.py::test_renderer_is_normalized_deterministic_and_embeds_spanish_dejavu_font`; logical no-leak projection: `test_reporting_domain.py::test_report_composes_fixed_immutable_sections_from_pinned_snapshots`. | PASS |
| **reports-api — Report Metadata Read (3 scenarios)** | Latest ordering and side-effect-free reads: `services/api/tests/test_reporting_service.py::test_latest_metadata_is_deterministic_and_side_effect_free`. Missing session/no report: `test_reporting_service.py::test_latest_metadata_without_report_matches_missing_session`. HTTP DTO/read behavior: `test_reports_api.py::test_report_api_generates_exact_metadata_and_streams_pdf` and `::test_report_api_availability_errors_are_stable_and_side_effect_free`. | PASS |
| **reports-api — Report Download (4 scenarios)** | Ready PDF stream/checksum: `services/api/tests/test_reports_api.py::test_report_api_generates_exact_metadata_and_streams_pdf`. Missing/not-ready equivalence: `::test_report_api_availability_errors_are_stable_and_side_effect_free`. Download re-authorization: `::test_report_api_denies_evaluado_before_lookup_and_audits_denial`. Chunked stream/no URL/close: `::test_report_api_streams_in_chunks_without_exposing_storage_key`. | PASS |
| **reports-api — Report State Machine (3 scenarios)** | Transitions and artifact requirements: `services/api/tests/test_reporting_repository.py::test_repository_transitions_processing_to_ready_and_failed` and `test_reporting_service.py::test_generate_stages_outside_io_and_persists_pins_artifact_and_aggregate_audit`. Renderer/storage/audit failures: `test_reporting_service.py::test_renderer_failure_marks_failed_and_same_key_retry_converges`, `::test_storage_failure_marks_failed_without_artifact`, and `::test_audit_failure_cleans_orphan_and_fails_closed`. Same-row retry: `::test_renderer_failure_marks_failed_and_same_key_retry_converges`. | PASS |
| **data-schema — Empty-but-migrated F5/F6 (3 scenarios)** | Seeded template with zero runtime rows: `services/api/tests/test_seed.py::test_f5_f6_seed_state_after_seed` and `::test_report_template_is_seeded_once_and_manifested`. Pre-seed schema: `test_schema.py::test_fresh_upgrade_creates_all_families`. Linear/repeat upgrade: `test_schema.py::test_upgrade_is_idempotent`, `::test_linear_history`, and `test_catalog_migration.py::test_f1_backfill_upgrade_is_idempotent`. | PASS |
| **data-schema — Report Persistence Shape (4 scenarios)** | Existing F1–F5 constraints and model/migration lockstep: `services/api/tests/test_schema.py::test_check_constraints_present`, `::test_reporting_models_match_migrated_columns`, and `test_catalog_migration.py::test_f1_seed_identity_and_references_survive`. Status/format and ready checks: `test_schema.py::test_report_check_constraints_use_ratified_vocabularies` and `test_reporting_repository.py::test_repository_ready_transition_requires_complete_artifact_metadata`. Ready/failed fields: `test_reporting_repository.py::test_repository_transitions_processing_to_ready_and_failed`. Runtime UUID4/flags and pins: `::test_repository_creates_pending_report_with_pins_and_runtime_flags`. | PASS |
| **data-schema — Report Template Persistence Shape (3 scenarios)** | Published immutability and retired readability: `services/api/tests/test_schema.py::test_report_template_published_rows_are_immutable`. Version/id pin: `services/api/tests/test_reporting_repository.py::test_repository_creates_pending_report_with_pins_and_runtime_flags`; source `services/api/app/modules/reporting/repository.py::get_template` permits pinned `published`/`retired` versions. | PASS |
| **contracts — Idempotent Mutations (11 scenarios)** | Existing F2–F5 replay/conflict/history contracts pass in `services/api/tests/test_catalog_idempotency.py::test_miss_stores_a_successful_result_and_same_hash_replays`, `::test_same_key_with_different_body_is_a_conflict_without_a_new_record`, `test_session_api.py::test_create_and_response_idempotency_replay_or_conflict_without_duplicates`, `test_results_api.py::test_score_replay_key_reuse_and_new_key_are_run_safe`, and `test_recommendation_api.py::test_generation_api_replay_key_reuse_and_new_key_are_run_safe`. F6 replay/conflict/new historical report and event counts: `test_reports_api.py::test_report_api_replay_new_key_and_strict_request_body` and `test_reporting_service.py::test_idempotency_replays_conflicts_and_creates_historical_report`. Catalog audit replay: `test_catalog_audit.py::test_replayed_create_has_one_row_and_one_audit_event`. | PASS |
| **contracts — Report Access Matrix (2 scenarios)** | Professional operations and route/auth lockstep: `services/api/tests/test_auth.py::test_view_reports_is_professional_only`, `test_reports_api.py::test_report_api_generates_exact_metadata_and_streams_pdf`, and `test_reporting_service.py::test_idempotency_replays_conflicts_and_creates_historical_report`. Evaluado excluded and all three denials audited: `test_reports_api.py::test_report_api_denies_evaluado_before_lookup_and_audits_denial`. | PASS |
| **contracts — Report Availability Errors (4 scenarios)** | Missing/unscored/ungenerated: `services/api/tests/test_reporting_service.py::test_prerequisites_are_indistinguishable_and_engines_are_never_called`. In-progress conflict and download not-ready equivalence: `test_reports_api.py::test_report_api_availability_errors_are_stable_and_side_effect_free`. Renderer token/envelope: `test_reporting_service.py::test_renderer_failure_marks_failed_and_same_key_retry_converges`. | PASS |
| **contracts — Report DTO and No-leak Boundary (2 scenarios)** | Exact DTO fields/omissions and strict request: `services/api/tests/test_reports_api.py::test_report_api_generates_exact_metadata_and_streams_pdf`, `::test_report_api_replay_new_key_and_strict_request_body`, and `test_reporting_service.py::test_latest_metadata_is_deterministic_and_side_effect_free`. DTO/PDF/audit no-leak: `test_reporting_pdf.py::test_renderer_is_normalized_deterministic_and_embeds_spanish_dejavu_font`, `test_reporting_domain.py::test_report_composes_fixed_immutable_sections_from_pinned_snapshots`, and `test_audit.py::test_report_generated_event_contract_is_aggregate_only`. | PASS |
| **audit-consent — Append-only Audit Log (6 scenarios)** | Append-only trigger: `services/api/tests/test_audit.py::test_update_on_audit_log_rejected` and `::test_delete_on_audit_log_rejected`. Deny-list: `test_audit.py::test_deny_list_rejects_forbidden_metadata` and `::test_deny_list_clean_across_whole_log`. Catalog aggregate metadata: `test_catalog_audit.py::test_explicit_saves_are_audited_once_each_and_content_is_excluded`. Scoring/recommendation aggregate metadata: `test_scoring_service.py::test_score_persists_completed_runtime_run_and_aggregate_audit` and `test_recommendation_api.py::test_generate_api_persists_rows_audit_and_exact_safe_payload`. Report aggregate metadata: `test_audit.py::test_report_generated_event_contract_is_aggregate_only` and `test_reporting_service.py::test_generate_stages_outside_io_and_persists_pins_artifact_and_aggregate_audit`. | PASS |
| **synthetic-seed — --reset Scoped to Seed-owned Rows (5 scenarios)** | Scoped/non-seed survival: `services/api/tests/test_seed.py::test_reset_keeps_non_seed`. Runtime catalog/reporting survival: `::test_runtime_report_score_run_artifact_and_template_survive_seed_reset`. Cross-ownership atomic abort: `::test_seed_reset_rejects_runtime_recommendation_dependency`. Runtime reporting dependency conflicts: `::test_seed_reset_preflight_rejects_runtime_reporting_dependencies_atomically` and `::test_seed_reset_preflight_rejects_runtime_report_over_seed_template`. | PASS |
| **synthetic-seed — Report Template Seed Content (4 scenarios)** | UUID5/published v1/synthetic seed flags/manifest: `services/api/tests/test_seed.py::test_report_template_is_seeded_once_and_manifested`. Runtime reports/runs never seeded: `::test_f5_f6_seed_state_after_seed` and `::test_reset_appends_manifest_without_changing_seed_template_identity`. Reseed/reset idempotence and stable id: `::test_report_template_is_seeded_once_and_manifested` and `::test_reset_appends_manifest_without_changing_seed_template_identity`; source evidence `services/api/app/seed/loader.py:50` confirms `SEED_VERSION = "1.2.0"`. | PASS |

**Compliance summary**: 61/61 scenarios compliant; 15/15 requirements compliant.

### Correctness (static/source evidence)

| Area | Result | Evidence |
|---|---|---|
| Pure composition/no hidden engines | PASS | `services/api/app/modules/reporting/domain.py` uses data/stdlib only; `test_reporting_domain.py::test_reporting_domain_has_no_db_api_io_clock_or_dynamic_execution_dependencies`; service engine monkeypatch tests pass. |
| Fixed content and no-leak projection | PASS | `compose_report` projects only ratified score/F5 fields; normalized PDF test checks fixed sections, separate notes, font, metadata, paths, and leak markers. |
| Schema/migration | PASS | `0006_reports_pdf.py` is the sole linear successor to `0005_catalog_four_level`; model/migration introspection, fresh/repeat upgrades, and preserved F1–F5 constraints pass. |
| State machine/staging | PASS | Repository is flush-only; service commits T1, performs renderer/storage outside locks, finalizes ready + audit, and compensates failures by artifact cleanup plus failed state. |
| Strict DTO/stream | PASS | `ReportGenerateRequest` and `ReportMetadata` use `extra="forbid"`; routes declare `require_roles(ADMIN, PSICOLOGO)` and return authenticated `StreamingResponse`, never a path/URL. |
| Access/audit lockstep | PASS | `view_reports` and `report.generated` agree across permissions, audit catalog, contracts README, and tests. |
| Seed/reset ownership | PASS | `SEED_VERSION=1.2.0`, deterministic UUID5 template, `SEED_TABLES`, manifest/checksum, preflight, and runtime retention are implemented and tested. |
| Scope protection | PASS | No F6 web/UI, integration, outbox, F4/F5 engine, published-instrument, or `usuarios.md` work was included. |

### Design coherence

| ADR | Result | Evidence |
|---|---|---|
| ADR-01 pure domain/repository/service/route seams | PASS | Module boundaries and pure-domain import test match the design. |
| ADR-02 fixed ordered document and separate notes | PASS | Domain and normalized PDF tests pass. |
| ADR-03 linear persistence, pins, checks, immutable templates | PASS | Migration/model/schema/repository tests pass. |
| ADR-04 T1/T2 staging and failure compensation | PASS | Transaction-state, failure, orphan-cleanup, and retry tests pass. |
| ADR-05 ReportLab, embedded font, BYTEA, opaque stream | PASS | PDF/storage tests and rebuilt API image pass. |
| ADR-06 strict DTOs, professional-only access, lockstep audit | PASS | API/auth/audit/contracts tests pass. |
| ADR-07 seed/reset ownership and preflight | PASS | Seed fixture, manifest, conflict, and survival tests pass. |

### Task traceability

All 22 task checkboxes are `[x]`, with corresponding apply-progress evidence. Tasks 1.1–5.4 map to the domain, schema/repository, renderer/storage, service/lockstep, API, and seed tests listed above. Task 6.1 records API image rebuild, full-suite regression twice, identical functional summaries, and `git diff --check`; task 6.2 records artifact reconciliation and archive handoff. No task remains pending.

### TDD Compliance

| Check | Result | Details |
|---|---|---|
| TDD evidence reported | PASS | `apply-progress.md` contains a TDD Cycle Evidence table for all six slices. |
| All implementation tasks have tests | PASS | 20/20 implementation tasks have existing test files and runtime evidence; 6.1/6.2 are verification-only tasks. |
| RED confirmed | PASS | Apply evidence records tests written before implementation and expected absent-module/initial-failure results. |
| GREEN confirmed | PASS | Current F6/lockstep/schema/seed set is 99 passed; all apply focused gates are green. |
| Triangulation adequate | PASS | Happy paths, failure paths, replay/conflict/history, no-leak, schema, seed, and boundary cases assert distinct behavior. |
| Safety nets | PASS | Pre-edit safety nets are recorded for modified files; new files are marked N/A; Slice 6 is docs-only. |

**TDD Compliance**: 6/6 checks passed.

### Test layer distribution

| Layer | Cases | Files | Tools |
|---|---:|---:|---|
| Unit | 33 | 4 mixed/pure files | pytest |
| Integration | 66 | 10 mixed/DB/TestClient/PDF files | pytest + Docker Compose PostgreSQL |
| E2E | 0 | 0 | not available and out of scope |
| **Total** | **99** | **11 F6/lockstep/schema/seed files** | |

### Changed-file coverage

Coverage analysis skipped — no coverage tool detected; configured threshold is `0`. This is informational, not a failure.

### Assertion quality

**Assertion quality**: PASS — all inspected F6 and lockstep assertions call production code or a real runtime boundary and verify non-trivial behavior. No tautologies, empty-only assertions without companion non-empty checks, ghost loops, smoke-only tests, dynamic-execution gaps, or mock-heavy test files were found. Monkeypatches are used only to prove forbidden engine calls and failure boundaries.

### Quality metrics

**Linter**: not available (`ruff` is not installed).  
**Type checker**: `next build` passed for the web; API `pyright` is configured but unavailable, so no API type-check result is claimed.  
**E2E/browser runner**: unavailable and not in F6 scope.

### DoD and issues

| DoD item | Result |
|---|---|
| Full suite twice, identical functional result | PASS WITH WARNING — 264 collected, 262 passed, same two inherited web failures in both runs. |
| No F6-caused failures | PASS — the prior stale 0005 migration assertion is corrected and passes; no F6 failure appears. |
| Focused F6 suites | PASS — current and apply-progress focused gates are green. |
| `git diff --check` | PASS. |
| Task traceability | PASS — 22/22 checked. |
| Scope/synthetic-only policy | PASS. |
| Only documented inherited debt remains | PASS — exactly the two web tests listed above. |

**CRITICAL**: None.  
**WARNING**:
1. `services/api/tests/test_web.py::test_page_is_spanish` and `services/api/tests/test_web.py::test_page_never_leaks_stack_trace` remain inherited web failures outside F6 scope; both are unchanged and reproducible.
2. The PowerShell wrapper masks pytest's direct nonzero exit; the direct exit is `1` solely because of those two inherited failures, so pytest summaries are authoritative.
3. Coverage, Ruff, and API Pyright are unavailable; no unsupported quality claim is made.

**SUGGESTION**:
1. Track the two web failures in a web-owned change rather than altering F6 during archive.
2. Preserve the exact admitted report bytes when running `sdd-archive`.

### Verdict

**PASS WITH WARNINGS — READY FOR ARCHIVE**. All 15 requirements and 61 scenarios have passing F6/runtime evidence, all 22 tasks are complete, design ADRs are coherent, focused F6 suites are green, and both full-suite runs contain only the two documented inherited web failures.

## Key Learnings

1. Direct Compose pytest summaries are authoritative because the PowerShell wrapper masks failures.
2. F6 verification covered 15 requirements and 61 scenarios across pure, PostgreSQL, TestClient, PDF, seed, and audit boundaries.
3. The corrected migration-head assertion removes the only F6-caused regression from the prior Slice-6 attempt.

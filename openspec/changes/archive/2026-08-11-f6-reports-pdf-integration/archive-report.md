# F6 Reports/PDF Integration — Archive Report

**Change**: `2026-08-11-f6-reports-pdf-integration`
**Date**: 2026-08-12
**Owner**: Ivan (F6; consuming F4/Juan Carlos and F5/Piere)
**Final state**: ARCHIVED
**Base**: `master @ adc7ae6` (`docs(openspec): archive f5-profiles-recommendation change`)
**Commits**: NONE — working-tree changes only; HEAD remains `adc7ae6`. No commit or push was requested for implementation or archive.

## Summary

F6 delivered the first reports capability: deterministic, traceable professional PDFs composed exclusively from persisted F4/F5 snapshots — never recomputing scoring or recommendations. A pure reporting domain (`modules/reporting/{domain,errors,repository,service,pdf_renderer,storage}.py`) mirrors the F4/F5 layering; a linear schema-only migration `0006_reports_pdf` extends the reporting family (score-run FK pin, F5 JSONB value snapshot, template version pin, `pending/processing/ready/failed` status and `pdf` format CHECKs, artifact fields, lifecycle timestamps, immutable versioned `report_templates`); ReportLab 4.4.10 with an embedded redistributable DejaVuSans TTF renders normalized-deterministic Spanish PDFs stored as opaque PostgreSQL BYTEA artifacts; three thin authorized routes expose manual idempotent generation (`session:{id}` keys), latest-metadata reads, and authenticated stream downloads — all gated by the new professional-only `view_reports` capability and the aggregate-only `report.generated` audit event, updated in lockstep across `permissions.py`, `audit.py::EVENT_CATALOG`, `packages/contracts/README.md`, and the auth/audit contract tests. Seed owns the immutable `informe-basico` template (UUID5, `SEED_VERSION=1.2.0`, in `SEED_TABLES`/manifest/checksum) and reset preflight now covers `score_runs`/`reports`, never deleting runtime rows or artifacts. No web UI, no integration/outbox/vendor, no F2–F5 contract change, no published-instrument edit. Delivered as 6 strict-TDD stacked slices (per the tasks forecast; no commits were created because the task list did not request them).

## Spec Promotion

| Domain | Action | Requirements (post-merge canonical) |
|---|---|---|
| `reports-api` | NEW domain — full spec copied mechanically to `openspec/specs/reports-api/spec.md` | 5 requirements / 17 scenarios |
| `data-schema` | MODIFIED `Empty-but-migrated F5/F6` replaced (F6 `0006_*` migration, seeded `informe-basico`, scenarios `Reporting rows and seed template after seed` / `Migration chain stays linear and idempotent` added) + ADDED `Report Persistence Shape` + ADDED `Report Template Persistence Shape` | 8 requirements / 20 scenarios |
| `contracts` | MODIFIED `Idempotent Mutations` replaced (F6 report trigger with `session:{id}` scope, historical-pinning new-key semantics, `F6 report replay is run-safe` + `F6 new key creates historical reports` scenarios added; F2–F5 scenarios preserved) + ADDED `Report Access Matrix` + ADDED `Report Availability Errors` + ADDED `Report DTO and No-leak Boundary` | 10 requirements / 31 scenarios |
| `audit-consent` | MODIFIED `Append-only Audit Log` replaced (catalog ratifies `report.generated`; aggregate-only report metadata; `Report event carries aggregates only` scenario added; lockstep obligation covers report events) | 5 requirements / 15 scenarios |
| `synthetic-seed` | MODIFIED `--reset Scoped to Seed-owned Rows` replaced (preflight covers `score_runs`/`reports`; `Runtime report over seed session aborts atomically` + `Runtime reporting rows survive reset` scenarios added) + ADDED `Report Template Seed Content` | 7 requirements / 19 scenarios |

F6-contributed total: **15 requirements / 61 scenarios** (matches verify-report authority). Merges followed the F2–F5 promotion convention: new-domain full spec copied verbatim via shell with `diff -r` readback; MODIFIED requirements replaced wholesale with the delta body (delta-only `(Previously: …)` notes dropped); ADDED requirements appended; unrelated requirements preserved byte-for-byte (verified by requirement-name inventory after merge). No delta contains REMOVED or RENAMED sections — no destructive merge was required (`openspec/config.yaml` `rules.archive: Warn before merging destructive deltas` satisfied by absence).

## Final Task State

- **22/22 tasks complete** (`tasks.md`): 20 implementation tasks (`1.1`–`5.4`) plus verification tasks `6.1`–`6.2`. No unchecked tasks remain in the archived copy; **no archive-time checkbox reconciliation was needed** (the Task Completion Gate passed on the persisted artifact as-is).
- Verify-report (on-disk, FINAL): `verdict: pass_with_warnings`, `blockers: 0`, `critical_findings: 0`, `requirements: 15/15`, `scenarios: 61/61`, `tasks: 22/22`.

## Commit State

No commits exist for this change. `git status` at archive time shows only working-tree changes: 13 modified tracked files (contracts README, router, audit, permissions, models, seed loader, pyproject, six test files) and untracked implementation paths (`0006_reports_pdf.py`, `app/api/routes/reports.py`, `app/modules/reporting/`, `app/schemas/reports.py`, seed fixture, five reporting test files, the change folder). HEAD is still `adc7ae6`. Commits/push remain deferred pending explicit instruction, per HANDOFF-F6 DoD.

## Discrepancies Recorded (per Final-State Authority)

- **Stale migration-head failure (resolved, not open).** The first `apply-progress` Work Unit 6 attempt (2026-08-12) recorded `3 failed, 261 passed` in both runs, including `test_catalog_migration.py::test_f1_backfill_upgrade_is_idempotent` asserting the pre-F6 head `0005_catalog_four_level`. That assertion was stale: the F6 migration legitimately moved the linear head to `0006_reports_pdf`. The orchestrator corrected the test to assert `0006_reports_pdf`; the Work Unit 6 retry and the on-disk `verify-report.md` (higher-ranked sources) record `264 collected / 262 passed / 2 failed / 98 warnings` in both runs with the corrected assertion passing. The intermediate snapshot's failure claim is superseded and is NOT carried forward as open.
- **Test counts.** Final-state counts (262 passed / 2 failed / 98 warnings per run, 264 collected) come from `verify-report.md` (final authority), not from `apply-progress` intermediate snapshots.
- **Review shorthand.** No review artifacts exist for this candidate (`reviewGate` structurally absent); no receipt-driven review was started, and archive proceeds under ordinary repository policy.

## Decisions Registered (ratified baselines)

- **D1/D4 — Content/audience**: professional-only PDF containing F4 raw/z/percentile/T/eneatype and overall scores plus F5 program fit/justification, with `norm_note` and the F5 disclaimer in separate sections (never one substituted for the other); no option values/ids, response keys, 1–5 mapping, item content, secrets, or PII beyond the session id.
- **D2 — Trigger/idempotency**: manual `POST /api/v1/reports/{session_id}/generate` with `Idempotency-Key` scoped `session:{id}`; same-key replay replays, different body conflicts with `idempotency_key_reused`, new key creates a new historical pinned report; never invokes/imports F4/F5 engines; missing/unscored/ungenerated identical `NOT_FOUND`/`resource_not_found` with zero effects; `in_progress` → `CONFLICT`/`session_not_completed`.
- **D3 — Templates**: immutable versioned `draft/published/retired` templates (published rows protected by trigger, retired rows remain readable for reproduction), templates are data never code (allow-list parser, no eval/exec/import); seed default `informe-basico` UUID5/`synthetic=true`/`source='seed'` in `SEED_TABLES`, manifest, checksum, reset scope and preflight; no client template selection.
- **D5/D6 — Renderer/storage**: ReportLab 4.4.10 (BSD) with embedded redistributable DejaVuSans TTF, injected clock/UTC/Spanish locale, normalized-deterministic PDF (structure/text/metadata, not bytes); PostgreSQL `report_artifacts` BYTEA with opaque UUID4 keys, SHA-256, size, media type, renderer version; indefinite MVP retention; downloads re-authorize and stream bytes — never bare/signed URLs or internal paths.
- **Schema/reset**: `0006_reports_pdf` linear schema-only successor to `0005_catalog_four_level`; nullable `score_run_id` FK + F5 JSONB value snapshot (no F5 schema change, no `recommendation_generation` entity); ratified status/format vocabularies enforced by CHECKs; preflight extended to `score_runs`/`reports` (`seed_reset_dependency_conflict`, zero deletions); runtime reports/runs/artifacts never deleted by reset; `SEED_VERSION` bumped to `1.2.0`.
- **D7/D8 — Deferral**: no integration/outbox/worker (no target ratified), no web UI, no signed URLs; `view_reports` + `report.generated` updated in lockstep; audit stays aggregate-only (`report.downloaded` does not exist; downloads are not separately audited); `report_generation_failed` is the only new message token (no new error codes).

### ADRs (from design.md)

ADR-01 seams (`modules/reporting/{domain,errors,repository,service,pdf_renderer,storage}.py`; pure domain, caller-owned commits) · ADR-02 composition (frozen `ReportInput -> ReportDocument`, fixed ordered sections) · ADR-03 persistence (schema-only `0006_reports_pdf`, pins/checks/timestamps, template trigger) · ADR-04 staging (T1 claim/`pending -> processing` + idempotency lock; render/storage outside row locks; T2 `ready` + aggregate audit; failure compensates to `failed`, retry converges on the same row) · ADR-05 adapters (ReportLab + DejaVuSans, BYTEA `report_artifacts`, opaque keys, indefinite retention) · ADR-06 API/security (strict DTOs `extra="forbid"`, `require_roles(ADMIN, PSICOLOGO)`, evaluado denied before lookup with `auth.denied`, indistinguishable availability errors) · ADR-07 seed/reset (`informe-basico` seed ownership, extended preflight, runtime retention).

## Verification Facts (final-state authority)

- Source of truth: on-disk `verify-report.md` (`verdict: pass_with_warnings`), corroborated by the orchestrator's final-state handoff facts. Intermediate snapshots (`apply-progress` slices, including the first WU6 attempt) are superseded where they differ.
- Full suite ×2 (direct Compose, `-p no:cacheprovider --tb=short`): **264 collected → 262 passed, 2 failed, 98 warnings — identical in both runs**. The only failures are the two documented inherited web tests (`test_web.py::test_page_is_spanish`, `test_web.py::test_page_never_leaks_stack_trace`); no web file changed. `test_catalog_migration.py::test_f1_backfill_upgrade_is_idempotent` passes in both runs.
- Focused F6/lockstep/schema/seed evidence (current): 11 changed/F6-relevant files → `99 passed, 19 warnings`; selector `-k "report or template or pdf or seed or schema"` → `84 passed, 180 deselected, 13 warnings`. Apply evidence additionally records `31 passed, 14 warnings` (API+seed) and `103 passed, 46 warnings` (cumulative F6 gate).
- `docker compose build api` exit 0; `alembic upgrade head` idempotent at `0006_reports_pdf`; seed CLI `seed_version=1.2.0`, `report_templates=1`, `score_runs=0`, `reports=0`; `--reset` preflight and runtime-survival scenarios green; web `npm run build` exit 0 (no web change).
- `git diff --check` → PASS at close. `usuarios.md` untouched (still untracked, never read/modified/staged/deleted).

## Inherited Debt / Follow-ups (non-blocking, handoff)

- **2 inherited `test_web.py` failures** (F2b): `test_page_is_spanish` and `test_page_never_leaks_stack_trace` — documented debt outside F6 scope; track them in a web-owned change.
- **`scripts/test.ps1` exit-code masking**: the wrapper returns 0 without propagating `$LASTEXITCODE`; direct in-container pytest summaries are the authoritative evidence.
- **Tooling gaps**: no coverage tool (threshold 0), no Ruff, no API Pyright binary, no E2E/browser runner — unchanged; no unsupported quality claim is made.
- **AGENTS.md pointer**: the "Cambio activo actual" row still reads "F1–F5 archivados" (updated by the F5 archive); recommend updating it to "F1–F6 archivados" in a future docs commit, together with the pending F6 commit/push when authorized.
- **Next phase**: none — F6 closes the planned F1–F6 chain. No active OpenSpec change remains; `openspec/changes/` contains only `archive/`. Future work candidates (web UI for reports, integration target, `report.downloaded` event, sort tie-break pinning) require new ratified changes.

## Traceability (Engram observation IDs read)

- `#2147` proposal · `#2148` spec · `#2149` design · `#2151` tasks · `#2152` apply-progress · `#2165` verify-report (all topics under `sdd/2026-08-11-f6-reports-pdf-integration/`).
- `reviewGate`: structurally absent — no review artifacts exist for this candidate; archive proceeded under ordinary repository policy.

## Mechanical Copy Evidence

- **NEW-domain promotion** (`reports-api`): `diff -r` (delta spec vs staged temp) — **EMPTY**, exit 0; `diff -r` (delta spec vs `openspec/specs/reports-api/spec.md`) — **EMPTY**, exit 0 (byte-identical).
- **Archive move**: pre-move recursive snapshot (Git `cp -R`) vs `openspec/changes/archive/2026-08-11-f6-reports-pdf-integration/` — `diff -r` **EMPTY**, exit 0 (byte-identical; `archive-report.md` is additive-only and excluded from the comparison). Source directory confirmed absent after the move.
- No Read→Write byte routing was used for any artifact copy or move.

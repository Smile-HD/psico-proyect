# Apply Progress: F6 — Traceable Reports, PDF & Authorized Download

## Work Unit 1

- Change: `2026-08-11-f6-reports-pdf-integration`
- Slice: 1 of 6 — Pure reporting domain, errors, and template parser
- Artifact store: hybrid (OpenSpec + Engram)
- Strategy: stacked-to-main
- Review budget: 800 changed lines for the full change; this slice is autonomous
- Assigned tasks: 1.1 → 1.3 only
- Mode: Strict TDD (`pytest`)
- Boundary: create only `services/api/app/modules/reporting/{__init__,errors,domain}.py`
  and `services/api/tests/test_reporting_domain.py`; update only this change's
  `tasks.md` checkboxes and `apply-progress.md`. No database, renderer, ReportLab,
  seed, service, route, web, migration, or F4/F5 files were changed.

## Completed Tasks

- [x] 1.1 RED — frozen `ReportInput`/`ReportDocument`, deterministic fixed section
  order, source pins, input immutability, safe snapshot projection, and pure-domain
  import boundary.
- [x] 1.2 RED — literal template allow-list parser with typed unknown/missing
  placeholder failures, malformed-expression rejection, and no-leak projection.
- [x] 1.3 GREEN — reporting `__init__`, stable API error factories, frozen domain
  types/composer, and parser; focused suite is green.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | `services/api/tests/test_reporting_domain.py` | Pure unit | N/A — new test and production files | ✅ written first; local collection failed with `1 error`, `ModuleNotFoundError: app.modules.reporting` | ✅ final focused suite `5 passed` | ✅ fixed section order, score/overall projection, pins, deterministic repeat, frozen values, wrapped F4 `raw` payload, and input immutability | ✅ preserved outer `norm_note` while accepting wrapped `raw`; removed unused import; final Compose run remained green |
| 1.2 | `services/api/tests/test_reporting_domain.py` | Pure unit | N/A — new test and production files | ✅ written first in the same collection RED (`1 error`) | ✅ final focused suite `5 passed` | ✅ valid allow-listed substitutions, unknown names, missing values, malformed expression syntax, and no `eval`/`exec`/dynamic import | ✅ parser split validation from substitution; final Compose run remained green |
| 1.3 | `services/api/app/modules/reporting/{__init__,errors,domain}.py` | Pure unit | N/A — all production files are new | ✅ prerequisite RED suite collected against absent module | ✅ local `pytest` final `5 passed in 0.06s`; authoritative Compose final `5 passed` | ✅ all domain and parser scenarios exercised real production code, including non-trivial snapshots and alternate wrappers | ✅ pure standard-library domain, explicit section/value types, stable aliases, and no renderer/database coupling |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command and exact result | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_reporting_domain.py` → `5 passed, 1 warning in 1.15s`; warning is the known read-only `/repo/services/api/.pytest_cache` `PytestCacheWarning` only |
| Runtime harness command/scenario and exact result | `N/A` — slice 1 is intentionally a pure unit boundary with no database, HTTP route, clock, filesystem, renderer, Compose service interaction, or external runtime behavior under test |
| Rollback boundary | Remove exactly `services/api/app/modules/reporting/__init__.py`, `services/api/app/modules/reporting/errors.py`, `services/api/app/modules/reporting/domain.py`, and `services/api/tests/test_reporting_domain.py`; revert only the three slice-1 checkbox marks and this progress artifact. Leave all later slices and `usuarios.md` untouched. |

## Implementation Notes

- `ReportInput` accepts canonical score/F5 snapshots plus explicit adapter aliases
  without mutating caller-owned mappings.
- `compose_report` projects only the ratified score fields and program name,
  fit, and justification. Option values/ids, response keys/ids, item content,
  rule parameters, and secret fields are never copied into `ReportDocument`.
- `ReportDocument.sections` is always the immutable order
  `scores → overall → recommendations → norm_note → disclaimer`; the two notes
  remain separate values and cannot substitute for one another.
- Template syntax is literal `{{name}}` substitution for the six allow-listed
  names: `session_id`, `scores`, `overall`, `recommendations`, `norm_note`, and
  `disclaimer`. No expression, directive, import, `eval`, or `exec` path exists.
- `services/api/pyproject.toml` and `usuarios.md` were not read for modification,
  changed, staged, or deleted; ReportLab remains deferred to slice 3.

## Deviations from Design

None — implementation matches ADR-01 and ADR-02. The parser lives in
`domain.py`, matching the slice-1 task list; no additional template module was
introduced.

## Remaining Tasks

- [x] 2.1 RED schema/migration lockstep — completed in Work Unit 2 below
- [x] 2.2 RED reporting repository reads, pins, and transitions — completed in Work Unit 2 below
- [x] 2.3 GREEN reporting models and migration — completed in Work Unit 2 below
- [x] 2.4 GREEN reporting repository — completed in Work Unit 2 below
- [ ] 3.1 RED deterministic PDF renderer contract
- [ ] 3.2 RED opaque artifact storage contract
- [ ] 3.3 GREEN ReportLab renderer/storage adapters and dependency
- [x] 4.1 RED staged report generation and failure behavior — completed in Work Unit 4 below
- [x] 4.2 RED report idempotency replay/key reuse/new-key history — completed in Work Unit 4 below
- [x] 4.3 RED prerequisite, no-engine, and authorization behavior — completed in Work Unit 4 below
- [x] 4.4 RED latest metadata read behavior — completed in Work Unit 4 below
- [x] 4.5 GREEN reporting service — completed in Work Unit 4 below
- [x] 4.6 Lockstep permissions, audit event, contracts, and tests — completed in Work Unit 4 below
- [ ] 5.1 RED reports API routes and strict DTOs
- [ ] 5.2 RED seed template and reset/preflight behavior
- [ ] 5.3 GREEN reports schemas/routes/router
- [ ] 5.4 GREEN seed fixture/loader
- [ ] 6.1 Verification regression/build evidence
- [ ] 6.2 Apply/verify/archive reconciliation

## Review / PR Boundary

- Current PR: stacked-to-main slice 1, targeting the applicable prior/main chain
  state; no commit was created because the task list did not request one.
- Start: F6 planning artifacts existed, but no reporting domain, errors module,
  template parser, or reporting-domain tests existed.
- Finish: pure report composition and literal template parsing are green and can
  be removed independently without touching persistence or later adapters.
- Follow-up: slice 2 owns models, migration, and repository integration.
- Out of scope: every database, renderer, service, route, seed, web, and F4/F5
  change.

## Work Unit 1 Status

3/22 implementation tasks complete. Ready for slice 2; not ready for final
verification.

---

## Work Unit 2

- Change: `2026-08-11-f6-reports-pdf-integration`
- Slice: 2 of 6 — Reporting models, migration `0006_reports_pdf`, and repository
- Artifact store: hybrid (OpenSpec + Engram)
- Strategy: stacked-to-main
- Review budget: 800 changed lines for the full change; this slice is autonomous
- Assigned tasks: 2.1 → 2.4 only
- Mode: Strict TDD (`pytest`)
- Boundary: modify only `services/api/app/models/reporting.py`, create only
  `services/api/alembic/versions/0006_reports_pdf.py` and
  `services/api/app/modules/reporting/repository.py`, create
  `services/api/tests/test_reporting_repository.py`, and extend
  `services/api/tests/test_schema.py`; update only this change's `tasks.md` and
  `apply-progress.md`. `test_seed.py`, F4/F5 production modules, web files, and
  `usuarios.md` remain untouched.

## Cumulative Completed Tasks

- [x] 1.1–1.3 — Work Unit 1 pure reporting domain, errors, and literal template parser; evidence remains above.
- [x] 2.1 — schema/model lockstep, source pins, status/format and artifact checks, template version uniqueness, immutability trigger, preserved F1–F5 constraints, linear `0006` successor, and repeat upgrade checks.
- [x] 2.2 — PostgreSQL repository reads/pins, runtime report flags, state transitions, ready artifact validation, caller-owned transactions, and historical multi-report behavior.
- [x] 2.3 — reporting SQLAlchemy models and one schema-only `0006_reports_pdf` migration immediately after `0005_catalog_four_level`.
- [x] 2.4 — reporting repository adapter with deterministic F4/F5/template reads and pending/processing/ready/failed staging.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 2.1 | `services/api/tests/test_schema.py` | Real PostgreSQL schema integration | ✅ pre-edit `test_schema.py` + `test_seed.py`: `25 passed, 1 warning` | ✅ schema expectations written first; initial schema run `8 failed, 3 passed`, including missing `0006` columns/head/trigger | ✅ final focused schema run `11 passed, 1 warning` | ✅ model columns, score-run FK, JSONB snapshot, exact status/format/template vocabularies, artifact checks, F1–F5 checks, template uniqueness/immutability, linear successor, and idempotent head | ✅ constraint assertions use one introspection path; published-row test cleans its synthetic row without weakening the trigger |
| 2.2 | `services/api/tests/test_reporting_repository.py` | Real PostgreSQL repository integration | N/A — new test file | ✅ written first; collection failed with `1 error`, missing `app.modules.reporting.repository` | ✅ final focused repository run `6 passed, 1 warning` | ✅ latest persisted F4/F5/template reads, value pinning, UUID4/runtime flags, both terminal transitions, incomplete ready metadata, rollback ownership, and two reports per session | ✅ deterministic runtime fixtures and delta counts avoid shared seeded-profile totals; compatibility aliases mirror F4/F5 repository vocabulary |
| 2.3 | `services/api/app/models/reporting.py`, `services/api/alembic/versions/0006_reports_pdf.py` | SQLAlchemy/Alembic + real PostgreSQL | ✅ existing schema/seed safety net above | ✅ schema RED preceded model/migration implementation | ✅ combined schema/repository gate `17 passed, 1 warning`; migration head is `0006_reports_pdf` | ✅ fresh schema creation, repeated `upgrade head`, one linear head, preserved pre-existing constraints, template trigger behavior, and report state checks | ✅ migration has a single linear revision and a non-destructive operational rollback boundary; no F1–F5 rewrite |
| 2.4 | `services/api/tests/test_reporting_repository.py` | Real PostgreSQL repository integration | N/A — new repository module/test | ✅ covered by the repository collection RED before production repository code | ✅ combined repository/schema gate `17 passed, 1 warning` | ✅ source selection, immutable value snapshots, all required transitions, failure cleanup, caller rollback, and latest historical ordering exercise real SQLAlchemy/PostgreSQL paths | ✅ no hidden commits, no renderer/storage imports, and composition remains outside the repository |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command and exact result | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_schema.py tests/test_reporting_repository.py` → `17 passed, 1 warning in 11.09s`; warning is the known read-only `/repo/services/api/.pytest_cache` `PytestCacheWarning` only |
| Runtime harness command/scenario and exact result | `docker compose build api` completed successfully; direct Compose `docker compose run --rm api alembic upgrade head` ran twice with exit code 0, and `docker compose run --rm api alembic current` reported `0006_reports_pdf (head)`; the second upgrade emitted no migration step. Supporting regression: `pytest tests/test_seed.py` → `18 passed, 1 warning` and F4/F5 repository tests → `8 passed, 1 warning` |
| Rollback boundary | Before migration application, remove exactly `services/api/app/models/reporting.py` changes, `services/api/alembic/versions/0006_reports_pdf.py`, `services/api/app/modules/reporting/repository.py`, `services/api/tests/test_schema.py` slice-2 additions, and `services/api/tests/test_reporting_repository.py`; revert only tasks/progress marks. After `0006` is deployed, do not use a destructive downgrade: disable later reporting adapters/routes and apply a forward fix while retaining report/template history and source snapshots. Leave slice 1, F4/F5 modules, `test_seed.py`, and `usuarios.md` untouched. |

## Implementation Notes

- `ReportTemplate` now permits multiple versions per key through
  `uq_report_template_key_version`, constrains `draft`/`published`/`retired`, and
  installs a PostgreSQL trigger that rejects published/retired in-place edits or
  deletes while allowing the ratified `published → retired` lifecycle move.
- `Report` pins `score_run_id`, the F5 JSONB snapshot, and template id/version;
  carries the PDF artifact metadata and lifecycle timestamps; and preserves
  multiple historical rows per session without a session uniqueness constraint.
- The migration is one schema-only `0006_reports_pdf` successor to
  `0005_catalog_four_level`; no F1–F5 table was retyped, dropped, or weakened.
- `ReportingRepository` delegates source selection to the existing F4/F5
  repository adapters, projects the latest persisted F5 generation into a JSON-safe
  snapshot, deep-copies pins, stages runtime rows, and flushes only. The caller
  owns commit/rollback; rendering and storage are not imported. An explicit
  version pin can still resolve a retired template for retry/history, while a
  new unpinned generation selects only the published version.
- Runtime report ids use SQLAlchemy UUID4 defaults, with `synthetic=False` and
  `source='runtime'`. Ready transitions require all artifact fields; failed
  transitions clear artifact fields and set `failed_at`.
- No seed implementation was changed in this slice; seeded `informe-basico`, reset,
  and manifest behavior remain assigned to Slice 5.

## Deviations from Design

None — implementation follows ADR-03 persistence and ADR-04 caller-owned staging.
The repository adds only deterministic adapter aliases and database-level ready/
failed artifact checks needed to enforce the ratified state semantics.

## Issues Found

- Compose pytest emits the established read-only `.pytest_cache` warning; it does
  not affect the functional result.
- The PowerShell wrapper remains unsuitable as authoritative evidence because it
  masks pytest exit status; direct Compose pytest summaries above are authoritative.

## Remaining Tasks

- [ ] 3.1 RED deterministic PDF renderer contract
- [ ] 3.2 RED opaque artifact storage contract
- [ ] 3.3 GREEN ReportLab renderer/storage adapters and dependency
- [x] 4.1 RED staged report generation and failure behavior
- [x] 4.2 RED report idempotency replay/key reuse/new-key history
- [x] 4.3 RED prerequisite, no-engine, and authorization behavior
- [x] 4.4 RED latest metadata read behavior
- [x] 4.5 GREEN reporting service
- [x] 4.6 Lockstep permissions, audit event, contracts, and tests
- [ ] 5.1 RED reports API routes and strict DTOs
- [ ] 5.2 RED seed template and reset/preflight behavior
- [ ] 5.3 GREEN reports schemas/routes/router
- [ ] 5.4 GREEN seed fixture/loader
- [ ] 6.1 Verification regression/build evidence
- [ ] 6.2 Apply/verify/archive reconciliation

## Review / PR Boundary

- Current PR: stacked-to-main slice 2, targeting the preceding slice/main chain
  state; no commit was created because the task list did not request one.
- Start: Work Unit 1's pure reporting domain, errors, and parser were green; F6
  still had the F1 scaffold-only reporting tables and no repository.
- Finish: one linear `0006` schema extension and a PostgreSQL-backed reporting
  repository are green as an autonomous models/migration/repository unit.
- Follow-up: Slice 3 owns ReportLab renderer and opaque artifact storage adapters.
- Out of scope: service, routes, seed/reset, permissions/audit lockstep, web,
  renderer/storage dependencies, F4/F5 production changes, and `usuarios.md`.

## Status

10/22 implementation tasks complete. Ready for Slice 3; not ready for final
verification.

---

## Work Unit 3

- Change: `2026-08-11-f6-reports-pdf-integration`
- Slice: 3 of 6 — Deterministic ReportLab PDF renderer and PostgreSQL BYTEA storage
- Artifact store: hybrid (OpenSpec + Engram)
- Strategy: stacked-to-main
- Review budget: 800 changed lines for the full change; this slice is autonomous
- Assigned tasks: 3.1 → 3.3 only
- Mode: Strict TDD (`pytest`)
- Boundary: create `services/api/app/modules/reporting/pdf_renderer.py`,
  `services/api/app/modules/reporting/storage.py`,
  `services/api/tests/test_reporting_pdf.py`,
  `services/api/tests/test_reporting_storage.py`, the embedded
  `services/api/app/modules/reporting/fonts/DejaVuSans.ttf` and license; update
  `services/api/pyproject.toml` with pinned ReportLab and PDF parser test
  dependencies. Complete the ADR-05 `report_artifacts` BYTEA table through the
  existing `0006_reports_pdf` model/migration and schema lockstep assertions.
  `usuarios.md`, service, routes, seed, permissions, audit, web, and F4/F5
  files remain untouched.

## Cumulative Completed Tasks

- [x] 1.1–1.3 — Work Unit 1 pure reporting domain, errors, and literal template parser; evidence remains above.
- [x] 2.1–2.4 — Work Unit 2 reporting models, migration `0006_reports_pdf`, and PostgreSQL repository; evidence remains above.
- [x] 3.1 — RED/GREEN normalized PDF contract: repeatable structure/text/metadata normalization, fixed section boundaries, Spanish output, embedded DejaVuSans, controlled metadata, and recursive no-leak scan.
- [x] 3.2 — RED/GREEN opaque PostgreSQL artifact storage contract: UUID4 keys, BYTEA payloads, persisted checksum/size/media type, stream reads, idempotent put/delete, missing-key handling, conflict detection, and orphan cleanup.
- [x] 3.3 — GREEN ReportLab/storage adapters, pinned dependencies, embedded font asset, ADR-05 artifact table, `docker compose build api`, and focused gate.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 3.1 | `services/api/tests/test_reporting_pdf.py` | Unit + PDF structure integration | N/A — new renderer test file | ✅ test written first; direct Compose collection failed with `ModuleNotFoundError: app.modules.reporting.pdf_renderer` | ✅ direct Compose renderer run `3 passed, 1 warning` | ✅ repeated render normalization, page structure/text, separate `norm_note`/disclaimer sections, Spanish labels, injected clock/timezone, DejaVuSans `/FontFile2`, metadata/path/internal scan, and alternate locale failure path | ✅ controlled ReportLab `TimeStamp` now derives `/CreationDate` and `/ModDate` from the injected clock; final renderer run remained `3 passed` |
| 3.2 | `services/api/tests/test_reporting_storage.py` | Real PostgreSQL integration | N/A — new storage test file | ✅ test written first; direct Compose collection failed with `ModuleNotFoundError: app.modules.reporting.storage` | ✅ direct Compose storage run `3 passed, 1 warning` | ✅ real BYTEA persistence, same-payload replay, conflicting payload rejection, stream read, opaque-key validation, idempotent delete, and orphan cleanup against PostgreSQL | ✅ caller-owned transactions, path-free `ArtifactStream`, UUID4 validation, and correlated orphan delete; final storage run remained `3 passed` |
| 3.3 | `services/api/app/modules/reporting/{pdf_renderer,storage}.py`, `services/api/pyproject.toml`, `services/api/app/modules/reporting/fonts/DejaVuSans.ttf`, `services/api/app/models/reporting.py`, `services/api/alembic/versions/0006_reports_pdf.py` | ReportLab adapter + SQLAlchemy/Alembic/PostgreSQL | ✅ pre-edit schema safety net `11 passed, 1 warning`; domain/repository safety net `11 passed, 1 warning` | ✅ adapter tests for the absent renderer/storage seams failed before production implementation | ✅ `docker compose build api` completed; focused PDF/storage gate `6 passed, 1 warning` | ✅ schema/storage lockstep `14 passed, 1 warning`, image-only PDF generation, and cumulative reporting gate `28 passed, 1 warning` | ✅ normalized metadata control, minimal public renderer result, opaque storage references, and no filesystem fallback; cumulative gate remained green |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command and exact result | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_reporting_pdf.py tests/test_reporting_storage.py` → `6 passed, 1 warning in 8.44s`; the warning is the known read-only `/repo/services/api/.pytest_cache` `PytestCacheWarning` only. The wrapper confirmation `powershell -ExecutionPolicy Bypass -File scripts/test.ps1 -k "reporting_pdf or reporting_storage"` reported `6 passed, 234 deselected, 2 warnings`; direct Compose is authoritative. |
| Runtime harness command/scenario and exact result | `docker compose build api` → `Image psico-api Built`; image-only `/app` smoke scenario generated a real PDF and printed `23681 reportlab-4.4.10 2026-08-11T12:30:00+00:00`; the direct focused Compose gate exercised real PostgreSQL migrations, BYTEA put/open/delete/checksum/orphan paths and real ReportLab generation. The image does not include test files, so the image runtime proof uses the inline `/app` scenario while mounted Compose pytest remains the authoritative test harness. |
| Rollback boundary | Remove exactly `services/api/app/modules/reporting/pdf_renderer.py`, `services/api/app/modules/reporting/storage.py`, `services/api/tests/test_reporting_pdf.py`, `services/api/tests/test_reporting_storage.py`, `services/api/app/modules/reporting/fonts/DejaVuSans.ttf`, `services/api/app/modules/reporting/fonts/LICENSE-DejaVu.txt`, and the ReportLab/PyPDF dependency lines; revert only the `ReportArtifact` model/export, `report_artifacts` migration/table assertions, and Slice-3 task/progress marks. If `0006_reports_pdf` has already been deployed, do not destructively downgrade: disable the adapter and use a forward migration while retaining report/artifact history, per ADR-05. Leave Slices 1–2, F4/F5, and `usuarios.md` untouched. |

## Implementation Notes

- `ReportLabRenderer` accepts injected locale (`es` only), timezone, clock, and
  font path; it uses the committed DejaVuSans TTF, fixed A4/Spanish layout, and
  application-owned minimal metadata with no ReportLab producer/path leakage.
- `RenderedReport` reports PDF bytes, `application/pdf`, renderer version
  `reportlab-4.4.10`, and controlled locale/timezone/generated-at metadata.
- `ReportArtifact` stores opaque UUID4 keys, report ids, BYTEA payloads, SHA-256,
  byte size, media type, and creation time. The report id is intentionally not a
  foreign key so staged storage can leave an orphan for deterministic cleanup
  after a report transaction rolls back.
- `PostgresReportStorage` does not commit, returns file-like authenticated-stream
  preparation metadata without paths/URLs, makes same-payload put/delete replay
  safe, rejects conflicting same-report payloads, and cleans missing-report rows
  idempotently.
- `reportlab==4.4.10` is a production dependency; `pypdf==6.15.0` is a test-only
  parser dependency. DejaVuSans is accompanied by its redistributable license.

## Deviations from Design

None from ADR-05. The existing Slice-2 `0006_reports_pdf` implementation had the
report metadata columns but not the ADR-05 `report_artifacts` BYTEA table, so this
slice completed that missing storage persistence shape and its model/schema
lockstep assertions. No service, API, seed, audit, permission, web, or F4/F5
behavior was added.

## Issues Found

- Compose pytest emits the established read-only `.pytest_cache` warning; it does
  not affect the functional result.
- `scripts/test.ps1` still masks pytest exit status, so direct Compose summaries
  remain authoritative.
- The API image intentionally excludes test files from its runtime context; an
  image-only pytest path is unavailable, but the rebuilt image successfully ran
  the inline PDF generation harness and mounted Compose tests covered the real
  PostgreSQL/reporting paths.

## Remaining Tasks

- [x] 1.1–1.3 — Work Unit 1 complete
- [x] 2.1–2.4 — Work Unit 2 complete
- [x] 3.1 RED deterministic PDF renderer contract
- [x] 3.2 RED opaque artifact storage contract
- [x] 3.3 GREEN ReportLab renderer/storage adapters and dependency
- [x] 4.1 RED staged report generation and failure behavior
- [x] 4.2 RED report idempotency replay/key reuse/new-key history
- [x] 4.3 RED prerequisite, no-engine, and authorization behavior
- [x] 4.4 RED latest metadata read behavior
- [x] 4.5 GREEN reporting service
- [x] 4.6 Lockstep permissions, audit event, contracts, and tests
- [ ] 5.1 RED reports API routes and strict DTOs
- [ ] 5.2 RED seed template and reset/preflight behavior
- [ ] 5.3 GREEN reports schemas/routes/router
- [ ] 5.4 GREEN seed fixture/loader
- [ ] 6.1 Verification regression/build evidence
- [ ] 6.2 Apply/verify/archive reconciliation

## Review / PR Boundary

- Current PR: stacked-to-main slice 3, targeting the preceding slice/main chain
  state; no commit was created because the task list did not request one.
- Start: Work Units 1–2 were green; reporting had no renderer/storage seam and
  `0006` had no BYTEA artifact table.
- Finish: one autonomous PDF renderer/storage unit now produces normalized,
  Unicode Spanish PDFs and persists opaque PostgreSQL artifacts with real
  checksum/stream/cleanup behavior.
- Follow-up: Slice 4 owns service staging, failure mapping, idempotency, and
  authorization/audit lockstep.
- Out of scope: API routes, seed/reset, permissions, audit catalog, web,
  integration, F4/F5 production changes, and `usuarios.md`.

## Work Unit 3 Status

10/22 implementation tasks complete. Slice 3 is green and ready for Slice 4;
the change is not ready for final verification.

---

## Work Unit 4

- Change: `2026-08-11-f6-reports-pdf-integration`
- Slice: 4 of 6 — Reporting service staging, failure convergence, and lockstep contracts
- Artifact store: hybrid (OpenSpec + Engram)
- Strategy: stacked-to-main
- Review budget: 800 changed lines for the full change; this slice is autonomous
- Assigned tasks: 4.1 → 4.6 only
- Mode: Strict TDD (`pytest`)
- Boundary: create `services/api/app/modules/reporting/service.py` and
  `services/api/tests/test_reporting_service.py`; modify only the capability/event
  lockstep files `services/api/app/core/permissions.py`,
  `services/api/app/core/audit.py`, `packages/contracts/README.md`,
  `services/api/tests/test_auth.py`, and `services/api/tests/test_audit.py`.
  Routes, schemas, seed/reset, web, F4/F5 production modules, and `usuarios.md`
  remain untouched.

## Cumulative Completed Tasks

- [x] 1.1–1.3 — Work Unit 1 pure reporting domain, errors, and literal template parser; evidence remains above.
- [x] 2.1–2.4 — Work Unit 2 reporting models, migration `0006_reports_pdf`, and PostgreSQL repository; evidence remains above.
- [x] 3.1–3.3 — Work Unit 3 deterministic ReportLab renderer, PostgreSQL BYTEA storage, pinned dependencies, and artifact persistence; evidence remains above.
- [x] 4.1 — T1 claim/pinning and T2 finalization stage the slow renderer/storage work outside the claim transaction; renderer, storage, and audit failures converge to `failed` without an artifact and map to `INTERNAL_ERROR/report_generation_failed`.
- [x] 4.2 — Idempotency uses operation `report.generated` and `resource_scope=session:{id}`; same-body replays are exact, different bodies conflict, failed retries reuse the same report, and new keys create historical rows.
- [x] 4.3 — Missing, unscored, and ungenerated prerequisites are indistinguishable `NOT_FOUND/resource_not_found` with zero report effects; in-progress sessions conflict; the service does not import or invoke F4/F5 engines; evaluado is denied and audited before lookup.
- [x] 4.4 — Latest metadata reads order by `created_at DESC, id DESC`, expose only the ratified metadata projection, and remain side-effect-free; no-report and missing-session reads share the same not-found error.
- [x] 4.5 — `ReportingService` composes pinned persisted snapshots, stores opaque artifacts, finalizes ready reports with complete artifact fields, and emits one aggregate-only `report.generated` event.
- [x] 4.6 — `view_reports` and `report.generated` are updated in lockstep across code, contracts README, and contract tests.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 4.1 | `services/api/tests/test_reporting_service.py` | Real PostgreSQL service integration | N/A — new service test file | ✅ written first; collection failed with `ModuleNotFoundError: app.modules.reporting.service` before production implementation | ✅ final combined Compose gate `37 passed`; service-only confirmation `9 passed` | ✅ happy path, T1 transaction release, renderer failure, storage failure, audit failure, orphan cleanup, and failed-row retry convergence | ✅ separated T1 claim, artifact transaction, T2 finalize, and compensating failure helpers; focused suite remained green |
| 4.2 | `services/api/tests/test_reporting_service.py` | Real PostgreSQL idempotency integration | N/A — covered by new service test file | ✅ same-key/reused-key/new-key tests were written before service implementation | ✅ same combined gate `37 passed` | ✅ `session:{id}` scope assertion, exact replay, `idempotency_key_reused`, historical second report, unchanged first artifact, and same-row retry after failure | ✅ final replay returns the persisted DTO without re-reading expired response state |
| 4.3 | `services/api/tests/test_reporting_service.py` | Real PostgreSQL availability/auth integration | N/A — covered by new service test file | ✅ prerequisite/no-engine/denial tests were written before service implementation | ✅ same combined gate `37 passed` | ✅ missing UUID, completed-but-unscored, scored-but-ungenerated, in-progress, monkeypatched F4/F5 engines, and evaluado-before-lookup denial | ✅ authorization is an early capability gate and does not perform resource queries for denied users |
| 4.4 | `services/api/tests/test_reporting_service.py` | Real PostgreSQL read integration | N/A — new service test coverage | ✅ latest metadata tests were written before service implementation | ✅ final service-only gate `9 passed` | ✅ tie-break by report UUID, repeated side-effect-free reads, no-report, and missing-session indistinguishability | ✅ metadata projection is centralized and conditionally adds checksum/size only for ready rows |
| 4.5 | `services/api/app/modules/reporting/service.py` | Service + repository/renderer/storage adapters | ✅ prior Slice-3 PDF/storage gates remained available | ✅ service tests referenced the absent orchestration module | ✅ final combined Compose gate `37 passed` | ✅ actual PostgreSQL report/artifact rows, persisted pins, complete ready fields, and aggregate audit event | ✅ no F4/F5 imports; I/O is isolated from T1 and finalization owns commit boundaries |
| 4.6 | `services/api/tests/test_auth.py`, `services/api/tests/test_audit.py` | Pure lockstep contract tests | ✅ pre-edit auth/audit safety net `26 passed, 8 warnings` | ✅ expected matrix/catalog and aggregate event test were written before capability/catalog edits; initial collection stopped at absent service | ✅ final combined Compose gate `37 passed` | ✅ professional-only capability, evaluado denial, exact event catalog, exact aggregate metadata, and deny-list sweep | ✅ README §3/§6 wording mirrors the code/test contract without adding public fields |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command and exact result | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_reporting_service.py tests/test_auth.py tests/test_audit.py` → `37 passed, 8 warnings in 13.97s`; final service-only triangulation → `9 passed, 1 warning in 10.87s`. Direct Compose pytest is authoritative; warnings are the established FastAPI/httpx, JWT key-length, and read-only `.pytest_cache` warnings only. |
| Runtime harness command/scenario and exact result | The same direct Compose command exercised the real PostgreSQL migration/seed fixture, reporting rows, BYTEA artifact storage, audit persistence, TestClient auth paths, and lockstep contracts. No separate HTTP reports route exists in Slice 4, so the service integration tests are the applicable runtime boundary. |
| Rollback boundary | Remove exactly `services/api/app/modules/reporting/service.py`, `services/api/tests/test_reporting_service.py`, the `view_reports` entries in `services/api/app/core/permissions.py` and `services/api/tests/test_auth.py`, the `report.generated` entries/contract test in `services/api/app/core/audit.py` and `services/api/tests/test_audit.py`, and the corresponding `packages/contracts/README.md` lines. Revert only Slice-4 task/progress marks. Leave Slices 1–3, F4/F5 production code, routes/seed/web, and `usuarios.md` untouched. |

## Implementation Notes

- T1 locks the session while it snapshots the latest completed score run,
  recommendation generation, and published `informe-basico` version; it then
  commits `pending → processing` plus an internal idempotency claim before any
  composition, rendering, or storage work.
- Storage is committed independently so T2 can finalize the report and audit
  atomically; any T2 failure deletes the opaque artifact first and then commits
  `failed` with all artifact fields cleared.
- Failed-key retries load the persisted score/template pins and F5 value snapshot,
  transition the same row back to `processing`, and converge on one ready row,
  one artifact, and one success event.
- `report.generated` metadata contains exactly session/report/template ids,
  `template_version_no`, `processing->ready`, checksum/size, and created/generated
  timestamps. It never contains report body, scores, justifications, PDF bytes,
  storage keys, tokens, or paths.
- The new capability is professional-only: admin and psicólogo can operate any
  session; evaluado is rejected before lookup and only the aggregate denial audit
  record is committed.

## Deviations from Design

None — implementation follows ADR-04 and ADR-06. The service adds no route or seed
behavior, and lockstep changes are limited to the ratified capability/event matrix,
contracts README, and their contract tests.

## Issues Found

- The first GREEN harness attempt exposed a test-fixture-only FK ordering defect;
  an explicit flush of the new runtime session fixed it before production assertions.
- The next GREEN attempt exposed the required failed-to-processing transition on
  same-key retry; the service now performs that T1 convergence step.
- Direct Compose pytest remains authoritative because `scripts/test.ps1` masks the
  pytest exit code; read-only `.pytest_cache` warnings remain non-functional.

## Remaining Tasks

- [x] 1.1–1.3 — Work Unit 1 complete
- [x] 2.1–2.4 — Work Unit 2 complete
- [x] 3.1–3.3 — Work Unit 3 complete
- [x] 4.1–4.6 — Work Unit 4 complete
- [ ] 5.1 RED reports API routes and strict DTOs
- [ ] 5.2 RED seed template and reset/preflight behavior
- [ ] 5.3 GREEN reports schemas/routes/router
- [ ] 5.4 GREEN seed fixture/loader
- [ ] 6.1 Verification regression/build evidence
- [ ] 6.2 Apply/verify/archive reconciliation

## Review / PR Boundary

- Current PR: stacked-to-main slice 4, targeting the preceding slice/main chain
  state; no commit was created because the task list did not request one.
- Start: Work Units 1–3 were green; reporting had persistence, deterministic PDF,
  and BYTEA seams but no orchestration service or ratified report access/event
  lockstep.
- Finish: one autonomous service/lockstep unit stages report generation safely,
  converges retries, preserves no-leak boundaries, and passes service/auth/audit
  contracts against real PostgreSQL.
- Follow-up: Slice 5 owns HTTP DTOs/routes/router plus seed/reset/template fixture.
- Out of scope: API routes, schemas, seed/reset, web, F4/F5 production changes,
  and `usuarios.md`.

## Work Unit 4 Status

16/22 implementation tasks complete. Slice 4 is green and ready for Slice 5;
the change is not ready for final verification.

---

## Work Unit 5

- Change: `2026-08-11-f6-reports-pdf-integration`
- Slice: 5 of 6 — Reports API routes/DTOs and synthetic template seed/reset extension
- Artifact store: hybrid (OpenSpec + Engram)
- Strategy: stacked-to-main
- Review budget: 800 changed lines for the full change; this slice is autonomous
- Assigned tasks: 5.1 → 5.4 only
- Mode: Strict TDD (`pytest`)
- Boundary: create `services/api/app/schemas/reports.py`,
  `services/api/app/api/routes/reports.py`,
  `services/api/tests/test_reports_api.py`, and
  `services/api/app/seed/fixtures/report_template.json`; modify only
  `services/api/app/api/router.py`, `services/api/app/modules/reporting/service.py`,
  `services/api/app/seed/loader.py`, the reporting migration's reset-compatible
  template trigger, `services/api/tests/test_seed.py`, this change's
  `tasks.md`, and this `apply-progress.md`. `usuarios.md`, web files, F4/F5
  engines, and unrelated active-slice files remain untouched.

## Cumulative Completed Tasks

- [x] 1.1–1.3 — Work Unit 1 pure reporting domain, errors, and literal template parser; evidence remains above.
- [x] 2.1–2.4 — Work Unit 2 reporting models, migration `0006_reports_pdf`, and repository; evidence remains above.
- [x] 3.1–3.3 — Work Unit 3 deterministic ReportLab renderer, PostgreSQL BYTEA storage, pinned dependencies, and artifact persistence; evidence remains above.
- [x] 4.1–4.6 — Work Unit 4 staged reporting service, failure convergence, idempotency, professional-only access, audit event, and lockstep contracts; evidence remains above.
- [x] 5.1 — RED API TestClient coverage for generation, exact DTOs, strict request validation, envelopes, replay/new-key behavior, latest metadata, zero-effect reads, download checksum/size/streaming, not-ready indistinguishability, and evaluado denial.
- [x] 5.2 — RED seed/reset coverage for UUID5 `informe-basico`, published v1 synthetic ownership, manifest/checksum/version, runtime score/report/template/artifact survival, dependency preflight, zero deletions, and idempotency FK protection.
- [x] 5.3 — GREEN strict report schemas, three thin authorized routes, authenticated chunked PDF streaming, checksum/size headers, service download re-authorization, and router registration.
- [x] 5.4 — GREEN report-template fixture and loader integration: `SEED_TABLES`, manifest counts/checksum, `SEED_VERSION=1.2.0`, reset preflight for reporting dependencies, and runtime-safe reset behavior.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 5.1 | `services/api/tests/test_reports_api.py` | TestClient + real PostgreSQL integration | ✅ pre-edit service/auth/audit gate `37 passed, 8 warnings` | ✅ tests written first; initial route execution `4 failed` with HTTP 404 because the reports router did not exist | ✅ final focused API gate `6 passed, 14 warnings` | ✅ ready generation, exact ready/pending DTO projections, strict unknown-body validation, replay/new-key history, latest/no-report reads, missing/not-ready download equivalence, checksum/size, chunked stream, idempotency-key requirement, and evaluado denial | ✅ centralized DTO validation/projection, streaming generator closes the opaque stream, and artifact integrity is checked before delivery |
| 5.2 | `services/api/tests/test_seed.py` | Real PostgreSQL seed/reset integration | ✅ prior seed gate `18 passed, 1 warning` | ✅ tests written before loader changes; initial seed gate `19 passed, 3 failed`, exposing absent template seed and reporting FK preflight | ✅ final seed gate `24 passed, 1 warning` | ✅ fixture syntax, UUID5 identity, exact ownership/status/version, manifest/checksum, reseed idempotence, runtime score/report/artifact/template survival, seed-session/reference/template conflicts, and seed-user idempotency FK conflict | ✅ reset dependency checks are stable and atomic; published template reset follows the existing `app.seed_reset` trigger convention without bypassing runtime template protection |
| 5.3 | `services/api/tests/test_reports_api.py` | FastAPI/TestClient + real PostgreSQL | ✅ service-only/API-adjacent safety net remained green | ✅ route tests referenced absent schemas/routes/router/download seam | ✅ final API gate `6 passed, 14 warnings` | ✅ admin and psicólogo paths, strict Pydantic `extra="forbid"`, route envelopes, metadata omission rules, authenticated stream, and denial audit | ✅ routes stay thin; orchestration and artifact integrity remain in `ReportingService` |
| 5.4 | `services/api/tests/test_seed.py` | SQLAlchemy/Alembic + real PostgreSQL | ✅ seed/schema safety nets remained green | ✅ seed assertions preceded fixture/loader implementation | ✅ combined final gate `103 passed, 46 warnings` across schema/reporting/API/seed/auth/audit/results/recommendations; focused seed/API gate `30 passed, 14 warnings` | ✅ fresh/repeat migration, seed and reset CLI, reporting row counts, runtime row retention, and all ratified reset dependency classes | ✅ fixture is data-only and deterministic; loader owns the seed scope while runtime reports/artifacts remain outside deletion scope |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command and exact result | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_reports_api.py tests/test_seed.py` → `30 passed, 14 warnings in 145.13s`; direct Compose pytest is authoritative. Warnings are the established FastAPI/httpx, JWT key-length, and read-only `.pytest_cache` warnings only. |
| Runtime harness command/scenario and exact result | `docker compose build api` → `Image psico-api Built`; `docker compose run --rm api alembic upgrade head` completed with exit code 0; `docker compose run --rm api python -m app.seed` completed with `seed_version=1.2.0`, `report_templates=1`, `score_runs=0`, `reports=0`; after clearing only test-created runtime rows, `docker compose run --rm api python -m app.seed --reset` completed successfully with the same template/count contract. The cumulative direct Compose gate was `103 passed, 46 warnings in 154.22s`. |
| Rollback boundary | Remove exactly `services/api/app/schemas/reports.py`, `services/api/app/api/routes/reports.py`, `services/api/tests/test_reports_api.py`, and `services/api/app/seed/fixtures/report_template.json`; revert the reports router registration, reporting-service download seam, loader/template/reset/preflight changes, the reset-compatible reporting trigger change, Slice-5 additions to `test_seed.py`, and Slice-5 task/progress marks. Preserve Slices 1–4, the deployed `0006` reporting schema, runtime reports/artifacts, audit history, F4/F5 code, and `usuarios.md`; if `0006` is deployed, disable routes/adapters and use a forward fix rather than destructive downgrade. |

## Implementation Notes

- `ReportGenerateRequest` is an intentionally empty strict DTO: templates and other options cannot be selected by clients. `ReportMetadata` forbids unknown fields and requires checksum/byte size only for `ready` reports.
- The three routes declare `require_roles(ADMIN, PSICOLOGO)`. The service retains the `view_reports` capability gate and performs a second authorization check for downloads before any report lookup; evaluado receives only the standard forbidden envelope and an `auth.denied` event.
- Metadata reads return the latest report using the service's deterministic `created_at DESC, id DESC` ordering and never expose storage keys, paths, PDF payloads, scores, or justifications. Download returns an authenticated `StreamingResponse` with `application/pdf`, `Content-Length`, and `X-Checksum-SHA256`; no URL or path is returned.
- `report_template.json` is literal Spanish data using only the six allow-listed placeholders. Its UUID5 is `seed_id("report-template:informe-basico")`, status is `published`, version is `1`, and it is `synthetic=true/source='seed'`.
- Reset preflight now rejects runtime score runs/reports that reference seed sessions, reference sets, or the seed template, and also protects seed users referenced by idempotency records so FK failures cannot occur after preflight. Runtime reports, score runs, artifacts, and runtime templates are never in the deletion scope.
- The reporting-template immutability trigger honors the already established transaction-local `app.seed_reset` guard, matching catalog reset guards; normal published/retired runtime template edits remain protected.

## Deviations from Design

None — implementation matches ADR-06 and ADR-07. The only supporting schema-file change is the existing reset guard in `0006_reports_pdf`; it does not change the reporting schema or weaken normal template immutability.

## Issues Found

- `scripts/test.ps1` is not authoritative because it masks pytest's exit code; direct Compose summaries above are the evidence source.
- Compose emits the established read-only `.pytest_cache`, FastAPI/httpx deprecation, and JWT key-length warnings; no functional test failures remain in the slice gate.
- The development database contains test-created runtime rows after integration suites; this is expected test behavior and does not alter repository artifacts. A clean seed/reset CLI scenario was executed separately after clearing only those runtime test rows.

## Remaining Tasks

- [x] 1.1–1.3 — Work Unit 1 complete
- [x] 2.1–2.4 — Work Unit 2 complete
- [x] 3.1–3.3 — Work Unit 3 complete
- [x] 4.1–4.6 — Work Unit 4 complete
- [x] 5.1–5.4 — Work Unit 5 complete
- [ ] 6.1 Verification regression/build evidence
- [ ] 6.2 Apply/verify/archive reconciliation

## Review / PR Boundary

- Current PR: stacked-to-main slice 5, targeting the preceding slice/main chain state; no commit was created because the task list did not request one.
- Start: Work Units 1–4 were green; the reporting service had no HTTP route/DTO/download adapter and seed reset did not own the default template or preflight reporting dependencies.
- Finish: the reports API exposes strict metadata and authenticated PDF streams for professional roles, while the seed engine owns the deterministic default template and fails reset atomically before runtime reporting FK damage.
- Follow-up: Slice 6 owns regression ×2 and final verify/archive reconciliation.
- Out of scope: web, new F4/F5 engines, integration/outbox/vendor delivery, published instrument edits, and `usuarios.md`.

## Work Unit 5 Status

20/22 implementation tasks complete. Slice 5 is green and ready for Slice 6 verification; the change is not ready for final verification/archive.

---

## Slice 5 Apply Recheck — 2026-08-12

- The merged Work Units 1–5 artifact and all Slice-5 task checkboxes were present before this invocation; no implementation task outside Slice 5 was started.
- Authoritative focused gate: `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_reports_api.py tests/test_seed.py` → `31 passed, 14 warnings in 157.15s`.
- Runtime/build evidence: `docker compose build api` → `Image psico-api Built`; `docker compose run --rm api alembic upgrade head` completed with exit code 0; `docker compose run --rm api python -m app.seed` completed with `seed_version=1.2.0`, `report_templates=1`, `score_runs=0`, and `reports=0`.
- Repository hygiene evidence: `git diff --check` → `PASS`; `usuarios.md` was not read or modified.
- No code files were changed during this recheck; the Slice-5 implementation remains ready for Slice 6 verification.

---

## Work Unit 6

- Change: `2026-08-11-f6-reports-pdf-integration`
- Slice: 6 of 6 — Full-suite regression ×2 and apply evidence consolidation
- Artifact store: hybrid (OpenSpec + Engram)
- Strategy: stacked-to-main
- Review budget: 800 changed lines for the full change; this slice is docs-only
- Assigned tasks: 6.1 → 6.2 only
- Mode: Strict TDD (`pytest`), verification-only boundary
- Boundary: rebuild the API image, run the direct Compose full pytest suite twice,
  compare pytest summaries, run `git diff --check`, and consolidate evidence here.
  No implementation, web, migration, seed, or `usuarios.md` changes are permitted.

## Cumulative Completed Tasks

- [x] 1.1–1.3 — Work Unit 1 complete
- [x] 2.1–2.4 — Work Unit 2 complete
- [x] 3.1–3.3 — Work Unit 3 complete
- [x] 4.1–4.6 — Work Unit 4 complete
- [x] 5.1–5.4 — Work Unit 5 complete
- [ ] 6.1 — Not complete: both full-suite runs reproduced an additional
  F6-caused migration expectation failure in addition to the two documented
  inherited web failures.
- [ ] 6.2 — Not complete: evidence was consolidated, but final reconciliation
  cannot mark the change ready for verify while 6.1 has a non-permitted failure.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 6.1 | `services/api/tests` | Full regression + real PostgreSQL integration | ✅ API image rebuilt before both runs | ➖ N/A — verification-only task; no new test or production code was authored | ❌ not achieved: each run ended with `3 failed, 261 passed, 100 warnings`; one failure is outside the permitted inherited web debt | ❌ functional failure set was reproducible across both runs, but the required two-failure-only invariant was not met | ➖ no refactor permitted in final verification slice |
| 6.2 | `openspec/changes/2026-08-11-f6-reports-pdf-integration/{tasks,apply-progress}.md` | SDD artifact reconciliation | N/A — documentation-only consolidation | ➖ N/A — no production behavior to drive a RED test | ❌ blocked from completion by the 6.1 regression result | ✅ both run summaries and all three failure names were consolidated verbatim below | ➖ no refactor; preserve prior cumulative evidence |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command and exact result | `docker compose build api` → `Image psico-api Built`. Run 1: `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests` → `3 failed, 261 passed, 100 warnings in 172.38s (0:02:52)`. Run 2: the same command → `3 failed, 261 passed, 100 warnings in 165.17s (0:02:45)`. Both runs collected 264 tests and reproduced the same three failure names. |
| Runtime harness command/scenario and exact result | The direct Compose full suite exercised the real PostgreSQL/TestClient runtime boundary twice after the rebuilt API image. Both runs reached 100% collection/execution and produced the identical functional result set below; the extra migration failure prevents a passing runtime gate. |
| Rollback boundary | Revert only the appended Slice-6 section in `openspec/changes/2026-08-11-f6-reports-pdf-integration/apply-progress.md`; no implementation files, tests, web files, migration, seed data, or `usuarios.md` were changed by this slice. |

## Full-suite Regression Evidence

### Run 1 — 2026-08-12

Command:

```text
docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests
```

Pytest summary (verbatim):

```text
3 failed, 261 passed, 100 warnings in 172.38s (0:02:52)
```

Failures:

- `tests/test_catalog_migration.py::test_f1_backfill_upgrade_is_idempotent`
- `tests/test_web.py::test_page_is_spanish`
- `tests/test_web.py::test_page_never_leaks_stack_trace`

### Run 2 — 2026-08-12

Command:

```text
docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests
```

Pytest summary (verbatim):

```text
3 failed, 261 passed, 100 warnings in 165.17s (0:02:45)
```

Failures:

- `tests/test_catalog_migration.py::test_f1_backfill_upgrade_is_idempotent`
- `tests/test_web.py::test_page_is_spanish`
- `tests/test_web.py::test_page_never_leaks_stack_trace`

### Comparison and failure classification

- The two runs are functionally identical: 264 collected, 261 passed, 3 failed,
  and the same three failure names in the same failure classes.
- The two permitted inherited web failures are exactly the documented debt:
  `test_web.py::test_page_is_spanish` and
  `test_web.py::test_page_never_leaks_stack_trace`.
- The additional failure is not permitted inherited debt:
  `test_catalog_migration.py::test_f1_backfill_upgrade_is_idempotent` asserts the
  old `0005_catalog_four_level` head, while the F6 migration correctly leaves the
  linear head at `0006_reports_pdf`. The observed assertion was
  `assert '0006_reports_pdf' == '0005_catalog_four_level'`.
- This is treated as F6-caused/stale migration expectation, not papered over in
  Slice 6. No code or test was changed to hide it.

## Repository Hygiene

- `git diff --check` → `PASS` after the Slice-6 evidence append.
- `usuarios.md` remained out of scope and was not read, modified, staged, or
  deleted.
- No implementation files changed during Slice 6.

## Deviations from Design

None in implementation. Final verification cannot satisfy the design/task DoD
because the existing catalog migration assertion still expects the pre-F6 head.

## Issues Found

- Blocking F6-related regression: `tests/test_catalog_migration.py::test_f1_backfill_upgrade_is_idempotent`
  expects `0005_catalog_four_level`, but F6's required linear successor is
  `0006_reports_pdf`.
- The two documented inherited web failures remain unchanged and are the same in
  both runs; no web file was touched.
- `scripts/test.ps1` remains non-authoritative because it masks pytest's exit
  status; direct Compose pytest summaries above are authoritative.
- Compose emitted the established non-functional FastAPI/httpx, JWT key-length,
  and read-only `.pytest_cache` warnings.

## Review / PR Boundary

- Current PR: final stacked-to-main Slice 6 evidence unit; docs-only, no commit
  created because the task list did not request one.
- Start: Work Units 1–5 were complete and Slice 5 focused evidence was green.
- Finish: API image rebuilt, full suite executed twice, identical functional
  failure set recorded, and merged evidence persisted; the change is **not** ready
  for `sdd-verify` because the third failure is not permitted inherited debt.
- Rollback: remove only this Work Unit 6 section from this artifact.

## Work Unit 6 Status

20/22 implementation tasks complete. Slice 6 failed its acceptance gate because
both full-suite runs contain one additional F6-caused migration expectation
failure beyond the two documented inherited web failures. Do not proceed to
`sdd-verify` until the orchestrator resolves that failure and reruns the required
regression evidence.

---

## Work Unit 6 Retry — 2026-08-12

- Change: `2026-08-11-f6-reports-pdf-integration`
- Slice: 6 of 6 retry after correction — full-suite regression ×2 and final evidence consolidation
- Artifact store: hybrid (OpenSpec + Engram)
- Strategy: stacked-to-main
- Review budget: 800 changed lines for the full change; this slice is docs-only
- Assigned tasks: 6.1 → 6.2 only
- Mode: Strict TDD (`pytest`), verification-only boundary
- Correction consumed: the orchestrator already updated
  `services/api/tests/test_catalog_migration.py::test_f1_backfill_upgrade_is_idempotent`
  to assert the legitimate F6 migration head `0006_reports_pdf`. This retry did not
  re-fix, revert, or otherwise modify that correction.
- Boundary: rebuild the API image, run the direct Compose full pytest suite twice
  with `-p no:cacheprovider --tb=short`, compare authoritative in-container
  summaries, run `git diff --check`, and consolidate this merged artifact. No
  implementation, web, migration, seed, or `usuarios.md` changes were permitted.

## Cumulative Completed Tasks

- [x] 1.1–1.3 — Work Unit 1 pure reporting domain, errors, and literal template parser.
- [x] 2.1–2.4 — Work Unit 2 reporting models, migration `0006_reports_pdf`, and repository.
- [x] 3.1–3.3 — Work Unit 3 deterministic ReportLab renderer, PostgreSQL BYTEA storage, pinned dependencies, and artifact persistence.
- [x] 4.1–4.6 — Work Unit 4 staged reporting service, failure convergence, idempotency, professional-only access, audit event, and lockstep contracts.
- [x] 5.1–5.4 — Work Unit 5 strict reports API, authenticated download, synthetic template seed, and reset/preflight ownership.
- [x] 6.1 — API image rebuilt; full suite executed twice through direct Compose with authoritative in-container summaries; both runs have identical functional counts and only the two documented inherited web failures.
- [x] 6.2 — Final regression evidence merged; task checkboxes reconciled; change is ready for `sdd-verify`. Archive remains deferred.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 6.1 | `services/api/tests` | Full regression + real PostgreSQL/TestClient integration | ✅ API image rebuilt before both runs; corrected migration-head assertion was present | ➖ N/A — verification-only task; no new test or production code was authored | ✅ both runs reached the same result: `2 failed, 262 passed, 98 warnings`; the only failures are documented inherited web debt | ✅ repeated full-suite execution produced the identical count and failure names; F6 migration assertion passed | ➖ no refactor permitted in final verification slice |
| 6.2 | `openspec/changes/2026-08-11-f6-reports-pdf-integration/{tasks,apply-progress}.md` | SDD artifact reconciliation | N/A — documentation-only consolidation | ➖ N/A — no production behavior to drive a RED test | ✅ cumulative slices 1–6 and final evidence are persisted; tasks 6.1/6.2 are marked complete | ✅ prior failed evidence and correction note are preserved, while clean retry evidence supersedes the failed gate | ➖ no refactor; preserve cumulative evidence |

## Work Unit Evidence

| Evidence | Exact result |
|---|---|
| Focused test command and exact result | `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api bash -lc 'pytest -p no:cacheprovider --tb=short tests > /tmp/f6-run1.txt 2>&1; status=$?; echo EXIT=$status; tail -5 /tmp/f6-run1.txt; exit $status'` → authoritative tail: `2 failed, 262 passed, 98 warnings in 181.66s (0:03:01)`. Run 2 with the same command and `/tmp/f6-run2.txt` → authoritative tail: `2 failed, 262 passed, 98 warnings in 183.99s (0:03:03)`. Both runs collected 264 tests. The command exits 1 only because the two pre-existing inherited web failures remain; the permitted failure set is exact and unchanged. |
| Runtime harness command/scenario and exact result | `docker compose build api` → `Image psico-api Built`; direct Compose full pytest exercised real PostgreSQL/TestClient runtime twice after the rebuild. Both runs passed the corrected F6 migration-head assertion and all F6 reporting/schema/seed/API tests; only the two documented inherited web tests failed. |
| Rollback boundary | Revert only the retry section appended to `openspec/changes/2026-08-11-f6-reports-pdf-integration/apply-progress.md` and the two Slice-6 checkbox changes in `tasks.md`. Do not revert `services/api/tests/test_catalog_migration.py`'s orchestrator correction or any implementation, web, migration, seed, or `usuarios.md` state. |

## Full-suite Regression Evidence — Retry

### Run 1 — 2026-08-12

Command:

```text
docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api bash -lc 'pytest -p no:cacheprovider --tb=short tests > /tmp/f6-run1.txt 2>&1; status=$?; echo EXIT=$status; tail -5 /tmp/f6-run1.txt; exit $status'
```

Authoritative pytest summary (verbatim from inside the container):

```text
2 failed, 262 passed, 98 warnings in 181.66s (0:03:01)
```

Collected: `264`; passed: `262`; failed: `2`.

Failures:

- `tests/test_web.py::test_page_is_spanish`
- `tests/test_web.py::test_page_never_leaks_stack_trace`

### Run 2 — 2026-08-12

Command:

```text
docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api bash -lc 'pytest -p no:cacheprovider --tb=short tests > /tmp/f6-run2.txt 2>&1; status=$?; echo EXIT=$status; tail -5 /tmp/f6-run2.txt; exit $status'
```

Authoritative pytest summary (verbatim from inside the container):

```text
2 failed, 262 passed, 98 warnings in 183.99s (0:03:03)
```

Collected: `264`; passed: `262`; failed: `2`.

Failures:

- `tests/test_web.py::test_page_is_spanish`
- `tests/test_web.py::test_page_never_leaks_stack_trace`

### Retry comparison and classification

- The two retry runs are functionally identical: `264 collected`, `262 passed`,
  `2 failed`, `98 warnings`, with the same two failure names.
- The only failures are exactly the documented inherited web debt:
  `test_web.py::test_page_is_spanish` and
  `test_web.py::test_page_never_leaks_stack_trace`.
- The prior F6-related stale migration-head failure is absent. The corrected
  assertion `== "0006_reports_pdf"` passes in both full-suite runs.
- No F6-caused failure appears. No failure was papered over in this retry, and no
  web or implementation file was changed.

## Repository Hygiene

- `docker compose build api` → `Image psico-api Built`.
- `git diff --check` → `PASS` after the retry evidence/task reconciliation.
- `usuarios.md` remained out of scope and was not read, modified, staged, or deleted.
- No implementation files were changed during Slice 6 retry.

## Deviations and Issues

- No implementation deviation from design.
- The two inherited web failures remain documented and unchanged; F6 explicitly
  excludes web and they are the only failures permitted by the handoff DoD.
- `scripts/test.ps1` remains non-authoritative because it masks pytest exit status;
  direct Compose pytest summaries printed from inside the container are authoritative.
- Compose emitted established non-functional warnings; the retry used
  `-p no:cacheprovider`, so the read-only `.pytest_cache` warning was not introduced.

## Review / PR Boundary

- Current PR: final stacked-to-main Slice 6 retry evidence unit; docs-only, no commit
  created because the task list did not request one.
- Start: Work Units 1–5 were complete; the previous Slice-6 gate was blocked by a
  stale F1 migration-head assertion that the orchestrator corrected before retry.
- Finish: API image rebuilt, full suite executed twice, summaries matched, only the
  two documented inherited web failures remained, and task/progress evidence was
  reconciled. The change is ready for `sdd-verify`; do not archive in this phase.
- Rollback: remove only this retry section and the Slice-6 checkbox updates.

## Work Unit 6 Retry Status

22/22 implementation tasks complete. Slice 6 retry satisfies its acceptance gate:
both full-suite runs have identical `264 collected / 262 passed / 2 failed`
functional counts, the only failures are the two documented inherited web failures,
and `git diff --check` is clean. `next_recommended: sdd-verify`.

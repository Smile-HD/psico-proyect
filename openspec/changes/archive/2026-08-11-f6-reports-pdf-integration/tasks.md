# Tasks: F6 — Traceable Reports, PDF & Authorized Download

## Review Workload Forecast

Estimated changed lines: ~1,800–2,250 (6 slices; budget 800) — exceeded.

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

Runner convention (all gates): `docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest <targets>`; `docker compose build api` after deps/migrations. Never trust `scripts/test.ps1` exit code (wrapper hides pytest status — cite pytest summary or use direct Compose).

Fixtures: F4 claims `evaluado_19..20`, F5 claims `evaluado_21..30`; F6 audits the suite first, then uses runtime-created sessions/runs/generations (or disjoint free profiles), always delta counts before/after, never absolute totals.

### Suggested Work Units

| Unit | Goal / commit | Focused test command | Runtime harness | Rollback boundary |
|------|---------------|----------------------|-----------------|-------------------|
| 1 | Domain+errors+template parser — `feat(api): add pure report composition domain` | `pytest tests/test_reporting_domain.py` | N/A — pure unit, no DB | Remove `modules/reporting/{domain,errors}.py` + test |
| 2 | Models+migration+repository — `feat(db): persist traceable report generations` | `pytest tests/test_schema.py tests/test_reporting_repository.py` | `compose run --rm api alembic upgrade head` fresh + repeat | Revert migration/models; else forward-fix |
| 3 | Renderer+storage+reportlab — `feat(api): add deterministic PDF rendering adapter` | `pytest tests/test_reporting_pdf.py tests/test_reporting_storage.py` | `docker compose build api` + real PDF generation | Remove adapters + pyproject dep, no DB impact |
| 4 | Service+lockstep — `feat(api): orchestrate report generation and ratify access` | `pytest tests/test_reporting_service.py tests/test_auth.py tests/test_audit.py` | TestClient + PG via compose | Revert service + permissions/audit/README/tests |
| 5 | API + seed/reset — `feat(api): expose the ratified reports API`; `feat(seed): seed informe-basico and extend reset preflight` | `pytest tests/test_reports_api.py tests/test_seed.py` | TestClient+PG; `compose run --rm api python -m app.seed [--reset]` | Remove routes/schemas/router edit; revert fixture/loader |
| 6 | Regression ×2 + verify/archive — `docs(openspec): verify and archive f6-reports-pdf-integration` | full suite twice, cite pytest summaries | `docker compose build api` + `pytest tests` ×2 | Docs-only revert |

## Phase 1: Domain & Templates (Slice 1)

- [x] 1.1 RED `tests/test_reporting_domain.py`: frozen `ReportInput`/`ReportDocument`; fixed section order scores→overall→recommendations→`norm_note`→disclaimer; pins (score_run_id, F5 snapshot, template id/version); determinism; inputs unmutated; no SQLAlchemy/FastAPI/I/O/clock imports
- [x] 1.2 RED same file: template allow-list parser — ratified placeholders only; unknown/missing → typed error; no eval/exec/import; no-leak (no option values/ids, 1–5 mapping, item content)
- [x] 1.3 GREEN `app/modules/reporting/{__init__,errors,domain}.py`; gate: `pytest tests/test_reporting_domain.py` green

## Phase 2: Schema & Repository (Slice 2)

- [x] 2.1 RED `tests/test_schema.py`: models=migration lockstep — `score_run_id` FK, F5 JSONB snapshot, `template_version_no`, status/format CHECKs, artifact fields, `created_at/updated_at/failed_at`; template `version_no`/status/unique(key,version_no)/published-immutability trigger; F1–F5 constraints intact; fresh 0005→0006, `upgrade head` ×2 idempotent, linear history
- [x] 2.2 RED `tests/test_reporting_repository.py` (runtime fixtures, delta counts): reads+pins; transitions pending→processing→ready, →failed; ready requires artifact fields; UUID4/`synthetic=False`/`source='runtime'`; no hidden commit; multi-report per session
- [x] 2.3 GREEN `app/models/reporting.py` + `alembic/versions/0006_reports_pdf.py`
- [x] 2.4 GREEN `app/modules/reporting/repository.py`; gate: schema+repository tests green

## Phase 3: Renderer & Storage (Slice 3)

- [x] 3.1 RED `tests/test_reporting_pdf.py`: normalized PDF determinism (structure/text/metadata, not bytes); sections present; `norm_note` and disclaimer in own sections (never one inside the other); Spanish locale + embedded DejaVu TTF; metadata no paths/renderer internals; no-leak scan of PDF text+metadata
- [x] 3.2 RED `tests/test_reporting_storage.py`: put/open/delete opaque keys; sha256/size/media_type persisted; missing-key error; idempotent orphan cleanup
- [x] 3.3 GREEN `app/modules/reporting/{pdf_renderer,storage}.py` + `pyproject.toml` (reportlab) + TTF asset + `docker compose build api`; gate: pdf+storage tests green

## Phase 4: Service & Lockstep (Slice 4)

- [x] 4.1 RED `tests/test_reporting_service.py`: staged T1 claim/pins (pending→processing) + idempotency lock; render/storage outside tx; T2 ready+artifact+`report.generated` (aggregate-only ids/version_no/transition/sha256/size/timestamps); audit/render/storage failure → failed, no artifact, `INTERNAL_ERROR`/`report_generation_failed`; same-key retry converges on same row
- [x] 4.2 RED same: idempotency `session:{id}` — replay same body → original DTO, no dup row/artifact/event; diff body → `idempotency_key_reused`; new key → 2nd historical report, 1st+artifact unchanged
- [x] 4.3 RED same: missing/unscored/ungenerated → identical `resource_not_found`, zero effects; in_progress → `session_not_completed`; never imports/invokes F4/F5 engines; evaluado → FORBIDDEN + `auth.denied`
- [x] 4.4 RED same: metadata latest = `created_at` DESC, id DESC; reads side-effect-free
- [x] 4.5 GREEN `app/modules/reporting/service.py`
- [x] 4.6 Lockstep (one unit): `view_reports` → `permissions.py` + contracts README §6 + `test_auth.py`; `report.generated` → `audit.py` EVENT_CATALOG + README §3 + `test_audit.py`; gate: service+auth+audit tests green

## Phase 5: API & Seed/Reset (Slice 5)

- [x] 5.1 RED `tests/test_reports_api.py`: POST `/api/v1/reports/{session_id}/generate` — 200 ready, DTO (id, session_id, template_id, template_version_no, status, format, generated_at, checksum/byte_size when ready); `extra="forbid"` → VALIDATION_ERROR; 404/409/403 no-leak; replay/key-reuse/new-key; GET metadata latest + 404 + no side effects; GET `/api/v1/reports/{id}/download` — 200 `application/pdf` stream, sha256 match, no URL/path; missing/not-ready identical 404; evaluado re-check 403 + `auth.denied`
- [x] 5.2 RED `tests/test_seed.py`: seed `informe-basico` (UUID5, published, v1, synthetic/source='seed'); `report_templates` in SEED_TABLES/manifest/checksum; `SEED_VERSION` bump; reports/score_runs stay 0; reseed idempotent; preflight covers `score_runs`/`reports` → `seed_reset_dependency_conflict` zero deletes; runtime report survives reset
- [x] 5.3 GREEN `app/schemas/reports.py` + `app/api/routes/reports.py` + `app/api/router.py`
- [x] 5.4 GREEN `app/seed/fixtures/report_template.json` + `app/seed/loader.py`; gate: API+seed tests green

## Phase 6: Verification (Slice 6)

- [x] 6.1 `docker compose build api`; slice `-k "report or template or pdf or seed or schema"` green; full suite ×2 direct Compose pytest (identical functional summaries); `git diff --check`; threat matrix all N/A — only the two documented inherited web failures remain
- [x] 6.2 `apply-progress.md` evidence consolidation and verify handoff; tasks reconciled for `sdd-verify`; archive remains deferred to `sdd-archive` and no docs commit is required

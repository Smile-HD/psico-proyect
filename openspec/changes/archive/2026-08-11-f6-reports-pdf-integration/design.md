# Design: F6 — Traceable Reports, PDF, and Authorized Download

## Technical Approach

Add an API-only reporting module that snapshots completed F4/F5 rows, composes a fixed professional document, renders it with ReportLab, stores the PDF in PostgreSQL, and exposes metadata/stream endpoints. F6 never imports or invokes either engine; it follows the existing repository-service-route layering and ratified no-leak, synthetic-only, idempotency, and append-only-audit contracts.

## Architecture Decisions

| ADR | Choice | Alternatives rejected | Rationale |
|---|---|---|---|
| ADR-01 seams | `modules/reporting/{domain,errors,repository,service,pdf_renderer,storage}.py`; domain has no SQLAlchemy/FastAPI/filesystem/clock/network/LLM, repository never commits, service owns transactions. | DB-aware composer; repository commits. | Preserves F4/F5 boundaries and makes ownership testable. |
| ADR-02 composition | Frozen `ReportInput -> ReportDocument`; fixed ordered sections for scores, overall, recommendations, `norm_note`, and the separate F5 disclaimer. | Recompute engines; executable templates. | Snapshots preserve history; templates remain data and cannot execute. |
| ADR-03 persistence | Schema-only `0006_reports_pdf` follows `0005_catalog_four_level`: `reports` adds nullable `score_run_id` FK, F5 `recommendation_snapshot` JSONB, `template_id`/`template_version_no` pin, status `{pending,processing,ready,failed}`, format `{pdf}`, `storage_key/sha256/byte_size/media_type/renderer_version/generated_at`, and `created_at/updated_at/failed_at`; runtime report rows carry `synthetic=False` and `source='runtime'` (UUID4 ids). `report_templates` gains `version_no`, status `{draft,published,retired}`, unique `(key,version_no)`, and a published-immutability trigger. | F1–F5 rewrites; unique session report. | Linear, non-destructive history; ready checks require artifact fields and no F1–F5 constraint is weakened. |
| ADR-04 staging | T1 validates all prerequisites, locks/claims `session:{id}` idempotency, pins snapshots, creates `pending -> processing`, then commits. Compose/render/storage run without row locks. T2 finalizes ready + aggregate audit + success replay. Failure takes `pending`/`processing -> failed`, cleans artifacts, and commits no-artifact failure. | One transaction around slow I/O. | `ready` always has an artifact; the key binds to the same row, so failed-key retries resume it; different body conflicts and new keys create history. |
| ADR-05 adapters | ReportLab + embedded redistributable DejaVu TTF; inject clock, UTC, Spanish locale, fixed layout, and minimal metadata. `report_artifacts(storage_key PK, report_id UNIQUE, payload BYTEA)` uses opaque UUID4 keys; storage persists sha256/size/media type and retains indefinitely. | WeasyPrint/system packages; filesystem/object storage; URLs. | Pure-Python Unicode rendering, authenticated streams, and idempotent orphan cleanup. Renderer/storage failures map to `INTERNAL_ERROR/report_generation_failed`. |
| ADR-06 API/security | Strict DTOs (`extra="forbid"`); `/api/v1/reports/{session_id}/generate`, `/api/v1/reports/{session_id}`, `/api/v1/reports/{id}/download`. Fixed seed default `informe-basico`, no client selection. Every route declares `require_roles(ADMIN, PSICOLOGO)` and `view_reports`; evaluado is denied before lookup and the denial is audited as `auth.denied` (no data exposure). Missing/unscored/ungenerated and missing/not-ready are identical `NOT_FOUND/resource_not_found` with zero effects; in-progress is `CONFLICT/session_not_completed`. | Hidden GET effects; signed/bare URLs; professional ownership filtering. | Matches professional-any-session access, reauthorizes downloads, and prevents leaks. `report.generated` metadata is aggregate-only (ids/version/status/hash/size/timestamps); update permissions, contracts README, `test_auth.py`, and `test_audit.py` together. |
| ADR-07 seed/reset | Seed `informe-basico` UUID5/published v1 with `synthetic=true/source=seed`; include it in `SEED_TABLES`, manifest/checksum, and bumped `SEED_VERSION`. Preflight checks runtime `score_runs`/`reports` and raises `seed_reset_dependency_conflict`; runtime rows/artifacts are never deleted. | Seed reports/runs; reset cleanup of runtime artifacts. | Reset fails atomically before FK damage and template recreation is idempotent. |

## Data Flow

```text
HTTP -> auth/DTO -> T1 claim/snapshot -> composer -> ReportLab -> BYTEA storage
       <- T2 ready + aggregate report.generated audit + idempotency commit
GET metadata -> latest(created_at DESC, id DESC) -> DTO
GET download -> reauthorize -> authenticated stream (never URL/path)
```

## File Changes

| File | Action | Description |
|---|---|---|
| `services/api/app/modules/reporting/` | Create | Six seams: pure domain, repository, service, renderer, storage, errors. |
| `services/api/app/models/reporting.py`, `services/api/alembic/versions/0006_reports_pdf.py` | Modify/Create | Exact pins/checks/timestamps, artifact BYTEA table, template trigger. |
| `services/api/app/schemas/reports.py`, `services/api/app/api/routes/reports.py`, `services/api/app/api/router.py` | Create/Modify | Strict DTOs and three thin routes. |
| `services/api/app/core/{permissions,audit}.py`, `services/api/app/seed/loader.py`, `packages/contracts/README.md` | Modify | Capability/event lockstep and seed/reset. |
| `services/api/pyproject.toml`, seed template fixture, embedded TTF | Modify/Create | ReportLab and deterministic inputs. |
| Reporting tests plus `test_schema.py`, `test_seed.py`, `test_auth.py`, `test_audit.py` | Create/Modify | RED/GREEN, migration, seed, auth, and audit contracts. |

## Interfaces / Contracts

`ReportInput` contains pinned run raw data, F4 `norm_note`, F5 snapshot, and template id/version/body; `ReportDocument` contains immutable ordered allowed sections. `ReportRenderer.render()` returns bytes/media type/version/controlled metadata. `ReportStorage.put/open/delete()` accepts opaque keys and bytes. No public contract exposes paths, response/options/items, secrets, or PII beyond session id.

## Testing Strategy

Strict TDD order: pure domain/no-leak/determinism → template/parser allow-list/no-eval → repository+real PostgreSQL/migration/state/concurrency → service staging/idempotency/failure/orphan cleanup → API TestClient/roles/envelopes/no-effects → normalized PDF structure/text/metadata (not bytes) → storage stream/checksum. Schema tests lock models/migration, fresh 0005→0006, repeat upgrade, and one linear head. Use UUID4 runtime fixtures and delta counts; F4/F5 claim all 30 seeded profiles. Run regressions and the full suite twice. `scripts/test.ps1` hides pytest exit status; use direct Compose pytest and `docker compose build api` before evidence. Web/E2E are out.

## Threat Matrix

Routing changes, but no shell, subprocess, executable-file classification, VCS, or PR automation exists:

| Boundary | Applicability | Design response / RED test |
|---|---|---|
| Documentation-like paths | N/A — no executable docs | None |
| Git repository selection | N/A — no Git integration | None |
| Commit state | N/A — no commit automation | None |
| Push state | N/A — no push automation | None |
| PR commands | N/A — no PR automation | None |

## Migration / Rollout

No feature flag or destructive downgrade. Deploy migration/module/lockstep contracts together; rollback disables routes/adapters and uses a forward fix while retaining reports, artifacts, source snapshots, and audit history.

## Open Questions

None; all design decisions are ratified by the supplied proposal and delta specs.

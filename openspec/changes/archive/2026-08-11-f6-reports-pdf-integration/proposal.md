# Proposal: F6 — Traceable Reports, PDF, and Authorized Download

## Intent

F6 (Ivan) produces deterministic, traceable professional PDFs from persisted F4/F5 outputs, without recomputation. It preserves synthetic-only, no-leak, idempotency, audit, and immutable-instrument rules.

## Scope

### In Scope
- Manual idempotent `POST /api/v1/reports/{session_id}/generate`; metadata and authenticated stream download.
- Professional-only `admin`/`psicólogo`, any session; evaluado excluded. Missing/unscored/ungenerated: `NOT_FOUND/resource_not_found`; in-progress: `CONFLICT/session_not_completed`; zero effects.
- Immutable template versions/snapshots; seeded default `informe-basico`.
- Linear `0006_*` after `0005_catalog_four_level`, PostgreSQL artifact, ReportLab, reset/seed, and strict-TDD tests.

### Out of Scope
- No F2–F5 changes or published-instrument edits; no LLM/real data, web, integration/outbox/vendor, or inherited web fixes.

## Capabilities

### New Capabilities
- `reports-api`: report composition, generation, reading, and download.

### Modified Capabilities
- `data-schema`: pins, templates, states, artifacts, `0006_*`.
- `contracts`: access, idempotency, errors, no-leak.
- `audit-consent`: aggregate `report.generated` event.
- `synthetic-seed`: reset/preflight and seed ownership.

## Approach and Decisions

- **D1/D4:** Professional PDF: F4 raw/z/T/eneatype/percentiles; F5 fit/justification. Separate `norm_note` and disclaimer sections. Exclude option ids/values, responses, 1–5 mapping, item content, secrets, and PII unless ratified.
- **D2:** `Idempotency-Key` scope `session:{id}`; replay same body, conflict different body, new key = historical pinned report. No hidden F4/F5 calls; all-or-nothing.
- **D3:** Immutable `draft/published/retired` versions plus snapshots; templates are data. Seed default UUID5, `synthetic/source='seed'`, in `SEED_TABLES`/preflight/manifest/reset.
- **D5/D6:** ReportLab (BSD), embedded Unicode TTF, no Pango/Cairo image packages; normalize PDF structure/text/metadata, not bytes. PostgreSQL bytea artifacts use opaque key, SHA-256, size, media type, renderer version/timestamps; indefinite MVP retention; reauthorize streamed downloads, never bare URLs.
- **Schema/reset:** Add `score_run_id` FK; F5 JSONB source snapshot avoids F5 schema change but loses FK integrity. Ratify `pending/processing/ready/failed` before CHECKs. Preflight `score_runs`/`reports` (add to seed tables only for owned rows); never delete runtime reports; reset seed templates without touching runtime rows.
- **D7/D8:** Defer integration/web; no target, no outbox/worker. `view_reports`/`report.generated` update `permissions.py`, `audit.py::EVENT_CATALOG`, `packages/contracts/README.md`, spec deltas, `test_auth.py`, and `test_audit.py` together; audit stays aggregate-only.

## Affected Areas

`services/api/app/modules/reporting`, reporting models, `alembic/versions/0006_*`, seed, permissions/audit, contracts, specs/tests; no web.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Leakage/PDF drift | High | Pure composer, scans, pinned fonts |
| Reset/migration break | Med | Preflight, fresh/linear tests |

## Rollback Plan

Disable routes/adapter; forward-fix migration. Preserve runtime/artifact/F4/F5/audit data; no destructive downgrade.

## Dependencies

F4/F5 outputs, PostgreSQL, ReportLab, redistributable Unicode font.

## Success Criteria

- [ ] Specs ratify audience, state, pins, content, retention, errors, and lockstep.
- [ ] Tests prove determinism, no-leak, authorization, replay, and zero-effect failures.
- [ ] Migration/reset preserve runtime rows; no new API failures.

## Proposal question round

- Confirm PII/retention, admin authoring, and download-audit; baseline: none/indefinite/seed-only/no extra event.
- Confirm new key creates history, not latest replacement; baseline: historical.

# Tasks: F3 — Evaluation Session (Jhamil)

## Review Workload Forecast

Estimated lines: ~3,000–3,400 (PR1–4: ~900/800/600/900)

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

`auto-chain`: proceed per slice mapping (slices ≤ 800 lines).

### Suggested Work Units

| Unit | Goal | PR | Focused test | Harness | Rollback |
|---|---|---|---|---|---|
| 1 | core + tests | PR 1 | `scripts/test.ps1 -k session` | N/A (no HTTP) | Revert module+tests |
| 2 | routes/schemas + tests | PR 2 | `scripts/test.ps1 -k session_api` | Compose + TestClient | Revert routes |
| 3 | listing + consent | PR 3 | `scripts/test.ps1 -k "published_versions or consent"` | N/A (endpoint tests) | Revert both |
| 4 | web UI + contracts | PR 4 | `npm run build` (apps/web) | Compose + browser `/evaluacion` | Revert web |

## PR 1 · Slice 1: session_runtime core

- [x] **T1.1** — `session_runtime/domain.py`: `transition()` (`in_progress→completed` only), `required_missing()`, `validate_batch()` (foreign-item reject), option-id→1–5 mapping. RED `test_session_domain.py`. [F3]
- [x] **T1.2** — `session_runtime/errors.py`: factories for `resource_not_found`, `consent_required`, `idempotency_key_reused`, `validation_error`, `forbidden`, state-`CONFLICT`. [F3]
- [ ] **T1.3** — `session_runtime/repository.py`: `FOR UPDATE` locks; pinned re-projection (archived OK, values hidden); upsert on `UNIQUE(session_id,item_id)`. RED `test_session_repository.py`. Done: one row on re-save. [F3]
- [ ] **T1.4** — `session_runtime/service.py`: create (gate→consent, actor key), own list, detail (owner/admin), batch save (`session:{id}` key, no audit), complete (required check, `response_count` audit, admin override). RED `test_session_service.py`. Done: retries dedupe. [F3]

## PR 2 · Slice 2: session API wiring

- [ ] **T2.1** — `schemas/sessions.py`: StartRequest, batch DTO (option ids only), summary/detail — numeric-free. [F3]
- [ ] **T2.2** — Rewrite `api/routes/sessions.py`: adapters; `Idempotency-Key` on all mutations; four invalid ids → identical `NOT_FOUND`; own-session 403 (admin exempt); wire router. [F3]
- [ ] **T2.3** — `tests/test_session_api.py` (TestClient+PostgreSQL): handoff no-leak, gate-before-consent, own scope, foreign 403, upsert 1–5 mapping, foreign-item reject, required blocked, aggregate-only audit, no scoring, archival survival, replay/conflict. [F3]

## PR 3 · Slice 3: listing + consent retrofit (F2/F1 touchpoints)

- [ ] **T3.1** — `GET /api/v1/catalog/published-versions` via `CatalogService`/repository/schemas + `routes/catalog.py`: labels only, all roles, no draft/archived. RED `test_catalog_listing.py`. [F3]
- [ ] **T3.2** — Retrofit `core/consent.py` + `routes/consent.py`: idempotent grant/revoke — replay, no dup registry/audit, diff body → `idempotency_key_reused`. RED `test_consent_idempotency.py`. [F3]

## PR 4 · Slice 4: web UI

- [ ] **T4.1** — `apps/web/lib/session-api.ts`: client on `apiFetch` (list/create/detail/save/complete), per-intent keys, `consent_required` mapping, no numeric-value types. [F3]
- [ ] **T4.2** — `apps/web/app/evaluacion/page.tsx` + css: labels; start → create → redirect `sesiones/[id]`; consent state explained; neutral state on `NOT_FOUND`. [F3]
- [ ] **T4.3** — `apps/web/app/evaluacion/sesiones/[id]/page.tsx` + css: resume pre-fill; LikertMatrix (aria-labels, focus); single-flight debounced autosave, `role="status"` feedback, retry keeps input; required markers; completion, no scores; reduced motion. [F3]
- [ ] **T4.4** — `components/ui/NavBar.tsx`: "Evaluación" entry for auth users with `run_sessions` (incl. evaluado), active-route, hidden anonymous. [F3]
- [ ] **T4.5** — Update `packages/contracts/README.md`: session surface, gate, idempotency, listing, no-scoring. [F3]

## Cross-cutting gates

- [ ] **T5.1** — Idempotency-Key sweep: create/responses/complete/grant/revoke pinned: replay/conflict. [F3]
- [ ] **T5.2** — Full suite twice + `npm run build` green pre-archive. <!-- sdd-owner: parent -->

# Tasks — F2 Instrument Catalog (owner: Trevor)

Implementation plan derived from `proposal.md`, the 10 specs under `specs/`, and `design.md`. Every task is one-session-sized, references concrete paths, and carries a done-definition. Tests follow the F1 conventions (config reports `strict_tdd: false`, no runner detected yet); each feature is followed by its own tests. Tasks are tagged with the owning phase `[F2]`.

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | ~4,800–6,400 (additions + deletions) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (DB: migration/models/seed) → PR 2 (API + tests) → PR 3 (Web UI) → PR 4 (contracts + spec promotion) |
| Delivery strategy | ask-on-risk (default; not previously set in session) |
| Chain strategy | **RESOLVED: stacked-to-main** (user decision 2026-08-08) — 4 sequential PRs against main; apply one slice at a time |

```text
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High
```

Per-PR estimate: PR 1 ≈ 1,100–1,500 lines; PR 2 ≈ 2,400–3,100 lines; PR 3 ≈ 900–1,300 lines; PR 4 ≈ 300–500 lines. Each PR is an autonomous work unit with its own start (green CI/build) and finish (review + merge) boundary; see the forecast note at the end of this file.

---

## F2.1 — Database: migration, models, seed backfill (PR 1)

### F2.1.1 Extend the instruments model family

- [x] **F2.1.1** — In `services/api/app/models/instruments.py`, extend `InstrumentVersion` with `response_type` (VARCHAR(32), NOT NULL, `likert_1_5`), `adaptation_metadata` (JSONB nullable), `created_at`, `updated_at`, `archived_at` (TIMESTAMPTZ); extend `InstrumentItem` with `scale_id` (FK to `scales.id`), `item_order`, `locale`, `required` (default true). Add `Scale` and `ResponseOption` models per design §3.1 (orders, unique/value constraints as table args). Export all four entities through `services/api/app/models/__init__.py`. Done when: models import cleanly, constraints (UNIQUE(version_id, display_order), UNIQUE(scale_id, item_order), UNIQUE(item_id, value), CHECK value/order 1–5) are declared in table args, and `responses.item_id` still references `instrument_items.id`. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.1.2** — Add `IdempotencyRecord` in `services/api/app/models/idempotency.py` per design §3.2 (`actor_user_id` FK→`users.id`, `operation`, `resource_scope`, `idempotency_key`, `request_hash` CHAR(64), `response_status` SMALLINT, `response_body` JSONB, `created_at`; UNIQUE `(actor_user_id, operation, resource_scope, idempotency_key)`). Register it in `services/api/app/models/__init__.py`. Done when: the model autogenerates the intended DDL and is importable from `app.models`. [F2] <!-- sdd-owner: implementation -->

### F2.1.2 Migration 0005 — catalog four-level

- [x] **F2.1.3** — Create `services/api/alembic/versions/0005_catalog_four_level.py` (down_revision `0004_audit_append_only_trigger`, single transactional migration). Part A: preflight — abort if any `instrument_versions.status` is not `draft`/`published`/`archived`; create `scales`, `response_options`, `idempotency_records` with indexes/constraints from the models. Done when: `alembic upgrade head` on an empty DB creates the three tables with their constraints and the chain stays linear (one new revision, no merge). [F2] <!-- sdd-owner: implementation -->

- [x] **F2.1.4** — Migration part B: add version columns (`response_type`, `adaptation_metadata`, `created_at`, `updated_at`, `archived_at`), backfill `response_type=likert_1_5` and derived timestamps; replace the old immutability check with `ck_published_versions_immutable` (`(status='draft' AND is_immutable=false) OR (status IN ('published','archived') AND is_immutable=true)`) plus `CHECK status IN (...)`; add transitional nullable `scale_id`, `item_order`, `locale`, `required` to `instrument_items`. Done when: upgrade on an F1-seeded DB keeps all existing IDs and `published_at` values and the new checks are active. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.1.5** — Migration part C (backfill): one scale per distinct `(version_id, old scale)` group — `TP-S-01:v1` scales in seed fixture order (Intereses 1, Aptitud verbal 2, Aptitud numérica 3, Razonamiento abstracto 4, Valores/preferencias 5) with deterministic UUID5 ids (`psico-seed:` namespace); copy `scale_order`→`item_order`, set `scale_id`, `locale=es`, `required=true`; create five options per existing item with deterministic seed ids (`TP-S-01:i1:option:1` …) and neutral Spanish labels `Nunca/Casi nunca/A veces/Casi siempre/Siempre`, values/orders 1–5; non-seed legacy groups get stable UUID4 ids and first-seen order. Done when: `TP-S-01:v1` has 5 scales, 20 items, 100 options; runtime legacy rows (if any) are backfilled with UUID4; no row attaches to another version. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.1.6** — Migration part D: validate complete four-level graph and that all old FKs (`responses.item_id`, `sessions.instrument_version_id`, `reference_sets.instrument_version_id`) still resolve; only then set `scale_id`/`item_order`/`locale`/`required` NOT NULL, drop `scale`/`scale_order` and old constraints, add `UNIQUE(scale_id, item_order)`, composite FK `(scale_id, version_id) → scales(id, version_id)`. Done when: upgrade succeeds on seeded F1 snapshot, old references resolve, and cross-version item attachment is rejected at the DB level. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.1.7** — Migration part E (guards): install DB triggers/functions rejecting UPDATE/DELETE on published/archived hierarchy rows and version edits (only the service-controlled published→archived transition allowed); support a transaction-local `seed_reset` marker path. Done when: direct edits to a published version/children fail at the DB level while the seed-reset path and lifecycle transition still work. [F2] <!-- sdd-owner: implementation -->

### F2.1.3 Migration verification

- [x] **F2.1.8** — Integration test for the migration: upgrade from an F1 snapshot; assert preserved seed/version/item ids, 5/20/100 counts, `responses`/`sessions`/`reference_sets` FK resolution, status/immutability CHECK behavior, option value range 1–5, idempotent `alembic upgrade head`, and one linear revision. Done when: the migration test passes against a fresh and a pre-seeded database. [F2] <!-- sdd-owner: implementation -->

### F2.1.4 Seed loader and reset preflight

- [x] **F2.1.9** — Extend `services/api/app/seed/loader.py` and fixtures: seed the deterministic `TP-S-01` graph through the new hierarchy (scales + response_options, UUID5 ids, orders/labels matching the backfill), include the new tables in seed ownership and reset order, keep `seed.executed` audit. Done when: `python -m app.seed` reproduces the same graph as the migration backfill (byte-identical ids/orders). [F2] <!-- sdd-owner: implementation -->

- [x] **F2.1.10** — Implement the atomic reset preflight in the seed CLI (`python -m app.seed --reset`): advisory/transaction lock, non-seed FK dependency scan into seed-owned catalog rows, stable `CONFLICT` + full rollback before any delete on cross-ownership, else delete only `source='seed'` rows in reverse FK order and re-seed. Done when: reset with independent runtime rows recreates the seed graph untouched, and an injected non-seed reference aborts atomically with `seed_reset_dependency_conflict`. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.1.11** — Integration tests for seed: scoped reset, reset coexists with runtime catalog content, cross-ownership aborts atomically (per `specs/synthetic-seed/spec.md`). Done when: all three scenarios pass. [F2] <!-- sdd-owner: implementation -->

---

## F2.2 — Domain core (PR 2)

- [x] **F2.2.1** — Implement `services/api/app/modules/assessment_authoring/domain.py`: status constants (`draft`/`published`/`archived`), hierarchy/aggregate validation (≥1 scale, ≥1 item per scale, exactly 5 options per item, one option per value 1–5), positive contiguous orders, `likert_1_5`/`locale=es` rules, parent-membership checks, and clone semantics. No SQLAlchemy session or side effects. Done when: pure functions cover every design §4.2/§5 validation rule and are callable without a DB. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.2.2** — Unit tests for `domain.py`: non-contiguous order rejected, duplicate option value rejected, incomplete option set rejected, unsupported response type rejected, empty scale blocked, scale cross-version attachment invalid, seed-vs-runtime identity rules. Done when: tests pass and match `specs/catalog-model/spec.md` scenarios. [F2] <!-- sdd-owner: implementation -->

---

## F2.3 — API layer: idempotency, schemas, repository, service (PR 2)

- [x] **F2.3.1** — Implement `services/api/app/modules/assessment_authoring/errors.py`: map catalog failures to the F1 `ApiError` envelope codes with stable messages (`invalid_catalog_version`, `version_not_draft`, `version_immutable`, `archive_requires_published`, `seed_catalog_read_only`, `idempotency_key_reused`, `seed_reset_dependency_conflict`) and safe details (field paths, ids, expected state, counts only). Done when: every design §4.4 mapping has a named error factory. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.3.2** — Implement `services/api/app/modules/assessment_authoring/idempotency.py`: canonical request hashing (SHA-256), scoped record lookup/locking per `(actor, operation, resource_scope, key)`, completed-result replay (returns stored status/body, skips mutation+audit), same-key/different-body `CONFLICT`, record only successful mutations with summary bodies. Done when: unit-testable behavior for replay, conflict, and miss paths matches design §8.3. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.3.3** — Unit tests for `idempotency.py`: same-hash replay, different-hash conflict, distinct keys independent, no record stored for failed mutations. Done when: tests pass. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.3.4** — Implement request DTOs in `services/api/app/schemas/catalog.py` (Pydantic v2): `CreateInstrumentRequest` (key 2–64 uppercase/`_`/`-`/`.`; title; description; adaptation), `CreateDraftVersionRequest` (`source_version_id` nullable), `SaveDraftContentRequest` (`response_type: Literal["likert_1_5"]`, `adaptation`, `scales: list[ScaleInput]`, `ItemInput` with exactly five `OptionInput`), `OptionInput` without `value` (derived from order), `AdaptationMetadata` (bounded strings, locales `es`, no dynamic fields). Done when: schema validation rejects malformed bodies with `VALIDATION_ERROR`-compatible details and no numeric option value is accepted in input. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.3.5** — Implement response DTOs in `services/api/app/schemas/catalog.py`: `VersionSummary`, `CreateInstrumentResponse`, `MutationResult` (with `counts`), `AdminVersionDetail` (no option values), `PublishedVersionRead` (ordered scales/items/options with labels, `required`, locale; no `value`, no answer keys). Done when: DTOs serialize per design §4.3 and `PublishedVersionRead` provably omits internal fields. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.3.6** — Implement `services/api/app/modules/assessment_authoring/repository.py`: SQLAlchemy queries/persistence for instruments, versions, scales, items, options; row locks (`SELECT ... FOR UPDATE`) on instrument/version; seed-root detection (`source='seed'` + UUID5 identity); no HTTP concerns. Done when: repository methods cover create/upsert/delete-within-version/list/read and lock semantics used by the service. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.3.7** — Implement `service.py` create paths: create runtime instrument + initial draft v1 (`synthetic=true`, `source=runtime`, UUID4 ids, `response_type=likert_1_5`) in one transaction with `instrument.draft_created` audit + idempotency record; reject seed keys/seed parents (`CONFLICT`). Done when: creation returns `CreateInstrumentResponse`, audit and idempotency rows commit together, and seed authoring is rejected. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.3.8** — Implement `service.py` draft-version creation: lock parent instrument row, `max(version_no)+1` allocation, optional clone from a runtime published version (fresh UUID4 child rows, source untouched), reject non-published/seed/foreign sources; unique-constraint backstop maps to stable `CONFLICT`. Done when: concurrent allocations produce consecutive `version_no`s and a clone never references seed rows. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.3.9** — Implement `service.py` aggregate save: lock version, require `status=draft` and `is_immutable=false`, validate full request (domain rules + ID membership/parent stability), upsert supplied ids, insert new UUID4 rows, delete only omitted draft children; emit `instrument.draft_updated` only after successful persistence; failed save leaves prior draft content unchanged. Done when: atomic save semantics and validation-failure rollback pass integration checks. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.3.10** — Implement `service.py` publish and archive: publish locks aggregate, revalidates (response type, locale, graph, contiguous order, five options, markers, DB constraints), sets `published/published_at/is_immutable=true`, emits `instrument.published`, stores idempotency result, atomic commit; archive requires `published` else `CONFLICT`, sets `archived/archived_at`, keeps immutable, emits `instrument.archived`. Done when: design §5 publish/archive flows and the §8.2 failure flow (rollback, no event) hold. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.3.11** — Implement `services/api/app/modules/assessment_authoring/projections.py`: published evaluator payload (hierarchy, labels, ids, `required`, locale — no numeric values) and the non-public F4 fixture projection (option ids + values 1–5). Evaluator projection must never call the fixture projection. Done when: both projections serialize correctly and the published payload contains no `value` field. [F2] <!-- sdd-owner: implementation -->

---

## F2.4 — API wiring: permissions, audit, routes (PR 2)

- [x] **F2.4.1** — Extend `services/api/app/core/permissions.py`: add `manage_instruments` (admin, psicólogo), retain `publish_instruments` (admin only), keep `read_catalog` for the three roles with the published-only contract; unknown capabilities stay deny-by-default. Done when: the capability constants exist and the F1 matrix test passes with the new entries. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.4.2** — Extend `services/api/app/core/audit.py`: add `instrument.draft_created`, `instrument.draft_updated`, `instrument.published`, `instrument.archived` to `EVENT_CATALOG`; add aggregate-only metadata validation (ids, `version_no`, transition, counts) enforced by the existing deny-list (`assert_deny_list`). Done when: catalog events record and metadata with item text/option values is rejected. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.4.3** — Lockstep contracts update: extend `packages/contracts/README.md` event catalog and the event-catalog contract test with the four catalog events. Done when: `EVENT_CATALOG`, README, and the contract test agree (per `specs/audit-consent/spec.md` lockstep scenario). [F2] <!-- sdd-owner: implementation -->

- [x] **F2.4.4** — Implement routes in `services/api/app/api/routes/catalog.py` — published read: `GET /api/v1/catalog/published-versions/{version_id}` with `require_roles(ADMIN, PSICOLOGO, EVALUADO)`; draft/archived/missing ids all return the same `NOT_FOUND` envelope (no status/existence leak). Done when: route returns 200 only for published versions and identical `NOT_FOUND` otherwise. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.4.5** — Implement administration routes in `services/api/app/api/routes/catalog.py`: `GET /catalog/admin/instruments` (paginated, `page`/`page_size`/`key`/`status` filters, summaries only), `GET /catalog/admin/instruments/{instrument_id}` (seed marked read-only), `POST /catalog/admin/instruments`, `POST /catalog/admin/instruments/{instrument_id}/versions`, `GET /catalog/admin/versions/{version_id}` — all with `require_roles(ADMIN, PSICOLOGO)` and `Idempotency-Key` on mutations. Done when: `evaluado` gets `FORBIDDEN` + `auth.denied` on every admin route and the matrix matches `specs/catalog-permissions/spec.md`. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.4.6** — Implement mutation routes: `PUT /catalog/admin/versions/{version_id}/content` (admin+psicólogo), `POST /catalog/admin/versions/{version_id}/publish` (admin only), `POST /catalog/admin/versions/{version_id}/archive` (admin+psicólogo) — all requiring `Idempotency-Key` and returning `MutationResult`. Done when: publish by psicólogo is `FORBIDDEN`, and all three follow the error mapping of design §4.4. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.4.7** — Wire the router: include the catalog router under `/api/v1` in `services/api/app/api/router.py`; confirm app boots with the new module. Done when: `GET /api/v1/catalog/...` routes are registered and startup tests pass. [F2] <!-- sdd-owner: implementation -->

---

## F2.5 — Integration and permission tests (PR 2)

- [x] **F2.5.1** — Lifecycle integration tests: create → save → publish → archive happy path; invalid draft publish fails with `VALIDATION_ERROR` and stays draft; in-place published edit returns `CONFLICT` and hierarchy is byte-identical; two published versions coexist and are independently readable; change to published spawns new draft `version_no=2`; archive of draft fails; no unarchive; version_no concurrency. Done when: all `specs/catalog-lifecycle/spec.md` and `catalog-api/spec.md` scenarios pass. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.5.2** — Idempotency integration tests: retried publish with same key replays and creates exactly one transition + one `instrument.published` audit row; distinct keys create independent instruments each audited once; same key + materially different body returns `CONFLICT` with no side effect; replay returns stored body and current request-id. Done when: `specs/contracts/spec.md` and `specs/catalog-api/spec.md` idempotency scenarios pass. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.5.3** — Permission tests per matrix: psicólogo manages drafts and archives (each audited), psicólogo cannot publish (`FORBIDDEN` + `auth.denied`), admin publishes, evaluado reads published only and gets `NOT_FOUND` (no leak) for draft/archived ids, evaluado blocked from admin routes, no default-allow on new routes. Done when: `specs/catalog-permissions/spec.md` and `specs/identity-auth/spec.md` scenarios pass. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.5.4** — Audit tests: draft creation audited; exactly two `draft_updated` rows for two explicit saves (keystrokes produce none); publish-then-archive order; metadata content-free (ids, `version_no`, transition, counts 2/10/50) and deny-list clean; replay does not duplicate audit; failed save not audited as updated. Done when: `specs/catalog-audit/spec.md` and `specs/audit-consent/spec.md` scenarios pass. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.5.5** — Published payload contract tests: evaluator payload contains ordered scales/items/five labeled options, stable ids, `required`, `locale=es`, Spanish content, no numeric values/answer keys/scoring rules; F4 fixture projection exposes the 1–5 mapping; rendering fixtures match `specs/catalog-model/spec.md` and `catalog-api/spec.md`. Done when: payload enumeration checks pass. [F2] <!-- sdd-owner: implementation -->

---

## F2.6 — Web UI (PR 3)

- [x] **F2.6.1** — Implement `apps/web/lib/catalog-api.ts`: typed client for all catalog endpoints, bearer propagation, `Idempotency-Key` generation with per-intent reuse on timeout retry and new key on content change, F1 error-envelope parsing (code/message/request_id/details), no option-value fields in published-read types. Done when: client calls all routes with correct headers and typed responses. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.6.2** — Implement `apps/web/components/catalog/` building blocks: status badge (Borrador/Publicada/Archivada), validation summary (maps `VALIDATION_ERROR.details` to scale/item/option paths), confirmation dialogs for publish/archive with Spanish copy (`Confirmar publicación`/`Confirmar archivo`), hierarchy sections (Escalas/Ítems/Opciones de respuesta), option-label editor with five 1–5 slots. Done when: components render the design §7 strings and enforce local validation (required fields, Spanish locale, contiguous positive orders, exactly five options, supported response type). [F2] <!-- sdd-owner: implementation -->

- [x] **F2.6.3** — Implement `apps/web/app/catalogo/page.tsx`: role-gated administration list (`admin`/`psicólogo` see it; `evaluado` sees no admin navigation) with filters Borradores/Publicados/Archivados and pagination. Done when: list renders server data and hides for `evaluado`. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.6.4** — Implement `apps/web/app/catalogo/nuevo/page.tsx`: create-instrument flow (key/title/description/adaptation) posting to `POST /catalog/admin/instruments` with an idempotency key, navigating to the new draft editor; seed key never offered as parent. Done when: creation succeeds end-to-end and error envelope renders request_id. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.6.5** — Implement `apps/web/app/catalogo/[instrumentId]/versiones/[versionId]/page.tsx` draft-editor branch: in-memory aggregate editing (Datos del instrumento, Escalas, Ítems, Opciones de respuesta), local validation while typing, complete-aggregate save via `PUT .../content` with per-intent key, conflict/network error display. Done when: save works for drafts and fails cleanly on invalid aggregates with the previous state kept. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.6.6** — Implement the read-only branch of the same page for published/archived versions: immutable detail view, publish button only for `admin` (with confirmation explaining the freeze), archive for `admin`/`psicólogo` (with confirmation explaining historical references), seed rows showing `Este instrumento es de referencia y no se puede editar` and no edit/clone/publish/archive controls. Done when: UI gating matches design §7 and server remains the authority. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.6.7** — Implement `apps/web/app/catalogo/[instrumentId]/versiones/[versionId]/vista/page.tsx`: published-only evaluator rendering of the Spanish hierarchy and labels; never renders numeric option values; handles NOT_FOUND/archived with the stable message. Done when: the view renders any published version and no numeric values appear in the DOM. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.6.8** — Web verification pass per design §7/§10: manual/automated check of permission gating, local+server validation, confirmation behavior, idempotent retry in the client, and published read rendering. Done when: the verification checklist passes against the running compose stack. [F2] <!-- sdd-owner: implementation -->

---

## F2.7 — Contracts documentation, handoff, promotion (PR 4)

- [x] **F2.7.1** — Update `packages/contracts/README.md` with the F2 catalog contract: endpoint surface (published read + administration), DTO summaries, lifecycle (`draft → published → archived`, immutability), idempotency rules (replay, same-key-different-body `CONFLICT`, indefinite retention), error codes, and the F3 handoff contract (published-only session gate with stable error cases for draft/archived/missing/invalid versions; `instrument_version_id` copy-and-never-change semantics) plus the F4 fixture-projection note (1–5 mapping, non-public). Done when: README documents the full F2 surface and matches the implemented routes. [F2] <!-- sdd-owner: implementation -->

- [x] **F2.7.2** — Promote specs to `openspec/specs/` per the F1 archive convention: write full specifications (Purpose/Requirements/Scenarios) for the five new capabilities (`catalog-api`, `catalog-model`, `catalog-lifecycle`, `catalog-audit`, `catalog-permissions`) and merge the five deltas into the existing promoted specs (`audit-consent`, `contracts`, `data-schema`, `identity-auth`, `synthetic-seed`) with the F2 amendments. Done when: `openspec/specs/` mirrors the ratified F2 state and no delta content is lost. [F2] <!-- sdd-owner: implementation -->

---

## F2.8 — Lifecycle gates (parent-owned, after apply)

- [ ] Start or reuse bounded review of each chained PR (DB → API → Web → contracts) before merge. <!-- sdd-owner: parent -->
- [ ] Run `sdd-verify` against the specs, confirm the promoted `openspec/specs/` state, then archive the change. <!-- sdd-owner: parent -->

---

## Forecast note (work units)

- **PR 1 (F2.1):** ~6–8 commits: models → idempotency model → migration parts A–E → migration test → seed loader → reset preflight → seed tests. Rollback boundary: revert the unapplied migration or restore the verified F1 snapshot; never destructively downgrade once runtime rows exist.
- **PR 2 (F2.2–F2.5):** ~12–15 commits: domain + tests → idempotency + tests → schemas → repository → service (create/draft/save/publish/archive) → projections → permissions/audit + contracts lockstep → routes → router → integration/permission/audit/payload tests. Rollback boundary: application release rollback preserving immutable rows and audit.
- **PR 3 (F2.6):** ~6–8 commits: client → components → list → nuevo → editor → immutable view → vista → verification. Rollback boundary: revert UI release; server contract unchanged.
- **PR 4 (F2.7):** ~2–3 commits: README contract + handoff → spec promotion. Rollback boundary: doc-only revert.
- Cross-cutting rule: never edit a published version in place; any discovered mutation requires a successor version, not history rewrite.

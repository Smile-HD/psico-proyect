# Exploration: F3 — Sesión de evaluación (Evaluation Session)

**Change**: `f3-sesion-evaluacion`
**Owner**: Jhamil
**Phase**: 3 of 6 (F1 Marces → F2 Trevor → F3 Jhamil → F4 Juan Carlos → F5 Piere → F6 Ivan)
**Date**: 2026-08-09 (post-F2 archive, `master @ 94f0e4d` + config.yaml reconciliation)
**Status**: Fact-finding report — NOT a design. Open questions at the end feed the proposal round.

---

## Current State

### 1.1 What exists today for sessions (F1 baseline, untouched by F2)

`services/api/app/api/routes/sessions.py` — two minimal endpoints, registered under `/api/v1` (`app/api/router.py`):

| Endpoint | Behavior today | F3-relevant gaps |
| --- | --- | --- |
| `POST /api/v1/sessions` (201) | Parses `SessionStartRequest{instrument_version_id: str}`; `db.get(InstrumentVersion, id)`; **NO status check** — a session can start on a **draft** version today; `require_consent(db, user.id)` → `409 CONFLICT consent_required` + `session.blocked_without_consent` audited when no granted grant; creates `Session(status="in_progress")`, audits `session.started`, returns `{id, status}` | **Violates the F3 handoff contract**: draft/archived versions are session-startable (existence+status leak); no `Idempotency-Key` (mutating); no GET/read surface; no response recording; no state machine beyond implicit start |
| `POST /api/v1/sessions/{session_id}/complete` | Loads session; own-session rule (`session.user_id != user.id and ADMIN not in roles` → `403 FORBIDDEN`); counts `Response` rows; sets `status="completed"`, `completed_at`; audits `session.completed` with `metadata={"response_count": n}` (deny-list-safe) | No `Idempotency-Key`; no validation (can complete with zero/partial responses); no idempotent replay; `blocked`/`cancelled` statuses exist in the CHECK but are never transitioned |

`services/api/app/models/sessions.py`:
- `Session`: `user_id` FK, `instrument_version_id` FK → `instrument_versions.id` (verbatim copy-and-never-change is already physical), `consent_grant_id` FK nullable, `status` CHECK `IN ('in_progress','completed','blocked','cancelled')`, `started_at`, `completed_at`, `SyntheticMixin` (`synthetic`, `source`). Index `ix_sessions_user_started`.
- `Response`: `session_id` FK, `item_id` FK → `instrument_items.id`, `value` CHECK `BETWEEN 1 AND 5`, `UNIQUE(session_id, item_id)` (`uq_response_per_session_item`), `SyntheticMixin`. **The table shape for response recording already exists and is F4-ready.**

`services/api/app/schemas/auth.py` — `SessionStartRequest` is the only session DTO (no response DTOs, no session-read DTOs).

`services/api/app/core/consent.py` — `require_consent(db, user_id)` returns a `granted` `ConsentGrant` or raises `409 CONFLICT "consent_required"` + audits; `grant_consent` / `revoke_consent` transition registry state with audit. `api/routes/consent.py`: `GET /versions`, `POST /{id}/grant`, `POST /{id}/revoke` — **none of these carry `Idempotency-Key`** (inherited F1 debt; same invariant applies).

### 1.2 What F2 delivers that F3 consumes

- **Published-only read with stable errors** — `CatalogService.published_read(db, version_id)` (`modules/assessment_authoring/service.py`): `NOT_FOUND` for missing **or** non-published, no existence/status leak. This is exactly the gate semantics the F3 session-creation gate must mirror (draft/archived/missing/invalid → indistinguishable `NOT_FOUND`). Payload: `PublishedVersionRead` with `scales → items → response_options` (labels only; numeric values never exposed — `published_evaluator_projection` in `projections.py`; the numeric 1–5 mapping lives only in the non-public `fixture_projection` for F4).
- **Idempotency infrastructure, reusable** — `modules/assessment_authoring/idempotency.py`: `lookup_idempotency` (scoped by `actor_user_id + operation + resource_scope + idempotency_key`; same key+same canonical body → replay; same key+different body → `409 CONFLICT idempotency_key_reused`; ADR-002) and `store_idempotency`. `idempotency_records` table persists indefinitely (ADR-003). It is generic, but physically lives inside the catalog module — F3 must decide reuse vs extraction.
- **Pure domain validation pattern** — `modules/assessment_authoring/domain.py`: constants `DRAFT/PUBLISHED/ARCHIVED`, `validate_hierarchy`, `validate_transition`, `clone_hierarchy`; no SQLAlchemy/HTTP/audit. The template F3 should follow for a session state machine.
- **Audit events already catalogued** — `app/core/audit.py` `EVENT_CATALOG` includes `session.started`, `session.completed`, `session.blocked_without_consent` (plus `consent.*`); deny-list enforced (`assert_deny_list`); event-catalog contract test pins the list. **No new event types needed unless F3 adds response-save/resume events** — a spec decision.
- **Permissions already granted** — `app/core/permissions.py` `CAPABILITIES`: `run_sessions` and `view_results` = all three roles; `read_catalog` = all three (published-only contract). No permission changes required for the core F3 surface; role gate `require_roles(ADMIN, PSICOLOGO, EVALUADO)` is the F1 pattern already used by `sessions.py`.

### 1.3 Seed state relevant to F3 (`app/seed/loader.py` + `fixtures/`)

- Instrument `TP-S-01:v1`: 5 scales, 20 items, 100 options; `status=published`, `is_immutable=true`, UUID5 ids (`TP-S-01:i1..i20`).
- 30 profiles `evaluado_01..30`: each has a `granted` consent (`grant:{key}`), **one `completed` session** (`session:{key}`, started+completed 2026-01-15), and **20 responses** (1–5, from `profiles/*.json` `responses` arrays). This is the F4 dataset; F3 must not break the seed chain (`SEED_TABLES` includes `sessions`/`responses`; `--reset` preflight guards runtime rows FK-referencing seed).
- Dev `evaluado` account: **no consent seeded** → session creation returns `409 consent_required` (documented expected behavior, pinned by `test_consent.py`).
- **No `in_progress` sessions exist anywhere in the seed** — resume/autosave has no seeded fixture data to test against (tests will create runtime rows).

### 1.4 Web state

- `apps/web/lib/api.ts` — `apiFetch<T>(path, {method, token, idempotencyKey, body})` already supports `Idempotency-Key` headers and unwraps the error envelope into `ApiError`. **Ready for F3 mutations with zero changes.**
- `apps/web/lib/auth.ts` — localStorage token + role claims for UI gating; `useSessionUser`, `hasRole`, `login`, `clearSession`.
- `apps/web/components/ui/LikertMatrix.tsx` — presentational, already has `interactive`, `valueByItem`, `onChange` props (radio inputs, `aria-label` per cell). F2 uses `interactive={false}` (vista page). Design system §3 explicitly anticipates F3 opting into controlled radios. `LikertItem`/`LikertOption` types map 1:1 to the published payload.
- UI kit: `Button`, `Field`, `Feedback` (`ErrorState`/`Notice`), `Skeleton`, `StatusLabel`, `Table`, `Dialog`, `EmptyState`, `Pagination`, `Breadcrumb`, `NavBar` — all presentational, token-driven (`app/globals.css` is the only token source; `apps/web/docs/design-system.md` freezes tokens, component contracts, accessibility rules and the owner manual checklist, which already includes an "Evaluator" section).
- Pages today: `/`, `/login`, `/catalogo`, `/catalogo/nuevo`, `/catalogo/[instrumentId]/versiones/[versionId]`, `.../vista`. **No session pages exist.** `NavBar` renders catalog links only for `admin`/`psicólogo` (`canManage`); there is no evaluado session entry point.

### 1.5 Tests

- Suite: pytest under `services/api/tests` (TestClient + real PostgreSQL via compose; `conftest.py` drops/recreates `psico` per run; fixtures `engine` / `db_session` / `seeded_db_session`). Handoff reports 113 tests (~103 `def test_` found in files).
- Session-related coverage today: `test_consent.py` (blocked-without-consent 409 + audit; grant → session starts 201 + `session.started`; revoke lifecycle); `test_audit.py` (event catalog pinned to contracts); `test_seed.py` (30 sessions / 600 responses counts, idempotent re-seed, manifest); `test_catalog_api.py` (published read 200 / non-published `NOT_FOUND` no-leak).
- **No tests exist for**: response recording, session read/resume, state transitions, idempotency on session endpoints, draft-version session rejection.

---

## Affected Areas

- `services/api/app/api/routes/sessions.py` — refactor to thin adapter over a new F3 service; add the published-version gate, idempotency, and new endpoints (read/responses).
- `services/api/app/schemas/auth.py` (or a new `schemas/sessions.py`) — `SessionStartRequest` today; needs response/session DTOs.
- `services/api/app/modules/assessment_authoring/idempotency.py` — reuse or extract (F3 decision; extraction would touch F2 code).
- `services/api/app/modules/assessment_authoring/service.py` `published_read` — the gate semantics F3 mirrors (no change expected).
- `services/api/app/models/sessions.py` — existing `Session`/`Response`; migration needed only if F3 adds columns (e.g. resume marker) — proposal decision.
- `services/api/app/seed/loader.py` — unchanged unless F3 seeds `in_progress` sessions (not required).
- `services/api/tests/` — new `test_session_*.py` following `test_consent.py`/`test_catalog_api.py` patterns.
- `apps/web/app/` — new session routes (`/evaluacion`-family pages), `NavBar` evaluado links, session client lib (reuse `apiFetch`), `LikertMatrix` interactive mode.
- `openspec/specs/` — F3 deltas land in `contracts`/`audit-consent`/`catalog-api` (only if new events or a published-listing endpoint are added); a new `sessions` spec is the expected delta target.
- `packages/contracts/README.md` — §7.6 (or similar) documenting the F3 endpoint surface if new endpoints are ratified.

---

## Approaches

1. **New `modules/session_runtime/` module following the F2 pattern** — `domain.py` (pure state machine), `service.py` (transaction orchestration: gate → consent → create; response upsert; complete), `repository.py` (queries/locks), `errors.py`; `sessions.py` route becomes a thin adapter; reuse `assessment_authoring.idempotency` as-is.
   - Pros: architecture-consistent with F2; pure-domain unit tests (RED→GREEN TDD per `strict_tdd`); keeps the route file small; idempotency and audit compose per operation.
   - Cons: largest surface; naming/location of the module and of idempotency (cross-module import) must be settled in the proposal.
   - Effort: High.

2. **Extend `sessions.py` in place** — add the published gate, `Idempotency-Key` handling, and response endpoints directly in the route file, reusing `require_consent` and idempotency helpers.
   - Pros: fastest; no new package.
   - Cons: route becomes fat; no domain-layer tests; drifts from the F2 module convention; hardest to verify state-machine rules.
   - Effort: Low–Medium.

3. **Hybrid** — keep route adapters thin but add only a small `domain.py` (pure state machine + response validation) next to `sessions.py`, skipping a full repository.
   - Pros: balances effort and testability; state rules get unit tests.
   - Cons: transaction logic still lives in the route; less consistent with F2 layering.
   - Effort: Medium.

---

## Recommendation

**Approach 1** — new `services/api/app/modules/session_runtime/` mirroring `assessment_authoring` (domain/service/repository/errors), with `sessions.py` reduced to thin adapters and idempotency reused from `assessment_authoring.idempotency` (or extracted to `app/core/idempotency.py` with a re-export, keeping F2 imports intact — proposal decision). The existing `Session`/`Response` tables, consent gate, audit events, and `apiFetch`+`Idempotency-Key` support mean F3 is mostly **additive**: gate + idempotency + read/resume + response recording + completion hardening + web session pages. Expected to need **no new audit events** unless response-save/resume events are ratified.

---

## Risks

- **Draft-version sessions exist as a live bug today** — `POST /sessions` accepts any version row; the F3 gate must make draft/archived/missing/invalid indistinguishable (`NOT_FOUND`, no status/existence leak) per the ratified handoff contract scenario. Verify against the contract, not against current behavior.
- **No published-catalog listing endpoint exists** — evaluado can only read a published version by id; there is no way to *discover* what to start a session on. Proposal must decide: new listing endpoint (contract change) vs. entry points from the admin-side pages vs. out-of-scope (session start only by direct id).
- **Consent grant/revoke lack `Idempotency-Key`** (F1 debt) while the invariant demands it on every mutating endpoint — proposal must decide if F3 fixes it or carries it.
- **State-machine semantics undefined** — `blocked`/`cancelled` statuses exist in the CHECK but no transition ever sets them; handoff sketch says `created → in_progress → completed`; completion currently allows partial/zero responses (required-flag enforcement is a proposal decision); resume semantics for `in_progress` are unspecified.
- **Idempotency module location** — reusing `assessment_authoring.idempotency` from a session module couples F3 to F2's package; extraction touches F2-delivered code (mitigated by existing idempotency tests).
- **No seed `in_progress` sessions** — resume/autosave tests must create runtime rows; seed stays untouched (30 completed sessions + 600 responses are F4's dataset; `--reset` preflight must keep passing).
- **Web scope creep risk** — LikertMatrix interactive mode, evaluado navigation, autosave UX, and error surfaces could balloon; the proposal must bound the web surface and respect the design-system freeze (no new tokens/components without an ADR; owner manual checklist must be updated).
- **Follow-up debt from HANDOFF-F3 §11** — config.yaml reconciliation is in the working tree (expected); `test_catalog_db.py:305` generic `pytest.raises(Exception)`; AGENTS.md stale pointer; no coverage/E2E configured.

---

## Open Questions for the Proposal

1. Session state machine: keep the 4 statuses (`in_progress|completed|blocked|cancelled`) or add `created`? Which transitions are user-facing vs. system-only? Is `blocked_without_consent` a row status or audit-only (today: audit-only)?
2. Endpoint surface: exact paths for session read/resume and response save (batch `PUT /sessions/{id}/responses` vs per-item `POST`), and whether a published catalog listing endpoint is in scope.
3. Completion rules: block completion while required items are unanswered (uses `item.required` from the published payload) or allow partial completion?
4. Idempotency scope: apply to `POST /sessions` + `POST /{id}/complete` + response mutations only, or also retrofit consent grant/revoke?
5. Audit events: reuse `session.started`/`session.completed` only, or add `session.response_saved`/`session.resumed` (requires EVENT_CATALOG + contracts + `test_audit.py` lockstep)?
6. Migration: none needed unless F3 adds columns (e.g., `updated_at` on responses, resume cursor) — keep schema-only linear chain.
7. Web surface: which pages/routes (`/evaluacion/...`), NavBar evaluado links, autosave UX scope, and how the design-system owner checklist is updated.

---

## Ready for Proposal

Yes — the codebase facts are complete. The proposal should answer the open questions above, declare the endpoint surface (including whether a published-listing endpoint is added, which would amend `catalog-api`), and bound the web scope before spec/design rounds.

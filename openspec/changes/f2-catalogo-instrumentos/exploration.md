# Exploration: F2 — Catálogo de instrumentos (Instrument Catalog)

**Change**: `f2-catalogo-instrumentos`
**Owner**: Trevor
**Phase**: 2 of 6 (F1 Marces → F2 Trevor → F3 Jhamil → F4 Juan Carlos → F5 Piere → F6 Ivan)
**Date**: 2026-08-05 (post-F1 archive)
**Status**: Fact-finding report — NOT a design. Open questions at the end feed the proposal round.

---

## 1. Current state inventory

### 1.1 Repo shape (all delivered by F1)

- `docker-compose.yml`: services `api` (FastAPI), `db` (PostgreSQL 16), `redis` 7, `web` (Next.js) — healthchecks, `${VAR:-default}`, named volumes. Compose project name `psico`.
- `scripts/`: `.sh` + `.ps1` twins for `init-env`, `dev-up`, `migrate`, `seed`, `clean`, `test` (parity-tested, no eval).
- `packages/contracts/README.md`: binding conventions (IDs, error envelope, audit deny-list, seed manifest, institution hierarchy, access matrix).
- `services/api`: FastAPI app under `app/{core,db,models,schemas,api,seed}`; Alembic linear chain `0001_identity_institutions → 0002_instruments_consent → 0003_scoring_recommendation → 0004_audit_append_only_trigger`; 75 passing tests, 87% coverage.
- `apps/web`: single Next.js page (`app/page.tsx`) — Spanish UI, health + seed status over the compose network. No navigation, no auth UI, no catalog UI.

### 1.2 Instruments family — what exists today (F1 schema)

| Table | Columns | Constraints |
| --- | --- | --- |
| `instruments` | `id` UUID4 PK, `key` (unique), `title`, `description`, `created_at`, `synthetic`, `source` | `key` UNIQUE |
| `instrument_versions` | `id` UUID4 PK, `instrument_id` FK, `version_no` int, `status` str (default `draft`), `published_at`, `is_immutable` bool, `synthetic`, `source` | UNIQUE(`instrument_id`,`version_no`); CHECK `(status <> 'published') OR is_immutable` |
| `instrument_items` | `id` UUID4 PK, `version_id` FK, `scale` str(64), `scale_order` int, `text`, `synthetic`, `source` | UNIQUE(`version_id`,`scale`,`scale_order`); CHECK `scale_order BETWEEN 1 AND 5` |

**Critical structural facts:**

- There is **NO `scales` table and NO `response_options` table**. `scale` is a denormalized string column on `instrument_items`. The F2 reparto explicitly tasks modeling `instrument → scale → item → response_option`, so F2 must extend the schema (new migration appended to the linear chain, per the data-schema spec).
- There is **NO `response_type`, required/optional flag, locale, or per-item ordering beyond `scale_order`** (which is capped at 5 by CHECK).
- `instrument_versions.status` is free-text — no CHECK on allowed states (`draft`/`published`/`archived`?). F2 must define and constrain the state machine.
- `instruments` has **no `institution_id`** even though `packages/contracts/README.md` §5 declares institution_id "the join key every downstream phase consumes (instrument ownership, session context, reporting rollups)". F1 did not deliver instrument ownership.
- `responses.value` is CHECK-constrained `BETWEEN 1 AND 5` — the response model is hard-wired to Likert 1–5 integers; `responses.item_id` FK → `instrument_items.id`.

### 1.3 Seeded instrument content (synthetic seed, F1)

`app/seed/fixtures/items.json` + `app/seed/loader.py` seed:

- Instrument `TP-S-01` — "Test Psicométrico Sintético — Orientación Vocacional (research-only)".
- Version seed key `TP-S-01:v1`, `version_no=1`, `status=published`, `is_immutable=true`, `published_at=2026-01-01`.
- 20 items (5 scales × 4): `Intereses`, `Aptitud verbal`, `Aptitud numérica`, `Razonamiento abstracto`, `Valores/preferencias`. Item seed keys `TP-S-01:i1..i20` (uuid5 `psico-seed:` namespace).
- No response-option rows exist anywhere; the "5-point Likert" semantics live only in the `responses.value` CHECK and the fixture text.
- Reference set `RS-TP-S-01` (F4 content) is already FK-linked to `TP-S-01:v1` — F4 depends on this version id remaining stable.
- 30 profiles → 30 completed sessions + 600 responses + consent grants, all FK-referencing `TP-S-01:v1` and its items.
- `--reset` deletes **seed-owned rows only** (`source='seed'`) in reverse FK order. If F2 creates runtime rows (e.g., a v2 of TP-S-01, or a new instrument) that FK-reference the seed instrument, reset deletes the seed parents → **FK violation risk** (see Gaps).

### 1.4 API surface today

Routers registered under `/api/v1`: `auth` (POST `/login`), `seed` (GET `/status`, POST `/run`, POST `/reset` admin-only), `audit` (GET, admin-only), `consent` (GET `/versions`, POST `/{id}/grant`, POST `/{id}/revoke`), `sessions` (POST `""`, POST `/{id}/complete`), plus public `/health`. **There are ZERO instrument endpoints and ZERO instrument Pydantic schemas** (`app/schemas/` only has `auth.py`).

Existing sessions route behavior relevant to F2: `POST /api/v1/sessions` accepts **any** `instrument_version_id` and does **not** check `status == 'published'` — a session can start on a draft version today.

### 1.5 Roles, permissions, audit

- `app/core/permissions.py` CAPABILITIES: `manage_users_roles` (admin), `manage_institutions` (admin), `publish_instruments` (**admin only**), `read_catalog` (all three roles), `run_sessions` (all), `sign_consent` (all), `view_results` (all), `view_audit` (admin), `manage_seed` (admin).
- **There is NO `manage_instruments` (create/edit draft) capability.** The reparto F2 wants an ABM + edit screen "para `psicólogo`, con permisos administrativos donde corresponda" → the matrix must be extended; proposal must pick the granularity.
- `app/core/audit.py` EVENT_CATALOG (10 events): `auth.login`, `auth.denied`, `user.role_changed`, `instrument.published`, `consent.granted`, `consent.revoked`, `session.started`, `session.completed`, `session.blocked_without_consent`, `seed.executed`. **Only `instrument.published` exists for the catalog domain**; the reparto requires auditing publication, archive ("archivo") and changes — new event types needed (e.g., `instrument.version_created`, `instrument.archived`, `instrument.draft_updated`). `test_audit.py::test_event_catalog_matches_contract` pins the catalog — it must move in lockstep with the contracts README.
- Audit deny-list forbids metadata containing item content (`item_text`, `item_content`), raw responses, tokens, PII — F2's "changes" audit metadata must stay at the level of counts/version_no/actor.

### 1.6 F1 verification outcome (archive)

- `verify-report.md`: verdict **PASS WITH WARNINGS** — 23/23 tasks, 75 tests, 41/47 scenarios compliant, 0 CRITICAL, 0 WARNING.
- 3 SUGGESTION follow-ups (spec requirements added during review, **not implemented in F1**):
  1. Token refresh + server-side revocation on role change (identity-auth).
  2. Audit outage resilience policy (audit-consent).
  3. **`Idempotency-Key` handling on every mutating endpoint (contracts spec)** — directly relevant to F2, which will add many mutating endpoints.
- F1 design open questions (checksum input, seed/status visibility) — resolved in delivery, no carry-over.

---

## 2. Phase-1 contracts that F2 consumes (exact names/semantics)

1. **Role model** (`identity-auth` spec, `app/core/permissions.py`): exactly `admin`, `psicólogo`, `evaluado`; deny-by-default `require_roles(...)` on every route; denials audited as `auth.denied` + generic 403 text. `get_current_user` behind `PSICO_AUTH_MODE=dev` seam.
2. **Auth endpoints**: `POST /api/v1/auth/login` (HS256 JWT carrying role); `exp` claim validated. Refresh/revocation NOT available (F1 follow-up).
3. **Error envelope** (`contracts` spec, `app/core/errors.py`): exactly `{"error":{"code","message","request_id","details"}}`; codes `VALIDATION_ERROR | UNAUTHORIZED | FORBIDDEN | NOT_FOUND | CONFLICT | INTERNAL_ERROR`; English contract tokens; `request_id` unique per request via middleware.
4. **Idempotency contract**: every mutating endpoint MUST accept `Idempotency-Key` and replay without duplicating side effects — **required by spec, unimplemented in F1**. F2's POST/PUT/PATCH endpoints fall under it the day they exist.
5. **ID convention**: runtime rows UUID4; seed rows UUID5 under `uuid5(NAMESPACE_URL, "psico-seed:" + key)`; pinned keys `TP-S-01`, `TP-S-01:v1`, `TP-S-01:i1..i20`, `RS-TP-S-01`, `evaluado_01..30`.
6. **Data schema** (`data-schema` spec): nine families + `seed_manifest`; ONE linear schema-only Alembic chain; F5/F6 empty-but-migrated. Instruments family currently `instruments`/`instrument_versions`/`instrument_items`.
7. **Immutable versioning invariant** (`config.yaml` + models): published versions are never edited — CHECK `(status <> 'published') OR is_immutable`; sessions FK-pin `instrument_version_id`.
8. **Audit & consent** (`audit-consent` spec): append-only `audit_log` (trigger rejects UPDATE/DELETE; app role INSERT+SELECT), deny-list (no item content / responses / tokens / PII), event `instrument.published` exists; consent-gated sessions (`require_consent` → CONFLICT + `session.blocked_without_consent`).
9. **Seed conventions** (`synthetic-seed` spec): idempotent deterministic seed, `synthetic=true`/`source='seed'` on every seeded row, `seed_manifest` per run, `--reset` scoped to seed-owned rows.
10. **Access matrix rows that constrain F2**: `publish_instruments` = admin; `read_catalog` = all three roles. (Psychologist create/edit is the gap the proposal must fill.)
11. **UI language rule**: user-facing texts in Spanish; contract tokens in English (`contracts` spec, `web-scaffold`).
12. **Institution hierarchy** (`contracts` README §5): `institutions/campuses/faculties/programs` with `institution_id` NOT NULL — currently NOT connected to instruments (see gaps).

---

## 3. Gaps and risks

| # | Severity | Gap | Detail / consequence for F2 |
| --- | --- | --- | --- |
| G1 | **HIGH** | `scales` and `response_options` tables do not exist | Reparto F2 mandates modeling `instrument → scale → item → response_option`. Current `scale` is a string column; `response_option` is entirely absent. Requires new schema-only migration appended to the linear chain (allowed) and a decision on whether the ratified data-schema spec (3-table family) must be amended. |
| G2 | **HIGH** | No `manage_instruments` capability; publish is admin-only | Reparto wants the psicólogo to run the ABM; the F1 matrix has no create/edit capability. Proposal must define granularity (e.g., `manage_instruments`: admin+psicólogo; `publish_instruments`: admin; drafts invisible to `evaluado`). |
| G3 | **HIGH** | `--reset` FK-violation risk with runtime versions | If F2 edits TP-S-01 (creating runtime v2) or creates instruments/versions with `source='runtime'`, `seed --reset` deletes seed parents (`instruments`, `instrument_versions`, `instrument_items` with `source='seed'`) before/despite runtime children → FK violation. Coexistence semantics between seed content and runtime edits must be decided (see OQ1). |
| G4 | **MEDIUM** | Session creation does not gate on `published` | `POST /api/v1/sessions` accepts any `instrument_version_id`, including drafts. F3's minimum tests include "intentar iniciar con un instrumento no publicado". F2 publishes the "estados y transiciones" contract — the proposal must decide who enforces published-only (F2 read endpoint only, or a status check in session creation) and when. |
| G5 | **MEDIUM** | `instrument_versions.status` unconstrained | Free-text column; F2 defines the state machine (draft → published → archived?), archive semantics ("archivo" must be audited), and coexistence of published versions. Needs CHECK constraint + migration. |
| G6 | **MEDIUM** | Audit catalog too narrow for F2 | Only `instrument.published` exists. Archive and change events are missing. Adding events touches `EVENT_CATALOG`, `test_event_catalog_matches_contract`, and `packages/contracts/README.md` in lockstep. Deny-list limits metadata to counts/ids, never item content. |
| G7 | **MEDIUM** | Idempotency-Key spec requirement unimplemented | Every F2 mutating endpoint (create/update/publish/archive) triggers the contracts-spec requirement. Either F2 implements platform-level idempotency or records a deliberate spec exception — proposal decision. |
| G8 | **MEDIUM** | Responses hard-wired to Likert 1–5 | `responses.value` CHECK 1–5 and sessions/seed expect integer 1–5. If `response_option` modeling implies other response types, the ripple hits F3 (`responses`) and F4 (scoring). Likely MVP boundary: keep 1–5 Likert, model options as labels within that range. |
| G9 | **MEDIUM** | No instrument ownership (`institution_id`) | Contracts README §5 promises instrument ownership as a downstream join key; F1 didn't deliver it. Multi-institution intent exists in `config.yaml`. Proposal must decide add-now vs defer (F2 or later phase). |
| G10 | **LOW/INFO** | F1 untested platform scenarios | Token refresh/revocation, audit outage resilience, idempotency (6 scenarios) are recorded as SUGGESTION follow-ups; only idempotency touches F2's surface directly. No CRITICAL/WARNING blockers from F1 verification. |
| G11 | **INFO** | No instrument schemas, endpoints, or UI exist | F2 is greenfield on top of stable conventions (envelope, require_roles, audit, seed, Spanish UI). No naming conflicts; F3/F4 already depend on `TP-S-01:v1` staying stable. |

---

## 4. Out-of-scope boundaries (from the reparto, binding for F2)

F2 MUST NOT deliver:

- Scoring, baremos, program profiles or recommendations (F4/F5).
- Real psychometric content or unapproved validity claims; the fictitious test stays synthetic/research-only.
- In-place editing of a published version (immutability invariant).
- LLM use for creating, scoring or explaining items (config.yaml invariant).
- Diagnostics, admissions, employment, hiring, rejection or high-impact decisions (global product boundary).
- F1's platform follow-ups (refresh/revocation, audit outage resilience) unless the proposal explicitly absorbs them.

F2 MUST hand off to:

- **Jhamil (F3)**: a published `instrument_version_id`, the read payload for rendering a session, the freezing rule, and error cases.
- **Juan Carlos (F4)**: synthetic response fixtures and the exact item ↔ scale ↔ option relationship.

---

## 5. OPEN QUESTIONS (for the proposal round — product/domain level)

1. **Seed instrument content policy**: Is `TP-S-01` v1 (seed-owned, published, immutable, referenced by 30 seed sessions + RS-TP-S-01) the working base for F2's UI (e.g., "new version from TP-S-01"), or must F2's workflows target new instruments only? What is the allowed relationship between runtime edits and seed-owned content, and how does `seed --reset` behave when runtime versions coexist (FK violation — see G3)? Options include: forbid editing seed instruments in UI, treat seed instrument as reference-only, or extend reset to handle dependent runtime rows with a documented rule.
2. **Permission granularity**: exact matrix for create/edit draft, publish, and archive. Does `psicólogo` create/edit drafts while only `admin` publishes (reparto: "con permisos administrativos donde corresponda")? Are drafts visible to `evaluado` (F1 matrix grants `read_catalog` to all — must it become "read published only")?
3. **Validation rules scope**: which validations are in the F2 MVP (order, belonging, mandatory, response type, scale/item consistency per reparto)? Is the response type fixed to Likert 1–5 for MVP (given `responses.value` CHECK 1–5) or generalized via `response_option`? Does "obligatoriedad" (mandatory) add an item-level flag?
4. **Audit granularity**: which new audit events does the catalog gain (e.g., `instrument.version_created`, `instrument.draft_updated`, `instrument.published`, `instrument.archived`), and what metadata shape (version_no, counts, actor — never item content per deny-list)? Is every draft save audited, or only state transitions?
5. **Coexistence semantics**: exact state machine (draft → published → archived?) and versioning rule (version_no auto-increment per instrument; publish freezes; edit spawns a new draft). May two published versions coexist and both be session-startable (F2 acceptance: "conservar dos versiones coexistentes")? What happens to in-flight/future sessions when a version is archived — blocked, or allowed until replaced?
6. **Schema extension vs ratified spec**: adding `scales` + `response_options` (and a status CHECK) changes the data-schema spec's instruments family. Does the proposal amend the spec, or implement the reparto's 4-level model as the new ratified shape? Same question for `institution_id` on instruments (add ownership now or defer).
7. **Idempotency-Key**: does F2 implement the contracts-spec idempotency requirement on its mutating endpoints (platform-level, carries to F3–F6) or defer with a documented exception?

---

## 6. Recommendation for next step

Proceed to `sdd-propose`. The proposal must answer OQ1–OQ7 and name the F1 gaps it absorbs (G2 permission matrix, G4 published-gate ownership, G6 audit events, G7 idempotency, G9 ownership). Design work (schema migration shape, endpoint surface, UI structure) belongs to the design phase, not here.

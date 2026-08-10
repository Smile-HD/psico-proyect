# Proposal: F3 — Evaluation Session

## Intent

F1 starts draft sessions, lacks response/read/resume APIs, and permits empty or partial completion. F3 gives evaluados a published-only, consent-gated workflow that pins an immutable version, autosaves/resumes answers, and closes without scoring.

**Owners:** F3/Jhamil; F1/Marces (consent), F2/Trevor (listing), F4/Juan Carlos (handoff).

## Scope

### In Scope
- **API:** `POST /api/v1/sessions`; own `GET /api/v1/sessions` and `GET /api/v1/sessions/{id}`; own batch `PUT /api/v1/sessions/{id}/responses` (server maps option IDs to 1–5); `POST /api/v1/sessions/{id}/complete` (existing admin operational override retained). All mutations require `Idempotency-Key`.
- **Discovery/gate:** add `GET /api/v1/catalog/published-versions` for published summaries. Session creation first maps malformed, missing, draft, and archived versions to indistinguishable `NOT_FOUND`; missing consent remains `CONFLICT consent_required`.
- **Web:** `/evaluacion` discovery/start and `/evaluacion/sesiones/[id]` controlled `LikertMatrix`, debounced `apiFetch` autosave/resume, completion feedback, and an evaluado NavBar entry. Reuse the frozen Spanish design system.
- Retrofit `Idempotency-Key` on existing consent grant/revoke mutations; preserve their semantics.

### Out of Scope
- F4 scoring/results, F5 recommendations, adaptive branching, new response types, seed changes, or instrument editing. Scoring starts in F4.

## Capabilities

### New Capabilities
- `sessions`: lifecycle, ownership, gate, response persistence, and completion.
- `evaluation-session-ui`: discovery, interaction, autosave, and resume.

### Modified Capabilities
- `catalog-api`: published-version listing.
- `audit-consent`: idempotent grant/revoke.
- `contracts`: session and consent mutation idempotency.

## Approach

- **State/migration:** persist only `in_progress → completed`; creation starts `in_progress`. Do not add `created`; `blocked`/`cancelled` remain reserved and unreachable; `blocked_without_consent` is audit-only. No migration.
- Reuse `assessment_authoring.idempotency` unchanged: canonical hash, replay, and same-key/different-body `CONFLICT`.
- Require every `required=true` item; optional items may remain blank. Emit only existing `session.started`/`session.completed`; add no audit events. Keep `EVENT_CATALOG` and `test_audit.py` unchanged; metadata is aggregate-only and never contains response content.
- Copy `instrument_version_id` verbatim. Existing sessions read their immutable pinned projection even after catalog archival; the public published-read route remains published-only.

## Affected Areas

| Area | Impact |
|------|--------|
| `services/api/app/modules/session_runtime/`, `routes/sessions.py`, tests | New API behavior; no migration |
| `apps/web/app/evaluacion*`, `NavBar`, `LikertMatrix` consumers | New evaluado workflow |
| `openspec/specs/{sessions,catalog-api,audit-consent,contracts}` | New specs and deltas |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Archived versions and retry races | Med | Owned pinned projection; transactional idempotency tests |
| Cross-phase scope growth | Med | Reuse existing helpers/components; no new audit events or tokens |

## Rollback Plan

Roll back the API/web release and hide the new navigation/listing. Keep immutable rows and the status CHECK; no migration makes rollback non-destructive. Later schema changes use forward correction, never downgrade.

## Dependencies

F2 payload/immutability contract, existing session/response/consent tables, `apiFetch`, pytest/PostgreSQL, and web `next build`.

## Success Criteria

- [ ] Draft/archived/missing/invalid versions all return stable `NOT_FOUND` on session creation.
- [ ] Required items block completion; retries create no duplicate rows or audit events.
- [ ] Evaluados can discover, start, autosave, resume, and complete a session with no score exposed.

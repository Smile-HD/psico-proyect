# Proposal: F3 — Evaluation Session & Delivery (Fase 3)

## Intent

F3 team goal: *"Que un evaluado pueda rendir el test de principio a fin de forma confiable, con temporizador en servidor, autoguardado por ítem y reanudación ante caídas de red"*[cite: 4]. F3 implements the session lifecycle, server-enforced expiration, idempotent response recording, and full resumption support without altering frozen instrument versions[cite: 4]. Touches phase **F3 (owner: Jhamil)**[cite: 4].

## Scope

### In Scope
- Session lifecycle state machine: `created` → `in_progress` → `completed` | `cancelled`[cite: 4].
- Immutability binding: every session locks its exact `instrument_version_id` at creation time[cite: 4].
- Server-side time authority: expiration calculated from `started_at` + instrument duration; late submissions rejected or auto-submitted[cite: 4].
- Item-level autosave API: `POST /api/v1/sessions/{id}/responses` with `Idempotency-Key` header support to prevent duplicates on network retries[cite: 4].
- Resumption API: `GET /api/v1/sessions/{id}/resume` returning saved responses and server-calculated remaining time[cite: 4].
- Final submission API: `POST /api/v1/sessions/{id}/submit` freezing responses and setting status to `completed`[cite: 4].
- Audit trail logging for session creation, interruption, resumption, and final completion[cite: 4].

### Out of Scope
- Scoring calculations, norms, or percentiles (handled by F4)[cite: 4].
- Recommendation engine and career matching (handled by F5)[cite: 4].
- PDF report generation (handled by F6)[cite: 4].
- Modifying published instrument versions or item answer keys[cite: 4].

## Capabilities

### New Capabilities
- `delivery-session`: full session lifecycle management, server-side timer enforcement, idempotent response autosaving, resumption endpoint, and submission freezing[cite: 4].

### Modified Capabilities
None — uses existing `Session` and `Response` models under `app/models/sessions.py`[cite: 4].

## Approach

Implement API endpoints under `services/api/app/api/routes/sessions.py` connected to the main router[cite: 4]. Pydantic v2 schemas defined under `app/schemas/sessions.py`. Enforce server-side clock checking for timer expiration[cite: 4]. Use `Idempotency-Key` header in HTTP requests to handle network retries safely[cite: 4].

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `services/api/app/schemas/sessions.py` | New | Pydantic DTOs for session init, response autosave, resume, and submit |
| `services/api/app/api/routes/sessions.py` | New | FastAPI endpoints for session lifecycle (`/api/v1/sessions`) |
| `services/api/app/api/router.py` | Modified | Registers session delivery routes under `/api/v1` |
| `services/api/tests/test_sessions.py` | New | Pytest integration suite for autosave, idempotency, timer, and resumption |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Client clock skew bypasses test time limit | High | Server calculates remaining time from `started_at` in DB; rejects late posts[cite: 4]. |
| Network drop during autosave duplicates responses | Med | Enforce `Idempotency-Key` header and database unique constraints[cite: 4]. |
| Active session instrument version gets edited | Low | Session strictly locks `instrument_version_id` on creation; immutable[cite: 4]. |

## Rollback Plan

- Non-breaking changes: revert Git commits for `sessions.py` routes and schemas.
- Existing database schema in Alembic already includes `sessions` and `responses` tables; no migration rollback needed[cite: 4].

## Dependencies

- Depends on F1 (Auth & Users) and F2 (Published `InstrumentVersion` availability)[cite: 4].

## Success Criteria

- [ ] An `evaluado` creates a session locking a published `instrument_version_id`[cite: 4].
- [ ] Item responses autosave idempotently using `Idempotency-Key`[cite: 4].
- [ ] Refreshing or reconnecting via `/resume` restores all saved responses and exact server-calculated time remaining[cite: 4].
- [ ] Submitting (`/submit`) sets status to `completed` and freezes further edits[cite: 4].
- [ ] All integration tests in `test_sessions.py` pass cleanly in `pytest`[cite: 4].
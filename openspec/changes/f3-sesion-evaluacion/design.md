# Design: F3 — Evaluation Session

## Technical Approach

Add `app/modules/session_runtime/` with F2’s domain/service/repository/errors layering. Routes are adapters; the service owns gate, consent, transaction, idempotency, upsert, and completion. Existing tables suffice. The listing belongs to `CatalogService`; session reads use a safe projection and never score.

The repository locks the actor row for create and the session row with `SELECT FOR UPDATE` before response/complete idempotency lookup, validation, and PostgreSQL upsert; this serializes same-session autosaves and completion.

## Architecture Decisions

| ADR | Choice and rationale |
|---|---|---|
| ADR-001 Idempotency | Import `assessment_authoring.idempotency` unchanged. Create uses actor-wide scope; response/complete use `session:{id}`. Extraction risks changing F2’s hash/CONFLICT contract. |
| ADR-002 Pinned projection | Re-project immutable rows, including archived versions; hide catalog status and numeric values. A snapshot needs a migration and duplicates protected data. |
| ADR-003 Gate order | Published-only gate precedes consent. Consent-first leaks draft/archive existence and audits probes; gate-first mirrors F2 `NOT_FOUND`, while valid published requests still yield `consent_required` and its existing denial audit. |
| ADR-004 Autosave keys | One random key per debounced intent, reused for retries; a new cycle gets a new key. A single-flight queue prevents stale writes. Payload-derived keys conflate intents. |
| ADR-005 Proposal deviation | None: no migration, seed change, scoring, or new event. Successful lifecycle events are `session.started`/`session.completed`; autosave emits none. The existing consent-block event remains required. |

## Data Flow

```mermaid
sequenceDiagram
    actor E as Evaluado
    participant API as Sessions API
    participant S as Service
    participant DB as DB
    E->>API: POST /sessions + Idempotency-Key
    API->>S: lock actor; replay lookup
    S->>DB: published gate
    alt invalid or non-published
        DB-->>API: identical NOT_FOUND
    else published
        S->>DB: consent; deny audit if absent
        S->>DB: create + audit + result; commit
        API-->>E: 201 in_progress
    end
```

```mermaid
sequenceDiagram
    actor E as Evaluado
    participant API as Sessions API
    participant S as Service
    participant DB as DB
    E->>API: GET /sessions/{id}
    S->>DB: owner check; re-project pinned rows + option ids
    DB-->>E: progress and current answers
    E->>API: PUT /responses + cycle key
    S->>DB: lock; validate batch; upsert `(session,item)`; commit
```

```mermaid
sequenceDiagram
    actor E as User
    participant S as Service
    participant DB as DB
    E->>S: POST /sessions/{id}/complete + key
    S->>DB: lock and check required items
    alt incomplete or wrong state
        DB-->>E: VALIDATION_ERROR or CONFLICT; no audit
    else complete
        S->>DB: completed + aggregate audit + result; commit
        DB-->>E: 200 completed, no score
    end
```

## File Changes

| File | Action | Purpose |
|---|---|---|
| `services/api/app/modules/session_runtime/domain.py`, `service.py`, `repository.py`, `errors.py` | Create | Pure transitions; orchestration; `FOR UPDATE` queries/upsert; stable errors. |
| `services/api/app/schemas/sessions.py` | Create | Start, batch, summary/detail DTOs; option IDs only. |
| `services/api/app/api/routes/sessions.py` | Modify | Thin POST/GET/PUT/complete adapters; ownership/header rules. |
| `services/api/app/api/routes/catalog.py`, `services/api/app/modules/assessment_authoring/service.py`, `services/api/app/modules/assessment_authoring/repository.py`, `services/api/app/schemas/catalog.py` | Modify | All-role published labels listing. |
| `services/api/app/core/consent.py`, `services/api/app/api/routes/consent.py` | Modify | Atomic registry, audit, and idempotency retrofit. |
| `apps/web/app/evaluacion/page.tsx`, `apps/web/app/evaluacion/page.module.css`, `apps/web/app/evaluacion/sesiones/[id]/page.tsx`, `apps/web/app/evaluacion/sesiones/[id]/page.module.css`, `apps/web/lib/session-api.ts`, `apps/web/components/ui/NavBar.tsx` | Create/modify | Discovery, controlled matrix, resume, queued saves, completion, navigation. |
| `apps/web/components/ui/LikertMatrix.tsx` | No change | Existing controlled radios already satisfy the frozen matrix contract. |
| `services/api/tests/test_session_*.py` plus consent/listing tests | Create | RED→GREEN contracts and concurrency coverage. |

## Interfaces / Contracts

Pure API: `domain.transition(current, target)` permits only `in_progress → completed`; `required_missing(required_ids, answered_ids)` and `validate_batch(pairs, allowed_options)` are side-effect-free. `GET /sessions` is own-only; detail is owner-or-admin and returns progress plus the pinned projection; complete retains the admin operational override. `GET /catalog/published-versions` is labels-only for all roles. `POST /sessions` accepts `{instrument_version_id: string | null}`; absent, malformed, missing, draft, and archived IDs map to F2’s identical `NOT_FOUND/resource_not_found`. `PUT /responses` accepts `{responses: [{item_id, response_option_id}]}` and validates all pairs before writing. Numeric values, scores, and reference results never cross the API. Missing keys are `VALIDATION_ERROR`; reuse is `CONFLICT/idempotency_key_reused`; foreign mutations are `FORBIDDEN`. Completion audit metadata is only `response_count`, passed through the deny-list.

Web uses Spanish copy and frozen tokens/components: `/evaluacion` lists and starts; `/evaluacion/sesiones/[id]` resumes controlled `LikertMatrix`, announces queued-save success/failure with `Notice`, retains failed local input for retry, marks required items in text, and confirms completion without scores. WCAG 2.2 AA and reduced motion remain required.

## Testing Strategy

Unit tests cover transitions, reserved states, required items, batch rejection, and option mapping. PostgreSQL `TestClient` tests cover the handoff contract, identical no-leak errors, consent ordering/audit, replay, atomic upsert, own-session `403`, required completion, aggregate audit, and archival survival. `test_session_*.py` must pin those cases and absence of numeric fields; consent/listing get dedicated files. Strict TDD: RED, `powershell -ExecutionPolicy Bypass -File scripts/test.ps1`, GREEN, refactor, then full suite twice. Web has no E2E runner; use `npm run build` and the owner checklist.

## Threat Matrix

Routing changes are HTTP-only; the supplied shell/VCS matrix has no applicable boundary.

| Boundary | Applicability and safe/failure behavior | RED tests |
|---|---|---|
| Documentation-like paths | N/A — no files are executed. | None |
| Git repository selection | N/A — no Git command is invoked. | None |
| Commit state | N/A — no commit automation. | None |
| Push state | N/A — no push automation. | None |
| PR commands | N/A — no PR automation. | None |

## Migration / Rollout

No migration: existing foreign keys, response uniqueness/value checks, and immutable rows suffice. Deploy API then web; rollback the release and hide navigation/listing. No seed changes.

## Open Questions

None.

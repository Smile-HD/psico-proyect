# Sessions Specification

## Purpose

The F3 session runtime: consent-gated creation pinned to a published version, owner-only reads, batched response autosave, and completion without scoring. Only `in_progress → completed` are reachable statuses; `blocked`/`cancelled` remain reserved and unreachable, and `blocked_without_consent` is audit-only. Mutations reuse the ratified idempotency infrastructure; no new audit events are added.

## Requirements

### Requirement: Session Creation Gate

Session creation MUST require an `Idempotency-Key` and MUST map malformed, missing, draft, and archived `instrument_version_id` values to the same stable `NOT_FOUND` envelope, revealing neither existence nor status. A user without a `granted` consent MUST receive `CONFLICT` (`consent_required`) and the attempt MUST be audited as `session.blocked_without_consent`. On success the session MUST be created with status `in_progress`, MUST copy `instrument_version_id` verbatim (never changed afterwards), and MUST audit `session.started`.

#### Scenario: Draft version rejected per handoff contract

- GIVEN the F2 handoff contract and a draft `instrument_version_id`
- WHEN session creation is requested
- THEN the stable `NOT_FOUND` envelope is returned
- AND no session row or audit event is created

#### Scenario: All non-published ids are indistinguishable

- GIVEN malformed, missing, draft, and archived version ids
- WHEN each is used to create a session
- THEN all four responses are identical `NOT_FOUND` envelopes
- AND none reveals whether the version exists or its status

#### Scenario: Consent gate blocks creation

- GIVEN a user without a granted consent
- WHEN session creation is requested for a published version
- THEN `CONFLICT` with message `consent_required` is returned
- AND `session.blocked_without_consent` is audited

#### Scenario: Published version starts in progress

- GIVEN a user with a granted consent and a published version
- WHEN session creation succeeds
- THEN the session has status `in_progress` and the exact `instrument_version_id`
- AND `session.started` is audited

### Requirement: Own-session Read Surface

`GET /sessions` MUST return only the caller's sessions. `GET /sessions/{id}` MUST return status, the pinned `instrument_version_id`, progress (answered/total items), and — for the owner — current answers as stable `response_option_id` values; a missing id MUST return `NOT_FOUND`. A non-owner without `admin` MUST receive `FORBIDDEN`; `admin` MAY read any session. The read payload MUST NOT contain numeric option values or scoring data.

#### Scenario: Owner resumes a session

- GIVEN an `in_progress` session owned by the caller
- WHEN the session detail is read
- THEN status, pinned version, progress, and answered option ids are returned
- AND no numeric option values are present

#### Scenario: Foreign session denied

- GIVEN an `evaluado` user and a session owned by another user
- WHEN the session detail is requested
- THEN `FORBIDDEN` is returned
- AND no session data is exposed

#### Scenario: Own list is scoped

- GIVEN two users with sessions
- WHEN each calls `GET /sessions`
- THEN each response contains only that user's sessions

### Requirement: Response Recording

`PUT /sessions/{id}/responses` MUST accept a batch of `item_id`/`response_option_id` pairs, MUST map each option id server-side to its value 1–5, and MUST upsert on `UNIQUE(session_id, item_id)` so re-saving an item replaces its value without duplicate rows. Every item MUST belong to the session's pinned version; otherwise the whole batch MUST fail with `VALIDATION_ERROR` and no partial write. Recording on a session that is not `in_progress` MUST fail with `CONFLICT`. Autosave MUST NOT emit audit events.

#### Scenario: Batch autosave upserts

- GIVEN an `in_progress` session and three answered items
- WHEN the batch is saved
- THEN three rows exist with values mapped to 1–5
- AND no audit event is emitted

#### Scenario: Re-saving replaces the value

- GIVEN an answered item with option A
- WHEN the same item is saved with option B
- THEN exactly one row remains with B's value

#### Scenario: Foreign item rejects the batch

- GIVEN a batch containing an item not in the pinned version
- WHEN it is saved
- THEN `VALIDATION_ERROR` is returned
- AND no row from the batch is persisted

### Requirement: Completion without Scoring

`POST /sessions/{id}/complete` MUST require an answer for every `required=true` item of the pinned version; otherwise the session MUST stay `in_progress` and the response MUST be the stable `VALIDATION_ERROR` envelope. On success the session MUST become `completed` and `session.completed` MUST be audited with aggregate metadata only (e.g. `response_count`) — never response content, tokens, or item content. Completion MUST NOT compute or expose scores or reference-set results (F4 owns scoring); the completion response SHALL NOT contain scoring data.

#### Scenario: Required item unanswered blocks completion

- GIVEN an `in_progress` session missing a required answer
- WHEN completion is requested
- THEN `VALIDATION_ERROR` is returned
- AND the session remains `in_progress`

#### Scenario: Completion audits aggregates only

- GIVEN an `in_progress` session with all required items answered
- WHEN completion is requested
- THEN status becomes `completed`
- AND the `session.completed` metadata holds only aggregates such as `response_count`

#### Scenario: No scoring exposed

- GIVEN a completed session
- WHEN the completion response is inspected
- THEN it contains no scores, percentiles, or reference-set computations

### Requirement: Session State Machine

Only `in_progress` and `completed` MUST be reachable through F3 operations. `blocked` and `cancelled` MUST remain reserved and unreachable; `blocked_without_consent` is an audit event only, never a session status. Sessions MUST keep their pinned version projection even after the version is archived. A mutation targeting a session not in the expected state MUST fail with `CONFLICT`.

#### Scenario: Reserved statuses never occur

- GIVEN any F3 operation sequence
- WHEN session rows are inspected
- THEN no row ever has status `blocked` or `cancelled`

#### Scenario: Pinned projection survives archival

- GIVEN a session started on a published version
- WHEN that version is later archived
- THEN the session still reads against the same `instrument_version_id`

### Requirement: Idempotent Session Mutations

Every session mutation (create, save responses, complete) MUST require an `Idempotency-Key`. Replaying the same key with the same body MUST return the original result with no duplicate rows or audit events. Reusing the same key with a materially different body MUST fail with `CONFLICT` and message `idempotency_key_reused`, with no side effect.

#### Scenario: Retry replays without duplication

- GIVEN a completed creation with `Idempotency-Key: k`
- WHEN the same request is retried with the same key
- THEN the original result is replayed
- AND exactly one session row and one `session.started` event exist

#### Scenario: Same key, different body conflicts

- GIVEN a successful mutation with `Idempotency-Key: k`
- WHEN the same key arrives with a different body
- THEN `CONFLICT` with `idempotency_key_reused` is returned
- AND no second side effect is created

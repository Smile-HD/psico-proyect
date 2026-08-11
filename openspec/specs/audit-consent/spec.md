# Audit & Consent Specification

## Purpose

Append-only audit trail with a deny-list, plus a versioned consent registry that gates session creation.

## Requirements

### Requirement: Append-only Audit Log

`audit_log` MUST record `event_type` (catalog includes `auth.login`, `auth.denied`, `consent.granted`, `consent.revoked`, `session.started`, `session.completed`, `session.blocked_without_consent`, `seed.executed`, `instrument.draft_created`, `instrument.draft_updated`, `instrument.published`, `instrument.archived`, `scoring.run`), `actor_user_id` (nullable = system), `actor_role` snapshot, `resource_type`, `resource_id`, `action`, `outcome`, `occurred_at`, and `metadata` JSONB. A DB trigger MUST reject `UPDATE`/`DELETE` on `audit_log`; the app DB role MUST have only `INSERT`+`SELECT`. The deny-list MUST forbid logging raw responses, PII beyond actor id, tokens, and item content. For catalog events, metadata MUST be aggregate-only: actor, instrument/version identifiers, `version_no`, status transition, and aggregate counts; it MUST NOT contain item text, response-option keys or values, or internal rules. For scoring events, metadata MUST be aggregate-only: session, version, reference-set, and run identifiers, response/scale counts, and timestamps; it MUST NEVER contain response values, option keys, item content, or computed scores. The `EVENT_CATALOG`, `packages/contracts/README.md`, and the event-catalog contract test MUST be updated in lockstep when catalog events are added.

#### Scenario: Append-only enforced

- GIVEN an existing audit row
- WHEN a client issues `UPDATE` or `DELETE` on it
- THEN the trigger rejects the statement

#### Scenario: Deny-list respected

- GIVEN a completed session
- WHEN `session.completed` is written to audit
- THEN metadata contains no response values, tokens, passwords, or item content

#### Scenario: Catalog events carry aggregate metadata only

- GIVEN a published synthetic version with 2 scales, 10 items, and 50 response options
- WHEN `instrument.published` is written to audit
- THEN metadata contains identifiers, `version_no`, transition, and counts only
- AND it contains no item text, option values, or internal rules

#### Scenario: Scoring event carries aggregates only

- GIVEN a completed scoring run
- WHEN `scoring.run` is written to audit
- THEN metadata holds identifiers, counts, and timestamps only
- AND it contains no response values, option keys, item content, or scores

### Requirement: Audit Outage Resilience

Audit writes MUST NOT fail gated operations in cascade when the audit store is unavailable. The API MUST apply an explicit, configured policy: a bounded write timeout, in-process buffering with retry, and a declared fail-open/fail-closed choice per gated operation. When the policy fails closed and the audit outcome gates the response, the operation MUST return `INTERNAL_ERROR` instead of proceeding silently.

#### Scenario: Audit store unavailable

- GIVEN an unavailable audit store
- WHEN a gated operation performs an audit write
- THEN the operation applies the configured timeout and buffer policy instead of failing immediately
- AND buffered audit events are retried when the store recovers

#### Scenario: Fail-closed gate

- GIVEN a gated operation whose response depends on the audit outcome
- WHEN the audit store is unavailable beyond the buffer window
- THEN the operation fails with `INTERNAL_ERROR`
- AND no success is reported without the required audit write

### Requirement: Versioned Consent Registry

`consent_versions` MUST carry `id`, `version_no`, `title`, `body` (markdown), `effective_from`, `is_active`. `consent_grants` MUST carry `id`, `user_id`, `consent_version_id`, `state` (`pending`|`granted`|`revoked`|`expired`), `signed_at`, `ip`, `metadata`. Grant and revoke MUST write audit events and transition the registry state.

#### Scenario: Grant lifecycle

- GIVEN an active consent version
- WHEN a user signs it
- THEN a `granted` grant row exists
- AND `consent.granted` is audited

#### Scenario: Revoke lifecycle

- GIVEN a `granted` consent
- WHEN the user revokes it
- THEN state becomes `revoked`
- AND `consent.revoked` is audited

### Requirement: Consent-gated Sessions

A session MUST reference a consent grant in state `granted` for its user. Without it, session creation MUST be blocked and audited as `session.blocked_without_consent`.

#### Scenario: Blocked without consent

- GIVEN a user with no `granted` consent
- WHEN a session is requested
- THEN creation fails with error code `CONFLICT`
- AND `session.blocked_without_consent` is audited

#### Scenario: Granted session starts

- GIVEN a user with a `granted` consent
- WHEN a session is requested
- THEN the session is created
- AND `session.started` is audited

### Requirement: Idempotent Consent Mutations

`POST /api/v1/consent/{id}/grant` and `POST /api/v1/consent/{id}/revoke` MUST require an `Idempotency-Key`, preserving their existing registry semantics (state transitions and `consent.granted`/`consent.revoked` audit). Replaying the same key and body MUST return the original result with no duplicate registry effect or audit event. Reusing the same key with a materially different body MUST fail with `CONFLICT` and message `idempotency_key_reused`, with no side effect.

#### Scenario: Retried grant replays

- GIVEN a grant that succeeded with `Idempotency-Key: k`
- WHEN the same request is retried with the same key
- THEN the original result is replayed
- AND exactly one `consent.granted` event exists for that grant

#### Scenario: Retried revoke replays

- GIVEN a revoke that succeeded with `Idempotency-Key: k`
- WHEN the same request is retried with the same key
- THEN the original result is replayed
- AND exactly one `consent.revoked` event exists

#### Scenario: Same key, different body conflicts

- GIVEN a grant stored with `Idempotency-Key: k`
- WHEN the same key arrives with a different body
- THEN `CONFLICT` with `idempotency_key_reused` is returned
- AND no second registry effect or audit event occurs

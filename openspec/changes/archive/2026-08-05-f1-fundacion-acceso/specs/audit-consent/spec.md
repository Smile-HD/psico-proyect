# Delta Spec: audit-consent

# Audit & Consent Specification

## Purpose

Append-only audit trail with a deny-list, plus a versioned consent registry that gates session creation.

## ADDED Requirements

### Requirement: Append-only Audit Log

`audit_log` MUST record `event_type` (catalog includes `auth.login`, `auth.denied`, `consent.granted`, `consent.revoked`, `session.started`, `session.completed`, `session.blocked_without_consent`, `seed.executed`), `actor_user_id` (nullable = system), `actor_role` snapshot, `resource_type`, `resource_id`, `action`, `outcome`, `occurred_at`, and `metadata` JSONB. A DB trigger MUST reject `UPDATE`/`DELETE` on `audit_log`; the app DB role MUST have only `INSERT`+`SELECT`. The deny-list MUST forbid logging raw responses, PII beyond actor id, tokens, and item content.

#### Scenario: Append-only enforced

- GIVEN an existing audit row
- WHEN a client issues `UPDATE` or `DELETE` on it
- THEN the trigger rejects the statement

#### Scenario: Deny-list respected

- GIVEN a completed session
- WHEN `session.completed` is written to audit
- THEN metadata contains no response values, tokens, passwords, or item content

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


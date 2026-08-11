# Delta for Audit & Consent

## MODIFIED Requirements

### Requirement: Append-only Audit Log

`audit_log` MUST record `event_type` (catalog includes `auth.login`, `auth.denied`, `consent.granted`, `consent.revoked`, `session.started`, `session.completed`, `session.blocked_without_consent`, `seed.executed`, `instrument.draft_created`, `instrument.draft_updated`, `instrument.published`, `instrument.archived`, `scoring.run`), `actor_user_id` (nullable = system), `actor_role` snapshot, `resource_type`, `resource_id`, `action`, `outcome`, `occurred_at`, and `metadata` JSONB. A DB trigger MUST reject `UPDATE`/`DELETE` on `audit_log`; the app DB role MUST have only `INSERT`+`SELECT`. The deny-list MUST forbid logging raw responses, PII beyond actor id, tokens, and item content. For catalog events, metadata MUST be aggregate-only: actor, instrument/version identifiers, `version_no`, status transition, and aggregate counts; it MUST NOT contain item text, response-option keys or values, or internal rules. For scoring events, metadata MUST be aggregate-only: session, version, reference-set, and run identifiers, response/scale counts, and timestamps; it MUST NEVER contain response values, option keys, item content, or computed scores. The `EVENT_CATALOG`, `packages/contracts/README.md`, and the event-catalog contract test MUST be updated in lockstep when catalog events are added.

(Previously: the event catalog ended at `instrument.archived` with no scoring event; F4 ratifies `scoring.run` with aggregate-only metadata and no other new events.)

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

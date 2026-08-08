# Delta for Audit & Consent

## MODIFIED Requirements

### Requirement: Append-only Audit Log

`audit_log` MUST record `event_type` (catalog includes `auth.login`, `auth.denied`, `consent.granted`, `consent.revoked`, `session.started`, `session.completed`, `session.blocked_without_consent`, `seed.executed`, `instrument.draft_created`, `instrument.draft_updated`, `instrument.published`, `instrument.archived`), `actor_user_id` (nullable = system), `actor_role` snapshot, `resource_type`, `resource_id`, `action`, `outcome`, `occurred_at`, and `metadata` JSONB. A DB trigger MUST reject `UPDATE`/`DELETE` on `audit_log`; the app DB role MUST have only `INSERT`+`SELECT`. The deny-list MUST forbid logging raw responses, PII beyond actor id, tokens, and item content. For catalog events, metadata MUST be aggregate-only: actor, instrument/version identifiers, `version_no`, status transition, and aggregate counts; it MUST NOT contain item text, response-option keys or values, or internal rules. The `EVENT_CATALOG`, `packages/contracts/README.md`, and the event-catalog contract test MUST be updated in lockstep when the catalog events are added.

(Previously: the event catalog had ten events with only `instrument.published` for the catalog domain; draft and archive events did not exist.)

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
- WHEN the `instrument.published` audit row is inspected
- THEN metadata contains ids, `version_no`, the transition, and counts 2/10/50
- AND it contains no item text and no option keys or values

#### Scenario: Event catalog stays in lockstep

- GIVEN the contract event catalog after F2
- WHEN comparing `EVENT_CATALOG`, `packages/contracts/README.md`, and the event-catalog contract test
- THEN all three contain the same four catalog events

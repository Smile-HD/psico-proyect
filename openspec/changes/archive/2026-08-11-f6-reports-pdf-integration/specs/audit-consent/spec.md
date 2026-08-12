# Delta for Audit & Consent

## MODIFIED Requirements

### Requirement: Append-only Audit Log

`audit_log` MUST record `event_type` (catalog includes `auth.login`, `auth.denied`, `consent.granted`, `consent.revoked`, `session.started`, `session.completed`, `session.blocked_without_consent`, `seed.executed`, `instrument.draft_created`, `instrument.draft_updated`, `instrument.published`, `instrument.archived`, `scoring.run`, `recommendation.generated`, `report.generated`), `actor_user_id` (nullable = system), `actor_role` snapshot, `resource_type`, `resource_id`, `action`, `outcome`, `occurred_at`, and `metadata` JSONB. A DB trigger MUST reject `UPDATE`/`DELETE` on `audit_log`; the app DB role MUST have only `INSERT`+`SELECT`. The deny-list MUST forbid logging raw responses, PII beyond actor id, tokens, and item content. For catalog events, metadata MUST be aggregate-only: actor, instrument/version identifiers, `version_no`, status transition, and aggregate counts; it MUST NOT contain item text, response-option keys or values, or internal rules. For scoring events, metadata MUST be aggregate-only: session, version, reference-set, and run identifiers, response/scale counts, and timestamps; it MUST NEVER contain response values, option keys, item content, or computed scores. For recommendation events, metadata MUST be aggregate-only: session id, program and rule identifiers, rule/result counts, and timestamps; it MUST NEVER contain fit scores, justification text, response values, option keys, item content, or computed scores. For report events, metadata MUST be aggregate-only: session id, report id, template id and `version_no`, status transition, sha256 checksum, byte size, and timestamps; it MUST NEVER contain the report body, scores, justifications, PDF bytes, storage keys, tokens, or internal paths. The `EVENT_CATALOG`, `packages/contracts/README.md`, and the event-catalog contract test MUST be updated in lockstep when catalog, recommendation, or report events are added.

(Previously: the event catalog ended at `recommendation.generated`; F6 ratifies `report.generated` with aggregate-only metadata and no other new events — downloads are not separately audited.)

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

#### Scenario: Recommendation event carries aggregates only

- GIVEN a completed recommendation generation
- WHEN `recommendation.generated` is written to audit
- THEN metadata holds session, program and rule identifiers, counts, and timestamps only
- AND it contains no fit scores, justification text, or response data

#### Scenario: Report event carries aggregates only

- GIVEN a `ready` report with a stored artifact
- WHEN `report.generated` is written to audit
- THEN metadata holds session and report ids, template id and `version_no`, status transition, checksum, byte size, and timestamps only
- AND it contains no report body, scores, justifications, PDF bytes, storage keys, or tokens

## Non-goals

- No per-step report events: downloads are not audited as separate events (`report.downloaded` does not exist).
- No PDF bytes, storage keys, or internal paths in any audit metadata; the deny-list is not weakened.

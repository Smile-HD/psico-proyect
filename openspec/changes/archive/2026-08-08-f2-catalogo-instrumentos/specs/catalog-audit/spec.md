# Catalog Audit Specification

## Purpose

The four catalog audit events (D4): `instrument.draft_created`, `instrument.draft_updated`, `instrument.published`, and `instrument.archived`, with aggregate-only metadata that never contains item content, plus the idempotency interplay that prevents duplicate audit on replays. The event catalog amendment is mirrored in the `specs/audit-consent/spec.md` delta in this change.

## Requirements

### Requirement: Catalog Audit Events

The system MUST record catalog events in the append-only `audit_log` per the ratified audit-consent spec:

- `instrument.draft_created` — on successful creation of an instrument or draft version.
- `instrument.draft_updated` — on an explicit successful save of a draft. It MUST NOT be emitted for every unsaved field change or internal persistence operation.
- `instrument.published` — on successful draft-to-published transition; this remains the canonical publication event.
- `instrument.archived` — on successful published-to-archived transition.

#### Scenario: Draft creation audited

- GIVEN a psicólogo creates a synthetic instrument
- WHEN the creation succeeds
- THEN `instrument.draft_created` is recorded with the instrument and version identifiers

#### Scenario: Explicit save only

- GIVEN an open draft editor making several field changes
- WHEN the user triggers two explicit successful saves
- THEN exactly two `instrument.draft_updated` events are recorded
- AND unsaved keystrokes produce no audit events

#### Scenario: Publish and archive events

- GIVEN a valid draft
- WHEN an `admin` publishes it and later a `psicólogo` archives it
- THEN `instrument.published` and then `instrument.archived` are recorded in order

### Requirement: Aggregate-only Metadata

Catalog audit metadata MUST be limited to safe metadata: actor user id and role snapshot, `instrument_id`, `instrument_version_id`, `version_no`, status transition, and aggregate counts (for example number of scales, items, and response options). It MUST NOT contain item text, response-option keys or values, raw responses, tokens, PII, or other denied content, per the ratified audit deny-list.

#### Scenario: Publication metadata is content-free

- GIVEN a published synthetic version with 2 scales, 10 items, and 50 response options
- WHEN the `instrument.published` audit row is inspected
- THEN metadata contains ids, `version_no`, transition, and counts 2/10/50
- AND it contains no item text and no option keys or values

#### Scenario: Deny-list enforced for catalog events

- GIVEN any catalog audit event
- WHEN its metadata is scanned against the deny-list
- THEN it contains no item content, responses, tokens, or PII

### Requirement: Idempotent Audit Emission

Audit emission MUST be part of the idempotent mutation transaction: a replayed request with the same `Idempotency-Key` MUST NOT duplicate audit events. Failed or rejected mutations MUST NOT emit the corresponding success event.

#### Scenario: Replay does not duplicate audit

- GIVEN a publish that succeeded with `Idempotency-Key: k`
- WHEN the same request is retried with the same key
- THEN the audit log contains exactly one `instrument.published` row for that transition

#### Scenario: Failed save not audited as updated

- GIVEN a draft save that fails validation
- WHEN the save is attempted
- THEN no `instrument.draft_updated` event is recorded

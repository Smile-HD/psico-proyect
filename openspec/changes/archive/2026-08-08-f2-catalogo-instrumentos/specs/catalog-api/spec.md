# Catalog API Specification

## Purpose

The F2 endpoint surface built on F1 conventions (single error envelope, `require_roles` guards, `Idempotency-Key`): published-version read, protected draft administration, publish, and archive operations; the evaluator read payload contract; stable error cases; and the F3 session handoff contract. Exact URL nesting and DTO names are design-phase decisions; this spec fixes behavior.

**Related amendments in this change:** idempotency implementation obligations are recorded in the amended `specs/contracts/spec.md` delta; role guards are defined in `specs/catalog-permissions/spec.md` and the amended `specs/identity-auth/spec.md` delta.

## Requirements

### Requirement: Published Version Read

Authenticated `admin`, `psicólogo`, and `evaluado` MUST be able to request one published version by `instrument_version_id` (optionally with its instrument key). Draft and archived versions MUST NOT be exposed through this endpoint. A request for a draft, archived, or missing `instrument_version_id` MUST return the stable `NOT_FOUND` envelope and MUST NOT leak whether the version exists or what its status is.

#### Scenario: Evaluado reads a published version

- GIVEN an authenticated `evaluado` user and a published synthetic version `TP-S-01:v2`
- WHEN the user requests the version by `instrument_version_id`
- THEN the response is 200 with the published read payload

#### Scenario: Draft id does not leak existence

- GIVEN a draft version id known only to the editor
- WHEN an `evaluado` user requests that id
- THEN the response is the stable `NOT_FOUND` envelope
- AND the response reveals no status or draft existence

#### Scenario: Archived version not offered

- GIVEN an archived version id
- WHEN any authenticated role requests it through the read endpoint
- THEN the response is `NOT_FOUND`
- AND the archived version is not presented as a new catalog choice

### Requirement: Evaluator Read Payload

The published read payload MUST include everything required to render a session: the complete ordered hierarchy (scales, items, response options), `locale`, Spanish labels, item `required` flags, and stable item and response-option identifiers for submitting responses. Response-option labels MUST be included: this is an orientation instrument without right/wrong answers, so labels are render content. The payload MUST NOT include response-option numeric values, answer keys or right-answer semantics, scoring rules, hidden internal notes, or any item content not intended for that version.

#### Scenario: Payload renders a session

- GIVEN the published read payload for a synthetic version
- WHEN F3 renders a session from it
- THEN ordered scales, items, and five labeled options per item are present with stable identifiers and required flags
- AND the payload contains no numeric option values

#### Scenario: No scoring or answer-key fields

- GIVEN the published read payload
- WHEN its fields are enumerated
- THEN there are no answer keys, right-answer markers, scoring rules, or internal notes

### Requirement: Protected Draft Administration

Protected administration endpoints MUST allow `admin` and `psicólogo` to list and inspect authorized catalog content, create instruments and draft versions, and save draft hierarchy content. Draft administration MUST be a surface separate from the published read. `evaluado` MUST NOT reach draft administration: any attempt MUST return `FORBIDDEN` with the stable envelope and be audited as `auth.denied`.

#### Scenario: Psicólogo manages a draft

- GIVEN an authenticated `psicólogo` user
- WHEN the user creates a synthetic instrument draft and saves its scales, items, and options
- THEN the draft is persisted with a draft status
- AND no published content is affected

#### Scenario: Evaluado denied administration

- GIVEN an authenticated `evaluado` user
- WHEN the user calls a draft administration endpoint
- THEN the response is `FORBIDDEN` with the stable envelope
- AND `auth.denied` is recorded in the audit log

### Requirement: Publish Operation

Publication MUST be an administrator-only operation available to `admin`. It MUST validate the full hierarchy before any change; on failure it MUST return the stable error envelope with `VALIDATION_ERROR` and MUST leave the version `draft` with no partial transition. On success it MUST assign the stable `instrument_version_id`, status `published`, publication timestamp, immutability, and the agreed audit metadata, and freeze the complete hierarchy.

#### Scenario: Invalid draft cannot be published

- GIVEN a draft with an empty scale
- WHEN an `admin` requests publication
- THEN the response is the stable envelope with `VALIDATION_ERROR`
- AND the version remains `draft`

#### Scenario: Valid draft publishes atomically

- GIVEN a fully valid synthetic draft
- WHEN an `admin` requests publication
- THEN the version becomes `published` and immutable
- AND the publication is audited as `instrument.published`

### Requirement: Archive Operation

`psicólogo` and `admin` MUST be able to archive a published version. Archiving MUST NOT rewrite or invalidate historical session references, and the archived version MUST remain immutable and addressable by identifier. An archive attempt on a non-published version MUST fail with `CONFLICT`.

#### Scenario: Published version archived

- GIVEN a published synthetic version with existing sessions
- WHEN a `psicólogo` archives it
- THEN its status becomes `archived`
- AND existing sessions still resolve against the same `instrument_version_id`
- AND `instrument.archived` is recorded

#### Scenario: Archive of draft fails

- GIVEN a draft version
- WHEN an archive operation targets it
- THEN the response is `CONFLICT`
- AND the version remains `draft`

### Requirement: Idempotency on All Mutations

Every F2 mutating endpoint (`POST`, `PUT`, `PATCH`: create instrument, create draft version, save draft hierarchy, publish, archive) MUST require an `Idempotency-Key` header. Repeating a request with the same key for the same resource MUST replay the original result without duplicating data side effects or audit events; a new key MUST start an independent operation. When the same key is reused with a materially different request body, the system MUST NOT create a second side effect; the implementation MUST either replay the stored original result or reject with `CONFLICT` (the exact choice is a design decision per the proposal open questions). This implements the ratified contracts Idempotent Mutations requirement, which F1 ratified but did not implement.

#### Scenario: Retried publish replays

- GIVEN a publish request that succeeded with `Idempotency-Key: k`
- WHEN the client retries the same request with the same key
- THEN the response repeats the original result
- AND no second transition, version row, or audit event is created

#### Scenario: Distinct keys are independent

- GIVEN two create requests with different `Idempotency-Key` values
- WHEN both are executed
- THEN two independent instruments are created, each audited exactly once

#### Scenario: Same key, different body is safe

- GIVEN a stored idempotency result for `Idempotency-Key: k` with one request body
- WHEN the same key arrives with a materially different body
- THEN no second side effect is created
- AND the request either replays the stored result or fails with `CONFLICT`

### Requirement: Error Contract

All catalog errors MUST use the F1 single error envelope. Catalog error codes MUST be: `VALIDATION_ERROR` for invalid hierarchy or failed publication validation; `FORBIDDEN` for role failures; `NOT_FOUND` for draft/archived/missing reads through the evaluator-facing endpoint (no existence leak); `CONFLICT` for mutation of an immutable version, archive of a non-published version, same-key-different-body collisions, and seed-reset preflight conflicts; `UNAUTHORIZED` and `INTERNAL_ERROR` per the ratified contracts spec.

#### Scenario: Stable envelope on catalog failure

- GIVEN a draft save that violates an order rule
- WHEN the save is attempted
- THEN the response contains exactly one `error` object with code `VALIDATION_ERROR`, message, `request_id`, and details

### Requirement: F3 Session Handoff Contract

The F2 catalog contract MUST define the published-only availability rule for session creation: a session MUST NOT start against a non-published `instrument_version_id`. The contract MUST document the stable error cases for draft, archived, missing, and invalid versions. Enforcement of the session-creation gate is explicitly owned by F3; F2 MUST hand off the rule and error cases without implementing or silently changing F3 session behavior.

#### Scenario: Contract specifies the session gate

- GIVEN the F2 handoff contract and a draft `instrument_version_id`
- WHEN F3 implements session creation per the contract
- THEN session creation rejects the non-published id with the documented stable error
- AND F3's behavior is verified against the contract, not against an F2 session implementation

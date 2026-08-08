# Catalog Model Specification

## Purpose

The four-level catalog hierarchy `instrument → scale → item → response_option` introduced by F2 (D3), with the MVP response type fixed to `likert_1_5`, write/publish-time validation rules, locale/adaptation/availability semantics, and the synthetic/research-only marking on all catalog content.

**Related amendments in this change:** the instruments family of the ratified data-schema spec is amended to the four-level model in `specs/data-schema/spec.md`; the id space and error conventions remain per the ratified contracts spec.

## Requirements

### Requirement: Four-Level Hierarchy

The catalog MUST model the hierarchy `instrument → instrument_version → scale → item → response_option`. An instrument MUST own one or more ordered versions; each version MUST own one or more scales; each scale MUST own one or more items; each item MUST own exactly five response options.

- `instrument`: stable UUID identifier (UUID4 for runtime rows, deterministic UUID5 for seed rows), unique human-readable `key`, `title`, `description`, `synthetic`, and `source`. The MVP MUST NOT include `institution_id`; institution ownership is deferred.
- `instrument_version`: `instrument_version_id` (stable UUID primary identifier exposed to downstream consumers), parent `instrument_id`, unique `version_no` within the instrument, `status`, creation/publication/archive timestamps as applicable, `is_immutable`, `synthetic`, `source`.
- `scale`: stable identifier, parent `instrument_version_id`, synthetic localized display name/label, unique positive `order` within the version. A scale MUST belong to exactly one version; cross-version or cross-instrument attachment is invalid.
- `item`: stable identifier, parent scale identifier, synthetic item text, `locale`, positive `order` within its scale, and a `required` flag. An item MUST belong to exactly one scale and therefore exactly one version.
- `response_option`: stable identifier, parent item identifier, synthetic localized label, positive display `order`, and a fixed server-side Likert value in the inclusive range 1–5.

#### Scenario: Runtime vs seed id space

- GIVEN a runtime instrument created through the administration surface and the seeded instrument `TP-S-01`
- WHEN inspecting their ids
- THEN the runtime id is UUID4 and the seed id is UUID5 under the `psico-seed` namespace

#### Scenario: Scale belongs to exactly one version

- GIVEN a draft version `v2` of a synthetic instrument and a scale already attached to `v1`
- WHEN the scale is attached to `v2` as well
- THEN the write is rejected with a `VALIDATION_ERROR`

### Requirement: MVP Response Type likert_1_5

Every F2 instrument version MUST have `response_type` fixed to `likert_1_5`. Any other response type MUST be rejected as unsupported. Each item MUST have exactly five response options whose server-side values are exactly 1, 2, 3, 4, and 5, with exactly one option per value. This MUST preserve compatibility with the existing `responses.value BETWEEN 1 AND 5` invariant and give F4 an exact item-to-scale-to-option relationship.

#### Scenario: Duplicate option value rejected

- GIVEN a draft item with two response options both carrying server-side value 3
- WHEN the draft is saved
- THEN the save fails with `VALIDATION_ERROR` and no option row is persisted

#### Scenario: Incomplete option set rejected

- GIVEN a draft item with only four response options
- WHEN the draft is saved
- THEN the save fails with `VALIDATION_ERROR`

#### Scenario: Unsupported response type rejected

- GIVEN a draft version declared with `response_type` other than `likert_1_5`
- WHEN the draft is saved
- THEN the operation fails with `VALIDATION_ERROR`

### Requirement: Validation Rules

A version MUST be publishable only when it contains at least one scale, each scale contains at least one item, and each item contains exactly five response options. Orders MUST be positive, unique within their parent, and contiguous from 1 for deterministic rendering. Parent membership and version consistency MUST be validated both at write time and at publish time. The `required` flag is explicit item metadata and MUST be honored by F3 when it validates session completion.

#### Scenario: Empty scale blocks publication

- GIVEN a draft whose second scale has no items
- WHEN an administrator requests publication
- THEN publication fails with the stable error envelope and `VALIDATION_ERROR`
- AND the version remains `draft` with no partial transition

#### Scenario: Non-contiguous order rejected at save

- GIVEN a scale whose items are ordered 1, 3, 4
- WHEN the draft is saved
- THEN the save fails with `VALIDATION_ERROR`
- AND the version keeps its previous valid state

### Requirement: Locale, Adaptation and Availability

Human-facing labels and item text MUST be Spanish (`locale=es`) in the MVP; contract tokens and error codes MUST remain English. Adaptation MUST be descriptive metadata only: it MUST NOT dynamically alter the published item set or branch a session; adaptive behavior is deferred. Availability is status-based in the MVP: only `published` versions are available through the evaluator-facing read endpoint; `archived` versions remain addressable for historical references but MUST NOT be offered as new catalog choices.

#### Scenario: Spanish content, English contract

- GIVEN a published synthetic instrument version
- WHEN the read payload is inspected
- THEN item texts and option labels are Spanish (`locale=es`)
- AND error codes and contract tokens are English

#### Scenario: Adaptation metadata does not alter rendering

- GIVEN a published version carrying descriptive adaptation metadata
- WHEN a session renders the version
- THEN the rendered item set and options are exactly the published set
- AND the adaptation metadata does not branch or remove content

### Requirement: Synthetic Research-only Marking

All catalog content — seed and runtime — MUST be synthetic and marked `synthetic`/`research-only`. Runtime instruments, versions, scales, items, and response options created through the administration surface MUST carry `synthetic=true` and a runtime `source`. No catalog content MAY assert real psychometric or normative claims.

#### Scenario: Runtime draft marked synthetic

- GIVEN a psicólogo creates a new instrument draft from the UI
- WHEN the draft rows are inspected
- THEN every row has `synthetic=true` and `source` indicating runtime authorship

### Requirement: Server-side Value Secrecy

The server-side numeric mapping of response options (values 1–5) MUST be exposed only through the non-public fixture/internal contract used by F4, and MUST NOT appear in the evaluator-facing read payload. Response-option labels are public render content, but the numeric value and any answer-key semantics are not.

#### Scenario: Values only in the internal contract

- GIVEN a published version with five options per item
- WHEN the internal fixture contract and the evaluator read payload are compared
- THEN the internal contract exposes the 1–5 mapping for F4
- AND the evaluator payload contains no numeric option values

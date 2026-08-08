# Catalog Lifecycle Specification

## Purpose

The catalog lifecycle: the constrained status machine `draft → published → archived`, immutability of published and archived versions, coexistence of multiple published versions, the exact `instrument_version_id` semantics, and the D1 seed coexistence rule (seed content is reference-only and `seed --reset` runs an atomic dependency preflight).

**Related amendments in this change:** the reset preflight behavior is mirrored in the amended `specs/synthetic-seed/spec.md` delta; version status constraints are part of the `specs/data-schema/spec.md` delta.

## Requirements

### Requirement: Constrained Status Machine

The status of an instrument version MUST be exactly one of `draft`, `published`, or `archived`; any other value MUST be rejected. The only allowed transitions are `draft → published` (administrator-only, after all validation passes) and `published → archived` (explicit archive transition available to `psicólogo` and `admin`). There MUST be no unarchive transition in the MVP and no direct `draft → archived` transition; a replacement for an archived version is a new draft/version.

#### Scenario: Free-text status rejected

- GIVEN a version whose status value is not one of `draft`, `published`, `archived`
- WHEN the row is written
- THEN the write is rejected by the status constraint

#### Scenario: Direct draft-to-archived rejected

- GIVEN a `draft` version of a synthetic instrument
- WHEN an archive operation is attempted on it
- THEN the operation fails with `CONFLICT`
- AND the version remains `draft`

#### Scenario: No unarchive transition

- GIVEN an `archived` version
- WHEN a publish or unarchive operation targets it
- THEN the operation fails with the stable error envelope
- AND the version remains `archived`

### Requirement: Immutability of Published and Archived Versions

A published version MUST NOT be updated, deleted, or replaced in place; it MUST retain its identifier, timestamps, hierarchy, and audit history. An archived version MUST remain immutable and MUST NOT be physically deleted by normal catalog operations. Editing a published instrument MUST always create or update a draft version and MUST never change the published version.

#### Scenario: In-place edit of published version rejected

- GIVEN a published version `TP-S-01:v2` of a synthetic instrument
- WHEN a mutation attempts to change one of its items
- THEN the mutation fails with `CONFLICT`
- AND the published hierarchy is byte-identical after the attempt

#### Scenario: Archived version retained

- GIVEN an archived version
- WHEN catalog operations run normally
- THEN the version, its hierarchy, and its audit history remain present and readable by identifier

### Requirement: Published Version Coexistence

Multiple published versions of the same instrument MAY coexist. Each MUST have a distinct `instrument_version_id` and a distinct `version_no`, and each MUST be queryable independently. Each coexisting published version MUST be session-startable under the F3 published-only rule. Creating a change to a published version MUST create a new draft with a new `version_no` rather than editing the published row; `version_no` allocation MUST remain unique per instrument even under concurrent administration (the exact concurrency mechanism is a design decision).

#### Scenario: Two published versions coexist

- GIVEN a synthetic instrument with published `v1` and published `v2`
- WHEN both versions are requested by `instrument_version_id`
- THEN both return the published payload independently
- AND each can start a session under the F3 published-only rule

#### Scenario: Change to published spawns a new draft

- GIVEN published version `v1` of a synthetic instrument
- WHEN an editor creates a change from it
- THEN a new draft with a new `instrument_version_id` and `version_no` 2 is created
- AND the published `v1` rows are unchanged

### Requirement: instrument_version_id Semantics

`instrument_version_id` MUST identify the exact immutable version, not merely the instrument or a displayable version number. When F3 creates a session, it MUST copy this identifier into the session and keep it unchanged for the session lifetime; responses and downstream scoring fixtures MUST resolve against that same version. A new catalog version MUST always receive a new identifier. No session MAY be re-pointed to another version as a side effect of editing, publishing, or archiving. Archiving MUST NOT rewrite or invalidate historical session references; whether a new session may use an archived version is denied by the F3 session gate.

#### Scenario: Archive does not invalidate sessions

- GIVEN a session pinned to published version `v1`
- WHEN `v1` is archived
- THEN the session still resolves against the original `instrument_version_id`
- AND the pinned identifier is unchanged

#### Scenario: New version does not re-point sessions

- GIVEN a session pinned to `v1` and a new published `v2` of the same instrument
- WHEN `v2` is published
- THEN the session continues to reference `v1`

### Requirement: Seed Read-only and Coexistence (D1)

`TP-S-01:v1` MUST be read-only in all F2 workflows. The F2 UI MUST NOT edit it, MUST NOT create a new version under the seed instrument, and MUST NOT treat its seed content as runtime-authorable content. Runtime instruments and versions MUST use their own runtime rows and MUST NOT create foreign-key dependencies from runtime catalog content to seed-owned instrument, version, or item rows. Runtime creation that uses a seed key or a seed entity as an editable parent MUST be rejected.

#### Scenario: Seed instrument is not authorable

- GIVEN the seeded instrument `TP-S-01` with its immutable version `v1`
- WHEN an editor attempts to save a draft under the seed instrument
- THEN the operation is rejected
- AND no runtime version row references seed-owned rows

#### Scenario: Runtime instrument is an independent root

- GIVEN a runtime synthetic instrument created by a psicólogo
- WHEN its rows are inspected
- THEN it has its own runtime instrument, version, scale, item, and option rows
- AND none of them reference seed-owned catalog rows

### Requirement: Atomic Seed Reset Preflight (D1)

`seed --reset` MUST perform an atomic dependency preflight before deleting anything. If any non-seed row references a seed-owned catalog row, reset MUST stop with a stable `CONFLICT` and make no deletion; it MUST never delete a seed parent and leave a runtime foreign key broken. Under the normal F2 rule, runtime rows are separate roots, so reset MUST be able to recreate the seed graph without affecting runtime instruments or versions.

#### Scenario: Reset coexists with runtime content

- GIVEN a seeded database plus runtime instruments and versions with no cross-ownership
- WHEN `seed --reset` runs
- THEN the seed graph is recreated
- AND all runtime instruments and versions remain intact

#### Scenario: Cross-ownership stops reset atomically

- GIVEN a non-seed row that references a seed-owned catalog row
- WHEN `seed --reset` runs
- THEN reset stops with a stable `CONFLICT`
- AND no deletion is performed

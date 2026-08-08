# Delta for Synthetic Seed

## MODIFIED Requirements

### Requirement: --reset Scoped to Seed-owned Rows

`--reset` MUST delete only seed-owned rows, in FK order, then re-seed. It MUST NOT touch non-seed data. Before deleting anything, `--reset` MUST run an atomic dependency preflight: if any non-seed row references a seed-owned catalog row, reset MUST stop with a stable `CONFLICT` and make no deletion; it MUST never delete a seed parent and leave a runtime foreign key broken. Under the F2 coexistence rule, runtime catalog rows are separate roots and never depend on seed-owned catalog rows, so the normal reset recreates the seed graph without affecting runtime instruments or versions.

(Previously: `--reset` deleted seed-owned rows in FK order with no dependency preflight, leaving a foreign-key risk when runtime content referenced seed rows.)
(Reason: D1 coexistence rule — seed content is reference-only and runtime content must not be orphaned by a reset.)
(Migration: `seed --reset` gains the atomic preflight step; existing seed sessions, responses, and reference set rows remain seed-owned and are reset as before. Runtime catalog content created by F2 is unaffected as long as it obeys the no-cross-ownership rule.)

#### Scenario: Scoped reset

- GIVEN seed-owned rows plus one manually created non-seed row
- WHEN `python -m app.seed --reset` runs
- THEN only seed-owned rows are removed and re-created
- AND the non-seed row remains intact

#### Scenario: Reset coexists with runtime catalog content

- GIVEN seed-owned rows plus runtime instruments and versions with no cross-ownership
- WHEN `python -m app.seed --reset` runs
- THEN the seed graph is recreated
- AND all runtime instruments and versions remain intact

#### Scenario: Cross-ownership aborts atomically

- GIVEN a non-seed row that references a seed-owned catalog row
- WHEN `python -m app.seed --reset` runs
- THEN reset stops with a stable `CONFLICT`
- AND no seed row is deleted

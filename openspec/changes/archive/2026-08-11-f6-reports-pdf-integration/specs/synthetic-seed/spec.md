# Delta for Synthetic Seed

## MODIFIED Requirements

### Requirement: --reset Scoped to Seed-owned Rows

`--reset` MUST delete only seed-owned rows, in FK order, then re-seed. It MUST NOT touch non-seed data. Before deleting anything, `--reset` MUST run an atomic dependency preflight: if any non-seed row references a seed-owned catalog row, reset MUST stop with a stable `CONFLICT` and make no deletion; it MUST never delete a seed parent and leave a runtime foreign key broken. Under the F2 coexistence rule, runtime catalog rows are separate roots and never depend on seed-owned catalog rows, so the normal reset recreates the seed graph without affecting runtime instruments or versions. The preflight MUST also cover `score_runs` and `reports`: a runtime score run or report referencing a seed-owned session, reference set, or template MUST stop reset with the stable `seed_reset_dependency_conflict` `CONFLICT` and zero deletions. `--reset` MUST NEVER delete runtime `score_runs`, runtime `reports`, or their artifacts; seeded template rows are recreated without touching any runtime row.

(Previously: the preflight covered catalog, sessions, references, and recommendation dependencies only; F6 extends it to `score_runs` and `reports` and ratifies that runtime reporting rows are never deleted by reset.)

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
- THEN the reset stops with a stable `CONFLICT`
- AND no deletion is made

#### Scenario: Runtime report over seed session aborts atomically

- GIVEN a runtime `score_run` or `reports` row referencing a seed-owned session, reference set, or template
- WHEN `python -m app.seed --reset` runs
- THEN the reset stops with `CONFLICT`/`seed_reset_dependency_conflict`
- AND no deletion is made, including the runtime report row

#### Scenario: Runtime reporting rows survive reset

- GIVEN a runtime report and score run referencing only runtime-owned rows
- WHEN `python -m app.seed --reset` runs
- THEN the seed graph is recreated
- AND the runtime report and score run rows and their artifacts remain intact

## ADDED Requirements

### Requirement: Report Template Seed Content

Seed MUST create the default template with stable key `informe-basico` (UUID5 under namespace `psico-seed`, key `report-template:informe-basico`), `synthetic=true` / `source='seed'`, status `published`, version 1, and the ratified Spanish report body as data. The template MUST join `SEED_TABLES`, the seed manifest counts, the checksum, the reset scope, and the reset preflight. `reports` and `score_runs` MUST NEVER be seeded (runtime-only). The seed MUST remain idempotent and MUST bump `SEED_VERSION`. Seed-template recreation during `--reset` MUST never create, update, or delete runtime template or report rows.

#### Scenario: Default template seeded

- GIVEN a completed seed
- WHEN counting `report_templates` and inspecting the `informe-basico` row
- THEN exactly one template exists with key `informe-basico`, status `published`, version 1, `synthetic=true`, `source='seed'`, and a UUID5 id

#### Scenario: Reports and runs are never seeded

- GIVEN a completed seed
- WHEN counting `reports` and `score_runs`
- THEN both counts are 0
- AND all seeded template rows are flagged synthetic with `source='seed'`

#### Scenario: Manifest covers reporting rows

- GIVEN a completed seed
- WHEN reading the latest `seed_manifest`
- THEN it contains the `report_templates` count
- AND the checksum reflects the seeded template

#### Scenario: Reseed is idempotent and reset-safe

- GIVEN a seeded database
- WHEN seed runs a second time, then `--reset` runs
- THEN template ids and counts are unchanged and a new manifest run row is appended
- AND the template is recreated with the same UUID5 id
- AND no runtime report or template row is created, updated, or deleted

## Non-goals

- No runtime reports or score runs seeded; no template authoring or `is_default` admin flag.
- No `--reset` cleanup of runtime artifacts: retention stays indefinite and reset never touches runtime rows.

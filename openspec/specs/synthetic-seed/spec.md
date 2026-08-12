# Synthetic Seed Specification

## Purpose

Idempotent, deterministic, fully synthetic seed producing visible data and a per-run manifest. All data is research-only; nothing references real UAGRM norms or people.

## Requirements

### Requirement: Idempotent Deterministic Seed

Seed rows MUST use deterministic UUID5 ids (namespace `psico-seed` + stable key) and upsert semantics. Running seed twice MUST produce identical ids and row counts.

#### Scenario: Seed twice, identical counts

- GIVEN a seeded database
- WHEN seed runs a second time
- THEN per-table row counts are unchanged
- AND a new `seed_manifest` run row is appended

#### Scenario: Deterministic ids

- GIVEN two separate seed runs
- WHEN comparing seeded ids
- THEN the ids are identical across runs

### Requirement: Seed Content

Seed MUST create instrument `TP-S-01` with 20 items (5 scales × 4 items, 5-point Likert, version 1 immutable); 1 invented reference set `RS-TP-S-01` with `reference_status=synthetic`, `use=research-only`, and `norm_note` "NO es una norma UAGRM. Datos inventados para desarrollo."; 30 JSON profiles (`evaluado_01..30`) loaded into sessions (30), responses (600), and consent grants. Every seeded row that has a synthetic column MUST set `synthetic=true` / `source='seed'`.

#### Scenario: Item and response math

- GIVEN a completed seed
- WHEN counting items by scale
- THEN 5 scales × 4 items = 20 items
- AND 30 profiles yield 30 sessions with 600 responses

#### Scenario: Research-only marking

- GIVEN seeded reference data
- WHEN reading `RS-TP-S-01`
- THEN it is flagged synthetic/research-only
- AND the norm_note "NO es una norma UAGRM. Datos inventados para desarrollo." is present

### Requirement: Seed Manifest

Each run MUST write `seed_manifest` with `seed_version`, per-table counts, a checksum, and `executed_at`.

#### Scenario: Manifest records the run

- GIVEN a completed seed run
- WHEN reading the latest manifest
- THEN counts match actual table rows
- AND seed_version, checksum, and executed_at are present

### Requirement: --reset Scoped to Seed-owned Rows

`--reset` MUST delete only seed-owned rows, in FK order, then re-seed. It MUST NOT touch non-seed data. Before deleting anything, `--reset` MUST run an atomic dependency preflight: if any non-seed row references a seed-owned catalog row, reset MUST stop with a stable `CONFLICT` and make no deletion; it MUST never delete a seed parent and leave a runtime foreign key broken. Under the F2 coexistence rule, runtime catalog rows are separate roots and never depend on seed-owned catalog rows, so the normal reset recreates the seed graph without affecting runtime instruments or versions. The preflight MUST also cover `score_runs` and `reports`: a runtime score run or report referencing a seed-owned session, reference set, or template MUST stop reset with the stable `seed_reset_dependency_conflict` `CONFLICT` and zero deletions. `--reset` MUST NEVER delete runtime `score_runs`, runtime `reports`, or their artifacts; seeded template rows are recreated without touching any runtime row.

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

### Requirement: Reference Set Value Shape

Reference set `RS-TP-S-01` MUST contain exactly 30 `reference_values` rows, all synthetic/research-only: 10 per-scale rows (one `mean` and one `sd` per scale, keyed by the scale label matching `items.json` labels exactly) and 20 `overall` rows mapping raw 1–20 to percentile/T/eneatype. The `norm_note` MUST be the pinned research-only disclaimer verbatim. F4 consumes this shape read-only; the seed MUST NOT change.

#### Scenario: Seeded reference rows match the contract

- GIVEN a completed seed
- WHEN counting `reference_values` for `RS-TP-S-01`
- THEN 30 rows exist: 10 per-scale mean/sd plus 20 overall rows

#### Scenario: Scale labels are the join key

- GIVEN the seeded per-scale rows
- WHEN comparing their `scale` values with `items.json` labels
- THEN they match exactly

### Requirement: Recommendation Seed Content

Seed MUST create 4–6 invented synthetic programs under `faculty:dev` (institution `institution:dev`), each with a distinct `code` and a stable key in the `program:<slug>` namespace, plus active `recommendation_rules` rows (keys `rule:<program-key>:<n>`, `is_active=true`) referencing the exact scale labels `Intereses`, `Aptitud verbal`, `Aptitud numérica`, `Razonamiento abstracto`, `Valores/preferencias`, and/or `overall`. Every seeded row MUST set `synthetic=true` / `source='seed'`. `recommendation_results` MUST NEVER be seeded (runtime-only). The seed MUST remain idempotent, MUST include the recommendation tables in manifest counts and `--reset` scope, and MUST bump `SEED_VERSION`. `--reset` MUST remove only seed-owned recommendation rows; runtime results referencing seed rules trigger the existing atomic preflight `CONFLICT` with no deletion.

#### Scenario: Programs and rules seeded

- GIVEN a completed seed
- WHEN counting `programs` under `faculty:dev` and `recommendation_rules` rows
- THEN 4–6 invented programs exist alongside `program:dev`
- AND every program has at least one active rule whose `scale` matches a seeded scale label or `overall`

#### Scenario: Results are never seeded

- GIVEN a completed seed
- WHEN counting `recommendation_results`
- THEN the count is 0
- AND all seeded recommendation rows are flagged synthetic with `source='seed'`

#### Scenario: Reseed is idempotent

- GIVEN a seeded database
- WHEN seed runs a second time
- THEN program and rule ids and counts are unchanged
- AND a new `seed_manifest` run row is appended

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


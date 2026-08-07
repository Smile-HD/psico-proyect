# Delta Spec: synthetic-seed

# Synthetic Seed Specification

## Purpose

Idempotent, deterministic, fully synthetic seed producing visible data and a per-run manifest. All data is research-only; nothing references real UAGRM norms or people.

## ADDED Requirements

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

`--reset` MUST delete only seed-owned rows, in FK order, then re-seed. It MUST NOT touch non-seed data.

#### Scenario: Scoped reset

- GIVEN seed-owned rows plus one manually created non-seed row
- WHEN `python -m app.seed --reset` runs
- THEN only seed-owned rows are removed and re-created
- AND the non-seed row remains intact


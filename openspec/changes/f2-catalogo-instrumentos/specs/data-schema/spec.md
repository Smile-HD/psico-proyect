# Delta for Data Schema

## MODIFIED Requirements

### Requirement: Nine Table Families

The schema MUST define: identity (`users`, `roles`, `user_roles`), institutions (`institutions`, `campuses`, `faculties`, `programs`), instruments (`instruments`, `instrument_versions`, `scales`, `items`, `response_options`), sessions (`sessions`, `responses`), scoring (`reference_sets`, `reference_values`, `score_runs`), recommendation (`recommendation_rules`, `recommendation_results`), reporting (`reports`, `report_templates`), audit (`audit_log`), consent (`consent_versions`, `consent_grants`), plus `seed_manifest`.

The instruments family is amended to the four-level model per D3: the F1 shape (`instruments`, `instrument_versions`, `instrument_items` with a denormalized `scale` string) is superseded by `instrument → instrument_version → scale → item → response_option`. Exact physical table/column names for `scale`, `item`, and `response_option` are design-phase decisions; the logical entities and their relationships are binding.

(Previously: the instruments family was the three-table shape `instruments`, `instrument_versions`, `instrument_items`, with `scale` as a denormalized string column and `scale_order` capped at 5 by CHECK.)

#### Scenario: Fresh upgrade creates the four-level family

- GIVEN an empty database
- WHEN `alembic upgrade head` runs
- THEN all nine families exist with the four-level instruments family: versions own scales, scales own items, and items own five response options

#### Scenario: Seeded instrument survives the amendment

- GIVEN a database migrated and seeded after the F2 migration
- WHEN inspecting `TP-S-01:v1`
- THEN the instrument, its version, 20 items, 5 scales, and 100 response options exist
- AND the seed item ids and version id are identical to their pre-migration values

### Requirement: Linear Alembic Chain

Migrations MUST be schema-only, generated from SQLAlchemy models, and arranged in ONE linear `versions/` chain. `alembic upgrade head` MUST be idempotent. F2 MUST append exactly ONE new schema-only migration to the existing F1 chain (0001–0004); that migration MUST create the `scale`, `item`, and `response_option` entities, backfill them from existing seed rows, preserve seed identity (deterministic UUID5 ids and stable keys) and existing foreign-key semantics (including `responses.item_id` and session references to `TP-S-01:v1`), and constrain version status to `draft`/`published`/`archived`.

(Previously: the chain was 0001–0004 and the instruments family had no migration for a four-level model.)

#### Scenario: Idempotent upgrade

- GIVEN a database already at head
- WHEN `alembic upgrade head` runs again
- THEN no migration executes and no error is raised

#### Scenario: Linear history retained

- GIVEN the migration history after F2
- WHEN listing `versions/`
- THEN the chain has exactly one new migration appended and no branches or merge points

#### Scenario: Existing references still resolve after backfill

- GIVEN the seeded sessions and responses referencing `TP-S-01:v1` and its items
- WHEN the F2 migration and backfill complete
- THEN every pre-existing reference still resolves to the same seed-owned rows

## ADDED Requirements

### Requirement: Four-level Family Integrity

The instruments family MUST enforce at schema level: version status constrained to exactly `draft`, `published`, or `archived`; the immutability CHECK `(status <> 'published') OR is_immutable` preserved and extended so archived versions are immutable; `version_no` unique per instrument; scale order unique within its version; item order unique within its scale; response-option value unique within its item and constrained to the inclusive range 1–5; and the foreign-key chain `instrument_version → scale → item → response_option`. The existing `responses.value BETWEEN 1 AND 5` invariant MUST be preserved.

#### Scenario: Status constraint rejects free text

- GIVEN a version with an unconstrained status value
- WHEN the row is written
- THEN the status CHECK rejects it

#### Scenario: Option value range enforced

- GIVEN a response option with server-side value 6
- WHEN the row is written
- THEN the value CHECK rejects it
- AND values 1 through 5 are accepted

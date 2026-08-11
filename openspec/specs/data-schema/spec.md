# Data Schema Specification

## Purpose

Full nine-family relational schema with a linear, schema-only Alembic chain. Recommendation (F5) and reporting (F6) families are created empty-but-migrated.

## Requirements

### Requirement: Nine Table Families

The schema MUST define: identity (`users`, `roles`, `user_roles`), institutions (`institutions`, `campuses`, `faculties`, `programs`), instruments (`instruments`, `instrument_versions`, `scales`, `items`, `response_options`), sessions (`sessions`, `responses`), scoring (`reference_sets`, `reference_values`, `score_runs`), recommendation (`recommendation_rules`, `recommendation_results`), reporting (`reports`, `report_templates`), audit (`audit_log`), consent (`consent_versions`, `consent_grants`), plus `seed_manifest`.

The instruments family is the four-level model `instrument → instrument_version → scale → item → response_option`. Versions own scales, scales own items, and items own five response options. The F1 three-table shape with a denormalized `scale` string is superseded.

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

Migrations MUST be schema-only, generated from SQLAlchemy models, and arranged in ONE linear `versions/` chain. `alembic upgrade head` MUST be idempotent.

#### Scenario: Idempotent upgrade

- GIVEN a database already at head
- WHEN `alembic upgrade head` runs again
- THEN no migration executes and no error is raised

#### Scenario: Linear history

- GIVEN the migration history
- WHEN listing `versions/`
- THEN the chain has no branches or merge points

### Requirement: Empty-but-migrated F5/F6

The recommendation and reporting families MUST be created by migrations and MUST exist since migration 0003; F5 MUST NOT change the schema (no migration). After a full seed, `recommendation_rules` MUST be populated by the seed while `recommendation_results` (runtime-only), `reports`, and `report_templates` MUST contain zero rows.

#### Scenario: Recommendation rules populated, results and reports empty after seed

- GIVEN a fully migrated and seeded database
- WHEN counting rows in `recommendation_rules`, `recommendation_results`, `reports`, and `report_templates`
- THEN `recommendation_rules` count is greater than 0
- AND `recommendation_results`, `reports`, and `report_templates` are 0 while identity, instruments, sessions, audit, and consent are seeded

#### Scenario: Schema exists before seed

- GIVEN a database migrated but not seeded
- WHEN introspecting F5/F6 tables
- THEN all columns exist even though no data is present

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

### Requirement: Score Run Persistence Shape

The `score_runs` table MUST permit multiple runs per session: no unique constraint exists on `session_id`, and F4 MUST NOT add one (no migration in this change). A run row MUST carry `status` (`pending` default, transitioned to `completed`), `raw` JSONB, nullable `computed_at`, and, as a runtime row, `synthetic=False` and `source='runtime'`. The table MUST already exist since migration 0003; F4 MUST NOT change the schema.

#### Scenario: Multiple runs are schema-legal

- GIVEN two scoring triggers with different keys for one session
- WHEN both runs are persisted
- THEN two `score_runs` rows exist for that session

#### Scenario: Runtime flags on runs

- GIVEN a scoring run persisted by the results API
- WHEN the row is inspected
- THEN `synthetic` is false and `source` is `'runtime'`
- AND status is `completed` with a non-null `computed_at`

### Requirement: Recommendation Result Persistence Shape

The `recommendation_results` table MUST permit multiple generations per session: no unique constraint exists on `session_id`, and F5 MUST NOT add one (no migration in this change). A generation MUST persist one row per evaluated rule, each carrying `fit_score` `Numeric(5,2)`, `justification` Text, and, as a runtime row, `synthetic=False` and `source='runtime'`. The table MUST already exist since migration 0003; F5 MUST NOT change the schema.

#### Scenario: Multiple generations are schema-legal

- GIVEN two generation triggers with different keys for one session
- WHEN both generations are persisted
- THEN two sets of `recommendation_results` rows exist for that session

#### Scenario: Runtime flags on results

- GIVEN a generation persisted by the recommendations API
- WHEN a result row is inspected
- THEN `synthetic` is false and `source` is `'runtime'`
- AND `fit_score` and `justification` are present


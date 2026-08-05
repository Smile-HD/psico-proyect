# Data Schema Specification

## Purpose

Full nine-family relational schema with a linear, schema-only Alembic chain. Recommendation (F5) and reporting (F6) families are created empty-but-migrated.

## Requirements

### Requirement: Nine Table Families

The schema MUST define: identity (`users`, `roles`, `user_roles`), institutions (`institutions`, `campuses`, `faculties`, `programs`), instruments (`instruments`, `instrument_versions`, `instrument_items`), sessions (`sessions`, `responses`), scoring (`reference_sets`, `reference_values`, `score_runs`), recommendation (`recommendation_rules`, `recommendation_results`), reporting (`reports`, `report_templates`), audit (`audit_log`), consent (`consent_versions`, `consent_grants`), plus `seed_manifest`.

#### Scenario: Fresh upgrade creates all families

- GIVEN an empty database
- WHEN `alembic upgrade head` runs
- THEN all nine families plus `seed_manifest` exist with the expected columns

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

The recommendation and reporting families MUST be created by migrations but MUST contain zero rows in F1.

#### Scenario: F5/F6 empty after seed

- GIVEN a fully migrated and seeded database
- WHEN counting rows in `recommendation_*`, `reports`, and `report_templates`
- THEN the count is 0 while identity, instruments, sessions, audit, and consent are seeded

#### Scenario: Schema exists before seed

- GIVEN a database migrated but not seeded
- WHEN introspecting F5/F6 tables
- THEN all columns exist even though no data is present

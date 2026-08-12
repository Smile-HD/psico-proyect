# Delta for Data Schema

## MODIFIED Requirements

### Requirement: Empty-but-migrated F5/F6

The recommendation and reporting families MUST be created by migrations and MUST exist since migration 0003; F5 MUST NOT change the schema (no migration). F6 MUST extend the reporting family through ONE new linear, schema-only migration `0006_*` immediately after `0005_catalog_four_level`, adding: a nullable FK `score_run_id` from `reports` to `score_runs`, an F5 JSONB source snapshot, a template version pin, CHECK constraints on `status` (`pending`, `processing`, `ready`, `failed`) and `format` (`pdf`) after the ratified vocabulary, artifact fields (opaque storage key, sha256 checksum, byte size, media type, renderer version, `generated_at`), and `created_at`/`updated_at`/`failed_at` timestamps; `report_templates` MUST gain version and status (`draft`/`published`/`retired`) semantics with published-immutability. After a full seed, `recommendation_rules` MUST be populated, `report_templates` MUST contain the seeded `informe-basico` template, and `recommendation_results` (runtime-only) and `reports` (runtime-only) MUST contain zero rows.

(Previously: both F5 and F6 were required to make no schema change and reporting rows had to stay at zero after seed; F6 now adds the linear `0006_*` migration and the seed default template makes `report_templates` non-zero.)

#### Scenario: Reporting rows and seed template after seed

- GIVEN a fully migrated and seeded database
- WHEN counting rows in `recommendation_rules`, `recommendation_results`, `reports`, and `report_templates`
- THEN `recommendation_rules` count is greater than 0
- AND `report_templates` contains exactly the seeded `informe-basico` template
- AND `recommendation_results` and `reports` are 0 while identity, instruments, sessions, audit, and consent are seeded

#### Scenario: Schema exists before seed

- GIVEN a database migrated but not seeded
- WHEN introspecting F5/F6 tables
- THEN all columns exist including the `0006_*` additions even though no data is present

#### Scenario: Migration chain stays linear and idempotent

- GIVEN a database at `0005_catalog_four_level`
- WHEN `alembic upgrade head` runs once, then again
- THEN migration `0006_*` applies after 0005 without branches or merge points
- AND the second run executes no migration and raises no error

## ADDED Requirements

### Requirement: Report Persistence Shape

The `reports` table MUST permit multiple historical reports per session (no unique constraint on `session_id`). A report row MUST carry a nullable FK `score_run_id` to `score_runs.id` (pin to the F4 source), an F5 JSONB source snapshot pinning the generation by value (no generation entity exists), a template version pin (id plus `template_version_no`), `status` CHECK-constrained to exactly `pending`/`processing`/`ready`/`failed`, `format` CHECK-constrained to exactly `pdf`, artifact fields (`storage_key` opaque and never an internal path, `sha256` checksum, `byte_size`, `media_type`, `renderer_version`, `generated_at`), and `created_at`/`updated_at`/`failed_at` timestamps. Runtime report rows MUST be UUID4 with `synthetic=False` and `source='runtime'`. The `0006_*` migration MUST NOT drop, retype, or weaken any existing F1–F5 column, index, or FK constraint: existing tables MUST keep full referential integrity.

#### Scenario: F1–F5 integrity preserved

- GIVEN a database migrated to `0006_*` with runtime F1–F5 rows
- WHEN introspecting the pre-existing constraints
- THEN every pre-existing FK, CHECK, and unique constraint still exists
- AND existing rows satisfy them unchanged

#### Scenario: Status and format vocabularies enforced

- GIVEN a report with status `ready` and format `pdf`
- WHEN the row is written
- THEN the CHECK constraints accept it
- AND any other status or format value is rejected

#### Scenario: Ready rows carry artifact fields

- GIVEN a report in `ready`
- WHEN the row is inspected
- THEN storage key, sha256 checksum, byte size, media type, renderer version, and `generated_at` are populated
- AND a `failed` report carries no artifact fields and `failed_at` is set

#### Scenario: Runtime flags on reports

- GIVEN a report persisted by the reports API
- WHEN the row is inspected
- THEN `synthetic` is false and `source` is `'runtime'`
- AND its id is UUID4

### Requirement: Report Template Persistence Shape

The `report_templates` table MUST express versioned, immutable templates: each template key MAY have multiple version rows, each with `status` constrained to `draft`/`published`/`retired` and a `version_no` unique per key. A `published` template MUST be immutable: its body, name, or version MUST NOT change in place; any change MUST create a new version row, and `retired` versions MUST remain readable so historical reports stay reproducible. A report MUST pin the exact template version id used (and its `version_no`) at generation time. Templates MUST remain data, never code: the stored body MUST NOT be executed, imported, or evaluated. Seed templates are UUID5 with `synthetic=True`/`source='seed'`; runtime templates (if any) are UUID4 with `synthetic=False`/`source='runtime'`.

#### Scenario: Published template is immutable

- GIVEN a template version in `published`
- WHEN an attempt edits its body in place
- THEN the change is rejected
- AND a new version row is required instead

#### Scenario: Version pin preserves history

- GIVEN a report pinned to template version 1
- WHEN version 2 is published later
- THEN the report still resolves against version 1's exact body
- AND the report's `template_version_no` equals 1

#### Scenario: Retired versions remain readable

- GIVEN a template version moved to `retired`
- WHEN a historical report references it
- THEN the version row is still available unchanged for reproduction

## Non-goals

- No `recommendation_generation` entity: the F5 source is pinned by JSONB value snapshot.
- No outbox, delivery, audience, locale, or retention columns in this change.
- No report uniqueness per session; no changes to F1–F5 tables.

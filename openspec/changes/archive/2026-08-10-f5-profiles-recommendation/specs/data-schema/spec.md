# Delta for Data Schema

## MODIFIED Requirements

### Requirement: Empty-but-migrated F5/F6

The recommendation and reporting families MUST be created by migrations and MUST exist since migration 0003; F5 MUST NOT change the schema (no migration). After a full seed, `recommendation_rules` MUST be populated by the seed while `recommendation_results` (runtime-only), `reports`, and `report_templates` MUST contain zero rows.

(Previously: both recommendation and reporting families were required to contain zero rows after seed; F5 now seeds `recommendation_rules` while runtime results and reports stay at 0.)

#### Scenario: Recommendation rules populated, results and reports empty after seed

- GIVEN a fully migrated and seeded database
- WHEN counting rows in `recommendation_rules`, `recommendation_results`, `reports`, and `report_templates`
- THEN `recommendation_rules` count is greater than 0
- AND `recommendation_results`, `reports`, and `report_templates` are 0 while identity, instruments, sessions, audit, and consent are seeded

#### Scenario: Schema exists before seed

- GIVEN a database migrated but not seeded
- WHEN introspecting F5/F6 tables
- THEN all columns exist even though no data is present

## ADDED Requirements

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

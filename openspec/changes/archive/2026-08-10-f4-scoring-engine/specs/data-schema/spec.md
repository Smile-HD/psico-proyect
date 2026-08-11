# Delta for Data Schema

## ADDED Requirements

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

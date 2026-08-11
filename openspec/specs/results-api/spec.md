# Results API Specification

## Purpose

API-only results surface (no web UI in F4): `POST /api/v1/results/{session_id}/score` triggers an eager, persisted scoring run; `GET /api/v1/results/{session_id}` reads the latest run. Roles per the ratified access matrix (`view_results`). F5 recommendations and F6 reports are out of scope.

## Requirements

### Requirement: Score Trigger

`POST /api/v1/results/{session_id}/score` MUST require an `Idempotency-Key` scoped `session:{id}` and MUST require the `view_results` capability (admin, psicólogo, and evaluado for own sessions only). It MUST score only sessions with status `completed`: run the pure engine, then persist a `score_runs` row (`pending → completed`, `raw` JSONB, `computed_at`, `synthetic=False`, `source='runtime'`) and audit `scoring.run` with aggregate metadata only. A missing session MUST return `NOT_FOUND`/`resource_not_found` (indistinguishable); an `in_progress` session MUST return `CONFLICT`/`session_not_completed` and MUST NOT be scored, exposed, or leaked. Replaying the same key and body MUST return the original result with no duplicate run or audit event; the same key with a different body MUST return `CONFLICT`/`idempotency_key_reused`; a NEW key MUST create a new run and a new `scoring.run` event (schema-legal: no unique constraint on `session_id`).

#### Scenario: Completed session scores

- GIVEN a `completed` session with 20 responses
- WHEN the trigger is called with a fresh key
- THEN a run is persisted as `completed` with `computed_at`
- AND one `scoring.run` event is written with aggregate metadata only

#### Scenario: In-progress session rejected

- GIVEN an `in_progress` session
- WHEN the score trigger is called
- THEN `CONFLICT` with `session_not_completed` is returned
- AND no run row, score, or response data is exposed

#### Scenario: Missing session indistinguishable

- GIVEN a non-existent `session_id`
- WHEN the score trigger is called
- THEN `NOT_FOUND` with `resource_not_found` is returned

#### Scenario: Foreign evaluado cannot trigger

- GIVEN an `evaluado` user and another user's session
- WHEN the score trigger is called
- THEN `FORBIDDEN` is returned
- AND no run is created

#### Scenario: Retry replays without duplication

- GIVEN a successful score with `Idempotency-Key: k`
- WHEN the same request is retried with the same key and body
- THEN the original result is replayed
- AND exactly one run row and one `scoring.run` event exist

#### Scenario: Same key, different body conflicts

- GIVEN a successful score with `Idempotency-Key: k`
- WHEN the same key arrives with a different body
- THEN `CONFLICT` with `idempotency_key_reused` is returned
- AND no second run or audit event is created

#### Scenario: New key creates a new run

- GIVEN a session scored once with key k1
- WHEN the trigger is called again with key k2
- THEN a second completed run and a second `scoring.run` event exist

### Requirement: Results Read

`GET /api/v1/results/{session_id}` MUST allow `admin` and `psicólogo` for any session and `evaluado` for own sessions only (otherwise `FORBIDDEN`). It MUST return the LATEST completed run, selected deterministically by greatest `computed_at`, tie-broken by run id descending. A session with no completed run MUST return `NOT_FOUND`/`resource_not_found` (indistinguishable from a missing session). Because completed-session responses are immutable (response writes fail outside `in_progress`), concurrent runs for one session MUST produce identical scores; the latest-run rule only selects which row is served.

#### Scenario: Owner reads own results

- GIVEN an `evaluado` user with a scored session
- WHEN the results are read
- THEN 200 returns the latest run's scores with the baremo `norm_note`

#### Scenario: Foreign evaluado denied

- GIVEN an `evaluado` user and another user's scored session
- WHEN the results are read
- THEN `FORBIDDEN` is returned
- AND no result data is exposed

#### Scenario: Unscored session is not found

- GIVEN a `completed` session with no run
- WHEN the results are read
- THEN `NOT_FOUND` with `resource_not_found` is returned

#### Scenario: Multiple runs resolve deterministically

- GIVEN two completed runs for one session
- WHEN the results are read
- THEN the run with the greatest `computed_at` (tie: greatest id) is returned

### Requirement: Results Payload and No-leak Boundary

The results payload MUST carry per-scale entries (scale label, raw, z, percentile, T, eneatype), the overall raw/transformed scores, the reference set id, `computed_at`, and the reference set's `norm_note` verbatim (research-only disclaimer). It MUST NOT contain numeric option values, response keys or ids, the 1–5 mapping, or item content. `fixture_projection` and the 1–5 mapping MUST remain non-public; session endpoints MUST NOT gain scoring data (the no-scoring boundary asserted by `test_session_api.py:375` MUST keep passing). The 2 inherited `test_web.py` failures are documented debt, not in scope.

#### Scenario: Payload exposes labels and scores only

- GIVEN a scored session
- WHEN the payload is inspected
- THEN scale labels, scores, and the `norm_note` are present
- AND no numeric option value or response key appears anywhere

#### Scenario: Session boundary unchanged

- GIVEN a completed session
- WHEN `GET /sessions/{id}` and completion responses are inspected
- THEN they contain no scores or reference-set data (F3 boundary intact)

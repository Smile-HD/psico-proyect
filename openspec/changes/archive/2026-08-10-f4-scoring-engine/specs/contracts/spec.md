# Delta for Contracts

## MODIFIED Requirements

### Requirement: Idempotent Mutations

Every mutating endpoint (`POST`, `PUT`, `PATCH`) MUST accept an `Idempotency-Key` header. Repeating a request with the same key for the same resource MUST replay the original result without duplicating the side effect; a new key MUST start an independent operation. Side effects include both data rows and audit events: a replayed request MUST NOT duplicate either. F2 was the first implementation, scoped to catalog mutations. F3 extends the implementation obligation to session mutations (create session, save responses, complete) and to consent grant/revoke mutations, preserving their existing semantics. When the same key is reused with a materially different request body, the system MUST NOT create a second side effect and MUST reject with `CONFLICT`; F3 session and consent mutations MUST use the message token `idempotency_key_reused`. F4 extends the obligation to the results score trigger (`POST /api/v1/results/{session_id}/score`), which MUST scope keys as `session:{id}`: a replayed key MUST NOT duplicate a scoring run or its `scoring.run` audit event, and a NEW key MUST start an independent run. F4 score-trigger key reuse with a different body MUST reject with `CONFLICT` and the message token `idempotency_key_reused`.

(Previously: the requirement covered F2 catalog and F3 session/consent mutations; F4 adds the score trigger with `session:{id}` key scope and independent-run semantics.)

#### Scenario: Retry without duplication

- GIVEN a mutation that succeeded with `Idempotency-Key: k`
- WHEN the client retries the same request with the same key
- THEN the response repeats the original result
- AND no second side effect is created

#### Scenario: Replay does not duplicate audit

- GIVEN a publish that succeeded with `Idempotency-Key: k`
- WHEN the same request is retried with the same key
- THEN exactly one `instrument.published` audit event exists for that transition

#### Scenario: Distinct keys are independent

- GIVEN two mutations with different `Idempotency-Key` values
- WHEN both are executed
- THEN each side effect is applied exactly once

#### Scenario: Same key, different body conflicts

- GIVEN a successful mutation with `Idempotency-Key: k` and body A
- WHEN the client sends the same key with a materially different body B
- THEN the system returns `CONFLICT`
- AND no second side effect is created

#### Scenario: F3 session mutation rejects key reuse

- GIVEN a session creation that succeeded with `Idempotency-Key: k`
- WHEN the same key arrives with a different `instrument_version_id`
- THEN `CONFLICT` with `idempotency_key_reused` is returned
- AND no second session row or audit event is created

#### Scenario: F4 score-trigger replay is run-safe

- GIVEN a scoring run completed with `Idempotency-Key: k` (scope `session:{id}`)
- WHEN the same request is retried with the same key and body
- THEN the original result is replayed
- AND no second run row or `scoring.run` event is created

#### Scenario: F4 new key starts an independent run

- GIVEN a session scored with `Idempotency-Key: k1`
- WHEN the trigger runs again with a new key k2
- THEN a second run and a second `scoring.run` event exist

## ADDED Requirements

### Requirement: Results Availability Errors

The results surface MUST return `NOT_FOUND` with message `resource_not_found` for a missing session and for a session with no completed run — indistinguishable responses that reveal no existence or state. A score trigger on a session that exists but is not `completed` MUST return `CONFLICT` with message `session_not_completed` and MUST NOT expose any response data. All results errors MUST use the single envelope (code, message, request_id, details).

#### Scenario: Missing and unscored are indistinguishable

- GIVEN a non-existent session and a completed-but-unscored session
- WHEN each is requested via the results surface
- THEN both return the identical `NOT_FOUND`/`resource_not_found` envelope

#### Scenario: In-progress triggers stable conflict

- GIVEN an `in_progress` session
- WHEN the score trigger is called
- THEN `CONFLICT` with `session_not_completed` is returned
- AND no response values or scores are exposed

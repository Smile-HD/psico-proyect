# Delta for Contracts

## MODIFIED Requirements

### Requirement: Idempotent Mutations

Every mutating endpoint (`POST`, `PUT`, `PATCH`) MUST accept an `Idempotency-Key` header. Repeating a request with the same key for the same resource MUST replay the original result without duplicating the side effect; a new key MUST start an independent operation. Side effects include both data rows and audit events: a replayed request MUST NOT duplicate either. F2 was the first implementation, scoped to catalog mutations. F3 extends the implementation obligation to session mutations (create session, save responses, complete) and to consent grant/revoke mutations, preserving their existing semantics. When the same key is reused with a materially different request body, the system MUST NOT create a second side effect and MUST reject with `CONFLICT`; F3 session and consent mutations MUST use the message token `idempotency_key_reused`.

(Previously: the requirement was implemented only for F2 catalog mutations, and the same-key/different-body conflict message token was not pinned.)

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

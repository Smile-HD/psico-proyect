# Delta for Contracts

## MODIFIED Requirements

### Requirement: Idempotent Mutations

Every mutating endpoint (`POST`, `PUT`, `PATCH`) MUST accept an `Idempotency-Key` header. Repeating a request with the same key for the same resource MUST replay the original result without duplicating the side effect; a new key MUST start an independent operation. Side effects include both data rows and audit events: a replayed request MUST NOT duplicate either. F2 is the first implementation of this requirement: every F2 catalog mutation (create instrument, create draft version, save draft hierarchy, publish, archive) MUST implement it. When the same key is reused with a materially different request body, the system MUST NOT create a second side effect and MUST either replay the stored original result or reject with `CONFLICT` (the exact choice is a design decision recorded in the F2 proposal open questions).

(Previously: the requirement was ratified in F1 but unimplemented; F2 is the first implementation, scoped to catalog mutations.)

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

# Delta for Audit & Consent

## ADDED Requirements

### Requirement: Idempotent Consent Mutations

`POST /api/v1/consent/{id}/grant` and `POST /api/v1/consent/{id}/revoke` MUST require an `Idempotency-Key`, preserving their existing registry semantics (state transitions and `consent.granted`/`consent.revoked` audit). Replaying the same key and body MUST return the original result with no duplicate registry effect or audit event. Reusing the same key with a materially different body MUST fail with `CONFLICT` and message `idempotency_key_reused`, with no side effect.

#### Scenario: Retried grant replays

- GIVEN a grant that succeeded with `Idempotency-Key: k`
- WHEN the same request is retried with the same key
- THEN the original result is replayed
- AND exactly one `consent.granted` event exists for that grant

#### Scenario: Retried revoke replays

- GIVEN a revoke that succeeded with `Idempotency-Key: k`
- WHEN the same request is retried with the same key
- THEN the original result is replayed
- AND exactly one `consent.revoked` event exists

#### Scenario: Same key, different body conflicts

- GIVEN a grant stored with `Idempotency-Key: k`
- WHEN the same key arrives with a different body
- THEN `CONFLICT` with `idempotency_key_reused` is returned
- AND no second registry effect or audit event occurs

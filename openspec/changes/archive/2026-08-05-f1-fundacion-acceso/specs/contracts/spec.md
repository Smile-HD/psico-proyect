# Delta Spec: contracts

# Contracts Specification

## Purpose

Binding conventions consumed by F2–F6: ID format, single error envelope with `request_id`, and contract language. Published in `packages/contracts/` and this spec, not implicit in code.

## ADDED Requirements

### Requirement: ID Convention

Runtime data MUST use UUID4 ids. Seed data MUST use deterministic UUID5 ids under namespace `psico-seed`. Human-readable seed keys MUST be stable: `evaluado_01`, `TP-S-01`, `RS-TP-S-01`.

#### Scenario: Runtime vs seed id space

- GIVEN a runtime row and a seed row
- WHEN inspecting their ids
- THEN the runtime id is UUID4 and the seed id is UUID5, verifiable via the version nibble

#### Scenario: Seed keys resolve deterministically

- GIVEN the same stable key in two runs
- WHEN the UUID5 is computed under `psico-seed`
- THEN the resulting id is identical both times

### Requirement: Single Error Envelope

Every API error MUST return exactly `{"error": {"code", "message", "request_id", "details"}}`. Codes MUST be one of `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `INTERNAL_ERROR`. Auth failures MUST return generic message text only. `request_id` MUST be unique per request.

#### Scenario: Envelope shape

- GIVEN a 403 denial
- WHEN the response is parsed
- THEN it contains exactly one `error` object with code, message, request_id, and details

#### Scenario: Unique request_id

- GIVEN two failing requests
- WHEN comparing their envelopes
- THEN the `request_id` values differ

#### Scenario: Safe auth text

- GIVEN a login attempt with unknown credentials
- WHEN the 401 is returned
- THEN the message is generic and reveals no account or role information

### Requirement: Idempotent Mutations

Every mutating endpoint (`POST`, `PUT`, `PATCH`) MUST accept an `Idempotency-Key` header. Repeating a request with the same key for the same resource MUST replay the original result without duplicating the side effect; a new key MUST start an independent operation.

#### Scenario: Retry without duplication

- GIVEN a mutation that succeeded with `Idempotency-Key: k`
- WHEN the client retries the same request with the same key
- THEN the response repeats the original result
- AND no second side effect is created

#### Scenario: Distinct keys are independent

- GIVEN two mutations with different `Idempotency-Key` values
- WHEN both are executed
- THEN each side effect is applied exactly once

### Requirement: Contract Language

The technical contract (IDs, error codes, seed manifest schema) MUST be in English. Human-facing UI texts MUST be in Spanish.

#### Scenario: English contract tokens

- GIVEN the error envelope
- WHEN inspecting `code` and `message`
- THEN both are English tokens (e.g., `FORBIDDEN`, `insufficient_role`)


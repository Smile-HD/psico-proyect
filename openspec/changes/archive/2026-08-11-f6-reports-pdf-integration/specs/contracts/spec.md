# Delta for Contracts

## MODIFIED Requirements

### Requirement: Idempotent Mutations

Every mutating endpoint (`POST`, `PUT`, `PATCH`) MUST accept an `Idempotency-Key` header. Repeating a request with the same key for the same resource MUST replay the original result without duplicating the side effect; a new key MUST start an independent operation. Side effects include both data rows and audit events: a replayed request MUST NOT duplicate either. F2 was the first implementation, scoped to catalog mutations. F3 extends the implementation obligation to session mutations (create session, save responses, complete) and to consent grant/revoke mutations, preserving their existing semantics. When the same key is reused with a materially different request body, the system MUST NOT create a second side effect and MUST reject with `CONFLICT`; F3 session and consent mutations MUST use the message token `idempotency_key_reused`. F4 extends the obligation to the results score trigger (`POST /api/v1/results/{session_id}/score`), which MUST scope keys as `session:{id}`: a replayed key MUST NOT duplicate a scoring run or its `scoring.run` audit event, and a NEW key MUST start an independent run. F4 score-trigger key reuse with a different body MUST reject with `CONFLICT` and the message token `idempotency_key_reused`. F5 extends the obligation to the recommendation generation trigger (`POST /api/v1/recommendations/{session_id}/generate`), which MUST scope keys as `session:{id}`: a replayed key MUST NOT duplicate result rows or the `recommendation.generated` audit event, and a NEW key MUST start an independent generation. F5 generation key reuse with a different body MUST reject with `CONFLICT` and the message token `idempotency_key_reused`. F6 extends the obligation to the report generation trigger (`POST /api/v1/reports/{session_id}/generate`), which MUST scope keys as `session:{id}`: a replayed key MUST NOT duplicate the report row, the PDF artifact, or the `report.generated` audit event, and a NEW key MUST create a new historical report pinned to the same sources (never replacing or deleting earlier reports). F6 report key reuse with a different body MUST reject with `CONFLICT` and the message token `idempotency_key_reused`.

(Previously: the requirement covered F2 catalog, F3 session/consent, F4 score-trigger, and F5 generation-trigger mutations; F6 adds the report generation trigger with `session:{id}` key scope and historical-pinning semantics.)

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

#### Scenario: F5 generation replay is run-safe

- GIVEN a generation completed with `Idempotency-Key: k` (scope `session:{id}`)
- WHEN the same request is retried with the same key and body
- THEN the original DTO is replayed
- AND no duplicate result rows or `recommendation.generated` events exist

#### Scenario: F5 new key starts a new generation

- GIVEN a session generated with `Idempotency-Key: k1`
- WHEN the trigger runs again with a new key k2
- THEN a second generation of result rows and a second `recommendation.generated` event exist

#### Scenario: F6 report replay is run-safe

- GIVEN a report generated with `Idempotency-Key: k` (scope `session:{id}`)
- WHEN the same request is retried with the same key and body
- THEN the original result is replayed
- AND no duplicate report row, PDF artifact, or `report.generated` event exists

#### Scenario: F6 new key creates historical reports

- GIVEN a report generated with `Idempotency-Key: k1`
- WHEN the trigger runs again with a new key k2
- THEN a second report row exists pinned to the same sources
- AND the first report and its artifact remain unchanged

## ADDED Requirements

### Requirement: Report Access Matrix

The capability `view_reports` MUST be ratified with admin ✅ and psicólogo ✅ for ANY session (generate, metadata read, and download), and evaluado ❌ for all three operations on all sessions, including own sessions. All three report routes MUST declare `require_roles(...)` (deny-by-default). An `evaluado` calling any report route MUST receive `FORBIDDEN` with no data exposure and an `auth.denied` audit record. The capability MUST be updated in lockstep across `permissions.py`, the contracts README §6 matrix, and the capability contract tests.

#### Scenario: Professional operates any session

- GIVEN an `admin` or `psicólogo` user and another user's session with a ready report
- WHEN generate, read, or download is called
- THEN the operation succeeds without ownership checks

#### Scenario: Evaluado is excluded

- GIVEN an `evaluado` user and any session, including an own session with a ready report
- WHEN generate, read, or download is called
- THEN `FORBIDDEN` is returned
- AND no report data is exposed and `auth.denied` is audited

### Requirement: Report Availability Errors

The report surface MUST return `NOT_FOUND` with message `resource_not_found` for: a missing session, a completed-but-unscored session, and a scored-but-ungenerated session (generate); a session with no report (read); and a report id that does not exist or a report that is not `ready` (download) — all indistinguishable responses that reveal no existence or state. The generation trigger on a session that is not `completed` MUST return `CONFLICT` with message `session_not_completed` and MUST NOT expose response or score data. A renderer or storage failure MUST return `INTERNAL_ERROR` with the new ratified message token `report_generation_failed` (the only new token in this change; no new error codes). All report errors MUST use the single envelope (code, message, request_id, details) without stack traces.

#### Scenario: Missing, unscored, and ungenerated are indistinguishable

- GIVEN a non-existent session, a completed-but-unscored session, and a scored-but-ungenerated session
- WHEN each is passed to the generation trigger
- THEN all return the identical `NOT_FOUND`/`resource_not_found` envelope

#### Scenario: In-progress trigger yields a stable conflict

- GIVEN an `in_progress` session
- WHEN the generation trigger is called
- THEN `CONFLICT` with `session_not_completed` is returned
- AND no response values, scores, or report data are exposed

#### Scenario: Download not-ready is indistinguishable from missing

- GIVEN a non-existent report id and a `pending` report
- WHEN each is downloaded
- THEN both return the identical `NOT_FOUND`/`resource_not_found` envelope

#### Scenario: Renderer failure maps to the ratified token

- GIVEN a generation whose renderer fails
- WHEN the response is returned
- THEN `INTERNAL_ERROR` with `report_generation_failed` is returned
- AND no stack trace or internal detail appears in the envelope

### Requirement: Report DTO and No-leak Boundary

Report DTOs MUST be strict: the generation request is validated with `extra="forbid"`, and all report responses MUST expose exactly the ratified metadata fields — never internal storage keys, paths, vendor payloads, renderer internals, scores, justifications, response data, or tokens. The no-leak boundary MUST extend to the downloaded PDF: the DTO, PDF text, PDF metadata, audit metadata, and logs MUST NOT contain numeric option values, response keys or ids, the 1–5 mapping, item content, secrets, or PII beyond the session id. The PDF is delivered only as an authenticated stream; no URL, signed or bare, grants access.

#### Scenario: DTO exposes ratified fields only

- GIVEN the generate response and the metadata read response
- WHEN every field is inspected
- THEN only the ratified metadata fields are present
- AND no storage key, path, or vendor field appears

#### Scenario: Recursive no-leak scan

- GIVEN a generated report
- WHEN scanning the DTO, PDF text, PDF metadata, and audit metadata
- THEN no option value, response key, 1–5 mapping, item content, secret, or token appears anywhere

## Non-goals

- No signed temporary URLs, no delivery/integration tokens, no new error codes.
- No token beyond `report_generation_failed`; download and read reuse `resource_not_found` indistinguishability.

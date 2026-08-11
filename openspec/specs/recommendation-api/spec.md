# Recommendation API Specification

## Purpose

F5 recommendation surface: DB-defined, deterministic, explainable profile×program fit with traceable justification. Rules live in DB rows; the engine never uses LLM, stored SQL, or code-embedded rules.

## Requirements

### Requirement: Declarative Rule Contract

The system MUST evaluate recommendations exclusively from `recommendation_rules` rows. `rule_type` MUST be one of the closed set {`percentile_min`}; `params` MUST follow the pinned JSONB schema; only `is_active = true` rows MUST be evaluated. `percentile_min` params MUST be `{scale, min_percentile, weight?}` where `scale` MUST be one of the exact scale labels (`Intereses`, `Aptitud verbal`, `Aptitud numérica`, `Razonamiento abstracto`, `Valores/preferencias`) or `overall`; `min_percentile` MUST be an integer in [1, 99]; a missing `weight` MUST default to 1.0, a present `weight` MUST be positive. Unknown rule types, unknown scale labels, missing required keys, out-of-range `min_percentile`, or non-positive weights MUST abort the generation with a typed integrity error (`INTERNAL_ERROR` / `recommendation_integrity_error`); invalid rules MUST NOT be silently skipped. Inputs MUST be the latest completed score run's percentiles, the active rules, and the program catalog. No LLM, stored SQL, or code-embedded rules MAY be used.

#### Scenario: Closed vocabulary enforced

- GIVEN an active rule whose `rule_type` is outside {`percentile_min`}
- WHEN a generation is requested
- THEN it fails with `recommendation_integrity_error`
- AND no result rows are persisted

#### Scenario: Missing weight defaults

- GIVEN an active rule with no `weight` in params
- WHEN the fit is computed
- THEN the rule contributes with weight 1.0

### Requirement: Fit Computation

For each program the fit MUST equal `100·Σ(w·satisfied)/Σ(w)` over its active rules, computed as the sum of per-rule contributions, each `round-half-up(100·w·satisfied/Σ(w))` to `Numeric(5,2)`. A rule is satisfied iff the run's percentile for `params.scale` is ≥ `params.min_percentile`. Programs with zero active rules MUST be excluded from results (no basis for a fit; fit 0.00 is reserved for evaluated-but-unsatisfied programs). Aggregated results MUST be ordered fit DESC, then program name ASC.

#### Scenario: Weighted fit

- GIVEN a program with rules (Aptitud numérica ≥ 60, w=1) and (Aptitud numérica ≥ 80, w=2), and percentiles 72/72
- WHEN the fit is computed
- THEN contributions are 33.33 and 0.00
- AND the program fit is 33.33

#### Scenario: Zero-rule program excluded

- GIVEN a program with no active rules
- WHEN a generation is computed
- THEN the program has no result rows and does not appear in the payload

### Requirement: Generation Endpoint

`POST /api/v1/recommendations/{session_id}/generate` MUST require `view_recommendations` and an `Idempotency-Key` scoped `session:{id}`. It MUST generate only from a completed score run: a missing session or a completed-but-unscored session MUST return `NOT_FOUND`/`resource_not_found` (indistinguishable); an `in_progress` session MUST return `CONFLICT`/`session_not_completed`. It MUST persist one `recommendation_results` row per evaluated rule (fit contribution + justification, `synthetic=False`, `source='runtime'`) and the aggregate audit event `recommendation.generated` in ONE transaction; an audit failure MUST roll back the generation and return `INTERNAL_ERROR`. Replaying the same key and body MUST return the original DTO with no duplicate rows or audit events; the same key with a different body MUST return `CONFLICT`/`idempotency_key_reused`; a NEW key MUST create a new generation (schema-legal).

#### Scenario: Completed session generates

- GIVEN a `completed` session with a completed score run
- WHEN the trigger is called with a fresh key
- THEN one `recommendation_results` row per evaluated rule is persisted
- AND one aggregate `recommendation.generated` event is written

#### Scenario: Replay is run-safe

- GIVEN a generation completed with `Idempotency-Key: k`
- WHEN the same request is retried with the same key and body
- THEN the original DTO is replayed
- AND no duplicate rows or `recommendation.generated` events exist

#### Scenario: Audit failure rolls back

- GIVEN a generation whose audit write fails
- WHEN the transaction commits
- THEN the generation is rolled back and `INTERNAL_ERROR` is returned

### Requirement: Recommendation Read

`GET /api/v1/recommendations/{session_id}` MUST require `view_recommendations` and MUST return the latest generation: the anchor is the session's result row with greatest `created_at` (tie: greatest id), and the generation is all rows sharing that `created_at`, aggregated per program (fit DESC, program name ASC), each program carrying its justification. A session with no generation MUST return `NOT_FOUND`/`resource_not_found`, indistinguishable from a missing session.

#### Scenario: Latest generation returned

- GIVEN two generations for one session
- WHEN the recommendations are read
- THEN the generation with the greatest `created_at` is returned, aggregated per program

#### Scenario: No generation is not found

- GIVEN a scored session with no generation
- WHEN the recommendations are read
- THEN `NOT_FOUND` with `resource_not_found` is returned

### Requirement: Payload, Disclaimer and No-leak Boundary

The payload MUST expose exactly `session_id`, `generated_at`, `disclaimer`, and `items[]` of `{program_id, program_name, program_code, fit_score, justification}`. Justifications MUST follow the Spanish template `"{scale} ≥ {min_percentile} pct: cumple ({percentile} pct)"` (or `"...: no cumple ..."`), joined per program in rule id ASC order. The payload MUST carry a versioned code-constant disclaimer, never the baremo `norm_note`, verbatim: "Recomendaciones orientativas sobre datos sintéticos (research-only). No constituyen una norma UAGRM ni asesoramiento profesional." (v1). The payload MUST NOT contain option values, response keys/ids, the 1–5 mapping, item content, or raw scores; percentiles MAY appear only inside justification text.

#### Scenario: Payload shape and disclaimer

- GIVEN a generated session
- WHEN the payload is inspected
- THEN program entries, fit scores, justifications, and the pinned disclaimer are present
- AND no option value, response key, or item content appears anywhere

#### Scenario: Percentiles confined to justifications

- GIVEN a generated session
- WHEN scanning the payload for numeric values
- THEN percentiles appear only within justification text

# Reports API Specification

## Purpose

API-only F6 reports surface (no web UI): manual idempotent generation, metadata read, and authenticated stream download of deterministic professional PDFs composed from persisted F4/F5 snapshots — never recomputing scoring or recommendations. Professional-only (`view_reports`); templates are seed-owned data, never code; artifacts retained indefinitely.

## Requirements

### Requirement: Report Generation Trigger

`POST /api/v1/reports/{session_id}/generate` MUST require an `Idempotency-Key` scoped `session:{id}` and MUST require the `view_reports` capability (admin or psicólogo; evaluado is always excluded). It MUST generate only from a `completed` session that has a completed score run AND a recommendation generation: a missing session, a completed-but-unscored session, and a scored-but-ungenerated session MUST return the identical `NOT_FOUND`/`resource_not_found` envelope with zero effects (no report row, no artifact, no audit event); an `in_progress` session MUST return `CONFLICT`/`session_not_completed`. The trigger MUST consume only persisted snapshots and MUST NOT invoke, import, or re-run the scoring or recommendation engines, MUST NOT recompute scores or fit, and MUST NOT create or modify score or recommendation rows (all-or-nothing). On success it MUST pin the exact `score_run_id`, the F5 generation snapshot, and the template version used, transition the report to `ready` with a stored artifact, and audit `report.generated` (aggregate-only). The request body MUST be validated strictly with `extra="forbid"`: any unknown field MUST be rejected with `VALIDATION_ERROR`, and the template is always the seed default `informe-basico` (no client template selection).

#### Scenario: Completed chain generates

- GIVEN a `completed` session with a completed score run and a recommendation generation
- WHEN the trigger is called with a fresh key
- THEN a report is persisted as `ready` with a stored artifact, pins, and one aggregate `report.generated` event

#### Scenario: Missing, unscored, and ungenerated are indistinguishable

- GIVEN a non-existent session, a completed-but-unscored session, and a scored-but-ungenerated session
- WHEN each is passed to the trigger
- THEN all three return the identical `NOT_FOUND`/`resource_not_found` envelope
- AND no report row, artifact, or audit event is created

#### Scenario: In-progress session rejected

- GIVEN an `in_progress` session
- WHEN the trigger is called
- THEN `CONFLICT` with `session_not_completed` is returned
- AND no report row is created and no response or score data is exposed

#### Scenario: No hidden F4/F5 invocation

- GIVEN a completed chain with a newer run and generation already present
- WHEN the trigger runs
- THEN no `score_runs` or `recommendation_results` rows are created or modified
- AND the report pins the sources that existed at generation time

#### Scenario: Strict request body

- GIVEN a trigger request carrying an unknown field
- WHEN the request is validated
- THEN `VALIDATION_ERROR` is returned
- AND no report row or audit event is created

### Requirement: Report Document Content

The report MUST present, in fixed sections: per-scale scores (scale label, raw, z, percentile, T, eneatype) and overall scores from the pinned run snapshot; per-program recommendations (program name, fit score, justification) from the pinned F5 snapshot; the baremo `norm_note` in its own section and the F5 disclaimer in its own section — one MUST NOT substitute for the other. The report MUST NOT contain numeric option values, response keys or ids, the 1–5 mapping, item content, secrets, tokens, or PII beyond the session id. Identical pinned inputs MUST produce an identical logical document; the rendered PDF MUST be normalized-deterministic (structure, text, and metadata), not byte-identical.

#### Scenario: Sections and disclaimers present

- GIVEN a ready report over a pinned run and generation
- WHEN the PDF text is extracted
- THEN scale scores, program fits with justifications, the `norm_note` section, and the disclaimer section are present
- AND neither note appears inside the other's section

#### Scenario: No-leak scan

- GIVEN a ready report
- WHEN scanning the DTO, PDF text, and PDF metadata recursively
- THEN no option value, response key, 1–5 mapping, item content, or secret appears
- AND the PDF metadata carries no internal storage path or renderer internals

### Requirement: Report Metadata Read

`GET /api/v1/reports/{session_id}` MUST require `view_reports` and MUST return the metadata DTO of the session's MOST RECENT report, selected deterministically by greatest `created_at`, tie-broken by id descending: `id`, `session_id`, `template_id`, `template_version_no`, `status`, `format`, `generated_at`, and, when `ready`, `checksum` and `byte_size`. It MUST NOT expose the storage key, internal paths, vendor payloads, scores, or justifications. A session with no report MUST return `NOT_FOUND`/`resource_not_found`, indistinguishable from a missing session. Reads MUST have no side effects: no rows, artifacts, or audit events are ever created or updated by a GET.

#### Scenario: Latest metadata returned

- GIVEN two reports for one session
- WHEN the metadata is read
- THEN the newest report's metadata DTO is returned with status and timestamps

#### Scenario: No report is not found

- GIVEN a scored and generated session with no report
- WHEN the metadata is read
- THEN `NOT_FOUND` with `resource_not_found` is returned

#### Scenario: Read has no side effects

- GIVEN a session with a ready report
- WHEN the metadata is read twice
- THEN both responses are identical
- AND no report row, artifact, or audit event was created or updated

### Requirement: Report Download

`GET /api/v1/reports/{id}/download` MUST require `view_reports` and MUST re-check authorization at download time (same-or-stricter than metadata read). It MUST stream the stored artifact bytes with media type `application/pdf` and the stored checksum and size; it MUST NEVER return a bare URL, a signed URL, or an internal storage path. A report id that does not exist and a report that exists but is not `ready` MUST return the identical `NOT_FOUND`/`resource_not_found` envelope with zero effects.

#### Scenario: Ready report streams

- GIVEN a `ready` report with a stored artifact
- WHEN the download is requested by an authorized professional
- THEN 200 streams the PDF bytes with `application/pdf`
- AND the streamed bytes match the stored sha256 checksum

#### Scenario: Missing and not-ready are indistinguishable

- GIVEN a non-existent report id and an existing report with status `pending`
- WHEN each is downloaded
- THEN both return the identical `NOT_FOUND`/`resource_not_found` envelope
- AND no bytes or state are revealed

#### Scenario: Download re-authorizes

- GIVEN an `evaluado` user and a `ready` report
- WHEN the download is requested
- THEN `FORBIDDEN` is returned and `auth.denied` is audited
- AND no bytes are streamed

#### Scenario: No bare URL

- GIVEN an authorized download
- WHEN the response is inspected
- THEN the body is a stream, not a URL or path

### Requirement: Report State Machine

A report's `status` MUST be one of `pending`, `processing`, `ready`, or `failed`. Transitions MUST be: `pending → processing → ready`; `pending` or `processing → failed`; a retry with the same idempotency key after `failed` MUST resume the SAME report row toward `ready` (convergence). `ready` MUST NOT be reachable without a stored artifact (storage key, checksum, size, media type, renderer version, `generated_at`); a renderer or storage failure MUST leave the report in `failed` with no artifact and MUST return `INTERNAL_ERROR`/`report_generation_failed` — failures MUST never degrade to success, and a `ready` report MUST never lose its artifact. Artifacts MUST be retained indefinitely in the MVP; no TTL or cleanup runs during seed operations.

#### Scenario: Happy path transitions

- GIVEN a completed chain
- WHEN generation succeeds
- THEN the report traverses `pending → processing → ready` with artifact fields populated

#### Scenario: Failure never degrades to success

- GIVEN a renderer or storage failure during generation
- WHEN the trigger completes
- THEN the report is `failed` with no artifact and no success audit event
- AND `INTERNAL_ERROR` with `report_generation_failed` is returned

#### Scenario: Retry converges on the same report

- GIVEN a report in `failed` under key k
- WHEN the trigger is retried with the same key k and body
- THEN the same report row reaches `ready` with one artifact
- AND no second report row or duplicate event exists

## Non-goals

- No automatic/batch generation, no F4/F5 cascade, no outbox/worker, no integration delivery.
- No web UI, no signed URLs, no template authoring surface (templates are seed-only).
- No per-audience redaction variants: the professional PDF is the only audience in F6.
- No real data, no LLM, no reinterpretation of F4/F5; `test_web.py` debt stays untouched.

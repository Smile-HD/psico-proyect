# Exploration: F6 — Traceable Reports, PDF, and Integration

Change: `2026-08-11-f6-reports-pdf-integration` · Owner: Ivan · Phase: F6
Explored against `master` @ `adc7ae6` (`docs(openspec): archive f5-profiles-recommendation change`), 2026-08-11. Working tree clean except untracked `HANDOFF-F6.md` and `usuarios.md` (`usuarios.md` untouched by this exploration). `.codegraph/` verified up to date (155 files / 2,275 nodes / 5,411 edges).

## Status

**Ready for proposal** — every handoff claim verified against the repo (no discrepancies), all eight open decisions analyzed with tradeoffs and intentionally left **open** for the proposal round. Exploration does not ratify any option.

## Executive Summary

F6 consumes the completed F4/F5 chain (persisted `score_runs` + `recommendation_results`), composes a deterministic report snapshot, renders a PDF through a replaceable adapter, and — only if ratified — delivers it to an integration. The database already carries empty-but-migrated `reports`/`report_templates` scaffolding (migration 0003), but that scaffolding ratifies nothing: no pins to sources, no template lifecycle, no CHECK constraints, no artifact fields, no reporting module, no routes, no capability, no audit event, no PDF library, no storage, no web surface. The change requires a linear migration after `0005_catalog_four_level` (if pins/versioning/states/artifact fields are ratified), seed/reset extension with tests, and lockstep ratification (permissions, EVENT_CATALOG, contracts README, specs, tests) for any new capability/event. Eight product/technical decisions remain open; the proposal round must close them with the owner before spec/design. Exploration scope is research only: no code, seed, spec, or schema was modified.

## Key Findings (handoff claims verified against baseline `adc7ae6`)

All handoff claims checked against real files; **zero discrepancies found**. Notable confirmations:

| Area | Verified evidence |
| --- | --- |
| Reporting models are bare scaffolding | `services/api/app/models/reporting.py`: `Report` = id/session_id FK/template_id FK nullable/format default pdf/status default pending/generated_at nullable + SyntheticMixin. `ReportTemplate` = id/key UNIQUE/name/description/template_body nullable + SyntheticMixin. No CHECKs, no timestamps, no pins, no artifact fields. Matches migration 0003 (`0003_scoring_recommendation_reporting_audit_seed.py`). |
| No F6 code exists | No `modules/reporting/`, no `routes/reports.py`, no `schemas/reports.py`; `app/api/router.py` registers auth/seed/audit/sessions/consent/catalog/results/recommendations only. |
| F4/F5 consumption surfaces match | `ScoringRepository.latest_completed_run` (computed_at DESC, id DESC); `RecommendationRepository.latest_generation_anchor` + `list_generation_rows` (group by shared `created_at`). No generation entity exists — a generation is only a timestamp group. |
| F4/F5 no-leak payloads | `ResultsResponse` (labels/scores/run/reference/norm_note verbatim; never option values/keys) and `RecommendationsResponse` (exact fields, code-constant disclaimer, percentiles only inside justification). `test_session_api.py:375` no-scoring boundary intact. |
| Access matrix | `CAPABILITIES` ends at `view_recommendations`; no report capability. `test_auth.py::test_capability_matrix_matches_contract` locks the matrix. |
| Audit catalog | `EVENT_CATALOG` ends at `recommendation.generated`; `test_audit.py::test_event_catalog_matches_contract` locks it. Deny-list + append-only trigger verified. |
| Seed/reset gap (real trap) | `SEED_TABLES` (loader.py) includes `recommendation_rules`/`recommendation_results` but **not** `score_runs`, `reports`, `report_templates`; `_seed_reset_preflight` has dependency queries for catalog/sessions/references/recommendation rows but **none** for `score_runs` or `reports`. A runtime report/run referencing a seed session would fail the delete mid-reset without the stable `seed_reset_dependency_conflict`. |
| Seed content | `SEED_VERSION = "1.1.0"`; 30 profiles with completed sessions + 20 responses each, no score_runs; `test_seed.py::test_f5_f6_seed_state_after_seed` pins rules>0, results/reports/templates=0. No template fixture exists. |
| PDF/storage/integration stack | `pyproject.toml` has NO PDF library; no python Redis client; no object storage/outbox/worker. Redis exists in Compose/Settings only (`redis:7-alpine`, `redis_url` setting) — not a delivery implementation. |
| Web | `apps/web/app` contains only login/catalogo/evaluacion routes; no results/recommendations/reports UI. 2 inherited `test_web.py` failures documented (not re-run this session; last full evidence: F5 verify 219 collected / 217 passed / 2 failed). |
| Profile reservation | F4 tests claim `evaluado_01..20` (API 01–18, repo 19, service 01–06/20), F5 claims 21–30 (API 21–26, repo 27–28, service 29–30). No free shared pool: F6 must build runtime fixtures (dev accounts admin/psicologo/evaluado) or audit disjoint profile usage + delta counts. |
| CodeGraph | `codegraph status`: up to date, 155 files / 2,275 nodes / 5,411 edges — matches the handoff exactly. |

**Note on testing**: this exploration did not re-run the suite (read-only phase; last authoritative evidence remains F5 verify at `1517ec7`). The suite must be re-measured during apply/verify.

## Open Decisions — Options Analysis (NO final answers; proposal must ratify)

### D1. Audience and ownership: who generates, lists, reads, downloads, delivers — and for which sessions

Current ratified precedent: `view_results`/`view_recommendations` = admin ✅ / psicólogo ✅ / evaluado ✅ own sessions only (service-enforced ownership; foreign access → `FORBIDDEN` + `auth.denied`). No report capability exists; F6 cannot extrapolate the matrix without ratifying it.

- **A. Professional-only reports (admin + psicólogo, any session; evaluado excluded).** The report is the professional deliverable; evaluado retains F4/F5 API visibility. Simplest privacy posture, smallest capability surface (one new capability or reuse of an existing role gate), no evaluado content/redaction split needed in D4.
- **B. Evaluado included for own sessions (mirror F4/F5).** Consistent with the ratified matrix and the "own results" story; but multiplies D4 content decisions (full vs redacted PDF for evaluado), raises delivery/consent questions for PDFs to the subject, and adds `auth.denied` paths for foreign sessions.
- **C. Split capabilities per operation (e.g. `view_reports`, `download_reports`, `manage_report_templates`).** Finest granularity and cleanest deny-by-default, but the largest lockstep surface (permissions.py, contracts README §6, test_auth.py, spec deltas) and more decision points for proposal.

Complexity: A Low · B Medium · C Medium–High.

### D2. Trigger and preconditions: manual vs automatic vs batch; missing-score/recommendation behavior

Precedent: F4/F5 are eager, manual, idempotent mutations (`POST .../score`, `POST .../generate`) with `session:{id}` keys; availability errors are indistinguishable (`NOT_FOUND`/`resource_not_found`); `in_progress` → `CONFLICT`/`session_not_completed`.

- **A. Manual trigger (e.g. `POST /api/v1/reports/{session_id}/generate`)** requiring completed session + completed run + a recommendation generation, all-or-nothing, **never invoking F4/F5 in secret** (handoff base). Mirrors F4/F5 exactly; deterministic; client-driven; easiest to test.
- **B. Automatic generation on F5 completion** (chained inside the recommendation service). Zero extra clicks, but couples F6 into F5's transaction, needs a template default + failure semantics at completion time, and expands F5's blast radius — contradicts the "no hidden dependency triggering" base unless explicitly ratified.
- **C. Batch/backfill trigger** (generate reports for a set of sessions). Requires a list/selection surface and batch idempotency; out of MVP proportion unless the product names a batch use case.

Precondition behavior sub-options: (i) fail without effects (`NOT_FOUND` for missing/unscored/ungenerated, `CONFLICT` for in_progress) — matches F4/F5 no-leak; (ii) explicit cascade (trigger score/generate from the report endpoint) — rejected by the handoff base ("No disparar F4/F5 en secreto") and by the invariant "no reinterpretation of F4/F5"; a cascade is a product decision that changes F4/F5 contracts, not something exploration can assume.

Complexity: A Low · B Medium · C High.

### D3. Template lifecycle: versioning, immutability, snapshot, default

Current: `report_templates` has `key` UNIQUE, editable `template_body`, no version/status/locale/checksum/ownership. Editable-in-place contradicts the project's immutability culture (instruments).

- **A. Immutable versioned templates** (version rows or version columns + status lifecycle draft/published/retired; the report pins the exact template version id). Matches the instrument-versioning invariant; reproducible historical renders; requires migration + template management surface (or seed-only templates).
- **B. Snapshot-only** (report stores its own content snapshot — rendered body or resolved placeholders — at generation time; template rows remain a lightweight catalog). Minimal schema change; templates can evolve freely because each report carries its snapshot; loses explicit "template version" traceability (snapshot is the trace).
- **C. Versioned template + per-report snapshot** (both: pin `template_version_id` and keep the resolved content). Maximum traceability and render reproducibility; largest schema/migration.

Default template sub-option: fixed code-constant key (e.g. `informe-basico`) selected when none is supplied vs an admin-managed `is_default` flag. Seeding a default template is possible but **touches the seed/reset gap** (see Cross-cutting) and must be ratified with ownership (`synthetic=True`/`source='seed'`, SEED_TABLES, preflight, manifest, reset tests).

Complexity: A Medium · B Low · C High.

### D4. Content and redaction: which F4/F5 fields per audience; norm_note vs disclaimer

F4 payload fields: per-scale `label/raw/direct.z/transformed{percentile,t_score,eneatype}` + `overall` + run/reference ids + `norm_note` verbatim. F5 payload fields: `generated_at`, code-constant disclaimer, `items[{program_id, program_name, program_code, fit_score, justification}]`. `norm_note` (F4, baremo research-only) and the F5 disclaimer are **distinct contracts** — one cannot substitute for the other (handoff explicit; both specs pin them).

Field-group sub-decisions (each needs an audience-aware answer):
- Scores in the PDF: full raw/z/T/eneatype/percentiles vs percentile-only vs overall-only. F4 permits these on the API for authorized roles; the PDF is a new exposure surface, so "what the API allows" does not automatically ratify "what the PDF prints".
- Recommendations in the PDF: fit + justification included vs excluded vs summary-only (fit without justification text).
- Disclaimer handling: both notes (norm_note in a "baremo" section + F5 disclaimer in a "recommendations" section), only the disclaimer, or only norm_note — audience-dependent.
- Identity data: session id, evaluado name (PII beyond actor id is deny-listed for audit, but a report is a document: who may carry the evaluado's name?), institution, date.
- Redaction mechanics: fixed per-audience section sets (professional full / evaluado redacted) vs a single content set for all authorized audiences.

Non-negotiables regardless of choice (invariants): no option ids/values, no response ids, no 1–5 mapping, no item content, no secrets/tokens; recursive no-leak scan of DTO + PDF text/metadata + audit + logs (handoff test matrix).

Complexity: Low (single audience, fixed section set) → High (per-audience variants).

### D5. PDF renderer stack: license, Unicode, fonts, Docker image

Current: no PDF library anywhere; API Dockerfile has no PDF system packages; testing must avoid fragile byte snapshots (normalized structure/text/metadata comparison is the ratified test criterion).

- **A. WeasyPrint (HTML/CSS → PDF, BSD-3).** Best typography/CSS; Unicode + font embedding via Pango/System fonts; but requires system libraries (pango, cairo, gdk-pixbuf) in the Docker image — image grows and build gains apt dependencies; HTML/CSS templates are data-like and testable.
- **B. ReportLab (direct PDF, BSD).** Pure Python wheels, no system deps, deterministic layout control, Unicode via embedded TTF (e.g. DejaVu); more layout code than HTML; Platypus suits tabular reports; license-friendly.
- **C. fpdf2 (MIT, pure Python).** Lightest; Unicode via TTF embedding; fewer primitives (manual layout); sufficient for simple structured reports.
- **D. xhtml2pdf/pisa.** HTML→PDF without system deps but weaker CSS/Unicode fidelity and slower maintenance; not recommended unless minimal-dependency HTML is a hard requirement.
- **E. LaTeX/Quarto (present in the stack for offline R analytics).** Excellent output but heavy, shell-dependent, and out of the service path; violates the template-as-data (no shell) posture.

Cross-cutting criteria for the ADR: license, Unicode + embedded fonts (Spanish text with accents is mandatory), Docker image impact, determinism (normalized, not byte-identical), testability (parse pages/text/metadata), maintenance. Effort: A Medium (image work) · B Medium · C Low–Medium · D Low · E High.

### D6. Storage, retention, and download

Current: nothing stored; `reports` has no artifact reference, checksum, size, media type, or error/retry fields.

- **Storage backend:**
  - **A. PostgreSQL** (bytea column or sibling `report_artifacts` table): single backend, transactional with the report row, same authz story, trivial rollback; grows DB dumps — acceptable for MVP volumes.
  - **B. Filesystem behind a storage adapter** (opaque key, never exposed): simple, dev-friendly; multi-instance/deployment concerns; manual retention/cleanup.
  - **C. Object storage (S3/MinIO)**: production-grade but new infra + credentials; premature unless ratified.
- **Retention:** forever (precedent: catalog ADR-003 "records retained indefinitely") vs TTL/expiry policy; if TTL, define cleanup ownership (never during `--reset`).
- **Download:** authenticated stream (`GET /reports/{id}/download` re-checking roles + ownership, same-or-stricter than metadata read — handoff base: "una URL por sí sola no concede acceso") vs signed temporary URL (needs signing infra + expiry semantics; still requires authorization at issuance).
- **Integrity fields:** checksum (sha256), size, media type, renderer version, generated_at — ratify which are persisted (handoff: "solo si la spec lo exige").

Complexity: A Low–Medium · B Low · C High.

### D7. Integration and delivery: explicit target or out of scope; async only if ratified

Current: no target named anywhere ("integración" without a target is not scope); Redis exists but is not a delivery implementation; no outbox/worker/queue; no python Redis client.

- **A. Out of F6 scope** (F6 = compose + persist + render + store + authorized download; delivery is a later phase with a named target). Smallest, honors the handoff base ("Crear outbox solo si la integración queda fuera... no crear outbox si la integración queda fuera de F6" — i.e. none if delivery is out).
- **B. Synchronous adapter to a named target** (same request writes report + pushes to target): requires the target, credentials, timeout, retry, and a delivery guarantee decision; long remote I/O must never hold a DB transaction.
- **C. Async outbox + worker** (outbox table + worker + dedupe key + correlation id + retry/backoff + dead-letter + at-least-once or effectively-once guarantee): only when the product names a target and requires async guarantees; largest surface (migration, worker, recovery tests, poison-message handling).

Any delivery path must keep payload redaction equal to the report's ratified content and must not duplicate events/reports on replay.

Complexity: A None · B Medium · C High.

### D8. Web scope: in or out of F6 MVP

Current: no results/recommendations/reports UI anywhere; session completion screen explicitly shows no scores; 2 inherited `test_web.py` failures are documented debt and must not be "fixed" inside F6.

- **A. API-only F6** (web deferred to a later phase). Matches F4/F5 precedent exactly; no new web debt; UI decisions (polling/status, role journeys, accessibility) postponed.
- **B. Minimal web surface** (e.g. psicólogo/admin: list reports, view status, download; possibly evaluado own reports if D1=B): adds Next.js routes/components/tests, `next build` typecheck, loading/error/empty/ready states, role-safe navigation — and must coexist with the inherited web debt without touching it.

Complexity: A None · B Medium–High.

## Cross-cutting Gaps (must be addressed by proposal/spec/design, with tests)

### Seed/reset dependency gap (verified real)

- `SEED_TABLES` omits `score_runs`, `reports`, `report_templates`; `collect_counts` (manifest) omits them; `_seed_reset_preflight` has no queries for them.
- Consequence: a runtime `report` (or `score_run`) referencing a seed-owned session/profile would make `--reset` fail mid-delete on an FK violation instead of the stable `seed_reset_dependency_conflict` CONFLICT; manifest counts would also lie about seed-owned reporting rows if templates are ever seeded.
- Options for proposal: (i) extend preflight + SEED_TABLES + manifest + tests for `score_runs` and `reports` (even if nothing is seeded, preflight must catch runtime dependencies and reset must scope-clean); (ii) if a default template is seeded, it joins SEED_TABLES/preflight/manifest/checksum/reset with `synthetic=True`/`source='seed'`, UUID5 keys; (iii) runtime templates/reports remain UUID4, `synthetic=False`/`source='runtime'`, never deleted by `--reset`.
- F6 tests must exercise: runtime report/run over seed session → stable preflight CONFLICT, zero deletes; seed templates (if any) recreated without touching runtime rows.

### Reporting schema gaps (verified real)

`reports` cannot express: which score run was used (no FK to `score_runs`), which F5 generation was used (no generation entity — only a shared `created_at` group on `recommendation_results`), template version/snapshot (nullable template_id only), status/format vocabulary (no CHECKs), artifact reference/checksum/size/media type/renderer version, created/updated/failed timestamps, error/retry fields, audience/locale/retention. `report_templates` cannot express version, status, locale, immutability, checksum, or ownership.

Options (for design, not resolved here):
- Pin F4 source via nullable FK `score_run_id` (clean, migration 0006).
- Pin F5 generation via (a) anchor `created_at` + result row ids (no new table, but timestamp-collision fragility and no single id), (b) a new `recommendation_generation` entity with a stable id (clean, bigger migration), or (c) a JSONB source snapshot in the report row (pins by value; no generation entity needed).
- Status vocabulary (e.g. `pending/processing/ready/failed`, or fewer) and `format` CHECKs only after the state machine is ratified (handoff: "Añadir CHECKs solo después de fijar el vocabulario").
- A linear migration `0006_*` after `0005_catalog_four_level`, schema-only from models, with fresh-upgrade/idempotent/linear-history tests extended; rollback = disable routes/workers + forward fix, never destructive revert with runtime data.

## Invariant Boundaries (must hold for every option)

- No reinterpretation of F4/F5: the composer consumes persisted snapshots (`score_runs.raw`, recommendation rows/aggregates); it never imports or invokes scoring/recommendation engines, never recomputes, never changes formulas, rules, DTOs, or no-leak boundaries.
- No LLM in the productive path: composition, templates, explanation, delivery.
- No real data: everything synthetic/research-only; no real UAGRM norms or claims; reports carry the ratified disclaimers, never real claims.
- No leak: reports, PDFs, audit, logs, and integration payloads contain no option ids/values, response ids, 1–5 mapping, item content, secrets, or PII beyond what is expressly ratified per audience.
- Audit aggregate-only: new events (if ratified) carry ids/status/counts/checksum-size only; lockstep across `permissions.py`, `audit.py`, contracts README, specs, `test_auth.py`, `test_audit.py`.
- Mutations idempotent: `Idempotency-Key` on every mutating trigger; replay never duplicates report/PDF/audit/delivery; same key + different body → `CONFLICT`/`idempotency_key_reused`.
- Templates are data, never code: no arbitrary evaluation, imports, shell, filesystem, or network.
- Failures do not degrade to success: renderer/storage/audit/delivery failures never leave a `ready` report without an artifact, and never duplicate success events.

## Risks

- **Open product decisions stall the chain**: eight decisions (D1–D8) must be closed in the proposal round; each unclosed one is a `blockedReason` for spec/design and a stop-signal for apply.
- **Schema under-specification**: adding pins/versioning/CHECKs/artifact fields without a ratified state vocabulary forces migration rework; the migration must be designed once, linearly, with model+migration tests in lockstep.
- **Seed/reset regression**: runtime reports over seed sessions (tests, demos) silently break `--reset` if preflight/SEED_TABLES are not extended and tested before reports exist in practice.
- **PDF determinism/test fragility**: byte-comparison tests will break on renderer metadata; the test strategy must normalize (structure/text/metadata) and pin fonts/locale/timezone/clock.
- **Leak regressions**: score/justification/option-value leakage through DTO, PDF text or metadata, audit, logs, or delivery payload — needs recursive scan tests per the handoff matrix.
- **Lockstep omissions**: new capability/event must land in permissions.py + audit.py + contracts README + specs + test_auth/test_audit in one unit; a missed piece fails the lockstep tests.
- **Profile contamination**: F4/F5 claim all 30 profiles; F6 must use runtime fixtures (dev accounts) or audited disjoint profiles with delta counting — absolute counts over the shared seed will flake.
- **Docker image staleness**: new PDF system packages/migration require `docker compose build api`; stale images produce phantom failures (AGENTS.md trap).
- **Review budget**: module + migration + renderer/storage adapters + routes + seed/reset + 4+ spec deltas + 5+ test files will likely exceed the 400-line guard; `sdd-tasks` must forecast chained slices (domain → schema/repository → renderer/storage seams → service+lockstep → API → integration/web if ratified).

## Ready for Proposal

**Yes.** Tell the user: exploration verified every HANDOFF-F6 claim against baseline `adc7ae6` (zero discrepancies) and analyzed all eight open decisions with tradeoffs but chose nothing — open decisions must remain open for the owner. The proposal round must obtain real owner answers to at least: (1) audience/ownership matrix and whether evaluado accesses reports; (2) trigger (manual vs auto vs batch) and missing-precondition behavior; (3) template lifecycle (versioned immutable vs snapshot vs both) and default template; (4) exact content/redaction per audience and handling of `norm_note` vs F5 disclaimer; (5) PDF renderer choice (licence/Unicode/fonts/Docker impact); (6) storage backend, retention, checksum, and download mode (authenticated stream vs signed URL); (7) integration target + delivery guarantee, or explicit out-of-scope; (8) web scope in/out of F6 MVP. Additionally the proposal must ratify the seed/reset extension and the reporting schema migration direction (pins, generation representation, state vocabulary, artifact fields). Recommend starting `proposal` next, keeping `exploration → proposal → spec → design → tasks → apply → verify → archive`.

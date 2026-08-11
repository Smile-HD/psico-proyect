# Exploration: F4 — Motor de calificación (scoring engine)

Change: `2026-08-10-f4-scoring-engine` · Owner: Juan Carlos · Phase: F4
Explored against `master` state per `HANDOFF-F4.md` (working tree clean, no active changes).

## Current State

F1–F3 delivered everything F4 consumes; **nothing scoring-related exists in code**:

- **Persistence**: `reference_sets`, `reference_values`, `score_runs` exist since migration `0003_scoring_recommendation_reporting_audit_seed.py` (F1), empty except the seed. `score_runs` has NO unique constraint on `session_id` — multiple runs per session are schema-legal; `status` defaults `pending`, `raw` JSONB, `computed_at` nullable, plus `synthetic`/`source` columns (SyntheticMixin) that runtime rows must set (`synthetic=False`, `source="runtime"`, same as F3 sessions).
- **Seed (verified in `seed/loader.py` + fixtures)**: `TP-S-01:v1` (20 items / 5 scales / 100 options, published+immutable), baremo `RS-TP-S-01` with 30 `reference_values` rows (10 per-scale `mean`/`sd` + 20 `overall` percentile rows mapping raw 1–20 → percentile 2–97, t_score 30–67, eneatype 1–7), `norm_note` "NO es una norma UAGRM. Datos inventados para desarrollo.", 30 profiles `evaluado_01..30` each with 1 `completed` session and 20 responses (600 total).
- **Private mapping**: `fixture_projection()` at `app/modules/assessment_authoring/projections.py:51` exposes `instrument_version_id` + scales → items → `response_options [{id, value 1–5}]`. Only the seed and F3's session runtime consume the 1–5 values today; the evaluator projection and public payloads never call it. F3 also keeps a private `response_option_map` in `session_runtime/repository.py`, but the **ratified F4 contract is `fixture_projection`** (contracts §7.5/§7.6.4).
- **F3 handoff**: `completed` sessions pin `instrument_version_id` verbatim; `responses` rows are immutable-by-construction (upsert on `(session_id, item_id)`, CHECK `value BETWEEN 1 AND 5`). No scoring, percentile, eneatype, or reference term crosses any public payload (asserted by `test_session_api.py:375`).
- **API conventions**: routers under `/api/v1` (prefix in `app/api/router.py`), thin adapters, `require_roles(...)` deny-by-default gate (capability `view_results` = admin/psicólogo/evaluado already ratified in `permissions.py`), single error envelope, `Idempotency-Key` on every mutating endpoint, idempotency store from `assessment_authoring/idempotency.py` (scope strings like `session:{id}`), module pattern `domain.py / service.py / repository.py / errors.py` (F2 `assessment_authoring`, F3 `session_runtime`).
- **Testing**: 149 collected (147 passed + 2 inherited F2b failures in `test_web.py` — do NOT touch). No scoring/reference/results tests exist. `scripts/test.ps1` masks the pytest exit code — output counts are the authoritative evidence. F4 slice selector: `-k "scoring or reference or results"`.
- **Web**: `design-system.md` has NO results/reporting section — F4 is API-only; results UI belongs to F5/F6.

## Affected Areas

| Area | Why |
| --- | --- |
| `services/api/app/modules/scoring/` (NEW: domain/service/repository/errors) | The F4 module per the F2/F3 pattern; domain holds the pure raw→direct→transformed chain |
| `services/api/app/api/routes/results.py` (NEW) | Read surface for results per role (admin/psicólogo/evaluado-own) — or `scoring` prefix, design decision |
| `services/api/app/schemas/results.py` (NEW) | DTOs; results carry scale labels, scores, and the baremo `norm_note`; never option values/keys |
| `services/api/app/modules/assessment_authoring/projections.py` | Consumed (read-only) via `fixture_projection` — do not modify |
| `services/api/app/models/scoring.py` | Consumed read-only; `ScoreRun` is the persistence destination |
| `services/api/app/modules/session_runtime/repository.py` | Consumed read-only (session/response reads, pinned version) — do not modify |
| `services/api/app/seed/loader.py` + `fixtures/reference.json` | Consumed read-only; seeding is already complete for F4 |
| `services/api/app/api/router.py` | Register the new router under `/api/v1` |
| `services/api/tests/test_scoring_*.py`, `test_results_api.py` (NEW) | Strict TDD slice; existing `test_seed.py`/`test_schema.py` already pin the reference-set shape |
| `openspec/specs/` (scoring/results domain delta) | New ratified spec for the F4 change; audit event `scoring.run` (if mutation) MUST be ratified here |

## Approaches

### 1. Eager persisted runs (score on demand, persist to `score_runs`)
Trigger endpoint (e.g. `POST /api/v1/results/{session_id}/score` or `/api/v1/sessions/{id}/score`) + read endpoint(s). Service: load session+version+reference via repository, invoke pure domain, persist `score_runs` row (`status pending → completed`, `raw` JSONB, `computed_at`), audit `scoring.run` (new ratified event). Idempotency-Key required; scope `session:{id}`.
- Pros: score_runs table finally used as designed; recomputation history; read path stays cheap; matches handoff §5.3 ("Persistir resultados en score_runs").
- Cons: mutation means Idempotency-Key + new audit event that MUST be ratified in the change; a state decision (re-run vs single-run) is needed since the schema allows duplicates; slightly larger surface.
- Effort: Medium

### 2. Lazy compute-on-read (no mutation, no new event)
Only `GET /api/v1/results/{session_id}`. Every read runs the pure chain in the service; `score_runs` optionally written opportunistically (or left untouched for F6). No Idempotency-Key, no new audit event, smallest surface.
- Pros: zero mutation surface; no event ratification; simplest spec; idempotent reads by construction.
- Cons: leaves `score_runs` unused (handoff expects persistence); recompute cost per read; no run history; diverges from the stated "persist results" scope.
- Effort: Low

### 3. Hybrid (recommended): lazy compute + persisted cache row
Read endpoint computes via the pure chain and persists/updates the `score_runs` row for the `(session, reference_set)` in the same request — but a **GET that persists is a mutation in spirit**: it must either keep the idempotency/audit contract (needs event ratification) or be justified as an internal cache. This collapses into Approach 1 with a cleaner read-only public surface.
- Pros: public surface is read-only for all roles; persistence happens; no Idempotency-Key visible to consumers if the write is an internal cache detail.
- Cons: hidden side effect in a GET breaks the project's "mutation requires Idempotency-Key + audit" convention unless ratified; spec must be very explicit about the cache semantics.
- Effort: Medium

### API prefix: `/results` vs `/scoring`
`/results` matches the ratified access-matrix capability token ("View results"), reads naturally for all three roles, and leaves `/scoring` free for the internal module name (`app/modules/scoring/`). `/scoring` would mirror the module but reads oddly for a non-technical evaluado consumer. Existing routers are domain-named (`sessions`, `catalog`, `consent`); `results` follows that convention.

## Recommendation

**Approach 1 (eager persisted runs)** with the public surface under **`/api/v1/results`**: `POST /api/v1/results/{session_id}/score` (mutation, `Idempotency-Key`, scope `session:{id}`, audits ratified `scoring.run` with aggregate metadata only) plus `GET /api/v1/results/{session_id}` (read-only, roles per access matrix, evaluado own-only). This is the only approach that satisfies all three handoff pillars simultaneously: score_runs persistence, pure engine invariant, and the mutation conventions. Module layout mirrors F2/F3: `app/modules/scoring/{domain,service,repository,errors}.py`.

**Engine contract to pin in the spec** (the seeded data leaves one genuine ambiguity): per-scale raw = sum of the 4 mapped 1–5 values (range 4–20); direct = z-score via `(raw − mean) / sd` from the per-scale `mean`/`sd` reference rows; transformed = percentile/T/eneatype. The seeded lookups only cover `overall` raw 1–20, so the spec MUST decide how per-scale percentiles derive from the z (normal-CDF mapping, or mean/sd→percentile approximation) and how `overall` maps (sum of scales → lookup raw 1–20). Whatever is chosen must be explicit; tests then pin it. **Reference rows key on the scale LABEL string** (`ReferenceValue.scale`), which matches `items.json` labels exactly — the join key for raw→reference is the label, not the scale id.

**Availability rule**: missing session → `NOT_FOUND` / `resource_not_found` (indistinguishable, per F2/F3 no-leak convention); existing session not `completed` (in_progress) → `CONFLICT` with stable token `session_not_completed` (mirrors F3's `invalid_session_state` style); never score, expose, or leak `in_progress` responses. Any results output MUST carry the baremo `norm_note` (research-only disclaimer) and scale labels; numeric option values/answer keys never cross the API.

## Risks

- **Transformed-chain math ambiguity**: percentile derivation for per-scale scores is not uniquely determined by the seed; if the spec leaves it open, tests and implementation drift. Must be pinned in the F4 spec (normal-CDF or table interpolation, exact rounding).
- **New audit event**: `scoring.run` is not in the ratified catalog (contracts §3); adding it requires explicit ratification in the F4 change, and metadata must be aggregate-only (ids, counts, timestamps) — never response values.
- **PR budget**: engine + repository + 2 routes + schemas + spec + ~5 test files will likely exceed the 400-line review budget; `sdd-tasks` should forecast chained slices (e.g. domain+unit → service+repository+persistence → API+audit).
- **Wrapper masks exit code**: `scripts/test.ps1` returns 0 on failure; verification must cite pytest output counts (149 collected baseline, 2 inherited `test_web.py` failures untouched).
- **Docker image staleness**: after any `services/api` change, `docker compose build api` is required or alembic/app from the old image produce phantom failures.
- **Boundary regressions**: F4 must not break the no-scoring boundary asserted by `test_session_api.py:375`; the 1–5 mapping and `fixture_projection` stay non-public.
- **Inherited debt to document, not fix**: the 2 F2b `test_web.py` failures; no E2E runner (F4 is API-only, so build+owner checklist is not needed unless web changes).

## Ready for Proposal

Yes — scope is fully verified against real code and matches `HANDOFF-F4.md` §5 with no contradictions. Tell the user: the engine, module layout, persistence, and error model are unambiguous; the two decisions the proposal/spec must ratify are (a) the exact transformed-chain math (per-scale percentile derivation) and (b) `scoring.run` event ratification if the eager-trigger approach is chosen. Recommend starting the change with `proposal` next, keeping `exploration → proposal → spec → design → tasks → apply → verify → archive`.

# Design: F5 — Declarative Profiles and Recommendation

## Technical Approach

Implement eager, deterministic generation from active `recommendation_rules` rows only. The repository consumes F4's latest completed `ScoreRun.raw`, programs, and rules; the pure domain receives snapshots and returns contributions plus an internal trace. The service persists per-rule runtime results and aggregate audit atomically; GET aggregates the latest generation. No migration, LLM, stored SQL, or embedded productive rules; F4/F3/F2 remain unchanged.

## Architecture Decisions (ADRs)

| ADR | Choice | Alternative rejected | Rationale |
|---|---|---|---|
| 1. Layering | Create `app/modules/recommendation/{domain,errors,repository,service}.py`; domain has no DB/I/O. | DB-aware engine/editing scoring | Mirrors F4 and protects the boundary. |
| 2. Fit | Validate `percentile_min` with exact scales or `overall`, `min_percentile` 1–99; default missing weight to `1.0`, reject non-positive; round each `100*w*satisfied/Σw` half-up to `Numeric(5,2)`, sum, exclude zero-rule programs, order fit DESC/name ASC. | Float `round()` or one-shot fit | Matches pinned vocabulary, math, and precision. |
| 3. Transaction | Load F4 latest run; insert `fit_score` contribution, justification, and runtime flags with one `created_at`; audit `commit=False` with ids/counts/timestamps only; store idempotency and commit once. Same key/body replays, different body conflicts, new key generates. Roll back on integrity/audit failure. | Separate audit commit or compute-on-read | Prevents partial generations, leakage, and replay drift. |
| 4. API/security | Add both exact recommendation routes; `require_roles(ADMIN, PSICOLOGO, EVALUADO)`, service ownership with evaluado-own-only, and `session:{id}` keys. | Reuse `view_results` or route-only ownership | NEW capability stays explicit and deny-by-default. |
| 5. DTO | Exact outer fields: `session_id`, `generated_at`, disclaimer, `items[{program_id,program_name,program_code,fit_score,justification}]`; aggregated `justification` is the template sentences joined per program in rule id ASC order. Per-rule traceability remains in persisted `RecommendationResult.justification` text; `generated_at` is the only public generation metadata. | Expose structured rule fields, run/result/reference IDs, or `norm_note` | Matches the authoritative payload contract; no unsanctioned public fields or shape are invented. |
| 6. Ratification | One slice updates permissions, contracts §§3/6, `EVENT_CATALOG`, and `test_audit.py`; `view_recommendations` and `recommendation.generated` are NEW. | Split changes | Reuse existing F4 `resource_not_found`, `session_not_completed`, idempotency tokens, and `ApiError` mapper without drift. |
| 7. Seed/reset | Add 4–6 programs/rules under `institution:dev`/`faculty:dev` beside `program:dev`, UUID5 namespaces, active weighted rules with exact labels/`overall`, seed flags, `SEED_TABLES += {recommendation_rules,recommendation_results}`/version, and atomic preflight: runtime results referencing seed rules cause conflict before deletion; reset deletes seed-owned rows only. | Inline fixtures or seed results | Preserves idempotency, FK safety, and runtime-only results. |
| 8. Testing | Strict RED→GREEN layers; reserve `evaluado_21..30`, use deltas, run `-k "recommendation or program"`. | Shared absolute counts/mock API | Avoids contamination and proves real-PG behavior. |
| 9. Rollout | No migration/flag; deploy F5 together; rollback disables/reverts F5 only. | Rewrite F4/remove history | 0003 suffices and existing history remains safe. |

## Data Flow

```text
POST generate: Route -> Service(auth/owner/idempotency) -> Repository(F4 run + rules/programs)
             -> Domain -> result rows + audit(commit=False) + replay row -> one commit -> DTO
replay:       Service -> idempotency lookup -> original DTO (no writes)
```

```text
GET latest: Route -> Service(owner) -> Repository(anchor created_at DESC, id DESC)
          -> rows sharing anchor timestamp -> aggregate/order -> DTO
in_progress POST -> CONFLICT/session_not_completed
foreign evaluado -> FORBIDDEN + auth.denied
missing/unscored POST or no-generation GET -> identical NOT_FOUND/resource_not_found
```

## File Changes

| File | Action | Description |
|---|---|---|
| `services/api/app/modules/recommendation/` | Create | Rule engine, F5 errors, repository, service. |
| `services/api/app/schemas/recommendations.py`, `services/api/app/api/routes/recommendations.py` | Create | Strict DTOs and protected adapters. |
| `services/api/app/api/router.py` | Modify | Register the new router. |
| `services/api/app/core/{permissions,audit}.py`, `packages/contracts/README.md`, `services/api/tests/test_audit.py` | Modify | Capability/event lockstep. |
| `services/api/app/seed/loader.py`, `services/api/app/seed/fixtures/{programs,recommendation_rules}.json`, `services/api/tests/test_seed.py` | Modify/Create | Seed, manifest, reset preflight. |
| `services/api/tests/test_recommendation_{domain,repository,service}.py`, `services/api/tests/test_recommendation_api.py` | Create | F5 TDD layers; models/migrations/F4 modules unchanged. |

## Interfaces / Contracts

Snapshots contain score-run percentiles, program identity, and rule `{id,type,params}`; persisted result rows retain one per-rule justification sentence, while the DTO joins those sentences per program in rule id ASC order. Invalid type/scale/params raise NEW `recommendation_integrity_error` (`INTERNAL_ERROR`) without skipping. The v1 constant is: “Recomendaciones orientativas sobre datos sintéticos (research-only). No constituyen una norma UAGRM ni asesoramiento profesional.” Never expose structured rule fields, options/response IDs, 1–5 mapping, item content, raw scores, or `norm_note`; recursively scan DTOs.

## Testing Strategy

| Layer | Coverage |
|---|---|
| Unit | Fit vectors/rounding, zero-rule exclusion, weights, vocabulary/params, ordering, trace text. |
| Repository/service | Latest selection, row flags/precision, ownership, idempotency, audit rollback/reset conflict; trigger scoring first. |
| API/seed/contract | Real-PG TestClient roles, five availability/error flows, recursive no-leak, seed counts/idempotency/reset; leave two inherited `test_web.py` failures. |

## Threat Matrix

Routing changes, but no shell, subprocess, VCS, or PR automation exists: Documentation-like paths — **N/A** (no executable docs); Git repository selection — **N/A** (no Git integration); Commit state — **N/A** (no commit automation); Push state — **N/A** (no push integration); PR commands — **N/A** (no PR automation). Therefore no threat-matrix RED tests or tasks apply.

## Migration / Rollout

No migration: tables exist since 0003. Deploy module/routes, seed, and ratifications together. Rollback disables/reverts F5, preserving F4 runs/sessions/audit/runtime history; reset remains fail-closed for runtime results referencing seed rules.

## Open Questions

None; all design-level choices are pinned by the proposal/specs.

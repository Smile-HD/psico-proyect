# Design: F4 — Scoring Engine and Results API

## Technical Approach

Add a thin `/results` adapter over a new `scoring` module. The repository reads the completed session, pinned version, private `fixture_projection`, response option ids, and only `RS-TP-S-01`; the pure domain receives frozen dataclasses and returns frozen score dataclasses. It computes `raw=sum(values)`, `z=(raw-mean)/sd` (`sd=0 => 0`), clamped percentile/T/eneatype, and the specified overall rescale plus exact lookup. The service owns orchestration, transactions, idempotency, DTO projection, and audit. No F2/F3 module or seed data is modified.

## Architecture Decisions (ADRs)

| ADR | Choice | Alternatives rejected | Rationale |
|---|---|---|---|
| ADR-01 Φ | `math.erf`: `Φ(z)=0.5*(1+erf(z/sqrt(2)))`; `RH(x)=floor(x+0.5)` for all real x. | scipy; lookup table | Stdlib double precision is deterministic, ≤1e-12 against vectors, and has no table interpolation/maintenance risk. |
| ADR-02 layering | `domain.py` is DB/I/O/clock/random/side-effect free; `service.py` orchestrates; `repository.py` persists; `errors.py` exposes `session_not_completed`, `resource_not_found`, `reference_unavailable`, and typed integrity errors as `ApiError`s. | DB-aware engine; changing F3 | Frozen typed inputs/outputs make the purity boundary directly unit-testable and preserve ownership. |
| ADR-03 API | Add `POST /api/v1/results/{session_id}/score` (required `Idempotency-Key`, scope `session:{id}`) and `GET /api/v1/results/{session_id}`; route roles are `require_roles(ADMIN, PSICOLOGO, EVALUADO)`, with own-only enforcement in service. The optional JSON object defaults to `{}` and is only canonicalized for idempotency. | Exposing scores through `/sessions`; separate permission system | Matches the access matrix and preserves F3's labels/options-only boundary. F4 defines `session_not_completed` as a new stable token in `app/modules/scoring/errors.py` and wires it through the existing `ApiError` mapper mechanism, following F3's `invalid_session_state` pattern; `resource_not_found` reuses the existing NOT_FOUND token. |
| ADR-04 runs | Create `pending`, compute, then mark `completed` with `computed_at`, explicit `synthetic=False`, and `source='runtime'` in one transaction. Do not lock sessions or runs; existing idempotency lookup/unique scope protects replay, while distinct keys may create multiple legal runs. | Unique session run; session lock | Completed responses are immutable, so concurrent fresh runs are identical; latest selection remains deterministic. |
| ADR-05 audit | Add `scoring.run` to `EVENT_CATALOG`, contracts README, and catalog tests; call `audit.record(..., commit=False)` in the scoring transaction. Metadata is exactly session/version/reference/run ids, `response_count`, `scale_count`, and `computed_at`. | Per-response or score metadata | Reuses F3's writer and deny-list while making audit atomic and aggregate-only. |
| ADR-06 testing | Strict RED→GREEN unit, repository/service, and TestClient/PostgreSQL integration coverage; run slice `-k "scoring or reference or results"`. | Mock-only API tests | Math purity needs fast parameterized tests; real DB proves JSONB, transaction, idempotency, roles, and latest-run behavior. |
| ADR-07 rollout | No migration or flag. Deploy module/routes and contract updates; rollback by reverting/disable routes, preserving existing runs/audit and never reverting F3/catalog. | Data rewrite or seed rollback | `score_runs` already exists since migration 0003 and is forward-compatible. |

## Data Flow

Reads map to existing consumers: `SessionRepository.get_session/get_version/answer_option_ids`, unchanged `fixture_projection` for option-id→1–5 mapping, direct `ReferenceSet/ReferenceValue` reads for the pinned reference, and direct `ScoreRun` writes/reads. Scale labels come from the loaded immutable `Scale` rows; `fixture_projection` remains private.

```text
POST -> route -> service -> repository reads -> pure domain -> pending/completed ScoreRun
                                      |                         |-> audit + idempotency -> commit
GET  -> route -> service -> owner + latest(computed_at DESC, id DESC) -> DTO
                      \-> no completed run (including completed-but-unscored) -> NOT_FOUND/resource_not_found, same as missing
```

```text
score happy: Route -> Service -> Idempotency -> Repo -> Domain -> Run/Audit -> commit
replay:      Route -> Service -> Idempotency -> original DTO (no writes)
latest:      Route -> Service -> owner + Repo(latest DESC, id DESC) -> DTO
no run:      Route -> Service -> no completed run -> NOT_FOUND/resource_not_found (no-leak)
in_progress: Route -> Service -> session status -> CONFLICT/session_not_completed
foreign:     Route -> Service -> owner check -> FORBIDDEN (no run)
```

## File Changes

| File | Action | Description |
|---|---|---|
| `services/api/app/modules/scoring/__init__.py`, `domain.py`, `service.py`, `repository.py`, `errors.py` | Create | Pure engine, orchestration, mapped reads/ScoreRun persistence, stable errors. |
| `services/api/app/schemas/results.py`, `services/api/app/api/routes/results.py` | Create | Strict result DTOs and two protected endpoints. |
| `services/api/app/api/router.py` | Modify | Include results router. |
| `services/api/app/core/audit.py`, `packages/contracts/README.md`, `services/api/tests/test_audit.py` | Modify | Ratify `scoring.run` in lockstep. |
| `services/api/tests/test_scoring_domain.py`, `test_scoring_repository.py`, `test_scoring_service.py`, `test_results_api.py` | Create | F4 RED/GREEN unit and PostgreSQL integration suites. |

## Interfaces / Contracts

Pure types: `ScoringInput(version_id, reference_set_id, scales: tuple[ScaleInput,...], overall_rows)` and `ScoreResult(scales, overall)`, with frozen nested dataclasses. Each scale has exactly four finite mapped integers, label, mean, and sd; overall uses `RH(1+19*(Σraw-4n)/(16n))` and an exact raw 1–20 row. `raw` JSONB is exactly `{"scales":[{"label", "raw", "direct":{"z"}, "transformed":{"percentile","t_score","eneatype"}}], "overall":{"raw","transformed":{"percentile","t_score","eneatype"}}}`. The API wraps it with `session_id`, `run: {id,status,computed_at}`, `reference_set_id`, and verbatim `norm_note`; T is serialized as `t_score`. It never returns option ids/values, response ids, mappings, or item content.

## Testing Strategy

Unit: every formula, Φ vectors, half-up ties, clamps, `sd=0`, exact overall lookup, missing/non-finite integrity errors, immutability, and no DB/I/O imports. Integration: repository reads/writes, pending→completed rollback, JSONB shape, replay/new-key runs, audit deny-list, latest tie-break, in-progress and foreign-owner errors. TestClient: envelope/status/roles/own-only and recursive no-`1–5` leakage; retain the two inherited `test_web.py` failures as out-of-scope debt. E2E is unavailable.

## Threat Matrix

Routing changes, but the matrix's command/process boundaries are all N/A:

| Boundary | Applicability / reason |
|---|---|
| Documentation-like paths | N/A — no executable documentation. |
| Git repository selection | N/A — no Git command integration. |
| Commit state | N/A — no commit automation. |
| Push state | N/A — no push automation. |
| PR commands | N/A — no PR automation. |

No threat-matrix RED tests are required.

## Migration / Rollout

No migration required. Existing `score_runs`, references, and immutable F3 data remain; rollback only removes/disable the new API surface.

## Open Questions

None.

# F4 Scoring Engine — Archive Report

**Change**: `2026-08-10-f4-scoring-engine`
**Date**: 2026-08-11
**Owner**: Juan Carlos (F4; consuming F3/Jhamil)
**Final state**: ARCHIVED
**Base**: `f9cb07f` (docs: add F4 handoff document) → `47bdd2a` (HEAD at archive)
**Archive commit(s)**: `docs(openspec): archive f4-scoring-engine change` (archive move, spec promotion, this report)

## Summary

F4 gave completed sessions a reproducible, pure scoring chain and an API-only results surface on top of F3's immutable session/response data: a new `scoring` module (`domain`/`errors`/`repository`/`service`), a transactional `score_runs` `pending → completed` flow with runtime flags, the ratified aggregate-only `scoring.run` audit event (lockstep: `EVENT_CATALOG` + contracts README §3 + `test_audit.py`), and protected `POST /api/v1/results/{session_id}/score` / `GET /api/v1/results/{session_id}` routes with strict score-only DTOs, `session:{id}` idempotency, stable no-leak errors, and the verbatim research-only `norm_note`. No migration, no seed change, no F2/F3 module change, no web change. Delivered as 4 stacked slices (`auto-chain`, `stacked-to-main`) plus a tests-only isolation remediation. The earlier failed verify report was superseded by the remediation commit `47bdd2a`; the on-disk `verify-report.md` is the FINAL PASS version.

## Spec Promotion

| Domain | Action | Requirements |
|---|---|---|
| `scoring-engine` | NEW domain — full spec copied to `openspec/specs/scoring-engine/spec.md` | 4 requirements / 9 scenarios |
| `results-api` | NEW domain — full spec copied to `openspec/specs/results-api/spec.md` | 3 requirements / 13 scenarios |
| `contracts` | MODIFIED `Idempotent Mutations` replaced in `openspec/specs/contracts/spec.md` (F4 extends the obligation to the results score trigger with `session:{id}` key scope, run-safe replay and independent-run semantics; 2 F4 scenarios added, F2/F3 scenarios preserved) + ADDED `Results Availability Errors` | 5 requirements / 15 scenarios |
| `audit-consent` | MODIFIED `Append-only Audit Log` replaced in `openspec/specs/audit-consent/spec.md` (catalog ratifies `scoring.run`; scoring metadata aggregate-only; lockstep obligation kept; `Scoring event carries aggregates only` scenario added) | 5 requirements / 13 scenarios |
| `data-schema` | ADDED `Score Run Persistence Shape` appended to `openspec/specs/data-schema/spec.md` | 5 requirements / 10 scenarios |
| `synthetic-seed` | ADDED `Reference Set Value Shape` appended to `openspec/specs/synthetic-seed/spec.md` | 5 requirements / 10 scenarios |

F4-contributed total: **12 requirements / 39 scenarios** (matches verify-report authority). Merges followed the F2/F3 promotion convention: full specs copied verbatim, MODIFIED requirements replaced wholesale with the delta body (delta-only `(Previously: …)` notes dropped), ADDED requirements appended, unrelated requirements preserved. No delta contains REMOVED or RENAMED sections — no destructive merge was required (`openspec/config.yaml` `rules.archive: Warn before merging destructive deltas` satisfied by absence).

## Final Task State

- **20/20 tasks complete** (`tasks.md`): 18 implementation tasks (`1.1`–`4.4`) plus cross-cutting gates `5.1` (F4 selector green; full suite twice) and `5.2` (diff scope; inherited web debt documented). No stale unchecked tasks; no archive-time reconciliation was needed.
- Verify-report (FINAL): `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 12/12`, `scenarios: 39/39`. F4 slice `-k "scoring or reference or results"` 32/32; full suite ×2 = 179 collected / 177 passed / 2 failed (only inherited F2b `test_web.py` failures, untouched); audit `11 passed`; `test_session_api.py:375` no-scoring boundary intact; diff scope shows no F2/F3/seed/migration/web paths.

## Commits (5, base `f9cb07f` → `47bdd2a`)

- `8eb59ae` feat(api): add pure scoring engine domain
- `c046840` feat(api): add scoring errors and repository reads
- `c8b1a97` feat(api): add scoring service orchestration and ratify scoring.run audit event
- `e212f9e` feat(api): add results API routes and schemas
- `47bdd2a` test(api): fix F4 scoring test isolation under shared seeded db

Total ~1.6k lines added. `git diff --check` clean; all five subjects conventional commits.

### Archive-time commits
- `docs(openspec): archive f4-scoring-engine change` (archive move, spec promotion, this report — per the F3 archive convention; the change folder and its artifacts were untracked before this commit, so this is also the first git commit containing the F4 SDD artifacts).

## Discrepancies Recorded (per Final-State Authority)

- The launch prompt stated a "verify-report commit" existed alongside the five implementation commits. Repository evidence at archive time shows HEAD = `47bdd2a` with the entire `openspec/changes/2026-08-10-f4-scoring-engine/` folder untracked — no verify-doc commit exists. The on-disk `verify-report.md` (FINAL PASS) and Engram observation #2102 agree; the discrepancy is only about git history, and it is resolved by including all SDD artifacts in the archive-time commit above. No unrankable contradiction remains.

## Decisions Registered (from design.md)

- **ADR-01** — Normal CDF via stdlib `math.erf` (IEEE-754 double, ≤1e-12 vs vectors); `round-half-up(x) = floor(x + 0.5)` everywhere.
- **ADR-02** — Layering `domain` (pure, DB/I/O/clock/random-free, frozen `ScoringInput`/`ScoreResult`) → `service` (orchestration) → `repository` (reads + ScoreRun persistence) → `errors` (stable `ApiError` tokens).
- **ADR-03** — Thin `/api/v1/results` adapter; `require_roles(...)` (admin/psicólogo/evaluado-own enforced in service); `session_not_completed` new stable token; `resource_not_found` reused; payload = labels/scores/run/reference/norm only.
- **ADR-04** — Transactional `pending → completed` runs with `computed_at`, `synthetic=False`, `source='runtime'`; no session/run locks; multi-run schema-legal; latest = `computed_at DESC, id DESC`.
- **ADR-05** — `scoring.run` ratified in `EVENT_CATALOG`, `packages/contracts/README.md`, `test_audit.py` in lockstep; metadata aggregate-only (ids, response/scale counts, timestamps).
- **ADR-06** — Strict RED→GREEN unit/repository/service/TestClient integration against real Compose PostgreSQL.
- **ADR-07** — No migration or feature flag; `score_runs` exists since migration 0003; rollback = revert/disable routes only.

## Inherited Debt / Follow-ups (non-blocking, handoff)

- **2 inherited `test_web.py` failures** (F2b): `test_page_is_spanish` and `test_page_never_leaks_stack_trace` — documented debt; F4 changed no web file; they belong to the F2b landing-page remediation.
- **`scripts/test.ps1` exit-code masking**: the wrapper returns 0 without propagating `$LASTEXITCODE`; pytest output counts remain authoritative in verification evidence (verify SUGGESTION #1).
- **No E2E/browser runner**: F4 is API-only; web build is N/A and the owner manual checklist does not apply.
- **F5 (Piere) handoff**: update the `AGENTS.md` "Cambio activo actual" pointer (follow-up #6 from HANDOFF-F4 §11 — it still points to `f2-catalogo-instrumentos`; suggest pointing to HANDOFF-F5 or "sin cambios activos"). The F4 scoring surface is `/api/v1/results`; F5 consumes `score_runs` for profiles/recommendation.

## Verification Facts (final-state authority)

- Final-state source of truth is the on-disk `verify-report.md` at `47bdd2a` (`verdict: pass`), corroborated by the orchestrator's final-state handoff facts. Intermediate snapshots (`apply-progress` slices, the earlier failed verify report) are superseded where they differ.
- The only verify-stage defect (shared seeded-profile contamination breaking absolute count assertions) was resolved by remediation commit `47bdd2a` (isolated profiles `evaluado_19`/`evaluado_20`); no CRITICAL issue exists at close, so the archive gate is clear.

## Traceability (Engram observation IDs read)

- `#2080` explore · `#2081` proposal · `#2083` spec · `#2085` design · `#2087` tasks · `#2089` apply-progress · `#2102` verify-report (all topics under `sdd/2026-08-10-f4-scoring-engine/`).
- `reviewGate`: structurally absent — no review artifacts exist for this candidate; archive proceeded under ordinary repository policy.

## Mechanical Copy Evidence

- NEW-domain promotions: `diff -r` (delta spec vs `openspec/specs/{domain}/spec.md`) — **EMPTY**, exit 0, for `scoring-engine` and `results-api`.
- Archive move: pre-move recursive snapshot vs `openspec/changes/archive/2026-08-10-f4-scoring-engine/` — `diff -r` **EMPTY**, exit 0 (byte-identical; `archive-report.md` is additive-only and excluded).

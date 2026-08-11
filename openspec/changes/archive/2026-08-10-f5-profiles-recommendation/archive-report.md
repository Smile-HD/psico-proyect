# F5 Profiles/Recommendation — Archive Report

**Change**: `2026-08-10-f5-profiles-recommendation`
**Date**: 2026-08-11
**Owner**: Piere (F5; consuming F4/Juan Carlos)
**Final state**: ARCHIVED
**Base**: `9e4b57e` (docs(openspec): update active change pointer to F1-F4 archived) → `1517ec7` (HEAD at archive)
**Archive commit**: `docs(openspec): archive f5-profiles-recommendation change` (archive move, spec promotion, this report, AGENTS.md pointer update)

## Summary

F5 implemented invariant nº3 — DB-defined, deterministic, explainable profile×program fit with traceable justification: a new `recommendation` module (`domain`/`errors`/`repository`/`service`) mirroring F4's pure-domain layering, declarative `recommendation_rules` rows (closed `rule_type` {`percentile_min`}, JSONB `{scale, min_percentile, weight?}`, `is_active`), weighted fit `100·Σ(w·satisfied)/Σ(w)` half-up to `Numeric(5,2)` with fit DESC/name ASC ordering and zero-rule exclusion, the ratified `view_recommendations` capability (admin/psicólogo/evaluado-own) and aggregate-only `recommendation.generated` audit event (lockstep: `permissions.py`, contracts README §§3/6, `EVENT_CATALOG`, `test_auth.py`/`test_audit.py`), and protected `POST /api/v1/recommendations/{session_id}/generate` / `GET /api/v1/recommendations/{session_id}` with `session:{id}` idempotency, indistinguishable availability errors, exact DTO (`session_id`, `generated_at`, versioned code-constant disclaimer, `items[]`), and recursive no-leak boundary (percentiles only inside justification text; never `norm_note`). Seed extension: five invented synthetic programs under `faculty:dev` + ten active weighted rules, `SEED_VERSION` bump, manifest/`--reset` scope; `recommendation_results` stays runtime-only. No migration, no web change, no F2/F3/F4 module change. Delivered as 5 stacked slices (`auto-chain`, `stacked-to-main`) plus a spec-pinned U+2265 correction (`970dc4d`) and a tests-only isolation remediation (`1517ec7`). The earlier failed verify report was superseded by the remediation commit; the on-disk `verify-report.md` is the FINAL PASS version.

## Spec Promotion

| Domain | Action | Requirements |
|---|---|---|
| `recommendation-api` | NEW domain — full spec copied mechanically to `openspec/specs/recommendation-api/spec.md` | 5 requirements / 11 scenarios |
| `data-schema` | MODIFIED `Empty-but-migrated F5/F6` replaced (scenario renamed to `Recommendation rules populated, results and reports empty after seed`; seed now populates `recommendation_rules` while runtime results and reports stay 0) + ADDED `Recommendation Result Persistence Shape` | 6 requirements / 12 scenarios |
| `synthetic-seed` | ADDED `Recommendation Seed Content` appended | 6 requirements / 13 scenarios |
| `audit-consent` | MODIFIED `Append-only Audit Log` replaced (catalog ratifies `recommendation.generated`; recommendation metadata aggregate-only; `Recommendation event carries aggregates only` scenario added; lockstep obligation covers recommendation events) | 5 requirements / 13 scenarios |
| `contracts` | MODIFIED `Idempotent Mutations` replaced (F5 generation trigger with `session:{id}` key scope and `idempotency_key_reused`; `F5 generation replay is run-safe` + `F5 new key starts a new generation` scenarios added; F2/F3/F4 scenarios preserved) + ADDED `Recommendation Access Matrix` + ADDED `Recommendation Availability Errors` | 7 requirements / 21 scenarios |

F5-contributed total: **12 requirements / 36 scenarios** (matches verify-report authority). Merges followed the F2/F3/F4 promotion convention: new-domain full specs copied verbatim, MODIFIED requirements replaced wholesale with the delta body (delta-only `(Previously: …)` notes dropped), ADDED requirements appended, unrelated requirements preserved. No delta contains REMOVED or RENAMED sections — no destructive merge was required (`openspec/config.yaml` `rules.archive: Warn before merging destructive deltas` satisfied by absence).

## Final Task State

- **16/16 tasks complete** (`tasks.md`): 15 implementation tasks (`1.1`–`5.2`) plus verification gate `6.1` (F5 selector green; full suite twice; diff scope; inherited web debt documented). No stale unchecked tasks; no archive-time reconciliation was needed.
- Verify-report (FINAL): `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 12/12`, `scenarios: 36/36`. F5 slice `-k "recommendation or program"` 40/40; full suite ×2 = 219 collected / 217 passed / 2 failed (only inherited F2b `test_web.py` failures, untouched); boundary regression 71 passed (`test_session_api.py:375` no-scoring boundary, F4 no-leak boundary, F5 recursive no-leak); auth/audit lockstep 26 passed (15 + 11); changed-test collection 78 tests across the seven F5/lockstep files.

## Commits (7, base `9e4b57e` → `1517ec7`)

- `b90673d` feat(api): seed synthetic program catalog and recommendation rules
- `52ea466` feat(api): add pure recommendation domain
- `f2a4131` feat(api): add recommendation repository (reads and generation writes)
- `5e1e2d5` feat(api): add recommendation service and ratify view_recommendations + recommendation.generated
- `970dc4d` fix(api): use spec-pinned U+2265 in recommendation justification template
- `1e4e95d` feat(api): add recommendation API routes and schemas
- `1517ec7` test(api): fix F5 recommendation test isolation with disjoint profiles

~2.5k lines total across the range. `git diff --check` clean; all seven subjects are conventional commits; forbidden-scope scan (F2/F3/F4 modules, seed catalog, migrations, web) empty.

### Archive-time commit
- `docs(openspec): archive f5-profiles-recommendation change` (archive move, spec promotion, this report, AGENTS.md pointer update — the change folder and its artifacts were untracked before this commit, so this is also the first git commit containing the F5 SDD artifacts). Unlike F4 (which updated the AGENTS.md pointer in a separate follow-up commit `9e4b57e`), the pointer update is folded into this single archive commit per explicit orchestrator commit discipline: exactly one conventional commit.

## Discrepancies Recorded (per Final-State Authority)

- The launch prompt's implementation-commit shorthand stated "8 commits" but listed seven; repository evidence at archive time shows exactly seven conventional commits in the range (`b90673d`…`1517ec7`). The on-disk `verify-report.md` (FINAL PASS) already flagged the same shorthand in its SUGGESTION. Repository and verify report agree; the prompt shorthand is superseded.
- The earlier failed verify report (pre-remediation) is superseded by remediation commit `1517ec7`; the on-disk `verify-report.md` and Engram observation #2133 agree on the FINAL PASS. No unrankable contradiction remains.

## Decisions Registered (from design.md)

- **ADR-01** — Layering: `app/modules/recommendation/{domain,errors,repository,service}.py`; domain pure (no DB/I/O, no LLM, no stored SQL), mirrors F4.
- **ADR-02** — Fit: `percentile_min` vocabulary with exact scale labels or `overall`, `min_percentile` 1–99, missing weight defaults 1.0, non-positive rejected; each `round-half-up(100·w·satisfied/Σw)` to `Numeric(5,2)`, summed; zero-rule programs excluded; order fit DESC / name ASC.
- **ADR-03** — Transaction: latest F4 completed run read; one result row per rule with shared `created_at` + runtime flags (`synthetic=False`, `source='runtime'`); audit `commit=False` aggregate-only; idempotency stored; single commit; rollback on integrity/audit failure.
- **ADR-04** — API/security: both routes declare `require_roles(ADMIN, PSICOLOGO, EVALUADO)`; evaluado-own-only enforced in service; `session:{id}` keys; foreign access → `FORBIDDEN` + `auth.denied`.
- **ADR-05** — DTO: exact outer fields; aggregated justification = template sentences joined per program in rule id ASC order; `generated_at` is the only public generation metadata; versioned code-constant disclaimer (never `norm_note`).
- **ADR-06** — Ratification: `view_recommendations` + `recommendation.generated` are NEW, updated in lockstep (permissions, contracts README §§3/6, `EVENT_CATALOG`, lockstep tests).
- **ADR-07** — Seed/reset: 4–6 programs/rules under `institution:dev`/`faculty:dev`, UUID5 keys, seed flags, `SEED_TABLES += {recommendation_rules, recommendation_results}`, `SEED_VERSION` bump, atomic preflight `seed_reset_dependency_conflict` on runtime refs, seed-owned-only reset.
- **ADR-08** — Testing: strict RED→GREEN layers; reserved `evaluado_21..30`; delta counts; slice `-k "recommendation or program"`.
- **ADR-09** — Rollout: no migration/flag (tables exist since migration 0003); rollback disables/reverts F5 only.

## Validator Observations (non-blocking)

- **Domain sort tie-break**: the domain adds a `str(program_id)` tie-break when ordering aggregated results beyond the spec-pinned `fit DESC, name ASC` — deterministic and harmless for the synthetic catalog, but worth pinning in a future spec touch if the tie-break should become contractual.
- **tasks.md 2.2 wording**: task 2.2's trace template was aligned to the Unicode `≥` (U+2265) operator during the `970dc4d` correction, mirroring the authoritative recommendation-api spec.

## Inherited Debt / Follow-ups (non-blocking, handoff)

- **2 inherited `test_web.py` failures** (F2b): `test_page_is_spanish` and `test_page_never_leaks_stack_trace` — documented debt; F5 changed no web file; they belong to the F2b landing-page remediation.
- **`scripts/test.ps1` exit-code masking**: the wrapper returns 0 without propagating `$LASTEXITCODE`; pytest output counts remain authoritative in verification evidence.
- **Tooling gaps**: no E2E/browser runner, no coverage command, no linter, no pyright binary — unchanged for F5; web build N/A (API-only change).
- **F6 (Ivan) handoff**: reports/PDF/integration — consumes `recommendation_results` + `score_runs`; the F5 recommendation surface is `/api/v1/recommendations`. AGENTS.md "Cambio activo actual" pointer updated to "F1–F5 archivados" as part of this archive.
- **Sort tie-break observation** above is a candidate future spec touch.

## Verification Facts (final-state authority)

- Final-state source of truth is the on-disk `verify-report.md` at `1517ec7` (`verdict: pass`), corroborated by the orchestrator's final-state handoff facts and Engram observation #2133. Intermediate snapshots (`apply-progress` slices, the earlier failed verify report) are superseded where they differ.
- The only verify-stage defect (shared seeded-profile contamination breaking absolute count assertions) was resolved by remediation commit `1517ec7` (disjoint profiles: service `evaluado_29..30`, repository `evaluado_27..28`, API `evaluado_21..26`; before/after delta assertions); no CRITICAL issue exists at close, so the archive gate is clear.

## Traceability (Engram observation IDs read)

- `#2112` explore · `#2113` proposal · `#2116` spec · `#2118` design · `#2121` tasks · `#2123` apply-progress · `#2133` verify-report (all topics under `sdd/2026-08-10-f5-profiles-recommendation/`).
- `reviewGate`: structurally absent — no review artifacts exist for this candidate; archive proceeded under ordinary repository policy.

## Mechanical Copy Evidence

- NEW-domain promotion: `diff -r` (delta spec vs `openspec/specs/recommendation-api/spec.md`) — **EMPTY**, exit 0 (byte-identical).
- Archive move: pre-move recursive snapshot vs `openspec/changes/archive/2026-08-10-f5-profiles-recommendation/` — `diff -r` **EMPTY**, exit 0 (byte-identical; `archive-report.md` is additive-only and excluded from the comparison).

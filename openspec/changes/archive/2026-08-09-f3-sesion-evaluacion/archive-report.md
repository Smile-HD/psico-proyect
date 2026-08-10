# F3 Evaluation Session — Archive Report

**Change**: `f3-sesion-evaluacion`
**Date**: 2026-08-09
**Owner**: Jhamil
**Final state**: ARCHIVED
**Base**: `94f0e4d` (docs: add F3 session handoff document) → `a5f3041` (HEAD at archive)
**Archive commit(s)**: `b676085` (planning artifacts + config reconciliation); `docs(openspec): archive f3-sesion-evaluacion change` (this archive)

## Summary

F3 gave evaluados a published-only, consent-gated session workflow on top of F1 session tables and F2 conventions: a new `session_runtime` module (domain/service/repository/errors), numeric-free session API (create, own list, own/admin detail, batched response upsert, complete without scoring), a published-version catalog listing, an idempotency retrofit on consent grant/revoke, and the `/evaluacion` web flow with autosave/resume, inline consent, and score-free completion. Delivered as 5 slices (`auto-chain`, `stacked-to-main`) plus a post-verify accessibility fix. No migration, no seed changes, no new audit events, no scoring surface.

## Spec Promotion

| Domain | Action | Requirements |
|---|---|---|
| `sessions` | NEW domain — full spec copied to `openspec/specs/sessions/spec.md` | 6 requirements / 17 scenarios |
| `web-pages` | NEW domain — full spec copied to `openspec/specs/web-pages/spec.md` | 5 requirements / 8 scenarios |
| `catalog-api` | ADDED `Published Version Listing` appended to `openspec/specs/catalog-api/spec.md` | 1 requirement / 3 scenarios |
| `audit-consent` | ADDED `Idempotent Consent Mutations` appended to `openspec/specs/audit-consent/spec.md` | 1 requirement / 3 scenarios |
| `contracts` | MODIFIED `Idempotent Mutations` replaced in `openspec/specs/contracts/spec.md` (body extended to sessions + consent, `idempotency_key_reused` token pinned, F3 key-reuse scenario added) | 1 requirement / 5 scenarios |

Total ratified: **14 requirements / 36 scenarios** (matches verify-report authority). Merges followed the F2 promotion convention: full specs copied verbatim, ADDED requirements appended, MODIFIED requirements replaced wholesale with the delta body (delta-only `(Previously: …)` notes dropped), unrelated requirements preserved.

## Final Task State

- **20/20 tasks complete** (`tasks.md`), including cross-cutting gates T5.1 (Idempotency-Key sweep) and T5.2 (full suite twice + `npm run build`) and the post-verify accessibility fix.
- Verify-report: `verdict: pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 14/14`, `scenarios: 36/36`, test exit 0, build exit 0.

## Commits (31, base `94f0e4d` → `a5f3041`)

### Slice 1 — session runtime core
- `71d6057` feat(session): add session runtime domain rules
- `1fa400d` feat(session): add stable runtime errors
- `1db6291` feat(session): add locked response repository
- `3cd0f2f` feat(session): orchestrate runtime mutations

### Slice 2 — session API wiring
- `216ad79` refactor(session): tighten repository projection surface
- `feb392f` feat(session): add numeric-free session schemas
- `256c3c2` feat(session): wire session API adapters
- `1866d28` test(session): cover session API contracts
- `8003b0d` chore(sdd): mark session API tasks complete

### Slice 3 — listing + consent retrofit
- `c0da923` feat(catalog): add published version discovery
- `d4f674f` feat(consent): retrofit mutation idempotency

### Slice 4 — web UI
- `601ab81` feat(web): add evaluation session API client
- `2d17cdc` feat(web): add evaluation discovery flow
- `630dcb3` refactor(web): tighten session API types
- `8331d2a` feat(web): add autosaving evaluation session
- `119c468` feat(web): expose evaluation navigation and contracts
- `f4deb7a` fix(web): reuse completion intent keys
- `30850d2` docs(contracts): clarify F3 route prefixes
- `cf5f03a` style(web): normalize evaluation navigation markup

### Slice 5 — UX port
- `cc898a9` feat(web): add consent and active session helpers
- `fb6fd1d` feat(web): port evaluation session wizard
- `3c0bfaa` feat(web): add inline consent and session resume
- `1e014ab` fix(web): preserve failed autosave intents
- `8229543` docs(sdd): record evaluation UX slice progress
- `57e93fd` docs(sdd): include slice progress commit
- `33b80f6` docs(sdd): record autosave retry boundary

### Cross-cutting gates + remediation
- `95a07a8` chore(sdd): mark cross-cutting gates T5.1/T5.2 complete
- `ac3a013` fix(web): announce completion confirmation to assistive tech (resolves the verify CRITICAL)

### Verify docs
- `f4c6140` docs(sdd): record post-verify accessibility fix
- `c505ac1` docs(sdd): record accessibility remediation in verify report
- `a5f3041` docs(sdd): finalize verify report with full scenario coverage

### Archive-time commits
- `b676085` chore(sdd): commit f3 planning artifacts and config reconciliation (exploration, proposal, design, 5 delta specs; test/build commands in `openspec/config.yaml`)
- `docs(openspec): archive f3-sesion-evaluacion change` (archive move, spec promotion, this report)

## Decisions Registered (from design.md)

- **ADR-001** — Reuse `assessment_authoring.idempotency` unchanged; actor-wide scope for create, `session:{id}` for responses/complete.
- **ADR-002** — Pinned projection: re-project immutable rows (archived versions included), hide catalog status and numeric values; no snapshot migration.
- **ADR-003** — Published-only gate precedes consent (no existence leak; valid published requests still yield `consent_required`).
- **ADR-004** — One random idempotency key per debounced autosave intent, reused for retries; single-flight queue prevents stale writes.
- **ADR-005** — No proposal deviation: no migration, seed change, scoring, or new audit event.

## Inherited Debt / Follow-ups (non-blocking, handoff)

- **2 inherited `test_web.py` failures** (F2b): `test_page_is_spanish` and `test_page_never_leaks_stack_trace` assert stale F1-era text/branch shapes in the F2b-redesigned landing page; F3 did not change that file. They belong to the F2b landing-page remediation, not F3.
- **No browser/E2E runner**: web verification is build + static inspection + the owner manual checklist (evaluator flow: published-only discovery, Spanish matrix, keyboard operation, autosave announcements, completion `role="status"`, consent/retry, 375px overflow, reduced motion, contrast, role-specific navigation). Owner must run the manual checklist before release.
- **PR5 wizard deviation**: the one-item native-radio wizard deviates from frozen `LikertMatrix` usage and the design's published-read wording; behavior-preserving (option-ID-only, accessible), but reconciliation in spec/design is pending.
- **`scripts/test.ps1` exit-code masking**: the wrapper returns 0 without propagating `$LASTEXITCODE`; pytest output counts must remain visible in verification evidence.
- **Own-list triangulation**: `GET /sessions` own-list scenario should add a second-owner runtime assertion (verify suggestion).
- **Earlier-slice TDD evidence**: per-task TDD cycle rows exist for T5.3–T5.6; earlier API slices are evidenced by committed tests + repeated suite rather than one final per-task table (only if strict auditability of all 20 tasks is later required).
- **F2-ux follow-up**: `login/error.tsx` and error surfaces share root CSS module via deep relative imports; consolidation is open (from the F2-ux archive report).

## F4 Handoff Readiness

- `session_runtime` records responses server-side with the private option→value 1–5 mapping (non-public `fixture_projection`), so F4 can consume the private mapping for scoring.
- Completed sessions keep immutable pinned versions and aggregate-only audit metadata; no scoring surface, reference results, or numeric values cross the public API or web UI.
- F4 scoring starts from the F3 response rows + instrument version + reference, per the ratified contracts boundary (§7.6.4 and the F4-scoring boundary in the promoted specs).

## Verification Facts (final-state authority)

- Final-state source of truth is the verify-report at HEAD `a5f3041` (`verdict: pass`), corroborated by the native dispatcher (`archive: ready`, no blockedReasons). Intermediate snapshots (`apply-progress` at slice 5, earlier verify revisions) are superseded where they differ.
- The single verify CRITICAL (completion live region) was resolved in `ac3a013` and re-verified at HEAD before this archive.

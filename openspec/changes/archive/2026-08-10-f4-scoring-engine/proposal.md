# Proposal: F4 — Scoring Engine and Results API

## Intent

F4 (owner Juan Carlos; consuming F3/Jhamil) makes completed sessions reproducibly scoreable (raw/direct/transformed) while preserving pure scoring. It adds API-only results for `View results` roles, reading each immutable instrument version without editing published instruments.

## Scope

### In Scope
- Pure, DB/I/O/side-effect-free scoring over private, never-public `fixture_projection`.
- Persist eager runs in `score_runs`; add `POST /api/v1/results/{session_id}/score` and `GET /api/v1/results/{session_id}`.
- Synthetic/research-only `RS-TP-S-01` output with `norm_note` disclaimer; roles admin/psicólogo/evaluado-own, envelope, idempotency, aggregate-only audit.

### Out of Scope
- F5 recommendations; F6 reports/PDF/integrations; real data, LLMs, or web results UI.
- No catalog/session/seed/published-version/Alembic changes; inherited `test_web.py` failures stay untouched.

## Capabilities

### New Capabilities
- `scoring-engine`: pure raw/direct/transformed chain.
- `results-api`: trigger/read, persistence, access, availability, and no-leak behavior.

### Modified Capabilities
- `contracts`: score-trigger idempotency and stable errors.
- `audit-consent`: ratify aggregate-only `scoring.run` (ids/counts/timestamps; never response values).

## Approach

Approach 1: thin `/results` routes; `domain/service/repository/errors`; transactional `score_runs` (`pending → completed`) after pure execution. Math proposal: scale raw = sum of four mapped 1–5 values (4–20); `z=(raw−mean)/sd`; `percentile=clamp(round-half-up(100·Φ(z)),1,99)`; `T=round-half-up(50+10z)`; `eneatype=clamp(ceil(7·percentile/100),1,7)`; `overall_raw=round-half-up(1+19·(Σraw−4n)/(16n))`, then exact `overall` 1–20 lookup. Spec pins precision, clamps, and ties.

Completed sessions score; missing → indistinguishable `NOT_FOUND/resource_not_found`; `in_progress` → `CONFLICT/session_not_completed`; no response leakage. Same key (scope `session:{id}`) replays; each new key creates a run/audit event; GET returns the latest.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `services/api/app/modules/scoring/` | New | Pure engine |
| `services/api/app/api/routes/results.py`, `schemas/results.py`, `api/router.py` | New/Modified | Results API |
| `openspec/specs/`, `services/api/tests/` | New/Modified | Specs and tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Math or duplicate-run errors | High | Formula and replay/re-run tests |
| Audit/mapping leakage | Med | Aggregate-only event and boundary tests |

## Rollback Plan

Revert the API and disable routes; no migration or F3/catalog rollback. Preserve append-only `scoring.run` audit and runtime `score_runs`; never rewrite sessions or instruments.

## Dependencies

- F3 contract, `fixture_projection`, scoring/idempotency/permissions/audit infrastructure.

## Success Criteria

- [ ] Pure tests pin the chain and prove no DB/I/O.
- [ ] API tests prove roles/own-only, errors/no leakage, `norm_note`, idempotency, reruns, and audit deny-list.
- [ ] No new failures; inherited `test_web.py` failures remain untouched.

## Proposal question round

- Confirm normal-CDF formulas, rounding/clamps, and overall rescale.
- Confirm new-key rerun and latest-run semantics under concurrency.
- Confirm `RS-TP-S-01` is the only reference set in this slice.

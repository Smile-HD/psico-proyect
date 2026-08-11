# Proposal: F5 — Declarative Profiles and Recommendation

## Intent

F5 (Piere) implements invariant nº3: DB-defined, explainable profile×program fit with
traceable justification; no code rules/LLM. It consumes F4 latest `score_runs.raw`, remains
synthetic/research-only, and never edits pinned versions.

## Scope

### In Scope
- Add the recommendation module and protected `POST /api/v1/recommendations/{session_id}/generate` plus `GET /api/v1/recommendations/{session_id}`.
- Persist active-rule rows in `recommendation_rules`/`recommendation_results`; aggregate latest per program. `Idempotency-Key` scope is `session:{id}`: replay is stable, a new key creates a generation, latest is `created_at DESC, id DESC`.
- Rules are per-program DB rows: closed `rule_type` (`percentile_min`), JSONB `{scale, min_percentile, weight}`, `is_active`; scales are five labels plus `overall`; no SQL or embedded rules. Fit over active rules is `100·Σ(w·satisfied)/Σ(w)`, `Numeric(5,2)`, fit DESC then program name, with rule/match/failure/reason justifications.
- Ratify `view_recommendations` (admin/psicólogo/evaluado-own) and aggregate-only `recommendation.generated` across `permissions.py`, contracts §6/§3, audit-consent, and `test_audit.py`.
- Seed 4–6 invented programs under the existing faculty via `programs.json`/`recommendation_rules.json`, referencing `Intereses`, `Aptitud verbal`, `Aptitud numérica`, `Razonamiento abstracto`, `Valores/preferencias`, and `overall`; update `SEED_TABLES`/`SEED_VERSION`.

### Out of Scope
- F6 reports/PDF/integration, web UI, LLM/real data, catalog/session/scoring changes, published instruments, and migrations.

## Capabilities

### New Capabilities
- `recommendation-api`: recommendation rules and endpoints.

### Modified Capabilities
- `contracts`: access, idempotency, errors, boundary.
- `audit-consent`: aggregate-only event.
- `data-schema`: populated 0003 tables; unchanged schema.
- `synthetic-seed`: fixtures and reset.

## Approach

Mirror F4's `domain/service/repository/errors` layering; the pure domain receives
snapshots, not DB access. Missing/unscored → `NOT_FOUND/resource_not_found`;
in-progress → `CONFLICT/session_not_completed`; unscored sessions are never recommended.
Outputs carry versioned code-constant disclaimer (no migration; never reuse baremo `norm_note`),
error envelope, private option values/keys and 1–5 mapping, and
`audit.record(..., commit=False)` in the generation transaction.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `services/api/app/modules/recommendation/`, schemas, routes, router | New/Modified | Domain, DTOs, persistence, API |
| `services/api/app/seed/loader.py`, fixtures | Modified/New | Synthetic programs/rules and manifest |
| `app/core/{permissions,audit}.py`, contracts README, specs, `test_audit.py` | Modified | Capability/event lockstep |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Fit/generation ambiguity | High | Pin math, rounding, tie-break, and row grouping in specs/tests |
| Seed contamination or leakage | Med | Reserve `evaluado_21..30`; use deltas and no-leak tests |

## Rollback Plan

Disable/revert module, routes, ratifications, and seed extension. Preserve F4 runs,
sessions, instruments, append-only audit, and runtime recommendation history; remove
seed-owned rows only through controlled synthetic-dev cleanup.

## Dependencies

- F4 `results-api`/`score_runs.raw`, migration 0003, idempotency, audit.

## Success Criteria

- [ ] Formula, `Numeric(5,2)`, ordering, justifications, roles, idempotency, errors, disclaimer, boundary, and audit atomicity tested.
- [ ] Seed is synthetic/research-only with updated checksum, counts, and version.
- [ ] No immutable instrument or F4/catalog/session/scoring behavior changes.

## Proposal question round

- Pin disclaimer, row grouping, zero-rule behavior, fixture keys, and `percentile_min` bounds.

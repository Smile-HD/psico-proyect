# Apply Progress: F3 — Evaluation Session

## Slice

- PR: 5 / Slice 5
- Work unit: `slice5-ux-wizard-port`
- Delivery: `auto-chain`, `stacked-to-main`
- Runtime ledger: max 800 changed lines; Slice 5 authored diff remains within the ledger.
- Scope: T5.3–T5.6 only; T5.1–T5.2 remain parent-owned cross-cutting gates.
- Mode: Strict TDD is enabled globally; the web package has no JS/unit or browser/E2E runner, so build and owner manual inspection are the available web evidence.

## Cumulative Completed Tasks

- [x] T1.1–T1.4 — session runtime core, stable errors, locked repository projection/upsert, and service lifecycle.
- [x] T2.1–T2.3 — numeric-free session DTOs, route adapters, and PostgreSQL API contract tests.
- [x] T3.1–T3.2 — published listing and idempotent consent retrofit.
- [x] T4.1 — `session-api.ts` uses `apiFetch` for listing, create, detail, batch save, and complete; each mutation accepts or creates an intent key; `consent_required` and no-leak errors map to friendly UI states; public response types carry option IDs, not numeric values.
- [x] T4.2 — `/evaluacion` lists published labels, creates and redirects sessions, explains missing consent, and renders a neutral unavailable state for `NOT_FOUND`.
- [x] T4.3 — session route restores answers, uses the frozen controlled `LikertMatrix`, queues one debounced intent at a time with ordered retries, preserves failed local input, announces save state through `Notice`/`role=status`, marks required items, focuses missing inputs, completes without scores, and reuses completion keys on retry.
- [x] T4.4 — NavBar shows `Evaluación` only to authenticated admin/psicólogo/evaluado role claims and marks the active route.
- [x] T4.5 — contracts README §7.6 documents endpoints, published-only no-leak gate, mutation idempotency, labels/options rule, and F4 scoring boundary.
- [x] T5.3 — `session-api.ts` exposes consent-version lookup/grant and SSR-safe active-session `sessionStorage` helpers.
- [x] T5.4 — session route presents one item per screen with position progress, previous/next controls, focus management, required validation, option-ID-only autosave, retry preservation, and score-free completion.
- [x] T5.5 — discovery route validates and offers stored-session resume, clears stale completed/not-found/forbidden storage, and renders inline consent acceptance before retrying creation with a fresh intent key.
- [x] T5.6 — evaluator controls use Spanish visible states, accessible radio labels, persistent polite save announcements, required text markers, design tokens, and reduced-motion handling.

## TDD Cycle Evidence

| Task | Test file | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| T5.3 | N/A — no web test runner | Build/typecheck | ✅ baseline build | N/A — no executable web test layer | ✅ `npm run build` passed | N/A — no browser/unit runner | ✅ SSR guards and API mapping kept in client layer |
| T5.4 | N/A — no browser/E2E runner | Build/typecheck | ✅ baseline build | N/A — no executable web test layer | ✅ `npm run build` passed | N/A — owner checklist covers wizard interaction | ✅ queue remains single-flight and item-scoped |
| T5.5 | N/A — no browser/E2E runner | Build/typecheck | ✅ baseline build | N/A — no executable web test layer | ✅ `npm run build` passed | N/A — owner checklist covers consent/resume states | ✅ stale storage is cleared only for terminal invalid states |
| T5.6 | N/A — documentation/manual UX | Static/build review | ✅ baseline build | N/A — no executable web test layer | ✅ `npm run build` passed | N/A — owner manual checklist required | ✅ reused frozen tokens and shared feedback primitives |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test command and exact result | `cd apps/web && npm run build` — **passed** after each implementation unit and at the end; TypeScript/build green and 8 routes generated. |
| Runtime harness command/scenario and exact result | **N/A** — no browser/E2E runner is installed; owner manual checklist and code inspection cover keyboard navigation, focus, consent, resume cleanup, live status, contrast-token use, reduced motion, and no-score behavior. |
| Full API suite command and exact result | `powershell -ExecutionPolicy Bypass -File scripts/test.ps1` — **147 passed, 2 failed, 61 warnings**; only the documented pre-existing `tests/test_web.py::test_page_is_spanish` and `tests/test_web.py::test_page_never_leaks_stack_trace` failures remain. |
| Rollback boundary | Revert Slice 5 web commits `cc898a9`, `fb6fd1d`, and `3c0bfaa`, plus this task/progress artifact commit; this removes only consent/session-storage helpers, evaluator wizard/discovery UX, and Slice 5 tracking. Do not revert API slices, NavBar, contracts, or unrelated SDD artifacts. |

## Files Changed

- `apps/web/lib/session-api.ts` — consent version/grant client helpers and active-session storage helpers.
- `apps/web/app/evaluacion/page.tsx`, `page.module.css` — validated resume card and inline consent acceptance/retry.
- `apps/web/app/evaluacion/sesiones/[id]/page.tsx`, `page.module.css` — one-item wizard, progress, navigation, focus, option-ID autosave, retry, and completion.
- `openspec/changes/f3-sesion-evaluacion/tasks.md` — T5.3–T5.6 marked complete; T5.1–T5.2 remain parent-owned.

## Commits

- `cc898a9 feat(web): add consent and active session helpers`
- `fb6fd1d feat(web): port evaluation session wizard`
- `3c0bfaa feat(web): add inline consent and session resume`

## Remaining Tasks

- [ ] T5.1 — parent-owned idempotency sweep.
- [ ] T5.2 — parent-owned full suite twice and final pre-archive build.

## Deviations and Issues

- No API code, `LikertMatrix`, landing page, `NavBar`, `test_web.py`, contracts README, or `src/` structure was changed.
- No numeric option values, scores, reference results, fake timer, or new audit event crosses the web surface.
- Consent is rendered at the actual session-creation boundary (`/evaluacion`); the session detail route only reads an already-created session and therefore has no consent mutation to duplicate.
- Web strict-TDD RED/GREEN execution could not use a web test runner because none is installed; the required build/manual verification path is explicit.

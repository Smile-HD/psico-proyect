# Apply progress — F2 Catalog UX Redesign

## Slice and boundary

- Change: `f2-catalogo-ux-redesign`
- Slice: 1 of 4 / PR 1, stacked-to-main
- Assigned work: implementation-owned T1.1–T1.7 only (foundations and shell)
- Out of scope: T2/T3/T4, V tasks, parent lifecycle tasks, API/auth contracts, services/api, packages/contracts, and content-page redesign.
- Delivery exception: the owner-approved budget exception and `stacked-to-main` strategy were consumed as provided by the parent. This slice did not add a styling dependency.

## Structured status consumed

- Artifact store: `openspec`
- Active change: `f2-catalogo-ux-redesign`
- Planning status: `nextRecommended: apply`, `blockedReasons: []`
- Edit authority: granted by the owner for `D:\Personal\Proyectos\TestPsico\psico-proyect`; all authored edits stayed under that root.
- Runtime attempt: parent-provided `state: proceed`; no second attempt was acquired.
- Windows cwd warning: native commands were run with the filesystem-case path `D:\Personal\Proyectos\TestPsico\psico-proyect`.
- `actionContext`: no unsafe edit-root warning was supplied; the delegated prompt supplied the authoritative root and slice boundary. The native status did not provide a separate `applyState`, so readiness was taken only from the parent-resolved planning status.

## Completed tasks and persisted checkboxes

- T1.1 `[x]`: vendored the Latin Source Sans 3 variable WOFF2 subset, added the SIL OFL license note, and configured `next/font/local` with `font-display: swap` and a tokenized non-`system-ui` fallback.
- T1.2 `[x]`: replaced `globals.css` with the single runtime token source, reset, typography, visible two-part focus, reduced-motion rules, and tabular numeral utility.
- T1.3 `[x]`: added the root shell module, skip link, `main#main-content`, `#app-shell`, viewport/theme metadata, and institutional research-only footer; root metadata no longer claims service status.
- T1.4 `[x]`: added the TestPsico favicon and metadata-only layouts for login, catalog, create, version editor, and evaluator view.
- T1.5 `[x]`: added the single role-aware responsive NavBar implementation, CSS module, logout flow, active-route semantics, and one-line compatibility re-export.
- T1.6 `[x]`: ran plain `npm install` and `npm ci`; `package.json` dependency declarations stayed unchanged and the already tracked `package-lock.json` remained reproducible.
- T1.7 `[x]`: final layer gate passed; the shell/NavBar anti-checklist and local-font source checks passed.

The persisted `openspec/changes/f2-catalogo-ux-redesign/tasks.md` was updated from `[ ]` to `[x]` for each of T1.1–T1.7 and re-read before return.

## Files changed by this slice

- `apps/web/app/fonts/SourceSans3-Variable.woff2`
- `apps/web/app/fonts/SourceSans3-LICENSE.txt`
- `apps/web/app/globals.css`
- `apps/web/app/layout.tsx`
- `apps/web/app/layout.module.css`
- `apps/web/app/login/layout.tsx`
- `apps/web/app/catalogo/layout.tsx`
- `apps/web/app/catalogo/nuevo/layout.tsx`
- `apps/web/app/catalogo/[instrumentId]/versiones/[versionId]/layout.tsx`
- `apps/web/app/catalogo/[instrumentId]/versiones/[versionId]/vista/layout.tsx`
- `apps/web/components/ui/NavBar.tsx`
- `apps/web/components/ui/NavBar.module.css`
- `apps/web/components/NavBar.tsx`
- `apps/web/public/favicon.svg`
- `openspec/changes/f2-catalogo-ux-redesign/tasks.md`

`apps/web/package-lock.json` was verified as already tracked in `HEAD`; `npm install` produced no lockfile delta. `apps/web/package.json`, `apps/web/lib/api.ts`, `apps/web/lib/auth.ts`, API services, contracts, and tests were not modified.

## Verification evidence

- Baseline before editing existing web files: `cd apps/web && npm run build` — passed.
- Layer builds after T1.1, T1.2, T1.3, T1.4, and T1.5 — passed each time.
- Reproducibility: `cd apps/web && npm install` — passed; `npm ci` — passed.
- Final gate: `cd apps/web && npm run build` — passed with Next.js 14.2.35, strict TypeScript checking, and all 7 routes generated/collected successfully.
- Final anti-check: the token audit confirmed required tokens, no `system-ui`, `999px`, or `#1e8e3e` outside the token definitions, and no network font URL in the shell/font integration. A broad repository scan also surfaced the intentionally untouched legacy page styles; the final gate was scoped to the assigned shell/NavBar boundary as required for Slice 1.

## Commit status

The seven requested work-unit commit operations were not materialized. The repository's native lifecycle guard rejected the lifecycle operation because no approved delivery receipt was present. `sdd-apply` is prohibited from creating or approving receipts, launching bounded review, or bypassing the guard with `--no-verify`. No commit is claimed here; the authored changes remain in the worktree (the initial font files/layout were staged by the preparatory add, while subsequent changes are unstaged). Parent lifecycle must perform receipt-authorized delivery/commits.

## Strict TDD / build-gated evidence

The project config enables strict TDD for the repository, but the web app has no test runner and the design explicitly prohibits adding a UI test framework. Per the parent-provided delivery decision, the web slice used build-gated RED/GREEN-equivalent evidence rather than inventing tests or dependencies.

| Task | Test file / layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- | --- |
| T1.1 | No web test runner; Next build gate | Baseline build passed | Build-gated structural check | Build passed after font integration | Not applicable: asset/config only | Final build passed |
| T1.2 | No web test runner; CSS/token audit | Baseline build passed | Token/anti-check assertions defined before final build | Build passed after globals rewrite | Not applicable: declarative token source | Token audit and final build passed |
| T1.3 | No web test runner; Next build gate | Baseline build passed | Shell contract checked before build | Build passed after shell rewrite | Not applicable: declarative shell | Final build passed |
| T1.4 | No web test runner; Next build gate | N/A for new route layouts/assets | Metadata/file contract checked before build | Build passed after metadata and favicon additions | Not applicable: static metadata/assets | Final build passed |
| T1.5 | No web test runner; Next build gate + static ARIA audit | Baseline build passed | Nav ARIA/role behavior contract checked before build | Build passed after NavBar implementation | Static route/role branches audited | Tokenized CSS cleanup retained green build |
| T1.6 | npm install / npm ci reproducibility gate | Existing tracked lockfile | Dependency set diff checked | npm ci passed | Not applicable: generated lockfile | No dependency changes |
| T1.7 | Final build + anti-check script | Prior layer builds passed | Gate assertions defined before final run | Final build passed | Shell/NavBar scoped scan passed | None needed |

No UI tests were added because doing so would violate the explicit no-new-framework constraint. No TDD runner failure is being hidden; the applicable web proof is `npm run build` plus scoped static gates.

## Deviations and risks

- Requested commits remain pending the parent-owned receipt-authorized lifecycle. This is an infrastructure/delivery constraint, not an implementation failure; no unsafe bypass was used.
- The root layout supplies the required `main#main-content` wrapper while existing route pages still contain their own page-level `<main>` elements. Content-page slices should reconcile those landmarks to avoid nested-main semantics.
- The favicon uses palette-equivalent `rgb()` literals because standalone SVG favicons cannot consume the CSS custom-property runtime token; no raw hex was added to the shell or NavBar.
- CodeGraph MCP was unavailable in this session; the read-only upstream `codegraph status` and `codegraph explore` commands were used instead. The index reported current before filesystem fallback.

## Workload and PR boundary

- Historical boundary: PR 1 / Slice 1 / T1.1–T1.7; preserved above for continuity.
- Current boundary: PR 2 / Slice 2 / T2.1–T2.11, stacked-to-main.
- Previous dependency: parent-provided approved planning artifacts, edit authority, and runtime attempt.
- Current next dependency: parent lifecycle review/delivery, then Slice 3.
- Do not re-apply Slice 1 or alter Slice 3/Slice 4 tasks in this work unit.

## Remaining unchecked tasks (exact persisted lines)

- [x] **T2.1** — Implement `apps/web/components/ui/Button.tsx` + `Button.module.css` per design §2 contract: `primary`/`secondary`/`ghost`/`danger` variants with distinct hover/pressed/disabled states, `compact`/`default` sizes (default ≥44px, compact ≥36px per WCAG 2.5.8), `busy` → `disabled` + `aria-busy="true"` + stable pending label supplied by the caller, attribute forwarding (`type`, `name`, `value`, `onClick`, `aria-*`, `data-*`), control radius (no pill), focus via `:focus-visible` only. [UX] Done when: a busy save button is disabled with `aria-busy` and a readable pending label, and a `danger` button is visually distinct from `primary` (web-components Button scenarios). <!-- sdd-owner: implementation -->
- [x] **T2.2** — Implement `apps/web/components/ui/StatusLabel.tsx` + `StatusLabel.module.css`: `kind` set (`draft`/`published`/`archived`/`reference`/`success`/`warning`/`error`/`neutral`), required visible Spanish text (e.g. "Archivada", "Referencia · sintético"), optional non-color `symbol` slot, bounded compact radius, no `role="status"` (static badge), text ≥4.5:1 on the label surface. [UX] Done when: archived status is identifiable by text alone without color perception (web-components StatusLabel scenario). <!-- sdd-owner: implementation -->
- [x] **T2.3** — Implement `apps/web/components/ui/Field.tsx` + `Field.module.css` per design §2 contract: `forwardRef<FieldControlHandle>` exposing `focus()`, controls `input`/`textarea`/`select`/`checkbox`, always-visible `<label htmlFor>`, deterministic `${id}-help`/`${id}-error` ids joined into `aria-describedby`, `aria-invalid="true"` on error, Spanish "Obligatorio" text for required fields (asterisk supplementary only), placeholder never the label, checkbox as a 44px hit area, `autoComplete` passthrough (mandatory `username`/`current-password` at login call sites). [UX] Done when: a field error is announced, linked via `aria-describedby`, and the form can focus the first invalid field through the handle (web-components Field scenario). <!-- sdd-owner: implementation -->
- [x] **T2.4** — Implement `apps/web/components/ui/Feedback.tsx` + `Feedback.module.css` with named exports `ErrorState` (title/message/retryLabel/onRetry/backAction; `role="alert"`, direct Spanish explanation, visible retry/recovery action, never prints raw exceptions or envelopes) and `Notice` (tone success/info/warning/error; `role="status"` + `aria-live="polite"` by default, `role="alert"` when tone is error; message stays in the DOM until replaced/dismissed — no too-short auto-dismiss). [UX] Done when: a load failure renders a Spanish `role="alert"` with a functional retry, and save feedback is announced politely and remains readable (web-components ErrorState/Notice scenarios). <!-- sdd-owner: implementation -->
- [x] **T2.5** — Implement `apps/web/components/ui/Skeleton.tsx` + `Skeleton.module.css`: variants `text`/`heading`/`control`/`block`/`table` (table matches the final `Table` column/row geometry), container `role="status"` + `aria-live="polite"` + visually hidden Spanish "Cargando…" label, low-key opacity pulse only, pulse disabled under `prefers-reduced-motion`. [UX] Done when: a catalog loading state reserves the final table layout with no page jump when data replaces the skeleton (web-components Skeleton scenario). <!-- sdd-owner: implementation -->
- [x] **T2.6** — Implement `apps/web/components/ui/EmptyState.tsx` + `EmptyState.module.css`: semantic `<section>` preserving page context (heading and navigation stay visible), `title`/`description`/`action`/`contextLabel` props, no decorative emoji or invented clinical claims; permission-denied usage explains why and never fakes a disabled action. [UX] Done when: an empty catalog explains the situation and offers create only when permitted (web-components EmptyState scenarios). <!-- sdd-owner: implementation -->
- [x] **T2.7** — Implement `apps/web/components/ui/Table.tsx` + `Table.module.css` per design §2 contract: `<div class=scrollRegion>` wrapping `<table>` with `max-width: 100%` + `overflow-x: auto` (document never scrolls horizontally), `<caption>` even when visually hidden, `<th scope="col">` for every column, `<th scope="row">` for the first column marked `rowHeader`, tabular-nums class for `numeric` columns, no `role="grid"`. [UX] Done when: the catalog table has a caption, scoped headers, and row-header association, and on 375px only the table region scrolls (web-components Table + web-foundations overflow scenarios). <!-- sdd-owner: implementation -->
- [x] **T2.8** — Implement `apps/web/components/ui/Pagination.tsx` + `Pagination.module.css` per design §2 contract: `<nav aria-label>` (default "Paginación del catálogo"), previous/next Buttons disabled at boundaries, page-number Buttons only when `totalPages > 1`, current page with `aria-current="page"` plus visible text "Página X de Y", page changes clamped and never mutating filters or page size. [UX] Done when: on page 1 the "Anterior" control is disabled and the current page is communicated in text (web-components Pagination scenario). <!-- sdd-owner: implementation -->
- [x] **T2.9** — Implement `apps/web/components/ui/Breadcrumb.tsx` + `Breadcrumb.module.css` per design §2 contract: `<nav aria-label="Ruta de navegación"><ol>…</ol></nav>`, final item is text with `aria-current="page"` and never a link, links ≥44px where practical; editor supplies `Catálogo → {instrument_key} → Versión {version_no}`. [UX] Done when: the editor shows the full hierarchy with the current position marked (web-components Breadcrumb scenario). <!-- sdd-owner: implementation -->
- [x] **T2.10** — Implement `apps/web/components/ui/Dialog.tsx` + `Dialog.module.css` per design §5 (React 18, zero dependencies): controlled client component, portal via `createPortal` after a `mounted` guard, `role="dialog"` + `aria-modal="true"` + `useId()`-generated `aria-labelledby`/`aria-describedby`, focus-in on open (initialFocusRef → `[data-dialog-autofocus]` → Cancel → first focusable → panel), `Escape` + explicit Cancel close, `Tab`/`Shift+Tab` trap within the panel, overlay NOT click-dismissible, app shell marked `aria-hidden`/`inert` while open, body scroll lock, and focus returned to the captured trigger on close with prior shell state restored; the Dialog owns no API calls. [UX] Done when: a manual keyboard pass confirms open → focus-in → Tab cycling → Escape/Cancel → focus return, and the underlying page is unreachable while open (web-components Dialog scenarios). <!-- sdd-owner: implementation -->
- [x] **T2.11** — Layer-2 gate: `cd apps/web && npm run build` after each component slice, then a focused browser keyboard pass at 375px and desktop over Button, Field, Dialog, Pagination, and Table scroll behavior. [UX] Done when: build is green after the final slice and no UI library or new dependency was added (design §6 Layer 2 gate). <!-- sdd-owner: implementation -->
- [ ] **T3.1** — Redesign the home: `apps/web/app/page.tsx` + `page.module.css` — keep the server `fetch` + `noStore()` boundary; render health status via `StatusLabel` and the seed summary (20 items, 1 reference set, 30 profiles, plus existing payload counts) with a clear typographic hierarchy, sober Spanish copy (no marketing clichés, no clinical claims), no role redirect; a non-OK health payload is an explicit error/warning state. [UX] Done when: a healthy seeded API shows health OK + seed counts in Spanish within hierarchy, and an unreachable API path surfaces a Spanish retryable state (web-pages Home scenarios). <!-- sdd-owner: implementation -->
- [ ] **T3.2** — Redesign login: `apps/web/app/login/page.tsx` + `page.module.css` — `Field` username/password with `autoComplete="username"`/`"current-password"`, `Button busy` during submission, invalid credentials render `role="alert"` and focus the password `Field` handle, success routes to `/catalogo` with no `alert()`, and a `Volver al inicio` link is always present; API/auth contracts unchanged. [UX] Done when: credential errors are announced and focused, and successful login navigates without a native alert (web-pages Login scenarios). <!-- sdd-owner: implementation -->
- [ ] **T3.3** — Redesign the catalog list: `apps/web/app/catalogo/page.tsx` + `page.module.css` — preserve the role guard (redirect for anonymous, explained denied treatment for `evaluado`, no table); filter toggle Buttons (Todos/Borradores/Publicados/Archivados) with `aria-pressed` and page reset to 1; `Table<InstrumentRow>` with `StatusLabel`, version, tabular numerals; skeleton while `rows === null`; `EmptyState` when zero rows (create action only when `canManage`); `ErrorState` with retry; `Pagination`; create Link Button; username not duplicated in the header. [UX] Done when: the active filter exposes `aria-pressed="true"`, an empty list offers first creation, and pagination boundaries are labelled (web-pages Catalog scenarios). <!-- sdd-owner: implementation -->
- [ ] **T3.4** — Redesign the new-instrument form: `apps/web/app/catalogo/nuevo/page.tsx` + `page.module.css` — preserve permission guard and create behavior; per-field key-pattern validation with persistent helper text and errors linked via `aria-describedby`; first-invalid `Field` receives focus after failed submit; permission-denied case is an explained `EmptyState` with no form; unchanged POST body and idempotency key; Cancel returns to catalog. [UX] Done when: a violating key shows a field-linked error and receives focus, and a denied user sees an explained state without a form (web-pages New Instrument scenarios). <!-- sdd-owner: implementation -->
- [ ] **T3.5** — Redesign the version editor: `apps/web/app/catalogo/[instrumentId]/versiones/[versionId]/page.tsx` + `page.module.css` — Breadcrumb (catálogo → instrumento → versión), page header with `StatusLabel`, `Skeleton` until the detail resolves, `Field` controls inside semantic fieldsets, read-only/seed states with explanatory text connected via `aria-describedby` (never disabled styling alone); save stays PUT with the existing payload/idempotency, `Button busy` + `Notice role="status"` "Borrador guardado"; publish/archive open the owned `Dialog` (`dialogAction` page-owned) and only the confirmation invokes the existing POST; published versions remain immutable and lifecycle guards unchanged. [UX] Done when: draft save announces and keeps a polite status, a seed version explains read-only with associated text, and publish uses the accessible dialog with no `confirm()` (web-pages Editor scenarios). <!-- sdd-owner: implementation -->
- [ ] **T3.6** — Implement `apps/web/components/ui/LikertMatrix.tsx` + `LikertMatrix.module.css` and migrate the evaluator preview: `apps/web/app/catalogo/[instrumentId]/versiones/[versionId]/vista/page.tsx` + `page.module.css` — published-only behavior preserved; matrix renders each item as a row and the five exact payload options as column headings (label + order preserved), required rows show visible Spanish "obligatorio" text, per-cell `headers` associations, inner overflow region at 375px, `interactive={false}` for F2 (no fake disabled controls); metadata header keeps key/version/date; API 404/unavailable renders a Spanish not-found/error treatment with back link and no partial matrix; no numeric values, answer keys, or scoring interpretation. [UX] Done when: a published synthetic version renders the full matrix with exact option headings and required markers, and at 375px only the matrix scrolls (web-components + web-pages Evaluator scenarios). <!-- sdd-owner: implementation -->
- [ ] **T3.7** — Add route surfaces: `apps/web/app/loading.tsx` (branded root fallback), `apps/web/app/error.tsx` (client error boundary using shared `ErrorState` with `reset()` retry), `apps/web/app/not-found.tsx` (branded Spanish 404 with a way back to `/`), plus `loading.tsx`/`error.tsx` under `login/`, `catalogo/`, `catalogo/nuevo/`, `[versionId]/`, and `[versionId]/vista/` — layout-matched `Skeleton` surfaces and `ErrorState` retry; focus moves to the main region on route change where the App Router structure supports it. [UX] Done when: an unknown URL renders the branded Spanish 404, every affected route has a skeleton loading surface, and transient failures offer a working retry (web-pages Route Surfaces + web-accessibility Focus Management scenarios). <!-- sdd-owner: implementation -->
- [ ] **T3.8** — Layer-3 gate: `cd apps/web && npm run build` after each route; run the proposal's route smoke checklist for anonymous, `admin`, `psicologo`, and `evaluado`; verify `apps/web/lib/api.ts`, `apps/web/lib/auth.ts`, and all API/contract files remain untouched via a git diff scope check. [UX] Done when: build is green, the smoke checklist passes, and the diff touches only `apps/web` (excluding `lib/api.ts`/`lib/auth.ts`) and documentation (design §6 Layer 3 gate). <!-- sdd-owner: implementation -->
- [ ] **T4.1** — Write `apps/web/docs/design-system.md` as the F3–F6 inheritance reference: token names/values (documenting, never redefining — no second token source), typography scale, spacing rhythm, component usage with the ARIA contracts, accessibility rules, the evaluator matrix pattern, and explicit do/don't rules (no raw hex, no `system-ui`, no styling dependency, no matrix reimplementation). [UX] Done when: F3 can consume tokens, typography, spacing, and the item/option pattern without adding a styling dependency or changing the API contract (web-foundations inheritance scenario). <!-- sdd-owner: implementation -->
- [ ] **T4.2** — Freeze token contrast: compute every foreground/background pairing actually used by the affected routes — normal text ≥4.5:1, large text ≥3:1, focus/control boundaries/status icons ≥3:1; success token ≥4.5:1 on the canvas where it appears; adjust only token values if a pair fails, preserving the navy/cold-neutral direction, and verify `#1e8e3e` never returns. [UX] Done when: every used pairing passes and the final values are recorded in `design-system.md` (web-foundations contrast scenarios). <!-- sdd-owner: implementation -->
- [ ] **T4.3** — Manual keyboard/accessibility pass: skip link → main; logical tab order and visible focus on all interactive elements (not obscured by sticky chrome); filters, forms, pagination, editor actions, Dialog focus trap, and table/matrix reading order with a screen reader; landmarks + single `h1` per page; `prefers-reduced-motion: reduce` pass (transitions near-instant, no delayed input); 375px and desktop viewports; target sizes ≥24×24px with ≥44px on primary controls and nav links; status identifiable without color. [UX] Done when: all web-accessibility spec scenarios pass (full route keyboard pass, dialog focus lifecycle, reduced-motion pass, target size, status-without-color). <!-- sdd-owner: implementation -->
- [ ] **T4.4** — Freeze the delivery: enumerate the final diff — changed files limited to `apps/web` and documentation; count additions + deletions and keep the total ≤ 3,500 changed lines (trim decoration before accessibility/state coverage if needed); confirm no `window.alert()`/`window.confirm()` remain; confirm no new dependency and `package.json` unchanged except the lockfile. [UX] Done when: the web-foundations scope-boundary scenario holds, the ceiling report is documented, and the anti-checklist passes for raw hex/`system-ui`/one-off values in route components. <!-- sdd-owner: implementation -->
- [ ] **V.1** — Final automated proof: `cd apps/web && npm run build` succeeds with TypeScript strictness intact; repository web/API smoke checks pass; git diff scope check confirms frontend/documentation-only with no API, contract, database, or lifecycle change (proposal AC1 + AC5). [UX] Done when: build is green and the scope boundary holds. <!-- sdd-owner: implementation -->
- [ ] **V.2** — Route-by-route manual checklist (proposal AC4) covering `/`, `/login`, `/catalogo`, `/catalogo/nuevo`, version editor, evaluator view, and shared navigation for anonymous, `admin`, `psicologo`, and `evaluado`: health/seed loading + error/retry; login autocomplete/busy/error announcement/focus recovery; catalog role guard, `aria-pressed` filters, responsive table, skeleton, empty state, error/retry, pagination labels, status labels; nuevo per-field validation and first-invalid focus; editor draft loading, save/busy/status, read-only/seed, breadcrumb, publish/archive dialogs; evaluator matrix and not-found treatment; wordmark, active route, role-preserving links, logout, keyboard operation, mobile layout. [UX] Done when: every checklist row passes and is recorded with no functional regression (proposal AC4). <!-- sdd-owner: implementation -->
- [ ] **V.3** — Contrast AA final verification on the delivered routes (rendered pairs, not only the token table): normal text ≥4.5:1, large text ≥3:1, meaningful non-text indicators ≥3:1 on the shipped pages. [UX] Done when: every sampled rendered pairing passes WCAG 2.2 AA (proposal AC3 + web-accessibility contrast scenarios). <!-- sdd-owner: implementation -->
- [ ] Start or reuse bounded review of each chained PR (foundations → components → pages → a11y/docs) before merge, then deliver each slice to main in order (stacked-to-main). <!-- sdd-owner: parent -->
    - [ ] Run `sdd-verify` against the 4 specs (web-foundations, web-components, web-pages, web-accessibility) and the proposal acceptance criteria, confirm the freeze/ceiling result, then archive the change. <!-- sdd-owner: parent -->

## Slice 2 — Layer 2: Low-state primitives (PR 2)

- Change: `f2-catalogo-ux-redesign`
- Slice: 2 of 4 / PR 2, stacked-to-main.
- Assigned work: implementation-owned T2.1–T2.11 only. T3/T4/V and parent-owned lifecycle rows were not changed.
- Delivery path: `stacked-to-main`; parent-provided size exception consumed for this chained slice.
- Scope guard: no pages, API/auth clients, services, contracts, or NavBar replacement was performed.

### Structured status consumed and produced

```yaml
schemaName: spec-driven
changeName: f2-catalogo-ux-redesign
artifactStore: openspec
changeRoot: openspec/changes/f2-catalogo-ux-redesign
artifacts: { proposal: done, specs: done, design: done, tasks: done, applyProgress: done, verifyReport: missing, syncReport: missing }
taskProgress: { total: 33, complete: 18, remaining: 15, unchecked: [T3.1–T3.8, T4.1–T4.4, V.1–V.3] }
deferredParentActions: { total: 2, complete: 0, remaining: 2 }
applyState: ready
dependencies: { apply: ready, verify: blocked, sync: blocked, archive: blocked }
actionContext:
  mode: repo-local
  workspaceRoot: D:\\Personal\\Proyectos\\TestPsico\\psico-proyect
  allowedEditRoots: [D:\\Personal\\Proyectos\\TestPsico\\psico-proyect]
  warnings:
    - Parent supplied edit authority and runtime attempt state: proceed; no second attempt acquired.
    - CodeGraph MCP unavailable; read-only CodeGraph CLI status/explore used before filesystem fallback.
    - No web browser runner exists; keyboard/overflow review was source-level and interactive follow-up remains for parent lifecycle.
nextRecommended: parent-lifecycle
```

### Completed work and persisted checkboxes

- T2.1–T2.10 `[x]`: created the ten requested UI primitive pairs with tokenized CSS Modules, native semantics, Spanish-facing states, and no new dependencies.
- T2.11 `[x]`: final build gate and static keyboard/ARIA/overflow audit passed.
- `tasks.md` was re-read after persistence; T2.1–T2.11 are visibly `[x]` and ownership audit found no malformed markers.

### Files created by Slice 2

- `apps/web/components/ui/Button.tsx`
- `apps/web/components/ui/Button.module.css`
- `apps/web/components/ui/StatusLabel.tsx`
- `apps/web/components/ui/StatusLabel.module.css`
- `apps/web/components/ui/Field.tsx`
- `apps/web/components/ui/Field.module.css`
- `apps/web/components/ui/Feedback.tsx`
- `apps/web/components/ui/Feedback.module.css`
- `apps/web/components/ui/Skeleton.tsx`
- `apps/web/components/ui/Skeleton.module.css`
- `apps/web/components/ui/EmptyState.tsx`
- `apps/web/components/ui/EmptyState.module.css`
- `apps/web/components/ui/Table.tsx`
- `apps/web/components/ui/Table.module.css`
- `apps/web/components/ui/Pagination.tsx`
- `apps/web/components/ui/Pagination.module.css`
- `apps/web/components/ui/Breadcrumb.tsx`
- `apps/web/components/ui/Breadcrumb.module.css`
- `apps/web/components/ui/Dialog.tsx`
- `apps/web/components/ui/Dialog.module.css`
- `openspec/changes/f2-catalogo-ux-redesign/tasks.md`
- `openspec/changes/f2-catalogo-ux-redesign/apply-progress.md`

### Verification evidence

- `cd apps/web && npm run build` — passed before Slice 2 and again after all components; Next.js 14.2.35 strict typecheck passed and all existing routes generated.
- Static component audit — passed: all ten pairs exist; no `role="grid"`, `999px`, `system-ui`, `window.alert`, or `window.confirm` in the new component files.
- Token audit — passed: no raw hex values in the new component TSX/CSS Modules.
- `git diff --check` and scope/dependency audit — passed; no package, API/auth, services, or contracts diff.
- Source-level keyboard audit — passed for Button, Field, Dialog, Pagination, and Table paths: native controls, `:focus-visible`, ref focus, Escape/Tab handling, disabled boundaries, and inner overflow are implemented.

### Strict TDD / build-gated evidence

Strict TDD is enabled repository-wide, but the web package has no test runner and the design forbids adding a UI test framework. Per the parent decision, `next build` is the applicable build-gated RED/GREEN-equivalent proof; no test dependency or web test suite was added.

| Tasks | Test layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| T2.1–T2.10 | N/A — web build/typecheck | Baseline build passed | Contract/static gates defined before implementation | Final build passed | Variant/ARIA/token audit passed | Final build passed after Dialog focus containment refinement |
| T2.11 | `npm run build` + static audit | Prior build passed | Layer gate assertions defined | Final build passed | 375px/desktop behavior checked against source contracts | No further code change |

### Deviations and risks

- Interactive browser keyboard execution was unavailable because no browser automation/test runner is installed. The source-level audit passed; parent lifecycle should perform the interactive 375px/desktop confirmation.
- Dialog focus priority recognizes consumer `[data-dialog-cancel]`/`[data-dialog-confirm]` markers and otherwise falls back to the first non-confirming button; Dialog remains presentational and owns no API mutation.
- New primitives are intentionally not consumed by pages until Slice 3.

### Workload / PR boundary

- PR 2 / Slice 2 / T2.1–T2.11 only; strategy `stacked-to-main`.
- Parent lifecycle owns bounded review, delivery, verification, and archive. No receipt was created or approved and no commit was made.
- The exact current unchecked task lines remain above under `Remaining unchecked tasks`; they begin at T3.1 and include T3/T4/V plus the two parent rows.


## Slice 3 (PR 3) — pages and route states (T3.1–T3.8)

- Home, login, catalog list, new-instrument form, and version editor migrated to the ui/ primitives (StatusLabel, Field, Table, Skeleton, EmptyState, ErrorState, Pagination, Breadcrumb, Dialog, Button busy); no `window.confirm`/`alert()` remain.
- LikertMatrix component created and integrated into the evaluator preview (item×option matrix with column headings, required markers, inner overflow).
- Route surfaces added: root `loading.tsx`/`error.tsx`/`not-found.tsx` + loading/error per route (login, catalogo, nuevo, editor, vista) with layout-matched Skeleton and ErrorState retry.
- Gate: `npm run build` PASS; scope check: `lib/api.ts`, `lib/auth.ts`, `services/api/**` untouched.
- The apply subagent timed out after implementing T3.1–T3.6; the parent completed the vista migration (T3.6 integration), created the missing route surfaces (T3.7), fixed relative CSS module paths, and ran the layer-3 gate (T3.8).
- Remaining: interactive browser smoke checklist (anonymous/admin/psicologo/evaluado) is manual, per design §6 Layer 3.

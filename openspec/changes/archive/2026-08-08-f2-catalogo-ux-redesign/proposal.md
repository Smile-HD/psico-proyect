# Proposal — F2 Catalog UX Redesign

## 1. Problem

The catalog frontend is functional but is not a reusable product foundation for the upcoming F3–F6 surfaces. The exploration found the following evidence:

- The six real frontend routes (`/`, `/login`, `/catalogo`, `/catalogo/nuevo`, the version editor, and the evaluator view) use repeated inline styles and `system-ui`, with no shared design tokens, typography scale, or component layer.
- Loading is represented by text and can shift the layout; catalog and editor routes have no composed empty state, route-level loading UI, or consistent retryable error state.
- Accessibility gaps include missing skip navigation, missing active navigation semantics, incomplete table semantics, filters without `aria-pressed`, missing login `autocomplete`, errors without live-region semantics, missing focus management, and native `alert()`/`confirm()` calls.
- The current home presents service/seed health as the primary product entry point without a deliberate hierarchy or institutional framing. The exploration proposes retaining that behavior while improving its presentation.
- The current evaluator preview renders Likert options as a bullet list instead of the domain-appropriate item-by-option matrix with column headings.
- The current success green (`#1e8e3e`) does not meet the 4.5:1 WCAG AA target for normal text on the existing background.
- Without a shared system, F3–F6 would likely repeat the same inline styling and accessibility gaps, increasing inconsistency and remediation cost.

This change is worth doing before F3 because the design tokens, interaction primitives, status patterns, and evaluator item pattern are explicit inheritance deliverables, not merely a visual polish pass.

## 2. Objective and non-goals

### Objective

Redesign the frontend catalog foundation as a serious, sober, clear interface for a professional psychometric-assessment platform. The result MUST provide:

- A coherent light-only visual system with semantic tokens, real typographic hierarchy, medium-to-high tool density, and restrained micro-interactions.
- Reusable UI primitives and documented conventions that F3–F6 can inherit without introducing new styling dependencies.
- WCAG 2.2 AA as the written technical accessibility target, including keyboard operation, visible focus, screen-reader semantics, contrast, live announcements, autocomplete, and accessible dialogs.
- Spanish human-facing UI copy and English identifiers/code.
- The same API payloads, permissions, lifecycle rules, and catalog behavior as F2.

### In scope

This change belongs to **F2, owned by Trevor**, and affects the frontend only:

- `apps/web/app/globals.css`: tokens, reset, base typography, focus, reduced-motion, and shared primitives.
- `apps/web/app/layout.tsx`: skip link, local font integration, base metadata, institutional footer, and global shell adjustments.
- `apps/web/components/NavBar.tsx`: TestPsico wordmark, active route semantics, role-preserving navigation, logout placement, and responsive behavior.
- The six existing frontend routes: home, login, catalog list, new instrument form, version editor, and evaluator preview.
- Route-level or shared `loading.tsx`, `error.tsx`, and `not-found.tsx` surfaces where supported by the App Router structure.
- A small owned UI layer of approximately twelve reusable components, including button, field controls, badge/status, table, dialog, notice, skeleton, empty state, page header, breadcrumb, and the reusable item/option presentation pattern.
- Local font assets and a concise design-system/tokens reference for F3–F6.
- Page metadata and a branded favicon.
- A committed `package-lock.json` to make the frontend installation state reproducible.

The implementation MUST remain within the product-owner budget of **3,500 changed lines**. The automatic PR forecast remains in force; if an implementation slice is estimated above 400 changed lines, the delivery decision is made at that point rather than assumed here.

### Out of scope / non-goals

- No API, database, migrations, DTOs, endpoint paths, error-envelope contracts, or `packages/contracts/` changes.
- No changes to `lib/api.ts` or `lib/auth.ts` unless a strictly presentation-only integration fix is proven necessary; their contracts and session behavior remain authoritative.
- No changes to role permissions, deny-by-default behavior, catalog lifecycle, immutable published versions, seed read-only behavior, idempotency, or audit rules.
- No scoring, recommendation, answer-key exposure, or business-logic changes in the client.
- No new F3–F6 routes or backend work. The system is prepared for those phases but does not implement their workflows.
- No drag-and-drop, reordering model, new editing capabilities, or changes to the instrument data model.
- No dark theme in this change.
- No new runtime styling dependency. Tailwind v3.4 remains a documented alternative, not the selected implementation.
- No role-based redirect from the home in this change.

## 3. Design requirements

### 3.1 Visual direction

The visual direction is **light, editorial, and structurally calm**: a professional assessment tool rather than a marketing landing page. Hierarchy comes primarily from typography, spacing, alignment, and semantic status treatment—not decoration.

#### Palette tokens

The implementation MUST use semantic CSS custom properties rather than raw colors in page components. Initial values are:

| Token role | Initial value | Use |
| --- | --- | --- |
| `--color-canvas` | `#F7F8FA` | Application background |
| `--color-surface` | `#FFFFFF` | Main panels and form surfaces |
| `--color-ink-1` | `#1B2430` | Primary text and headings |
| `--color-ink-2` | `#465260` | Secondary text; verify every pairing |
| `--color-accent` | `#24435F` | Primary actions, links, active navigation |
| `--color-accent-strong` | `#1F344A` | Hover/pressed accent state |
| `--color-border` | `#D8DEE5` | Low-emphasis separators and field boundaries |
| `--color-error` | `#B3261E` | Error text and danger actions |
| `--color-success` | `#2E7D32` | Success text and status |
| `--color-warning` | `#8A5A00` | Warning text and status |
| `--color-focus` | `#24435F` | Focus indicator with sufficient adjacent contrast |

Contrast MUST be checked for normal text, large text, controls, separators, and focus indicators. The final values MAY be adjusted only to satisfy the WCAG 2.2 AA acceptance checks while preserving the same cold-neutral/navy direction. Status MUST never be conveyed by color alone; every status includes text and, where useful, a non-color icon or symbol.

No gradients, purple accents, glossy surfaces, or decorative color fields are permitted.

#### Typography

- **Source Sans 3**, locally vendored as WOFF2, is the selected family because it has good Spanish coverage and a restrained humanist tone suitable for a professional assessment tool.
- Weights: 400 body, 500 labels and supporting emphasis, 600 headings and controls, 700 only for strong hierarchy where needed.
- The font MUST load locally with `font-display: swap`; it MUST NOT depend on a network fetch during the Docker build.
- Initial scale: 12px metadata/caption, 14px supporting text, 16px body/control text, 18px lead or section intro, 20px level-3 heading, 24px level-2 heading, 28–32px page heading.
- Body text uses approximately 1.5–1.65 line-height and a readable measure of roughly 60–75 characters on wide screens.
- Headings use balanced wrapping and sentence case. Data such as version numbers, dates, and counts uses tabular numerals.

#### Density and layout

- Use a 4/8px spacing rhythm with semantic spacing tokens.
- Use a constrained content container rather than edge-to-edge desktop content; the catalog and editor may be denser than login and home.
- Prefer semantic sections, tables, fieldsets, and aligned metadata over decorative cards.
- Use bounded radii (approximately 4–12px by hierarchy). Status labels MAY be compact, but no universal pill treatment or `999px` radius is allowed.
- Use hairline separators and at most a subtle, tinted elevation treatment where hierarchy requires it. Avoid shadow-led hierarchy.
- Responsive behavior MUST be mobile-first, avoid horizontal page overflow, preserve table usability through an intentional overflow region, and keep interactive targets at least 44px where practical.

### 3.2 Concrete anti-checklist for an AI-generated look

The implementation fails visual review if it introduces any of the following:

- Purple, blue-purple, or multicolor gradients; decorative mesh gradients; or glow effects.
- Oversized hero typography or deliberately giant empty sections unrelated to task priority.
- Generic equal three-column card rows, card-everything layouts, or floating cards with exaggerated shadows.
- Excessive rounded corners, `999px` borders, or pill buttons/badges used as the default for every component.
- Display/decorative fonts, emoji as icons, inconsistent icon families, or unlicensed guessed brand artwork.
- Generic Tailwind/shadcn defaults that have not been translated into the approved semantic system.
- Pure color changes as the only feedback for active, error, success, or permission states.
- Inline style duplication, raw hex values in route components, or one-off spacing/radius values that bypass tokens.
- Animations that move layout with `top`, `left`, `width`, or `height`, continuous scroll listeners, or motion that competes with assessment content.
- Marketing copy clichés, exclamation-heavy status messages, or copy that makes synthetic research data sound clinically validated.

### 3.3 Required states and interaction behavior

Every affected route MUST have an intentional treatment for the relevant states:

- **Loading:** layout-matched skeletons or reserved placeholders, not only a text spinner; loading controls expose disabled/`aria-busy` state where applicable.
- **Error:** direct Spanish explanation, `role="alert"` or an appropriate live region, a visible retry/recovery action, and no `window.alert()`.
- **Empty:** explanatory Spanish message, next useful action, and preserved page context; the empty catalog points to creating the first instrument when permissions allow.
- **Permission/read-only:** explain the reason in text and semantics; do not rely on disabled styling alone.
- **Success/status:** use `role="status"`/`aria-live="polite"` for non-blocking announcements and keep the message visible long enough to be read.
- **Destructive or irreversible action:** use an owned accessible dialog for publish/archive confirmation, with labelled title/description, keyboard escape/cancel, focus management, and return focus to the trigger.
- **Forms:** visible labels, persistent helper text where useful, field-level errors connected through `aria-describedby`, `autocomplete` on login credentials, and focus on the first invalid field after submission.
- **Navigation:** active route exposed with `aria-current="page"`; a keyboard-accessible skip link reaches main content; mobile navigation does not compress links below usable targets.
- **Evaluator preview:** required items are marked with text and accessible semantics; Likert options are represented as an item-by-option matrix with column headings or the equivalent accessible table structure.

Micro-interactions MUST be discreet and meaningful: approximately 150–300ms for hover, focus, pressed, and disclosure transitions; use transform/opacity where motion is needed; provide visible hover and pressed states; and disable or substantially reduce non-essential motion under `prefers-reduced-motion: reduce`. Motion MUST not delay keyboard or pointer input.

## 4. Assumed decisions (explicitly revisable during proposal review)

The product owner left five questions open in the exploration. This proposal resolves them as follows; each decision is an assumption and MAY be revised before specification/design is approved.

1. **Home behavior by role — assumed: preserve the home as the health/seed state page.** The home receives a deliberate entry design, but it does not redirect users by role. Role-aware navigation remains the responsibility of `NavBar`. This avoids changing F2 routing behavior while preserving a useful public health/seed surface.
2. **Theme — assumed: light-only.** One fully tested, high-quality theme is preferable to two partially tuned themes for this foundation. Dark mode is a later change and is not implied by these tokens.
3. **Brand — assumed: textual `TestPsico` wordmark.** The wordmark uses the approved typographic/accent treatment and no graphic logo. This keeps the brand quiet and avoids inventing an unsupported visual mark.
4. **Budget — fixed at 3,500 changed lines.** This is the product-owner ceiling, superseding the smaller exploration estimate. It includes implementation and necessary design-system documentation, with PR sizing still governed by the automatic forecast.
5. **Technical approach — ratified: CSS custom-property design tokens + CSS Modules + approximately twelve owned components, with zero new dependencies.** This gives F3–F6 an isolated, framework-native contract and avoids fighting framework defaults that could recreate the prohibited generic look. Tailwind v3.4 is retained only as a documented alternative if the team later values utility-speed more than dependency minimization and explicit styling control; it is not part of this change.

Additional standing assumptions from repository constraints: UI copy remains Spanish, identifiers and technical tokens remain English, all data remains synthetic/research-only, and the catalog API contract remains unchanged.

## 5. Verifiable acceptance criteria and success criteria

### Acceptance criteria

1. **Build and scope:** `cd apps/web && npm run build` succeeds with TypeScript strictness intact. The diff is frontend/documentation-only, stays within 3,500 changed lines, and introduces no API, contract, database, or catalog lifecycle changes.
2. **Shared foundation:** affected route components consume semantic tokens and reusable components; no repeated page-level `system-ui`, raw color literals, or broad inline-style redesign remains. Local Source Sans 3 loads without a network dependency during build.
3. **Accessibility:** a manual keyboard and screen-reader-oriented pass confirms skip navigation, logical focus order, visible focus, `aria-current`, labelled controls, table caption/header scope, filter state, field descriptions/errors, live announcements, accessible dialog behavior, and reduced-motion behavior. Contrast checks confirm WCAG 2.2 AA targets: 4.5:1 normal text, 3:1 large text and meaningful non-text indicators where applicable.
4. **Manual route smoke checklist:**
   - `/`: health/seed success, loading, and error/retry states; no role redirect; Spanish institutional context.
   - `/login`: visible labels, autocomplete, busy state, invalid-credential error announcement, focus recovery, and successful login without `alert()`.
   - `/catalogo`: role guard, active filters with `aria-pressed`, responsive table semantics, loading skeleton, empty state, error/retry, pagination labels, and status labels.
   - `/catalogo/nuevo`: permission guard, helper/error per field, first-invalid focus, validation, and unchanged create behavior.
   - Version editor: draft loading, save/busy/status feedback, read-only/seed behavior, breadcrumb, accessible publish/archive dialogs, and unchanged lifecycle permissions.
   - Evaluator preview: published-only behavior, metadata, responsive item-by-option matrix, required-item announcement, loading/error/not-found treatment, and unchanged labels/payload interpretation.
   - Shared navigation: TestPsico wordmark, active route, role-preserving links, logout behavior, keyboard operation, and mobile layout.
5. **Functional regression:** existing F2 CRUD, permission, draft/publish/archive, seed read-only, session storage, and API error-envelope behavior remain unchanged. The web build and the repository's relevant web/API smoke checks pass after the redesign.
6. **Inheritance handoff:** a design-system reference documents tokens, typography, spacing, component usage, accessibility rules, and the evaluator item/option pattern so F3–F6 can consume the foundation without recreating it.

### Success criteria

- A reviewer can identify the current route, primary action, status, and recovery path without relying on color or decorative effects.
- The catalog and editor feel like one professional assessment workspace rather than six separately styled pages.
- F3 can reuse the tokens and item/option presentation without adding a styling dependency or changing the API contract.
- No critical accessibility issue, functional regression, or prohibited AI-look anti-pattern remains at verification.

### Rollback plan

Because the change is frontend-only, rollback is a Git revert of the redesign commit(s) or PR slices in reverse order. No API, database, migration, contract, published instrument, seed, or audit rollback is required. After reverting, run the web build and the relevant F2 smoke checks to restore the previous known-good UI. If only one component or route causes a regression, revert that slice while retaining unaffected token/documentation work, then issue a focused follow-up rather than changing backend behavior.

## 6. Risks and mitigations

| Risk | Level | Mitigation |
| --- | --- | --- |
| A 3,500-line ceiling is exceeded or the implementation becomes difficult to review. | Medium | Keep the component layer small, track changed-line forecast per slice, and apply the automatic PR decision when a slice exceeds 400 lines. Remove decorative scope before removing accessibility or state coverage. |
| “Does not look AI-generated” is subjective. | Medium | Use the concrete anti-checklist above, the domain references from exploration, a single palette/accent, and an explicit visual review before implementation is considered complete. |
| CSS Modules and server/client boundaries introduce Next.js regressions. | Medium | Preserve existing route/data boundaries, make client components only where interaction requires them, and validate with `next build` after each implementation slice. |
| A custom accessible dialog is incomplete. | Medium | Limit the dialog to publish/archive confirmation, follow the WAI-ARIA modal pattern, test keyboard escape/cancel/focus return, and avoid using native `confirm()`. |
| Local font assets are unavailable, incorrectly licensed, or increase build complexity. | Medium | Confirm the asset/license before implementation, use `next/font/local` with `font-display: swap`, and keep a tokenized system fallback that preserves layout if the asset is removed. |
| No web e2e suite exists, so a visual refactor could hide functional regressions. | Medium | Keep API clients and payloads unchanged, run `next build`, run relevant repository smoke checks, and execute the route-by-route manual checklist above for roles, lifecycle, errors, and responsive behavior. |
| The Likert matrix becomes unusable on narrow screens or for long Spanish labels. | Medium | Design mobile-first, allow an intentional table overflow region rather than page overflow, preserve column headings and accessible associations, and verify at 375px and desktop widths. |
| Downstream phases diverge from the foundation. | Medium | Treat tokens, components, documentation, and the item/option pattern as explicit acceptance deliverables; make F3–F6 consumers of the documented contract. |
| Missing `docs/05` and `docs/06` could cause invented architecture assumptions. | Low | Use only `README.md`, `AGENTS.md`, `openspec/config.yaml`, `packages/contracts/README.md`, and the exploration as repository constraints. |

## 7. next_recommended

`sdd-spec`

The next phase should translate this proposal into Given/When/Then requirements, preserving the five revisable assumptions, the frontend-only boundary, the WCAG 2.2 AA target, the 3,500-line ceiling, and the F3–F6 inheritance handoff.

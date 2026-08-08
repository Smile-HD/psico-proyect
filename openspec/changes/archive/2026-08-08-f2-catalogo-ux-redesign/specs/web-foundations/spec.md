# Web Foundations Specification

## Purpose

The shared visual foundation of the TestPsico web frontend: semantic design tokens, locally vendored typography, base globals, layout and density conventions, and motion constraints. This is the explicit inheritance deliverable for F3–F6: no future phase MAY reintroduce per-page styling dependencies, raw color literals, or `system-ui` fallbacks. The system is light-only, cold-neutral with a single desaturated navy accent, and targets a professional psychometric-assessment tool appearance rather than a marketing page.

## Requirements

### Requirement: Semantic Design Tokens

The frontend MUST define and consume a semantic token layer implemented with CSS custom properties in `globals.css`. Tokens MUST cover color, spacing, radius, elevation, motion, and z-index. Initial color values: `--color-canvas` `#F7F8FA`, `--color-surface` `#FFFFFF`, `--color-ink-1` `#1B2430`, `--color-ink-2` `#465260`, `--color-accent` `#24435F`, `--color-accent-strong` `#1F344A`, `--color-border` `#D8DEE5`, `--color-error` `#B3261E`, `--color-success` `#2E7D32`, `--color-warning` `#8A5A00`, `--color-focus` `#24435F`. Final values MAY be adjusted only to satisfy the WCAG acceptance checks while preserving the cold-neutral/navy direction.

Spacing MUST follow a 4/8px rhythm expressed as semantic tokens. Radius MUST be bounded (approximately 4–12px by hierarchy); no universal pill treatment and no `999px` radius is allowed. Elevation MUST rely primarily on hairline separators and at most one subtle, tinted elevation level; shadow-led hierarchy is prohibited. Z-index MUST use a declared scale rather than arbitrary values.

#### Scenario: Route components consume tokens

- GIVEN any affected route or component renders colors, spacing, radius, or elevation
- WHEN the styles are inspected
- THEN every value resolves to a semantic custom property
- AND no raw hex literal, `system-ui` font stack, or one-off spacing/radius value remains in route components

#### Scenario: Elevation stays subtle

- GIVEN a surface that needs separation from the canvas
- WHEN its elevation treatment is inspected
- THEN it uses hairline separators and at most a single subtle tinted shadow
- AND no exaggerated or black-based drop shadows are present

### Requirement: Token Contrast Compliance

All foreground/background token pairings used for text MUST meet WCAG 2.2 AA: at least 4.5:1 for normal text and at least 3:1 for large text (18pt/24px or 14pt/18.66px bold) and meaningful non-text indicators. The success token MUST be at least 4.5:1 on the surfaces where it appears; the previous `#1e8e3e` value, which fails AA on the canvas, MUST NOT be used for text. Separators and focus indicators MUST meet the applicable 3:1 non-text contrast target.

#### Scenario: Success status passes AA

- GIVEN the success token `#2E7D32` rendered as text on the canvas `#F7F8FA`
- WHEN the contrast ratio is computed
- THEN it is at least 4.5:1

#### Scenario: Focus indicator is perceivable

- GIVEN a focused interactive element with the `--color-focus` indicator
- WHEN contrast against the adjacent background is measured
- THEN the indicator meets at least 3:1

### Requirement: Local Product Typography

The product MUST use **Source Sans 3** as its single family, vendored locally as WOFF2 and loaded with `next/font/local` and `font-display: swap`. Loading MUST NOT depend on a network fetch during the Docker build. Weights: 400 body, 500 labels and supporting emphasis, 600 headings and controls, 700 only for strong hierarchy. The initial scale MUST be: 12px metadata/caption, 14px supporting text, 16px body/control text, 18px lead or section intro, 20px level-3 heading, 24px level-2 heading, 28–32px page heading. Body text MUST use approximately 1.5–1.65 line-height and a readable measure of roughly 60–75 characters on wide screens. Headings MUST use balanced wrapping and sentence case. Version numbers, dates, and counts MUST use tabular numerals.

#### Scenario: Build works offline

- GIVEN a Docker build with no network access
- WHEN the web app is built
- THEN Source Sans 3 loads from the vendored WOFF2 assets
- AND the build succeeds without fetching the family remotely

#### Scenario: Data renders with tabular numerals

- GIVEN a version number, date, or count rendered in a data column
- WHEN the digits are inspected
- THEN they use tabular figures so aligned values do not shift

### Requirement: Base Globals and Reset

`globals.css` MUST define a reset, base typography, `:focus-visible` styling, `prefers-reduced-motion` handling, and consistent selection/scroll behavior. Focus MUST be visibly indicated (approximately 2px indicator with sufficient adjacent contrast) whenever the element receives keyboard focus, and focus styles MUST NOT be removed in favor of browser defaults or `outline: none`.

#### Scenario: Keyboard focus is always visible

- GIVEN a keyboard user tabbing through an affected page
- WHEN an interactive element receives focus
- THEN a visible focus indicator appears
- AND the indicator is never suppressed

### Requirement: Layout, Density, and Responsive Behavior

The layout MUST use a constrained content container rather than edge-to-edge desktop content; the catalog and editor MAY be denser than login and home. Responsive behavior MUST be mobile-first, MUST avoid horizontal page overflow, and MUST preserve table usability through an intentional overflow region rather than page overflow. Interactive targets MUST be at least 44px where practical. The root MUST declare an explicit viewport configuration and `theme-color`.

#### Scenario: Table overflows within its region

- GIVEN a wide instrument table on a 375px viewport
- WHEN the page is rendered
- THEN the page itself does not scroll horizontally
- AND the table scrolls within its own overflow region

### Requirement: Motion and Micro-interaction Constraints

Micro-interactions MUST be discreet: approximately 150–300ms for hover, focus, pressed, and disclosure transitions, using `transform`/`opacity` only. Motion MUST NOT animate layout-affecting properties (`top`, `left`, `width`, `height`), MUST NOT use continuous scroll listeners, and MUST NOT delay keyboard or pointer input. Under `prefers-reduced-motion: reduce`, non-essential motion MUST be disabled or substantially reduced.

#### Scenario: Reduced motion disables transitions

- GIVEN a user with `prefers-reduced-motion: reduce`
- WHEN an interactive element changes state
- THEN non-essential transitions are disabled or reduced to an instant or near-instant change

### Requirement: Change Scope and Inheritance Contract

This change MUST be frontend/documentation-only: no API, database, migration, DTO, endpoint, error-envelope, or `packages/contracts` change; no change to `lib/api.ts` or `lib/auth.ts` contracts; no change to role permissions, catalog lifecycle, immutable published versions, seed read-only behavior, idempotency, or audit rules. The web diff MUST stay within the product-owner ceiling of 3,500 changed lines. UI copy MUST remain Spanish, identifiers and technical tokens MUST remain English, and all data remains synthetic/research-only. A concise design-system/tokens reference MUST be produced so F3–F6 consume the foundation without recreating it.

#### Scenario: Scope boundary holds

- GIVEN the completed change diff
- WHEN the changed files are enumerated
- THEN they are limited to `apps/web` and documentation
- AND no API, contract, database, or lifecycle file is modified

#### Scenario: Foundation is documented for inheritance

- GIVEN the design-system reference produced by this change
- WHEN F3 consumes tokens, typography, spacing, and the item/option pattern
- THEN it can do so without adding a styling dependency or changing the API contract

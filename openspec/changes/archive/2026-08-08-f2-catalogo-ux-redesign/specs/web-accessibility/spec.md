# Web Accessibility Specification

## Purpose

The written WCAG 2.2 AA technical target for the redesigned TestPsico frontend, and the concrete anti-checklist that defines an acceptable "professional, not AI-generated" visual review. These requirements apply to the six affected routes and the shared components; they are the acceptance bar F3–F6 inherit. Verification is a manual keyboard and screen-reader-oriented pass plus contrast computation, since the project has no web e2e suite.

## Requirements

### Requirement: WCAG 2.2 AA Contrast Target

All text MUST meet 4.5:1 contrast for normal text and 3:1 for large text against its background (WCAG 1.4.3). Meaningful non-text indicators (focus indicators, control boundaries, status icons) MUST meet 3:1 against adjacent colors (WCAG 1.4.11). Separator lines MAY be lower contrast as long as they are not the only indicator of a required distinction.

#### Scenario: Every token pairing is verified

- GIVEN the token pairs actually used by the affected pages
- WHEN each pair's contrast ratio is computed
- THEN text pairs meet 4.5:1 (3:1 for large text)
- AND non-text indicators meet 3:1

### Requirement: Keyboard Operation and Visible Focus

Every interactive element on the affected routes MUST be operable by keyboard alone with a logical tab order matching the visual order (WCAG 2.1.1). Visible focus MUST be present on every focused interactive element (WCAG 2.4.7) and MUST NOT be obscured by sticky chrome or other elements (WCAG 2.4.11).

#### Scenario: Full route keyboard pass

- GIVEN a keyboard-only user on each affected route
- WHEN the user tabs through all interactive elements
- THEN every element receives visible focus in visual order
- AND no interactive element is unreachable or focus-obscured

### Requirement: Focus Management

Focus MUST be managed at the required transition points: the skip link moves focus to main content; after a failed form submission focus moves to the first invalid field; dialogs move focus in on open, contain it while open, and return it to the trigger on close; route changes that replace main content move focus to the main region where the App Router structure supports it.

#### Scenario: Dialog focus lifecycle

- GIVEN an open publish confirmation dialog
- WHEN the dialog opens, the user tabs inside, and the dialog closes
- THEN focus moves in on open, cycles within the dialog while open
- AND returns to the publish trigger on close

### Requirement: Live Regions and Announcements

Errors MUST be announced through `role="alert"` or an equivalent live region (WCAG 4.1.3). Non-blocking status changes (save confirmations, state transitions) MUST be announced politely through `role="status"`/`aria-live="polite"` and MUST remain visible long enough to be read. The application MUST NOT use `window.alert()` or `window.confirm()`.

#### Scenario: Login error is announced

- GIVEN a failed login attempt
- WHEN the error message renders
- THEN a screen reader announces it without user focus on the message
- AND the message remains visible for inspection

### Requirement: Input Purpose and Form Semantics

Input fields MUST identify their purpose where the HTML autocomplete vocabulary applies: login credentials MUST use `autocomplete="username"` and `autocomplete="current-password"` (WCAG 1.3.5). Every field MUST have a visible, programmatically associated label; errors MUST be connected through `aria-describedby` with `aria-invalid`; helper text MUST be persistent for complex fields rather than placeholder-only.

#### Scenario: Credential fields support autofill

- GIVEN the login form
- WHEN its fields are inspected
- THEN the username and password fields declare their autocomplete purpose
- AND labels are programmatically associated with each control

### Requirement: Semantic Structure and Landmarks

Pages MUST expose correct landmarks (`header`, `nav`, `main`, `footer`), a single `h1` per page with a sequential heading hierarchy, navigation with `aria-current="page"` on the active route, and complete table semantics (caption, header `scope`, row/column associations). The evaluator matrix MUST associate column headings with each item's options (WCAG 1.3.1, 4.1.2).

#### Scenario: Screen-reader structure pass

- GIVEN the catalog list and evaluator routes
- WHEN a screen reader navigates landmarks and tables
- THEN main content is reachable via the skip link
- AND the catalog table and the evaluator matrix announce headers and associations correctly

### Requirement: Motion Reduction

All non-essential motion MUST be disabled or substantially reduced under `prefers-reduced-motion: reduce` (WCAG 2.3.3). Essential motion (such as a focus indicator) MAY remain. Motion MUST never delay input handling or hide state changes behind an animation.

#### Scenario: Reduced-motion pass

- GIVEN a user with `prefers-reduced-motion: reduce`
- WHEN interacting with buttons, filters, dialogs, and skeletons
- THEN transitions collapse to instant or near-instant changes
- AND no interaction is delayed by animation

### Requirement: Target Size

Interactive targets MUST meet the WCAG 2.2 target-size minimum of 24×24 CSS px (WCAG 2.5.8) with exceptions applied only per the criterion's terms, and the implementation MUST aim for 44px on primary controls and navigation per the layout conventions. Filter buttons, pagination controls, and nav links MUST be verifiable as meeting this requirement.

#### Scenario: Filters and pagination meet target size

- GIVEN the catalog filter buttons and pagination controls
- WHEN their rendered hit areas are measured
- THEN each is at least 24×24 CSS px
- AND primary controls and nav links reach 44px where practical

### Requirement: Status Never Conveyed by Color Alone

State information (health OK, instrument status, validation errors, active filter, required items) MUST be conveyed by text and, where useful, a non-color symbol or shape in addition to color (WCAG 1.4.1). No state on the affected routes MAY rely on a pure color change as its only feedback.

#### Scenario: Status labels survive color blindness

- GIVEN the status labels, health indicators, and required markers
- WHEN rendered with color perception removed
- THEN each state remains identifiable from its text or symbol

### Requirement: Anti-checklist Visual Review Acceptance

The visual review of the redesigned frontend MUST fail if any of the following are present: purple, blue-purple, or multicolor gradients; decorative mesh gradients or glow effects; oversized hero typography or deliberately giant empty sections unrelated to task priority; generic equal three-column card rows, card-everything layouts, or floating cards with exaggerated shadows; excessive rounded corners, `999px` borders, or pill buttons/badges as the default; display/decorative fonts, emoji as icons, inconsistent icon families, or unlicensed guessed brand artwork; generic Tailwind/shadcn defaults not translated into the approved semantic system; pure color changes as the only feedback for active/error/success/permission states; inline style duplication, raw hex values in route components, or one-off spacing/radius values bypassing tokens; animations that move layout with `top`, `left`, `width`, or `height`, continuous scroll listeners, or motion that competes with assessment content; marketing copy clichés, exclamation-heavy status messages, or copy implying synthetic research data is clinically validated.

#### Scenario: Visual review of the home route

- GIVEN the redesigned home route
- WHEN it is reviewed against the anti-checklist
- THEN it uses sober editorial hierarchy with the approved accent
- AND it contains no prohibited gradients, hero excess, generic card rows, pills, emoji icons, or marketing clichés

#### Scenario: Visual review of the catalog and editor

- GIVEN the redesigned catalog list and version editor
- WHEN they are reviewed against the anti-checklist
- THEN tool density, hairline separators, and tokenized styling are used
- AND no raw hex values, one-off spacing, exaggerated shadows, or pill treatments appear

#### Scenario: Reviewer can identify state without color

- GIVEN any affected route
- WHEN a reviewer identifies the current route, primary action, status, and recovery path
- THEN the identification does not depend on color or decorative effects

# Web Pages Specification

## Purpose

Behavioral requirements for the six affected F2 routes and the shared route surfaces of the TestPsico web frontend: root layout and navigation shell, home, login, catalog list, new instrument form, version editor, and evaluator view. Every route MUST have an intentional treatment for loading, error, empty, permission/read-only, and success states, and MUST preserve the existing F2 API payloads, permissions, lifecycle rules, and catalog behavior.

## Requirements

### Requirement: Root Shell and Shared Navigation

The root layout MUST include a keyboard-accessible skip link that reaches main content, `lang="es"`, an explicit viewport configuration, a `theme-color` consistent with the token palette, base metadata, the NavBar with the TestPsico wordmark and active-route semantics, and an institutional footer with legal/research-only context. Route-level metadata MUST replace the generic global title on every affected page.

#### Scenario: Keyboard user skips navigation

- GIVEN a keyboard user on any affected page
- WHEN the user activates the skip link
- THEN focus moves directly to the main content region
- AND the link is the first focusable element

### Requirement: Home (Health and Seed Status)

The home MUST remain the health/seed state page with a deliberate entry design and no role-based redirect. It MUST show the API health result and seed status (20 items, 1 reference set, 30 profiles, all synthetic/research-only), with layout-matched loading, a retryable error state with a Spanish explanation, and institutional context. Copy MUST be sober: no marketing clichés, no exclamation-heavy status messages, and no claim that synthetic data is clinically validated.

#### Scenario: Healthy home renders with hierarchy

- GIVEN a healthy, seeded API
- WHEN `/` loads
- THEN it shows health OK and the seed counts in Spanish within a clear typographic hierarchy
- AND the page does not redirect by role

#### Scenario: Health check failure offers retry

- GIVEN an unreachable API
- WHEN `/` loads
- THEN a Spanish error explains the failure with `role="alert"`
- AND a visible retry action is available

### Requirement: Login

The login form MUST render visible labels, `autocomplete="username"` and `autocomplete="current-password"` on the respective fields, a busy state during submission, and an invalid-credential error announced through a live region or `role="alert"`. After a failed submission focus MUST move to the first invalid field; after success the user MUST be taken to the authenticated experience without `window.alert()`. A return link to the home route MUST be present.

#### Scenario: Credential error is announced and focused

- GIVEN a login attempt with an invalid password
- WHEN the request fails
- THEN the error is announced as an alert/live region
- AND focus returns to the password field

#### Scenario: Successful login without alert

- GIVEN valid credentials
- WHEN the form submits
- THEN the user is navigated to the authenticated experience
- AND no native `alert()` is invoked

### Requirement: Catalog List

The catalog list MUST preserve the role guard (admin/psicólogo access, evaluado denied per F2 rules), render filters as toggle buttons with `aria-pressed` reflecting the active filter (Todos/Borradores/Publicados/Archivados), and use the accessible Table with caption/scope, status labels, and tabular numerals. It MUST provide a loading skeleton, a composed empty state, an error state with retry, and labelled pagination with explicit boundary states. On mobile the table MUST scroll within its own overflow region. The page header MUST not duplicate the username already shown in the NavBar.

#### Scenario: Active filter is exposed

- GIVEN the catalog list with the "Publicados" filter active
- WHEN the filter buttons are inspected
- THEN the active button has `aria-pressed="true"`
- AND the list shows only published instruments

#### Scenario: Empty list offers first creation

- GIVEN an authenticated `psicólogo` with no instruments
- WHEN the catalog list renders
- THEN the empty state explains the situation
- AND an action to create the first instrument is offered

#### Scenario: Pagination boundaries are labelled

- GIVEN the catalog list with one page of results
- WHEN pagination renders
- THEN the previous control is disabled
- AND the current page is communicated in text

### Requirement: New Instrument Form

The new-instrument form MUST preserve the permission guard and the unchanged create behavior, render visible labels with helper text where useful, validate the key pattern per field (not only as a post-submit global error), connect field errors through `aria-describedby`, and move focus to the first invalid field on failed submission. The permission-denied case MUST be presented as a consistent explained state, not a loose styled paragraph.

#### Scenario: Key pattern error is per-field

- GIVEN a submitted key that violates the pattern
- WHEN the form re-renders
- THEN the key field shows the error linked via `aria-describedby`
- AND focus moves to the key field

#### Scenario: Denied creation explains why

- GIVEN an authenticated user without creation permission
- WHEN `/catalogo/nuevo` renders
- THEN the reason is explained in Spanish text with consistent styling
- AND no create form is exposed

### Requirement: Version Editor

The version editor MUST preserve the F2 lifecycle and permissions (draft save, publish by admin, archive by psicólogo/admin, immutable published versions, seed read-only). It MUST render a breadcrumb (catálogo → instrumento → versión), a loading skeleton, and save feedback through `role="status"` with the save control exposing `aria-busy`. Read-only and seed states MUST explain the reason in text connected via `aria-describedby`, not rely on disabled styling alone. Publish and archive MUST use the accessible Dialog (see `web-components`), never `window.confirm()`. Version numbers MUST use tabular numerals.

#### Scenario: Draft save announces status

- GIVEN a draft with unsaved changes
- WHEN the user saves
- THEN the save control is disabled with `aria-busy`
- AND on success a polite status notice ("Borrador guardado") is announced and stays visible

#### Scenario: Seed version explains read-only

- GIVEN a read-only seed version
- WHEN the editor renders
- THEN the read-only reason is visible as text
- AND it is associated with the disabled controls via `aria-describedby`

#### Scenario: Publish uses the accessible dialog

- GIVEN an admin with a valid draft
- WHEN the user triggers publish
- THEN a dialog opens with a labelled title and description, focus management, and Cancel/Escape
- AND no native `confirm()` is used

### Requirement: Evaluator View

The evaluator view MUST preserve published-only behavior (draft/archived versions not offered), render the version metadata in a page header, and present items through the LikertMatrix component with column headings and required-item text markers. It MUST provide loading and not-found treatment and MUST keep the existing labels and payload interpretation unchanged.

#### Scenario: Published version renders the matrix

- GIVEN a published synthetic version
- WHEN the evaluator view loads
- THEN the metadata header and the item-by-option matrix render with column headings
- AND required items are marked in text

#### Scenario: Missing version shows not-found treatment

- GIVEN a request for an unknown or unavailable version
- WHEN the evaluator view resolves
- THEN a Spanish not-found/error state renders
- AND no partial or broken matrix is shown

### Requirement: Route-level Loading, Error, and Not-found Surfaces

Affected routes MUST use `loading.tsx`, `error.tsx`, and `not-found.tsx` surfaces where supported by the App Router structure, or the equivalent composed in-page states. Loading MUST be layout-matched skeletons; errors MUST be Spanish, live-region compatible, and offer retry where the failure is transient; not-found MUST be a branded Spanish page rather than the generic Next.js 404.

#### Scenario: Unknown route renders branded 404

- GIVEN a URL that matches no route
- WHEN it resolves in the web app
- THEN a Spanish, branded not-found page renders
- AND it offers a way back to a known route

### Requirement: Page Metadata and Favicon

Every affected page MUST export route-appropriate metadata (title and description in Spanish, referencing the product context) and the app MUST expose a branded favicon. The home title MUST no longer be the generic global "Estado del servicio" on pages that have their own purpose.

#### Scenario: Each page announces itself

- GIVEN the login, catalog, editor, and evaluator routes
- WHEN their metadata is inspected
- THEN each has a specific Spanish title and description
- AND no page falls back to the generic root title

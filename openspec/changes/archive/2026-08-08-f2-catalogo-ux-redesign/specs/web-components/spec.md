# Web Components Specification

## Purpose

The owned UI component layer of the TestPsico web frontend: approximately twelve reusable primitives with explicit accessibility contracts. Components live under `apps/web/components/ui/`, use CSS Modules, consume the semantic tokens from `web-foundations`, and introduce zero new runtime dependencies. These components are the reusable contract that F3–F6 inherit; page-level code MUST compose them instead of duplicating inline styles.

## Requirements

### Requirement: Button

The Button component MUST support primary, secondary, ghost, and danger variants with distinct hover, active (pressed), focus-visible, and disabled states. A disabled button MUST be non-interactive and expose the `disabled` state semantically; a button performing an async operation MUST expose `aria-busy` and remain disabled for the duration. Buttons MUST not use a universal pill shape. Interactive hit area MUST be at least 44px where practical.

#### Scenario: Async save exposes busy state

- GIVEN a save button while a draft is being persisted
- WHEN the button is inspected during the request
- THEN it is disabled with `aria-busy="true"`
- AND its label or an adjacent indicator communicates the pending state

#### Scenario: Danger action is visually distinct

- GIVEN a destructive action button (archive) next to a primary action
- WHEN both are rendered
- THEN the danger variant uses the error token and is not visually confused with the primary action

### Requirement: StatusLabel (Badge)

Status labels for instrument states (draft, published, archived, reference) MUST pair a color with text and, where useful, a non-color symbol; color alone MUST NOT convey the state. Status labels MAY be compact but MUST NOT use a universal `999px` pill treatment, and their text MUST meet 4.5:1 contrast on the label surface.

#### Scenario: Archived status is identifiable without color

- GIVEN an archived instrument in the catalog list
- WHEN its status label is rendered and read without color perception
- THEN the word "Archivado" is present
- AND no state depends on color alone

### Requirement: Field Controls

Field controls (input, textarea, select, checkbox) MUST render a visible label, MAY render persistent helper text, and MUST connect errors to the control through `aria-describedby` with `aria-invalid`. Required fields MUST be marked with text and an accessible symbol, not a symbol alone. Placeholder text MUST NOT serve as the label. On form submission with errors, focus MUST move to the first invalid field.

#### Scenario: Field error is announced and linked

- GIVEN a submitted form with an invalid key field
- WHEN the error renders
- THEN the field has `aria-invalid="true"`
- AND the error message id is referenced by the field's `aria-describedby`
- AND focus moves to the first invalid field

### Requirement: Table

The Table component MUST render a `<caption>` or equivalent accessible summary, `scope` on header cells, and an intentional horizontal overflow region on small viewports. Data cells with versions, dates, or counts MUST use tabular numerals. The component MUST NOT require page-level horizontal scrolling.

#### Scenario: Table header structure is complete

- GIVEN the instrument catalog table
- WHEN its semantics are inspected
- THEN it has a caption and every header cell declares its scope
- AND each header cell is programmatically associated with its column

### Requirement: Skeleton

Loading representation MUST use layout-matched skeletons or reserved placeholders rather than a text-only spinner that shifts layout. Skeletons MUST respect `prefers-reduced-motion` and MUST NOT animate layout-affecting properties.

#### Scenario: Loading preserves layout

- GIVEN the catalog list is loading
- WHEN the skeleton renders
- THEN its shape matches the final table layout (rows and columns)
- AND the page does not jump when the data replaces the skeleton

### Requirement: EmptyState

The EmptyState component MUST present an explanatory Spanish message, a useful next action when permitted, and preserved page context (navigation and headings remain visible). The empty catalog MUST point to creating the first instrument when the user's permissions allow creation.

#### Scenario: Empty catalog guides creation

- GIVEN an authenticated `psicólogo` with zero instruments
- WHEN the catalog list renders empty
- THEN an explanatory message is shown
- AND a visible action to create the first instrument is offered

#### Scenario: Empty state without permission explains, not just disables

- GIVEN an authenticated `evaluado` with no catalog access
- WHEN the empty state would apply
- THEN the message explains the situation in text
- AND it does not rely on a disabled-looking control alone

### Requirement: ErrorState and Notice

Error presentation MUST use a direct Spanish explanation, `role="alert"` or an equivalent live region, and a visible retry/recovery action. Non-blocking status feedback (for example "Borrador guardado") MUST use `role="status"`/`aria-live="polite"` and remain visible long enough to be read. The application MUST NOT use `window.alert()` anywhere.

#### Scenario: Load failure offers retry

- GIVEN a catalog request that fails
- WHEN the error state renders
- THEN the message explains the failure in Spanish with `role="alert"`
- AND a retry action is visible and functional

#### Scenario: Save feedback is announced politely

- GIVEN a successfully saved draft
- WHEN the confirmation notice appears
- THEN it uses `role="status"` or `aria-live="polite"`
- AND it stays visible long enough to be read

### Requirement: Dialog

Destructive or irreversible confirmations (publish, archive) MUST use an owned accessible Dialog component following the WAI-ARIA modal pattern: labelled title and description, keyboard `Escape` and an explicit cancel to dismiss, focus moved into the dialog on open, focus contained while open, and focus returned to the trigger on close. The application MUST NOT use native `window.confirm()`.

#### Scenario: Archive confirmation is fully keyboard-operable

- GIVEN an admin triggering archive on a published version
- WHEN the confirmation dialog opens
- THEN focus moves into the dialog
- AND `Escape` or Cancel closes it returning focus to the trigger
- AND the dialog title and description are associated programmatically

#### Scenario: Focus cannot escape the dialog

- GIVEN the publish confirmation dialog is open
- WHEN the user tabs repeatedly
- THEN focus cycles within the dialog
- AND the underlying page is not reachable until the dialog closes

### Requirement: Breadcrumb

Breadcrumb navigation MUST expose the hierarchy (catálogo → instrumento → versión) as a `nav` with an accessible label, mark the current page, and provide a predictable way back. Breadcrumb links MUST meet the 44px target where practical.

#### Scenario: Editor shows full hierarchy

- GIVEN the version editor at three levels of depth
- WHEN the breadcrumb renders
- THEN it lists Catálogo, the instrument, and the current version
- AND the current position is marked as such

### Requirement: NavBar

The NavBar MUST show the textual TestPsico wordmark, expose the active route with `aria-current="page"`, preserve role-based links (evaluado without admin navigation), include logout in a consistent location, and remain keyboard-operable and usable on mobile without compressing links below usable targets. The wordmark MUST use the approved typographic/accent treatment; no graphic logo is required or permitted.

#### Scenario: Active route is announced

- GIVEN an admin on the catalog list page
- WHEN the navigation renders
- THEN the Catálogo link carries `aria-current="page"`
- AND the wordmark links to the home route

#### Scenario: Mobile navigation stays usable

- GIVEN a 375px viewport with an authenticated session
- WHEN the navigation renders
- THEN all links remain reachable with targets of at least 44px
- AND no link is hidden behind an unlabeled control

### Requirement: Pagination

Pagination MUST expose its purpose through labels (`aria-label` or visible text), render page numbers where the contract provides them, and disable the previous/next controls at the boundaries. The current page MUST be identifiable by text, not by color alone.

#### Scenario: Boundary state is explicit

- GIVEN the catalog list on its first page
- WHEN pagination renders
- THEN the "Anterior" control is disabled
- AND the current page number is communicated in text

### Requirement: LikertMatrix

The evaluator item presentation MUST render Likert options as an item-by-option matrix with column headings (or the equivalent accessible table structure), preserving the ordered scales, items, and five labeled options of the published payload. Required items MUST be marked with text and accessible semantics, not a red asterisk alone. The matrix MUST remain usable on narrow screens through an intentional overflow region while preserving column headings and accessible associations.

#### Scenario: Evaluator renders the matrix

- GIVEN a published synthetic version with likert_1_5 items
- WHEN the evaluator view renders
- THEN each item is a row and the five labeled options are columns with headings
- AND the option labels and required markers match the payload

#### Scenario: Required item is announced

- GIVEN a required item in the evaluator view
- WHEN its label is read by a screen reader
- THEN the required status is communicated in text
- AND it is not conveyed by the asterisk alone

#### Scenario: Matrix survives narrow screens

- GIVEN the evaluator view at 375px width
- WHEN the matrix is rendered
- THEN the page does not overflow horizontally
- AND the matrix scrolls within its own region with headings preserved

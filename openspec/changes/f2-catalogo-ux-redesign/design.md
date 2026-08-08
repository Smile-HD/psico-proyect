# Design — F2 Catalog UX Redesign

## 1. Final file tree

The implementation keeps the existing App Router routes and client/server boundaries wherever possible. The shared token layer is intentionally **not** split into a second `tokens.css`: the specification requires the CSS custom properties to live in `apps/web/app/globals.css`, and a second source would create drift. The inheritance reference is documentation, not a second token source.

```text
apps/web/
├── app/
│   ├── fonts/
│   │   └── SourceSans3-Variable.woff2
│   ├── globals.css                         # tokens, reset, element defaults, focus, motion
│   ├── layout.tsx                           # html/lang, local font, skip link, shell, footer
│   ├── layout.module.css
│   ├── loading.tsx                          # branded root loading fallback
│   ├── error.tsx                            # client error boundary; reset() retry
│   ├── not-found.tsx                        # branded global 404
│   ├── page.tsx                             # server home/health/seed page
│   ├── page.module.css
│   ├── login/
│   │   ├── layout.tsx                       # route metadata
│   │   ├── page.tsx                         # client form; API contract unchanged
│   │   ├── page.module.css
│   │   ├── loading.tsx
│   │   └── error.tsx
│   └── catalogo/
│       ├── layout.tsx                       # catalog metadata and segment shell
│       ├── page.tsx                         # client list, filters, pagination
│       ├── page.module.css
│       ├── loading.tsx
│       ├── error.tsx
│       ├── nuevo/
│       │   ├── layout.tsx                   # create metadata
│       │   ├── page.tsx                     # client create form
│       │   ├── page.module.css
│       │   ├── loading.tsx
│       │   └── error.tsx
│       └── [instrumentId]/
│           └── versiones/
│               └── [versionId]/
│                   ├── layout.tsx           # editor metadata
│                   ├── page.tsx             # client draft editor
│                   ├── page.module.css
│                   ├── loading.tsx
│                   ├── error.tsx
│                   └── vista/
│                       ├── layout.tsx       # evaluator metadata
│                       ├── page.tsx         # client published preview
│                       ├── page.module.css
│                       ├── loading.tsx
│                       └── error.tsx
├── components/
│   ├── NavBar.tsx                           # compatibility re-export; no duplicate implementation
│   └── ui/
│       ├── Button.tsx
│       ├── Button.module.css
│       ├── StatusLabel.tsx
│       ├── StatusLabel.module.css
│       ├── Field.tsx
│       ├── Field.module.css
│       ├── Table.tsx
│       ├── Table.module.css
│       ├── Skeleton.tsx
│       ├── Skeleton.module.css
│       ├── EmptyState.tsx
│       ├── EmptyState.module.css
│       ├── Feedback.tsx                      # named exports ErrorState and Notice
│       ├── Feedback.module.css
│       ├── Dialog.tsx
│       ├── Dialog.module.css
│       ├── Breadcrumb.tsx
│       ├── Breadcrumb.module.css
│       ├── NavBar.tsx
│       ├── NavBar.module.css
│       ├── Pagination.tsx
│       ├── Pagination.module.css
│       ├── LikertMatrix.tsx
│       └── LikertMatrix.module.css
├── docs/
│   └── design-system.md                     # F3–F6 inheritance reference
├── public/
│   └── favicon.svg                          # simple TestPsico textual/shape mark
├── package.json
└── package-lock.json                         # committed, generated without new dependencies
```

`not-found.tsx` is global because `/catalogo` and `/catalogo/nuevo` do not identify a server-resolved resource. The dynamic version and evaluator pages currently fetch through client-side `apiFetch`; an API 404 is therefore rendered as an in-page Spanish `ErrorState` with a not-found treatment and a back link. If a later server wrapper calls Next `notFound()`, the global branded surface remains the fallback. This avoids inventing an API or changing the existing client data boundary.

The existing `apps/web/components/NavBar.tsx` remains import-compatible as a one-line re-export of `components/ui/NavBar`. There is only one implementation and one CSS module. Route `layout.tsx` files exist primarily to provide metadata for client pages; they do not fetch data or alter permissions.

### Responsibility and data flow

- `layout.tsx` owns document metadata defaults, `lang="es"`, the local Source Sans 3 font, the skip link, the `#app-shell` wrapper, and institutional footer copy. It does not own session or API state.
- `NavBar` reads the hydration-safe `useSessionUser()` hook, derives role-visible links, derives the active route from `usePathname()`, and delegates logout to `clearSession()` plus `router.replace("/login")`. The server/API remains authoritative for permissions.
- Shared UI components are presentational. They do not import `lib/api.ts`, `lib/auth.ts`, or domain DTOs.
- The home keeps server-side `fetch` and `noStore()`. A failed request is thrown to the segment error boundary so `reset()` is a real retry; a non-OK health payload is rendered as an explicit status state.
- Client routes retain `apiFetch` and local-storage token usage. Each fetch effect gets a local `reloadKey`/retry counter so an `ErrorState` retry repeats the same request without changing its payload or endpoint.
- The editor retains the existing `response_options` → `options` adapter and mutation payload mapping. Dialog state is page-owned; the Dialog only manages presentation and focus.
- The evaluator maps the published response payload to `LikertMatrix` without exposing internal numeric values or answer keys.

## 2. Component contracts (props, variants, ARIA)

All components accept `className?: string` only as an escape hatch for layout composition. Visual values remain in their CSS Modules and resolve to semantic tokens. Icons are `ReactNode` slots supplied by the caller; no icon dependency or emoji fallback is introduced.

### `Button`

```ts
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "compact" | "default";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;       // default: "primary"
  size?: ButtonSize;             // default: "default"
  busy?: boolean;                // controlled async state
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
};
```

- Renders a native `<button>` and forwards `type`, `name`, `value`, `onClick`, `aria-*`, and `data-*` attributes.
- `busy` renders `disabled`, `aria-busy="true"`, and a stable pending label supplied by the caller (for example, `Guardando…`). It must not silently replace meaningful content with an unlabeled spinner.
- `primary`, `secondary`, `ghost`, and `danger` have distinct surface, text, border, hover, pressed, and disabled treatments. `danger` consumes error tokens and is reserved for archive/destructive actions.
- Minimum height is 44px for default controls; compact is allowed for dense editor secondary actions but remains at least 36px and satisfies WCAG 2.5.8.
- Focus is supplied by `:focus-visible` in `globals.css`; the module never uses `outline: none`.
- No universal pill shape: default radius is the control radius token, not `999px`.

### `StatusLabel`

```ts
type StatusKind =
  | "draft" | "published" | "archived" | "reference"
  | "success" | "warning" | "error" | "neutral";

type StatusLabelProps = {
  kind: StatusKind;
  children: React.ReactNode;     // required visible text, e.g. "Archivada"
  symbol?: React.ReactNode;      // optional non-color indicator
  className?: string;
};
```

- Renders a `<span>` with visible status text and optional decorative symbol. The text is the semantic source of truth; color never stands alone.
- Uses bounded compact radius and status surface/text tokens. Labels are not default pills.
- Does not use `role="status"`; status announcements belong to `Notice`, while a table badge is static content.
- Seed/reference status includes text such as `Referencia · sintético`, not only a `title` tooltip.

### `Field`

```ts
type FieldControl = "input" | "textarea" | "select" | "checkbox";

type FieldOption = { value: string; label: string };

type FieldProps = {
  id: string;
  name?: string;
  label: string;
  control?: FieldControl;        // default: "input"
  type?: React.HTMLInputTypeAttribute;
  value?: string;
  checked?: boolean;
  onChange?: React.ChangeEventHandler<
    HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
  >;
  options?: readonly FieldOption[]; // required for select
  helperText?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  readOnly?: boolean;
  placeholder?: string;
  autoComplete?: string;
  rows?: number;
  onBlur?: React.FocusEventHandler<
    HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
  >;
  className?: string;
};
```

- Implemented with `forwardRef<FieldControlHandle>` where `FieldControlHandle` exposes `focus(): void`. The form calls this handle for first-invalid focus; pages do not query arbitrary DOM selectors.
- Always renders a visible `<label htmlFor={id}>`. Placeholder is optional supplementary text and never the label.
- Required fields render the Spanish text `Obligatorio` in addition to the native `required` attribute; the asterisk, if used visually, is supplementary.
- Helper and error IDs are generated deterministically from `id` (`${id}-help`, `${id}-error`). The control joins them in `aria-describedby`.
- When `error` is present, the control exposes `aria-invalid="true"`; the error text is rendered with `role="alert"` only for blocking submit errors, avoiding duplicate announcements for every keystroke.
- `checkbox` uses the same visible label but composes the control and label as a 44px hit area. Select options are native `<option>` elements.
- `autoComplete="username"` and `autoComplete="current-password"` are mandatory at the login call sites.

### `Table`

```ts
type TableColumn<Row> = {
  id: string;
  header: React.ReactNode;
  render: (row: Row) => React.ReactNode;
  numeric?: boolean;
  rowHeader?: boolean;
};

type TableProps<Row> = {
  caption: string;
  captionHidden?: boolean;
  columns: readonly TableColumn<Row>[];
  rows: readonly Row[];
  rowKey: (row: Row) => string;
  className?: string;
};
```

- Renders a semantic `<div className={styles.scrollRegion}>` around `<table>`, with `max-width: 100%` and `overflow-x: auto`; the document never becomes the horizontal scroll container.
- Renders `<caption>` even when visually hidden, `<th scope="col">` for every column, and `<th scope="row">` for the first column marked `rowHeader`.
- Numeric columns receive a module class with `font-variant-numeric: tabular-nums`.
- The wrapper exposes a descriptive label from the caption; no `role="grid"` is added because this is a data table, not an application grid.
- Catalog usage sets columns for key, title, status, version, and actions; the first column is the row header.

### `Skeleton`

```ts
type SkeletonProps = {
  variant: "text" | "heading" | "control" | "block" | "table";
  lines?: number;
  rows?: number;
  columns?: number;
  label?: string;                 // default: "Cargando…"
  className?: string;
};
```

- `table` renders the same column/row geometry expected by `Table`; page loading files use it to reserve the final layout.
- The container exposes `role="status"`, `aria-live="polite"`, and a visually hidden Spanish loading label. It does not rely on a text-only spinner.
- The animation is a low-key opacity pulse; no gradient shimmer, width animation, or layout-affecting animation is used. Reduced motion removes the pulse.

### `EmptyState`

```ts
type EmptyStateProps = {
  title: string;
  description: string;
  action?: React.ReactNode;       // Button or Next Link styled as a control
  contextLabel?: string;
  className?: string;
};
```

- Renders a semantic `<section>` preserving the page heading, navigation, and surrounding context.
- The catalog empty state uses `title="No hay instrumentos todavía"`, explains the current filter/result, and supplies a `Button`/`Link` to `/catalogo/nuevo` only when `canManage` is true.
- A permission-denied state uses `EmptyState` without a fake disabled action and explicitly explains why the section is unavailable.
- No decorative emoji or invented clinical claims are used.

### `Feedback` (`ErrorState` and `Notice` named exports)

```ts
type ErrorStateProps = {
  title?: string;
  message: string;
  retryLabel?: string;
  onRetry?: () => void;
  backAction?: React.ReactNode;
  className?: string;
};

export function ErrorState(props: ErrorStateProps): JSX.Element;

type NoticeProps = {
  tone: "success" | "info" | "warning" | "error";
  message: string;
  title?: string;
  role?: "status" | "alert";    // default: "status" except error => "alert"
  className?: string;
};

export function Notice(props: NoticeProps): JSX.Element;
```

- `ErrorState` renders `role="alert"`, a direct Spanish explanation, and a visible retry/recovery action whenever a recovery path exists. It never prints raw exceptions or request envelopes.
- `Notice` renders `role="status"` and `aria-live="polite"` by default for save/status feedback. `tone="error"` defaults to `role="alert"`.
- The message remains in the DOM until replaced or dismissed by the parent; there is no too-short auto-dismiss timer.
- The module distinguishes tone with text, icon slot/shape, and layout as well as color.

### `Dialog`

```ts
type DialogProps = {
  open: boolean;
  title: string;
  description: string;
  onClose: () => void;
  children: React.ReactNode;      // action group/content, usually Buttons
  initialFocusRef?: React.RefObject<HTMLElement>;
  inertTargetId?: string;         // default: "app-shell"
  className?: string;
};
```

- Controlled, client-only component. The parent owns whether the pending action is publish or archive and supplies the final confirmation button.
- Creates a portal with `createPortal(dialog, document.body)` after a `mounted` guard so SSR/hydration never touches `document`.
- The panel has `role="dialog"`, `aria-modal="true"`, and generated `aria-labelledby`/`aria-describedby` IDs from `useId()`.
- On open it captures `document.activeElement`, then focuses `initialFocusRef.current`, `[data-dialog-autofocus]`, the Cancel button, the first focusable element, or the panel as a final fallback.
- A document-level keydown handler handles `Escape` and a panel keydown handler traps `Tab`/`Shift+Tab` between the current focusable elements. If no focusable elements exist, the panel itself is focusable.
- The overlay does not close on pointer click by default; destructive actions require an explicit Cancel or Escape route. This avoids accidental archive/publish dismissal.
- On close it removes the key handler, restores body overflow, restores any prior `aria-hidden`/`inert` value on `#app-shell` (or `inertTargetId`), and returns focus to the captured trigger if it remains connected.
- While open, the app shell is marked `aria-hidden="true"` and `inert=true` when supported. The portal is outside that shell, so screen-reader and keyboard navigation cannot reach the underlying page.
- The dialog does not own API calls. The editor starts the existing mutation only from the confirm Button and keeps the existing idempotency key/payload behavior.

### `Breadcrumb`

```ts
type BreadcrumbItem = {
  label: string;
  href?: string;
  current?: boolean;
};

type BreadcrumbProps = {
  items: readonly BreadcrumbItem[];
  className?: string;
};
```

- Renders `<nav aria-label="Ruta de navegación"><ol>…</ol></nav>`.
- Links are at least 44px high where practical. The final item is text with `aria-current="page"`; it is never an active link.
- The editor supplies `Catálogo → {instrument_key} → Versión {version_no}`. The evaluator supplies the same hierarchy and a predictable back path.

### `NavBar`

```ts
type NavBarProps = {
  className?: string;
  onLogout?: () => void;          // test/integration override; default clears session and routes
};
```

- Client component. Uses `useSessionUser()` and `usePathname()` internally; it does not accept a role prop that could diverge from the session.
- The wordmark is a textual `TestPsico` link to `/`. The home/status link is separate and sentence-cased.
- Visible links are `/` (Estado del servicio) and `/catalogo` only for `admin`/`psicologo`; `evaluado` never receives the admin link.
- Active exact/prefix route is marked with `aria-current="page"` and a non-color visual indicator. The catalog link remains current on nested editor/evaluator routes.
- Authenticated users receive username text and a consistently placed `Salir` Button; anonymous users receive `Iniciar sesión`.
- Mobile uses a native toggle Button with an explicit Spanish `aria-label`, `aria-expanded`, and `aria-controls`. The opened list remains in the DOM and every link retains a 44px target. No unlabeled hamburger or hover-only menu exists.

### `Pagination`

```ts
type PaginationProps = {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  ariaLabel?: string;              // default: "Paginación del catálogo"
  className?: string;
};
```

- Renders `<nav aria-label>` with previous/next Buttons and page-number Buttons when `totalPages > 1`.
- Previous is disabled at page 1; next is disabled at `page === totalPages`. Disabled state is native and textual.
- Current page has `aria-current="page"` and visible text `Página X de Y`; color is not the only indicator.
- Page changes are clamped to valid bounds and do not mutate filters or API page size.

### `LikertMatrix`

```ts
type LikertOption = { id: string; order: number; label: string };
type LikertItem = {
  id: string;
  order: number;
  text: string;
  required: boolean;
  options: readonly LikertOption[];
};

type LikertMatrixProps = {
  caption: string;
  items: readonly LikertItem[];
  interactive?: boolean;            // false for F2 evaluator preview
  valueByItem?: Readonly<Record<string, string>>;
  onChange?: (itemId: string, optionId: string) => void;
  className?: string;
};
```

- Renders a semantic table inside its own overflow region. The first column is the item row header; each option is a column header with the exact payload label and order.
- Required rows include visible Spanish text `(obligatorio)` and an accessible association; no red asterisk-only marker.
- In F2 preview mode, cells are presentation cells and do not expose fake disabled controls. If `interactive` is later enabled by F3, each row uses one radio group with an accessible label per item and one radio per option; controlled selection is explicit.
- Each cell uses `headers` linking it to the row and option header IDs. Long Spanish labels wrap inside the matrix; only the matrix scrolls horizontally at narrow widths.
- The component does not interpret scoring, answer keys, or numeric values.

## 3. Token system and CSS Modules convention

### Token ownership

`apps/web/app/globals.css` is the only runtime token source. `apps/web/docs/design-system.md` documents the same names and usage; it must not redefine them. No route component contains raw hex values, `system-ui`, or ad-hoc spacing/radius literals.

The initial token groups are:

```css
:root {
  /* semantic color */
  --color-canvas: #F7F8FA;
  --color-surface: #FFFFFF;
  --color-ink-1: #1B2430;
  --color-ink-2: #465260;
  --color-accent: #24435F;
  --color-accent-strong: #1F344A;
  --color-border: #D8DEE5;
  --color-error: #B3261E;
  --color-success: #2E7D32;
  --color-warning: #8A5A00;
  --color-focus: #24435F;
  --color-on-accent: #FFFFFF;

  /* typography */
  --font-family-sans: "Source Sans 3", sans-serif;
  --font-size-caption: 0.75rem;
  --font-size-supporting: 0.875rem;
  --font-size-body: 1rem;
  --font-size-lead: 1.125rem;
  --font-size-heading-3: 1.25rem;
  --font-size-heading-2: 1.5rem;
  --font-size-heading-1: clamp(1.75rem, 1.5rem + 1vw, 2rem);
  --line-height-body: 1.6;
  --line-height-heading: 1.2;

  /* 4/8px rhythm */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;

  /* bounded geometry */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --shadow-subtle: 0 2px 8px rgb(36 67 95 / 0.08);

  /* motion */
  --motion-fast: 150ms;
  --motion-standard: 220ms;
  --motion-slow: 300ms;
  --ease-standard: cubic-bezier(0.2, 0.8, 0.2, 1);

  /* declared layers */
  --z-base: 0;
  --z-header: 10;
  --z-overlay: 100;
  --z-dialog: 110;
}
```

The implementation must run the final token pairs through contrast calculation before freezing values. If a pair fails, only the token value changes, preserving the navy/cold-neutral semantic role. `--color-success` replaces the old `#1e8e3e`; that old value must not return.

### `globals.css` responsibilities

- `@font-face`/Next local-font integration contract is established by `layout.tsx`; `globals.css` sets the family fallback and base type rules.
- Reset `box-sizing`, body margin, inherited button/input font, link color, heading balance, `font-variant-numeric: tabular-nums` utility class, and `scroll-behavior: smooth` when motion is allowed.
- `:focus-visible` uses a two-part focus treatment (outline plus offset) with `--color-focus`; it must remain visible against both canvas and surface.
- `@media (prefers-reduced-motion: reduce)` sets motion durations to near-zero, disables skeleton pulse, and restores non-animated scroll behavior.
- Global styles do not contain page layout classes. `.module.css` files own component and route layout.

### CSS Modules naming and composition

- Every component stylesheet is named after its component: `Button.module.css`, `Dialog.module.css`, etc.
- Modules use stable local classes (`root`, `label`, `control`, `actions`, `scrollRegion`) and state/data selectors (`[data-variant="danger"]`, `[data-busy="true"]`, `[aria-current="page"]`). No BEM-like global names are exported.
- CSS custom properties are referenced as `var(--color-*)`, `var(--space-*)`, `var(--radius-*)`, `var(--motion-*)`, and `var(--z-*)`. Raw colors and magic spacing are prohibited in modules as well as routes.
- Route `page.module.css` files contain only page composition: max-width container, section gaps, grid/flex structure, and responsive arrangement. Visual primitives remain in UI modules.
- Links that need Button appearance use a shared module class composition or a small `LinkButton` style in the consuming page module; no `asChild` abstraction is introduced.
- Breakpoints are mobile-first and consistent: base/375px, `@media (min-width: 48rem)` for tablet (`768px`), `@media (min-width: 64rem)` for desktop (`1024px`), and a max content width around `75rem` (`1200px`).
- Page content uses `padding-inline: var(--space-4)` on mobile and increases to `var(--space-8)` on desktop. Tables and Likert matrices use an inner overflow region, never `body { overflow-x: auto; }`.
- The shell uses `min-height: 100dvh`, not `100vh`. No sticky header hides focused content; if the header becomes sticky, its z-index is `--z-header` and main content receives the necessary offset.
- Transitions are limited to 150–300ms and transform/opacity. No `top`, `left`, `width`, `height`, continuous scroll listener, gradient, glow, or generic dark shadow is introduced. The approved look is light, editorial, structurally calm, and tool-dense rather than a marketing hero.

## 4. Page-to-component and state mapping

| Route | Composition | Loading | Error / empty / permission | Success and interaction notes |
| --- | --- | --- | --- | --- |
| `/` | `layout` shell, page header, health status using `StatusLabel`, seed summary section, `Notice`/`ErrorState`, institutional footer context | `app/loading.tsx` with heading and health/seed skeleton blocks; no layout shift | Server fetch failure is thrown to `app/error.tsx`; `ErrorState` offers `Reintentar` through `reset()`. Non-OK health is an explicit error/warning state. No role redirect. | Shows health plus seed counts (20 items, 1 reference set, 30 profiles, plus existing counts from the payload) and states synthetic/research-only without clinical claims. Home metadata is specific to service status. |
| `/login` | `Field` username/password, `Feedback.ErrorState` or inline alert, `Button`, home `Link` | `login/loading.tsx` reserved form skeleton | Invalid credentials render `role="alert"`, focus the password Field handle, and keep the message visible. No permission empty state. | `autocomplete="username"`/`"current-password"`; `Button busy` during login; success routes to `/catalogo` without `alert()`. A `Volver al inicio` link is always present. |
| `/catalogo` | page header, filter toggle Buttons, `Table<InstrumentRow>`, `StatusLabel`, `Skeleton`, `EmptyState`, `Feedback.ErrorState`, `Pagination`, create Link Button | `catalogo/loading.tsx` uses table skeleton geometry. Client fetch also renders skeleton while `rows === null`. | Unauthenticated users preserve the existing redirect to `/login`. Unauthorized `evaluado` receives a consistent explained `ErrorState`/permission treatment and no table. Fetch failure has retry. Zero rows uses `EmptyState`; create action only when permitted. | Filter buttons set `aria-pressed`; active filter resets page to 1. Table caption/scope/overflow are owned by `Table`. Username is not repeated in the page header because NavBar owns identity. |
| `/catalogo/nuevo` | page header, Breadcrumb (catalog), `Field` for key/title/description, `Feedback.ErrorState`, primary/secondary `Button` | `nuevo/loading.tsx` form skeleton while session readiness is unresolved | Unauthenticated users route to login as today. Denied users see explained `EmptyState`/permission treatment with no form. Key pattern, required fields, and API errors are field-linked or alert-level; first invalid Field receives focus. | Preserve POST body and idempotency key. Key helper text is persistent; placeholder is not the label. Cancel returns to catalog. |
| `/catalogo/[instrumentId]/versiones/[versionId]` | Breadcrumb, page header, `StatusLabel`, `Skeleton`, `Field` controls inside semantic fieldsets, `Notice`, `ErrorState`, `Button`, `Dialog` | Dynamic route `loading.tsx` plus in-page skeleton until detail resolves | Existing role guard/redirect remains. Fetch failure has retry/back link. Seed and published read-only states include explanatory text and `aria-describedby` on disabled controls. Validation errors are announced. | Save remains PUT with existing payload and idempotency. Save Button uses `aria-busy`; success is `Notice role=status` with `Borrador guardado`. Publish/archive open controlled Dialogs; only confirmation starts the existing POST. Published versions remain immutable. |
| `.../[versionId]/vista` | Breadcrumb, page header/metadata, `StatusLabel` if useful, `LikertMatrix interactive={false}`, `ErrorState`, research-only Notice/footer | `vista/loading.tsx` skeleton for header and matrix geometry | Published-only API behavior remains unchanged. API 404/unavailable renders a Spanish not-found/error treatment, no partial matrix, and back link. | Metadata keeps key/version/date. Matrix has item rows, exact option headings, `headers` associations, required text, and inner overflow at 375px. Numeric internals and answer keys remain absent. |
| shared shell | textual TestPsico wordmark, NavBar links, skip link, `main#main-content`, footer | Root `loading.tsx` fallback | Root `not-found.tsx` branded Spanish page with link to `/`; segment `error.tsx` wrappers use shared `ErrorState` and `reset()`. | `lang="es"`, explicit viewport and theme-color metadata, route-specific metadata through segment layouts, focus-visible, reduced motion, and mobile 44px targets. |

### Exact anti-pattern replacements

- Home and login no longer use page-level `system-ui` or inline style objects; all presentation is CSS Module/token driven.
- Login success removes `alert()` entirely. Navigation itself and a persistent route/page state communicate success; invalid credentials use `role="alert"` and focus recovery.
- Editor publish/archive removes `window.confirm()`. Each action validates first, opens the owned Dialog, and only the Dialog confirmation invokes the unchanged API call. Cancel/Escape restore focus.
- Catalog filters become native Buttons with `aria-pressed`; visual active styling is accompanied by text and the semantic pressed state.
- Catalog table moves to `Table`, adding caption, scoped headers, row headers, numeric alignment, and an inner overflow region.
- Text-only `Cargando…` paths become layout-matched `Skeleton` surfaces; route-level `loading.tsx` files cover the App Router transition.
- Loose red error paragraphs become `ErrorState`/`Notice` with live-region semantics, direct recovery copy, and retry where possible.
- Catalog zero-result rendering becomes `EmptyState` with a permission-aware create action.
- The evaluator bullet list becomes `LikertMatrix`: item rows × option columns, exact option headings, required text, and per-cell header associations.
- Seed/reference and read-only states retain their existing permissions but add `StatusLabel`/explanatory text and `aria-describedby`; disabled styling is never the only explanation.

## 5. Dialog mechanism (React 18, zero dependencies)

`Dialog.tsx` is a controlled client component implemented with React 18 primitives:

1. The component tracks `mounted` with `useEffect`; it returns `null` during SSR and calls `createPortal` only after mount.
2. When `open` changes to true, an effect captures the current active element as the return target, sets the body scroll lock, marks `#app-shell` `aria-hidden` and `inert` where available, and schedules focus into the dialog. The preferred order is `initialFocusRef`, an element carrying `data-dialog-autofocus`, Cancel, first focusable, then the dialog panel.
3. The panel uses generated IDs from `useId()` for title and description and sets `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, and `aria-describedby`.
4. A keydown handler handles Escape by calling `onClose`. Tab and Shift+Tab are intercepted only when focus would leave the first/last focusable element, cycling within the panel. The panel has `tabIndex={-1}` as a fallback.
5. The overlay is not dismissible by click by default. The action group must include an explicit Cancel Button. This is deliberate for publish/archive confirmations.
6. On close or unmount, the effect removes listeners, restores body overflow and the previous shell accessibility state, and calls `.focus()` on the captured trigger only if it is still connected and focusable.
7. The editor owns `dialogAction: "publish" | "archive" | null`, validation, busy state, request ID/idempotency key, and notice/error state. Dialog remains unaware of catalog lifecycle and cannot change the API contract.

This is sufficient for the two bounded destructive confirmations in F2. A future dialog extension must preserve the same focus lifecycle and must not replace it with a native `confirm()` or a dependency without an explicit architecture change.

## 6. Layered implementation, tests, and rollout

Implementation should proceed in dependency order and keep each slice independently buildable:

### Layer 1 — foundations and shell

1. Add/verify the vendored Source Sans 3 WOFF2, local font configuration, `globals.css` tokens/reset/focus/reduced-motion, and the committed `package-lock.json` without changing dependencies.
2. Add root layout shell, skip link, `#app-shell`, institutional footer, base metadata/theme-color, favicon, and route segment metadata layouts.
3. Redesign the single NavBar implementation and compatibility re-export.

**Gate:** `cd apps/web && npm run build`; inspect computed token usage and verify no network font import.

### Layer 2 — low-state primitives

1. Implement `Button`, `StatusLabel`, `Field`, `Feedback`, `Skeleton`, and `EmptyState` with their CSS Modules and keyboard/focus contracts.
2. Implement `Table`, `Pagination`, and `Breadcrumb` with semantic markup and responsive overflow.
3. Implement `Dialog` and manually exercise open, focus-in, Tab cycling, Escape, Cancel, focus return, and busy/error behavior.

**Gate:** build after each component slice; run a focused keyboard pass in a browser at 375px and desktop. Do not add a UI library.

### Layer 3 — pages and route states

1. Redesign home and login first, preserving data/auth functions and removing `alert()`.
2. Redesign catalog list and new-instrument form, preserving filters, guards, payloads, and idempotency.
3. Redesign version editor, add Dialog confirmation and status announcements, and preserve all lifecycle guards.
4. Implement `LikertMatrix` and migrate evaluator preview without adding response/scoring logic.
5. Add route `loading.tsx`/`error.tsx` surfaces and the branded root `not-found.tsx` using the shared primitives.

**Gate:** build after each route. Run the route smoke checklist from the proposal for anonymous, `admin`, `psicologo`, and `evaluado` behavior. Verify API files and contracts remain untouched.

### Layer 4 — accessibility, documentation, and freeze

1. Write `apps/web/docs/design-system.md` from the final token/component contracts, including the matrix pattern and do/don't rules for F3–F6.
2. Compute final color pair contrast: normal text 4.5:1, large text 3:1, focus/non-text indicators 3:1. Verify status/required/active states without color perception.
3. Manual keyboard pass: skip link, navigation, filters, forms, pagination, editor actions, Dialog focus trap, and matrix/table reading order. Repeat with `prefers-reduced-motion: reduce` and 375px viewport.
4. Freeze the changed-line forecast before delivery; keep within 3,500 changed lines and split delivery if the implementation slice forecast exceeds the repository's 400-line review threshold.

### Verification and rollout

- Automated proof available in the repository is `npm run build` (Next build/typecheck); no new UI test framework or dependency is introduced.
- Manual proof is the proposal's route-by-route smoke checklist plus browser keyboard/screen-reader-oriented inspection and contrast computation.
- Rollback is a Git revert of frontend/documentation slices only; no API, database, contract, lifecycle, seed, or audit rollback is needed.
- F3–F6 consume the documented token names and component contracts. They must not create a second token source, import raw colors, add a styling dependency, or reimplement the evaluator matrix.

## 7. Design risks and mitigations

| Risk | Level | Mitigation |
| --- | --- | --- |
| A custom Dialog still misses a browser/screen-reader edge case. | Medium | Keep scope to publish/archive, implement `aria-modal` + `aria-hidden`/`inert` + focus trap/return, and manually test keyboard lifecycle before freeze. |
| Route metadata is unavailable in existing client pages. | Medium | Add server segment layouts for metadata only; do not move API/auth logic or create duplicate data fetches. |
| A matrix with long Spanish labels becomes hard to use on mobile. | Medium | Scroll only the matrix region, preserve the header row, allow wrapping, test at 375px and desktop, and keep item text as the row header. |
| CSS Modules drift from the semantic token contract. | Medium | Centralize all runtime tokens in `globals.css`, document them, and verify route/module styles for raw hex/system fonts before delivery. |
| Status and permission treatments become visually noisy in a dense tool. | Low | Use typography, spacing, bounded labels, and one navy accent as primary hierarchy; reserve semantic colors for actual status/error/warning meaning. |
| `aria-hidden`/`inert` restoration is incorrect after nested or interrupted close. | Medium | Capture previous values, make the Dialog controlled and single-instance in F2, restore in cleanup, and ensure the trigger remains the recorded return target. |
| Implementation exceeds the 3,500-line ceiling or a review slice becomes too large. | Medium | Build foundations first, reuse primitives, exclude decoration before accessibility/state coverage, and apply the delivery forecast at each slice. |
| No UI e2e suite exists to catch a visual regression. | Medium | Keep API/auth untouched, build after every layer, and execute the explicit manual route, keyboard, contrast, responsive, and reduced-motion checklist. |

## 8. Next recommended

`sdd-tasks`

Tasks should turn the four implementation layers into bounded work units, preserve the exact file tree and contracts above, include the build/manual verification gates, and keep the frontend-only/no-new-dependency boundary explicit.

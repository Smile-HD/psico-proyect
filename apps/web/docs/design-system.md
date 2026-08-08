# TestPsico web design system

This document is the F3–F6 inheritance reference for the F2 catalog foundation. It describes the runtime contract; it is **not** a second token source. Runtime tokens live only in `apps/web/app/globals.css`. Consumers MUST reference the custom properties from that file and MUST NOT copy these values into another stylesheet, route, component, or dependency.

The product direction is light-only, editorial, structurally calm, and cold-neutral with one desaturated navy accent. UI copy is Spanish; identifiers, token names, and technical documentation are English. Synthetic data remains marked as research-only.

## 1. Token ownership and usage

- `apps/web/app/globals.css` is the only runtime token source.
- CSS Modules own layout and component composition; they consume `var(--token-name)`.
- Route components MUST NOT contain color literals, `system-ui`, one-off spacing, or one-off radius values.
- F3–F6 MUST reuse the existing components and contracts before introducing a new primitive.
- A new semantic role requires an architecture decision and a change to the canonical global token layer, not a local override.

### Semantic color tokens

The values below are the final contrast-frozen values. They are documentation of the canonical globals, not a replacement definition.

| Token | Final value | Intended use |
| --- | --- | --- |
| `--color-canvas` | `#f7f8fa` | App background and low-emphasis table headers |
| `--color-surface` | `#ffffff` | Panels, controls, tables, and footer |
| `--color-ink-1` | `#1b2430` | Body text, headings, row headers, and primary content |
| `--color-ink-2` | `#465260` | Supporting text, captions, metadata, and helper copy |
| `--color-accent` | `#24435f` | Links, primary actions, active navigation, and focus |
| `--color-accent-strong` | `#1f344a` | Hover and pressed accent state |
| `--color-border` | `#84909d` | Control boundaries, table boundaries, separators, and panel edges |
| `--color-error` | `#b3261e` | Error text, error notices, and destructive actions |
| `--color-success` | `#2d7831` | Success text, success notices, and published status |
| `--color-warning` | `#8a5a00` | Warning text, warning notices, and read-only warnings |
| `--color-focus` | `#24435f` | Keyboard focus indicator |
| `--color-on-accent` | `#ffffff` | Text on accent, strong-accent, and error action surfaces |

The success token is intentionally darker than the initial value so success text also passes when rendered on its 10% success-tinted status surface. The superseded legacy success green is not part of the runtime source or this delivered system.

### Typography tokens

Source Sans 3 is vendored locally and loaded by `next/font/local` in `app/layout.tsx` with `font-display: swap`. The fallback remains tokenized and does not begin with `system-ui`.

| Token | Value | Use |
| --- | --- | --- |
| `--font-family-sans` | Source Sans 3, then `Segoe UI`, `Trebuchet MS`, `sans-serif` | Single product family and fallback |
| `--font-size-caption` | `0.75rem` / 12px | Metadata, captions, eyebrow labels |
| `--font-size-supporting` | `0.875rem` / 14px | Helper, supporting, and table metadata |
| `--font-size-body` | `1rem` / 16px | Body and control text |
| `--font-size-lead` | `1.125rem` / 18px | Introductory text |
| `--font-size-heading-3` | `1.25rem` / 20px | Section heading |
| `--font-size-heading-2` | `1.5rem` / 24px | Page section and dialog heading |
| `--font-size-heading-1` | `clamp(1.75rem, 1.5rem + 1vw, 2rem)` | Page heading |
| `--line-height-body` | `1.6` | Body readability |
| `--line-height-heading` | `1.2` | Heading hierarchy |

Use weight 400 for body, 500 for labels/supporting emphasis, 600 for headings and controls, and 700 only for strong hierarchy. Counts, versions, and dates use `.tabular-nums` or `font-variant-numeric: tabular-nums`.

### Spacing, geometry, motion, and layers

| Group | Canonical values |
| --- | --- |
| Spacing | `--space-1` 0.25rem, `--space-2` 0.5rem, `--space-3` 0.75rem, `--space-4` 1rem, `--space-5` 1.25rem, `--space-6` 1.5rem, `--space-8` 2rem, `--space-10` 2.5rem, `--space-12` 3rem |
| Radius | `--radius-sm` 0.25rem, `--radius-md` 0.5rem, `--radius-lg` 0.75rem |
| Elevation | `--shadow-subtle` is the single restrained tinted shadow; prefer borders and spacing |
| Motion | `--motion-fast` 150ms, `--motion-standard` 220ms, `--motion-slow` 300ms |
| Easing | `--ease-standard` `cubic-bezier(0.2, 0.8, 0.2, 1)` |
| Layers | `--z-base` 0, `--z-header` 10, `--z-overlay` 100, `--z-dialog` 110 |

Use mobile-first composition, a maximum content width near 75rem, and an intentional inner overflow region for wide tables. The page itself MUST NOT become the horizontal scroll container.

## 2. Component contracts and ARIA behavior

All shared components are presentational. They do not call the API, read domain DTOs, own permissions, or change lifecycle behavior. `className` is a layout escape hatch only; visual primitives remain in the component CSS Module.

| Component | Required contract |
| --- | --- |
| `Button` | Native `<button>`; variants `primary`, `secondary`, `ghost`, `danger`; default target ≥44px and compact target ≥36px; `busy` sets `disabled` and `aria-busy="true"` while retaining a caller-provided readable pending label; forwards native, `aria-*`, and `data-*` attributes; focus comes from `:focus-visible`. |
| `StatusLabel` | Static `<span>` with required visible status text and optional decorative `symbol` (`aria-hidden`); no `role="status"`; status meaning MUST survive loss of color. |
| `Field` | Visible `<label htmlFor>`; native input/textarea/select/checkbox; deterministic `${id}-help` and `${id}-error` IDs joined in `aria-describedby`; `aria-invalid` on error; visible `Obligatorio`; `forwardRef` handle exposes `focus()`; login uses `username` and `current-password`. |
| `ErrorState` | Spanish recovery copy in `role="alert"`, with a visible retry/back action where available; never prints raw exceptions or envelopes. |
| `Notice` | `role="status"` plus `aria-live="polite"` for non-blocking feedback; error notices use `role="alert"`; message remains visible until replaced or dismissed by the owner. |
| `Skeleton` | Layout-matched placeholder with `role="status"`, `aria-live="polite"`, and visually hidden `Cargando…`; pulse is removed under reduced motion. |
| `EmptyState` | Semantic `<section>` with a labelled heading, explanation, and permission-aware action; preserves surrounding page context and never fakes a disabled action. |
| `Table` | Region owns horizontal overflow; semantic `<table>` with caption, `scope="col"`, optional first-column `scope="row"`, numeric/tabular styling, and no `role="grid"`. |
| `Pagination` | `<nav aria-label>`; native disabled previous/next controls; page buttons only for multiple pages; current page uses `aria-current="page"` and visible `Página X de Y`; changes are clamped. |
| `Breadcrumb` | `<nav aria-label="Ruta de navegación"><ol>`; links for previous locations; final item is text with `aria-current="page"`, never a link. |
| `Dialog` | Controlled, portal-mounted client component with `role="dialog"`, `aria-modal="true"`, generated labelled title/description, focus-in, Escape and explicit Cancel, Tab trap, body scroll lock, shell `aria-hidden`/`inert`, and focus return to the trigger. Overlay clicks do not dismiss it. The page owns the API action. |
| `NavBar` | One responsive implementation inside a labelled `<nav>`; role-derived links; `aria-current="page"` for the active route; labelled expanded/collapsed toggle; all links and auth controls remain keyboard reachable. |
| `LikertMatrix` | Semantic item-by-option table; exact option labels/order; item row headers and option column headers; every cell has `headers`; required rows include visible `(obligatorio)`; F2 uses `interactive={false}` and contains no scoring or answer-key logic. |

## 3. Evaluator matrix pattern

F3 may consume the presentation pattern without changing the API contract:

1. Map each item to one table row with its item text as `th[scope="row"]`.
2. Derive the option columns from the payload order and preserve the exact Spanish labels.
3. Give each column heading a stable ID and set every cell's `headers` to the row-heading ID plus option-heading ID.
4. Add visible `(obligatorio)` to required item text; never use a color-only or asterisk-only marker.
5. Keep the matrix inside its own `overflow-x: auto` region at 375px; do not enable document-wide horizontal scrolling.
6. In F2 preview, render presentation marks only. F3 may opt into controlled radios later, with an accessible label per item and no scoring interpretation in the component.

Do not reimplement this matrix in a route or introduce numeric values, answer keys, scoring, recommendations, or clinical interpretation.

## 4. Accessibility rules

- Meet WCAG 2.2 AA: normal text ≥4.5:1, large text ≥3:1, and meaningful non-text indicators (focus, boundaries, status markers) ≥3:1.
- Keep status, health, active filters, required items, errors, and permissions identifiable by text or a non-color symbol/shape.
- Preserve the first-focusable skip link to `main#main-content`; keep one logical tab order and visible `:focus-visible` treatment.
- Use native controls and keyboard-operable links/buttons. Primary controls and navigation target 44px; every interactive target is at least 24×24px where the 44px convention is not practical.
- Use labelled landmarks (`header`, labelled `nav`, `main`, `footer`) and one `h1` per rendered page with sequential headings.
- Keep labels visible, helper text persistent, and field errors connected through `aria-describedby` and `aria-invalid`.
- Announce blocking errors with `role="alert"`; announce non-blocking state changes with a persistent polite status.
- Dialogs must move focus in, contain focus, expose an Escape/Cancel route, and return focus to the trigger.
- Under `prefers-reduced-motion: reduce`, transitions become near-instant, skeleton animation stops, and scrolling is not smoothed. Motion never delays input.
- Check both 375px and desktop widths. Tables and matrices scroll inside their regions; content and focus are not hidden behind chrome.
- Native `window.alert()` and `window.confirm()` are prohibited. Use `ErrorState`, `Notice`, or the owned `Dialog` contract.

### Owner manual checklist (V.2 / V.3)

These checks require a rendered browser and remain owner-owned; they are intentionally not task checkboxes for this apply slice.

- **Shared shell:** at `/`, `/login`, `/catalogo`, `/catalogo/nuevo`, editor, and evaluator view, press Tab from the address bar; verify skip link → main, labelled navigation, active route, logout/login action, focus visibility, and footer. Confirm anonymous, `admin`, `psicologo`, and `evaluado` see only permitted links.
- **Home:** verify health success, seed counts, loading, and retryable error; confirm Spanish research-only context and no role redirect.
- **Login:** verify visible labels, autofill purpose, busy label, alert announcement, password-field focus recovery, successful navigation without a native dialog, and the home link.
- **Catalog:** verify role guard, `aria-pressed` filter state, table caption/scopes, inner overflow at 375px, skeleton, empty/create permission, retry, status text, and pagination boundaries/labels.
- **New instrument:** submit empty/invalid fields; verify persistent helpers, linked errors, first-invalid focus, denied state without a form, unchanged cancel/create behavior, and no native alert.
- **Editor:** verify loading, breadcrumb, fieldsets, seed/published read-only explanation, save busy/status announcement, publish/archive dialog focus-in, Tab/Shift+Tab trap, Escape/Cancel, focus return, and unchanged lifecycle behavior.
- **Evaluator:** verify published-only behavior, exact matrix headings/order, item/option reading order, required text, cell associations, matrix-only overflow at 375px, not-found/retry/back treatment, and absence of numeric scoring data.
- **Reduced motion:** enable the OS/browser preference and repeat filters, forms, pagination, Dialog, skeleton, and navigation; verify no delayed input or skeleton pulse.
- **Contrast:** sample rendered text, controls, focus, status labels, success notice, borders, and matrix markers in both 375px and desktop layouts. Every sampled normal-text pair must be ≥4.5:1, large text ≥3:1, and meaningful non-text indicators ≥3:1.

## 5. Contrast freeze

Ratios below use WCAG relative luminance and the final token values. They cover the foreground/background combinations used by the affected routes and shared components. Normal text uses the 4.5 threshold; large text uses 3.0; control boundaries, focus, and status markers use 3.0.

### Text and action surfaces

| Foreground | Background | Ratio | Required | Result |
| --- | --- | ---: | ---: | --- |
| `--color-ink-1` | canvas | 14.73:1 | 4.5:1 | PASS |
| `--color-ink-1` | surface | 15.65:1 | 4.5:1 | PASS |
| `--color-ink-2` | canvas | 7.50:1 | 4.5:1 | PASS |
| `--color-ink-2` | surface | 7.97:1 | 4.5:1 | PASS |
| `--color-accent` | canvas | 9.67:1 | 4.5:1 | PASS |
| `--color-accent` | surface | 10.28:1 | 4.5:1 | PASS |
| `--color-accent-strong` | canvas | 11.99:1 | 4.5:1 | PASS |
| `--color-accent-strong` | surface | 12.74:1 | 4.5:1 | PASS |
| `--color-error` | canvas | 6.15:1 | 4.5:1 | PASS |
| `--color-error` | surface | 6.54:1 | 4.5:1 | PASS |
| `--color-success` | canvas | 5.14:1 | 4.5:1 | PASS |
| `--color-success` | surface | 5.47:1 | 4.5:1 | PASS |
| `--color-warning` | canvas | 5.58:1 | 4.5:1 | PASS |
| `--color-warning` | surface | 5.93:1 | 4.5:1 | PASS |
| `--color-on-accent` | accent action | 10.28:1 | 4.5:1 | PASS |
| `--color-on-accent` | strong-accent action | 12.74:1 | 4.5:1 | PASS |
| `--color-on-accent` | error action | 6.54:1 | 4.5:1 | PASS |

### Boundaries, focus, and status tints

| Foreground / marker | Background | Ratio | Required | Result |
| --- | --- | ---: | ---: | --- |
| `--color-border` | canvas | 3.06:1 | 3:1 | PASS |
| `--color-border` | surface | 3.25:1 | 3:1 | PASS |
| `--color-focus` | canvas | 9.67:1 | 3:1 | PASS |
| `--color-focus` | surface | 10.28:1 | 3:1 | PASS |
| warning text/marker | 10% warning + surface | 5.15:1 | 4.5:1 | PASS |
| success text/marker | 10% success + surface | 4.77:1 | 4.5:1 | PASS |
| archived text/marker | 10% ink-2 + surface | 6.84:1 | 4.5:1 | PASS |
| reference text/marker | 10% accent + surface | 8.68:1 | 4.5:1 | PASS |
| error text/marker | 10% error + surface | 5.55:1 | 4.5:1 | PASS |
| neutral text/marker | 10% ink-1 + surface | 12.89:1 | 4.5:1 | PASS |
| warning read-only boundary | surface | 5.93:1 | 3:1 | PASS |
| notice/status marker | surface | 4.83–6.54:1 | 3:1 | PASS |

The border token was darkened from the initial low-emphasis separator value because it is also used for form/control boundaries. The success token was darkened because the initial success value fell just below 4.5:1 on its 10% status tint. Both changes preserve the navy/cold-neutral direction and no other token role changed.

## 6. Do / don’t and delivery freeze

| Do | Don’t |
| --- | --- |
| Consume `var(--color-ink-1)`, spacing, radius, motion, and layer tokens. | Do not add a second token file or redefine tokens in a route. |
| Use Source Sans 3 through the existing local-font integration. | Do not add `system-ui`, a remote font, or a display/decorative family. |
| Compose `Button`, `Field`, `Table`, `Dialog`, `Notice`, `StatusLabel`, and `LikertMatrix`. | Do not reimplement the matrix or bypass component ARIA contracts. |
| Keep text, status labels, symbols, and recovery paths explicit. | Do not communicate state by color alone. |
| Keep wide data inside an intentional overflow region. | Do not make the document horizontally scroll. |
| Use CSS Modules and existing dependencies only. | Do not add a styling dependency, raw hex in route code, or one-off values. |
| Use the owned Dialog for publish/archive. | Do not use `window.alert()` or `window.confirm()`. |

Before delivery, the owner must confirm the final diff is limited to `apps/web` and documentation, `apps/web/package.json` is unchanged, no dependency was added, the protected API/auth/service paths are untouched, and the combined additions plus deletions remain under the approved 3,500-line ceiling. Decorative changes are removed before accessibility/state coverage when the ceiling is at risk.

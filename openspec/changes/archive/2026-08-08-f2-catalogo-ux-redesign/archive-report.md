# F2 Catalog UX Redesign — Archive Report

**Change**: `f2-catalogo-ux-redesign`
**Fecha**: 2026-08-08
**Estado final**: ARCHIVED

## Resumen

Rediseño completo del frontend del catálogo de TestPsico con un design system propio, cero dependencias nuevas y API intacta. Implementado en 4 PRs encadenados (stacked-to-main) con excepción de presupuesto aprobada por el owner.

## Entregables

- **Design tokens** (CSS custom properties en `globals.css`): paleta navy/cold-neutral, escala tipográfica Source Sans 3 vendida (WOFF2 local), ritmo 4/8, radii acotados, motion, focus-visible, reduced-motion.
- **11 componentes UI** (`components/ui/`): Button, StatusLabel, Field, Feedback (ErrorState/Notice), Skeleton, EmptyState, Table, Pagination, Breadcrumb, Dialog (focus trap, cero dependencias), LikertMatrix — con contratos ARIA documentados.
- **6 rutas rediseñadas**: home, login (autocomplete, sin alert()), catálogo (filtros aria-pressed, tabla con caption, paginación), nuevo (validación por campo), editor (Dialog para publicar/archivar, breadcrumb), vista evaluado (matriz Likert).
- **Surfaces por ruta**: loading (skeleton layout-matched), error (ErrorState con retry), not-found (404 branded español).
- **`docs/design-system.md`**: referencia de herencia para F3–F6 (tokens, tipografía, contratos, reglas do/don't, patrón matriz).

## Estado de tasks

- 30/30 tareas de la change: 28 implementation + V.2/V.3 aprobadas por el owner; 2 parent gates P documentadas como follow-up (bounded review de los 4 PRs; verify/archive ejecutados por el orquestador con esta resolución).
- Verify: **PASS for archive** (build green, smoke por ruta, scope check, contraste AA 10/10, anti-checklist IA limpio).

## Decisiones registradas

- Preflight: auto + híbrido + auto-forecast; presupuesto 3.500 con excepción aprobada; 4 PRs stacked-to-main.
- Edit authority: grant per-change otorgado por el owner (auditado, muere con este archive).
- Maintainer reset del objective del slice 3 (excedente de +272 líneas del attempt, dentro del presupuesto aprobado).
- Hallazgo de plataforma: mismatch de case en rutas Windows del CLI gentle-ai (usar `D:\Personal\...` canónico) — documentado en Engram.

## Follow-ups (no bloqueantes)

- Checklist manual V.2/V.3 (teclado, lector de pantalla, móvil real, roles) documentado en apply-progress para el owner.
- `login/error.tsx` y surfaces de error comparten módulo CSS de la raíz vía imports relativos profundos; F3 puede consolidar.

# Exploración — F2 Catálogo UX Redesign

**Change**: `f2-catalogo-ux-redesign`
**Fecha**: 2026-08-09
**Objetivo**: Rediseñar el frontend del catálogo (layout + login + home + páginas de catálogo) con calidad de diseño profesional de plataformas de evaluación psicométrica: serio, sobrio, claro, accesible (WCAG 2.2 AA), con jerarquía tipográfica real, estados cuidados y micro-interacciones discretas. Que NO parezca generado por IA.

> **Nota de fuentes**: esta sesión no dispone de herramienta webfetch; las referencias de dominio (sección 2) se citan desde conocimiento documentado con URLs canónicas. El proposal debe reverificarlas con fetch vivo si se requiere precisión de captura.
> **Nota de docs**: el brief citaba `docs/05-stack-tecnologico-y-arquitectura.md` y `docs/06-reparto-de-implementacion-por-fases.md`; **no existen** (no hay directorio `docs/` en el repo). Las restricciones equivalentes viven en `README.md`, `AGENTS.md`, `openspec/config.yaml` y `packages/contracts/README.md`. El objetivo "WCAG 2.2 AA" no está documentado en el repo: es declaración del product owner y conviene fijarla por escrito en el proposal.

---

## 1. Inventario actual de la UI

### 1.1 Estado general

- **Stack**: Next.js 14.2 App Router, React 18, TypeScript strict. **Sin ninguna librería de estilos**: `package.json` solo tiene `next/react/react-dom`; `globals.css` tiene 8 líneas. Todo el estilo es **inline** (`style={{...}}`) con `fontFamily: "system-ui, sans-serif"` repetido en cada página.
- **Rutas reales (6)**: `/` (home/estado), `/login`, `/catalogo`, `/catalogo/nuevo`, `/catalogo/[instrumentId]/versiones/[versionId]` (editor/detalle), `.../vista` (vista del evaluado). El brief habla de "5 páginas de catálogo"; son **4 páginas de catálogo** + login + home. No existen `loading.tsx`, `error.tsx`, `not-found.tsx`, ni favicon propio.
- **Gates de calidad web**: solo `next build` (typecheck). No hay tests de UI (pytest cubre solo la API; e2e no disponible). Sin `package-lock.json` commiteado (el Dockerfile usa `npm install`).
- `lib/api.ts` y `lib/auth.ts`: clientes limpios y correctos (envelope de errores, idempotency, sesión en localStorage con hook hidration-safe). **No tienen problemas de diseño; no se tocan** salvo necesidad puntual.
- Idiomas: textos UI en español ✓ (convención del repo), identificadores en inglés ✓.

### 1.2 Problemas por página

| Página | Qué hay | Problemas de diseño concretos |
| --- | --- | --- |
| `app/layout.tsx` | Root layout con NavBar + children, `lang="es"`, metadata global | Sin skip-link; metadata "Estado del servicio" es global y queda vieja para /login y /catalogo (esas páginas no exportan metadata propia); sin fuente configurada (system-ui → look dependiente del SO); sin `theme-color` ni configuración de viewport explícita; NavBar sin estado activo. |
| `app/globals.css` | 8 líneas: reset margin/padding, fondo `#fafafa`, tinta `#1a1a1a` | Sin tokens, sin tipografía base, sin `:focus-visible`, sin `prefers-reduced-motion`, sin estilos de scroll/selection. Todo lo demás es inline. |
| `/` (home, RSC) | Salud de API + estado de semilla, fetch server-side | Inline styles; colores de estado sin verificar contraste (**`#1e8e3e` "OK" ≈ 4.0:1 sobre #fafafa: FALLA AA 4.5:1** para texto normal); sin loading skeleton (RSC bloquea el render; un `loading.tsx` resolvería); error sin acción de reintento; sin footer legal/aviso institucional; "Estado del servicio" como h1 de entrada del producto (debería ser la puerta de entrada o redirigir según rol). |
| `/login` | Form username/password, error inline, busy state | **`alert()` tras login exitoso** (anti-patrón: bloquea, feo, no accesible); sin `autocomplete="username"/"current-password"` (WCAG 1.3.5); error sin `role="alert"` ni aria-live; sin focus management al campo inválido; sin helper text; sin link de retorno a home; sin password toggle (opcional); estilos inline. |
| `/catalogo` (lista) | Tabla de instrumentos, filtros (Todos/Borradores/Publicados/Archivados), paginación Anterior/Siguiente, tag "referencia" | Filtros como `<button>` sin `aria-pressed` (solo fontWeight bold para activo); tabla sin `<caption>` ni `scope` en `<th>`; **loading textual "Cargando…"** (salta el layout al llegar datos; sin skeleton); **sin empty state compuesto** (tabla con 0 filas); error en texto rojo sin retry; paginación sin aria-labels ni números de página; tag "referencia" con `title` solo (no accesible táctil), color `#8a5a00` (contraste ok); **sin overflow-x**: la tabla se rompe en móvil; username duplicado (NavBar + header de página); botones sin estados hover/active/focus. |
| `/catalogo/nuevo` | Form clave/título/descripción, validación de patrón de clave | Validación de patrón solo post-submit como **error global** (debería ser helper text persistente + error por campo con `aria-describedby`); sin focus al primer campo inválido; early return de permisos como `<p>` suelto con estilo inline (inconsistente con el resto); botones planos; estilos inline. |
| Editor de versión (`[versionId]/page.tsx`) | Editor de escalas/ítems/opciones (fieldsets anidados, semántica correcta), Guardar/Publicar/Archivar, vista read-only | **`window.confirm` nativo** para publicar/archivar (inconsistente, no estilizable; reemplazar por Dialog accesible); avisos ("Borrador guardado…") como texto coloreado **sin `role="status"`** → no los anuncia el lector de pantalla; readOnly comunica con `disabled` + texto plano (el porqué no es accesible; usar `aria-describedby`); "Quitar escala/ítem" destructivo sin confirm (estado local, aceptable, pero sin affordance de peligro); sin breadcrumb (3 niveles de profundidad: catálogo → instrumento → versión); números de versión sin `tabular-nums`; sin skeleton en carga; botones cambian label ("Guardando…") sin spinner ni `aria-busy`. |
| Vista del evaluado (`vista/page.tsx`) | Preview read-only de versión publicada: header con metadata, escalas, ítems con opciones | Ítems como `<p>` + `<ul>` con bullets: para un Likert 1–5 el patrón de dominio es **matriz ítem × opciones con encabezados de columna** (o al menos fila de opciones alineada); tarjetas "borde 1px #eee" planas; sin skeleton; ítem requerido marcado solo con `*` rojo (agregar texto/aria); sin breadcrumb; disclaimers ok. |
| `components/NavBar.tsx` | Links (Estado del servicio, Catálogo si admin/psicólogo), username o "Iniciar sesión" | Sin marca/wordmark del producto; **sin estado activo** (`aria-current`); sin comportamiento móvil (los links se aprietan); sin logout aquí (solo en /catalogo); etiqueta "Estado del servicio" como link de home en todas las páginas; sin skip-link (va en layout). |

### 1.3 Problemas transversales (a nivel sistema)

1. **Sin design tokens**: cada color/radio/spacing existe inline y duplicado (p. ej. `#b3261e` en 5 archivos).
2. **Sin tipografía del producto**: `system-ui` en todo; sin escala tipográfica; sin cifras tabulares para versiones/fechas/IDs.
3. **Sin estados**: loading textual, error textual sin retry, empty states ausentes.
4. **Sin micro-interacciones**: cero transiciones, cero hover/pressed/focus personalizados.
5. **Accesibilidad incompleta**: sin skip-link, sin focus visible estilizado, `alert()`/`confirm()` nativos, errores sin aria-live, tabla sin caption/scope, filtros sin estado aria, formularios sin autocomplete.
6. **Contraste**: `#1e8e3e` falla AA (≈4.0:1); `#666` sobre `#fafafa` (≈5.5:1) y `#8a5a00` (≈5.9:1) pasan; `#b3261e` pasa (≈6.3:1).
7. **Metadatos/SEO**: sin título por página, sin `not-found.tsx` (404 genérico de Next).
8. **Herencia F3–F6**: no hay sistema que heredar; cada fase nueva probablemente repetiría inline styles. Este change debe entregar el design system como producto.

---

## 2. Patrones de diseño del dominio investigados

Referencias (conocimiento documentado; verificar en proposal):

1. **Pearson Clinical / Pearson Assessments** — `pearsonassessments.com`, `pearsonclinical.com`
   Catálogo profesional de tests psicométricos (BASC-3, WISC, etc.). Patrones: paleta conservadora (azul marino + grises fríos, un único acento), **fichas de instrumento con metadata tipificada** (rango etario, tiempo de administración, formato, edición), navegación por disciplina, densidad media, cero decoración. Lección: el catálogo de tests se presenta como **ficha técnica seria**, no como cards de marketing.
2. **Hogan Assessments** — `hoganassessments.com`
   Assessment corporativo (HPI, HDS, MVPI). Patrones: tipografía sobria de una familia, jerarquía por peso y tamaño (no por color), paleta desaturada, informes densos y legibles, estados de avance discretos. Lección: sobriedad editorial; el peso tipográfico construye la jerarquía.
3. **O*NET Interest Profiler (U.S. Dept. of Labor)** — `onetonline.org`
   Orientación vocacional gubernamental. Patrones: **cuestionario Likert como matriz de filas (ítem) × columnas (opciones con encabezados: "Muy en desacuerdo … Muy de acuerdo")**, densidad alta con claridad, cumplimiento de accesibilidad federal (WCAG 2.x AA / Section 508). Lección: el estándar del dominio para presentar ítems con escala es la **matriz con encabezados de columna**, no una lista con bullets.
4. **MHS (Multi-Health Systems)** — `mhs.com`
   Editor de instrumentos clínicos (BASC-3, MSCEIT). Patrones: azul/teal desaturado, formularios densos con labels persistentes (nunca placeholder-only), **badges de estado discretos** (borrador/publicado), confirmaciones en diálogos propios. Lección: la edición de instrumentos es una herramienta clínica seria: labels visibles, estados tipificados, confirmación explícita para acciones irreversibles (publicar).

Fuente normativa: **WCAG 2.2** (`w3.org/TR/WCAG22`) — criterios directamente aplicables: 1.4.3 contraste 4.5:1, 1.4.11 non-text contrast 3:1, 2.4.7 focus visible, 2.4.11 focus not obscured, **2.5.8 target size mínimo 24×24 CSS px** (nuevo en 2.2), 1.3.5 identify input purpose, 4.1.2 name/role/value, 2.5.7 dragging movements (evitar drag en el editor). Diálogos según WAI-ARIA Authoring Practices (`w3.org/WAI/ARIA/apg/patterns/dialog-modal/`).

### Síntesis de patrones del dominio

- **Paleta**: neutros fríos + **un único acento desaturado profundo** (navy/teal). Nada de degradados ni púrpura.
- **Tipografía**: una familia sans profesional con 3–4 pesos; display solo para H1; cifras tabulares en datos.
- **Densidad**: media-alta en tablas y formularios (herramienta de trabajo); respiro en login/home.
- **Cuestionario**: matriz ítem × opciones con encabezados; requerido marcado con texto + símbolo.
- **Estados**: badges con color + texto (nunca color solo); skeleton en carga; empty state con guía y acción.
- **Metadata de instrumento** (clave, versión, fecha, tipo de respuesta) siempre visible en header/ficha.
- **Micro-interacciones**: 150–300 ms, transform/opacity, focus rings, `prefers-reduced-motion`.

---

## 3. Enfoque recomendado con tradeoffs

### 3.1 Opciones técnicas

| Enfoque | Pros | Contras |
| --- | --- | --- |
| **(a) Design tokens (CSS custom properties) + CSS Modules + componentes propios** | Cero dependencias nuevas (Dockerfile intacto, sin riesgo de compat); control estético total (clave para el requisito "no parece IA": sin defaults de framework que pelear); soporte nativo Next 14; aislamiento por CSS Modules (6 fases no colisionan); tokens en `globals.css` = contrato compartido que F3–F6 heredan | Más CSS manual por componente; la consistencia depende de usar los tokens (mitigable con revisión en verify); sin utilidades de velocidad |
| **(b) Tailwind CSS (v3.4 para Next 14)** | Velocidad de iteración; consistencia forzada por utilidades; ecosistema enorme | Dependencia + config PostCSS; **v4 tiene riesgo de compat con Next 14** (v3.4 es la versión segura); su look por defecto (rounded-lg, shadow-md, slate) es literalmente el "look IA" que el usuario prohíbe → exige theme fuerte; clases en JSX inflan el markup; sin lockfile hoy, la imagen Docker pierde determinismo si se agrega sin `npm ci` |
| **(c) CSS variables globales + clases sueltas** | Simplicidad máxima | Cascada global: con 6 personas en fases distintas es la receta de colisiones; no escala; sin aislamiento de nombres |
| **(d) shadcn/ui o Radix primitives** | Primitivas accesibles listas (Dialog, Select: focus, keyboard, ARIA) | shadcn **requiere Tailwind** (arrastra (b)); Radix suma dependencias; el look por defecto hay que re-themearlo entero igual; la superficie real del proyecto (tabla, 2 forms, editor, preview) es chica: las 2 primitivas que importan (Dialog accesible, Badge/estados) se construyen en ~100 líneas propias sobre tokens |

### 3.2 Recomendación

**(a): tokens + CSS Modules + capa de componentes propia**, con los siguientes pilares:

1. **Design tokens** en `app/globals.css` (CSS custom properties): color (fondo/superficie/tinta/semánticos), tipografía (escala fluida), spacing (escala 4/8px), radius, sombras (1 nivel de elevación, sutil), motion (duraciones/easings), z-index (escala declarada). Cada token con nombre semántico (`--color-ink-1`, `--color-accent`, `--space-4`…). Documentarlos en un archivo de referencia (p. ej. `apps/web/docs/design-tokens.md` o sección en README de apps/web) para que F3–F6 los consuman.
2. **Tipografía**: **Source Sans 3** (variable, cobertura latina completa para español, humanista profesional; alternativa: Public Sans de USWDS o IBM Plex Sans). **Vender los WOFF2 en el repo** y cargar con `next/font/local` (o `@font-face` + `font-display: swap`): `next/font/google` descarga en build y rompería builds Docker sin red. Una sola familia con pesos 400/500/600/700; H1 28–32px, cuerpo 16px, captions 12px+; `font-variant-numeric: tabular-nums` para versiones/fechas/conteos. Escala con `text-wrap: balance` en headings.
3. **Paleta (propuesta inicial, a verificar contraste en design)**: fondo `#F7F8FA` (gris frío papel), superficies blancas, tinta `#1B2430`, secundaria ≥4.5:1, **un acento navy/teal desaturado** (ej. `#24435F` o `#1F4E5F`; verificar 4.5:1 en superficies claras), semánticos: error `#B3261E` (ya en uso, ok), success **`#2E7D32`** (reemplaza al `#1e8e3e` que falla AA), warning `#8A5A00` (ok). Sin degradados, sin sombras exageradas: elevación con hairlines + una sombra difusa mínima y tintada.
4. **Componentes** (`apps/web/components/ui/`): Button (primary/secondary/ghost/danger + estados hover/active/focus/disabled), Input/Textarea/Select/Checkbox (label visible + helper + error con `aria-describedby`), Badge (estados del instrumento), Table (caption + scope + overflow-x), **Dialog accesible** (reemplaza `window.confirm`), Alert/Notice (`role="status"`/`role="alert"`), Skeleton, EmptyState, PageHeader (título + metadata + acciones), Breadcrumb, StatusBadge, NavBar rediseñada (marca + `aria-current` + menú móvil). ~12 componentes.
5. **Estados por página**: skeleton por ruta (`loading.tsx` o skeletons locales), `error.tsx` con reintento, `not-found.tsx` en español, empty states con acción (catálogo vacío → "Crear primer instrumento"), notificaciones con aria-live.
6. **Micro-interacciones**: 150–300 ms, solo transform/opacity, `active: scale(0.98)` en botones, focus ring visible 2px (≥3:1), touch targets ≥44px (supera el mínimo 2.5.8 de 24px), `prefers-reduced-motion`.
7. **Accesibilidad base**: skip-link en layout, `aria-current="page"` en nav, autocomplete en login, focus management en forms, `lang="es"` ya presente.
8. **Hygiene**: commitear `package-lock.json` (hoy no existe); metadata por página; favicon propio.

**Por qué no Tailwind como default**: el requisito central es un look profesional *no genérico*; (a) da control absoluto sin pelear defaults, sin dependencias nuevas y sin riesgo de compat. Si el equipo priorizara velocidad por encima de todo, la alternativa seria sería (b) v3.4 **con los mismos tokens y el mismo catálogo de componentes** (el token layer es el activo real de herencia para F3–F6, no el mecanismo).

---

## 4. Alcance propuesto

### 4.1 Se toca (frontend únicamente)

- `apps/web/app/globals.css` — reescritura: tokens + reset + base (fuente, focus-visible, reduced-motion, tabular-nums).
- `apps/web/app/layout.tsx` — skip-link, fuente local, metadata base, footer institucional.
- `apps/web/components/NavBar.tsx` — marca, aria-current, logout, menú móvil.
- `apps/web/app/page.tsx` — home rediseñada (estado del servicio como página de entrada con jerarquía real y estados).
- `apps/web/app/login/page.tsx` — rediseño: quitar `alert()`, autocomplete, aria-live, focus, error por campo.
- `apps/web/app/catalogo/page.tsx` — tabla accesible, filtros con estado aria, skeleton, empty state, error con retry, paginación con labels, badges, responsive.
- `apps/web/app/catalogo/nuevo/page.tsx` — formulario con helper/error por campo, focus management.
- `apps/web/app/catalogo/[instrumentId]/versiones/[versionId]/page.tsx` — header/breadcrumb, badges, Dialog accesible para publicar/archivar, notices con role=status, skeleton, botones con jerarquía visual.
- `apps/web/app/catalogo/[instrumentId]/versiones/[versionId]/vista/page.tsx` — patrón matriz/fila de opciones estilo O*NET, estados, metadata en header.
- Nuevos: `not-found.tsx`, `error.tsx`, `loading.tsx` (según ruta), `components/ui/*` (~12 componentes), assets de fuente WOFF2, `package-lock.json`, documentación de tokens/componentes para F3–F6.
- Metadata por página y favicon.

### 4.2 NO se toca (límites duros)

- **API, base de datos, semilla**: cero cambios. Los DTOs actuales (`/api/v1/catalog/admin/*`, `published-versions`) ya entregan todo lo que la UI muestra; el rediseño es 100% presentación.
- `lib/api.ts` y `lib/auth.ts`: contrato y sesión funcionan; no se rediseñan (solo se consumen).
- `packages/contracts/`, `openspec/specs/` ratificadas (catalog-model, catalog-lifecycle, catalog-api): sin cambios.
- **Lógica de permisos y roles** (evaluado sin nav admin, deny-by-default): se preserva exactamente.
- **No introducir** scoring, reglas de recomendación ni claves de respuesta en el cliente (invariante del dominio).
- **No cambiar el modelo de edición** (sin drag&drop, sin reordenamiento nuevo): solo estilo, accesibilidad y confirmaciones.
- Textos funcionales existentes se mantienen (salvo copy nuevo para estados).
- No se toca el backend de F3–F6 ni sus rutas (pero el design system queda listo para que F3 lo herede: componente de ítem/opción expuesto, tokens documentados).

---

## 5. Riesgos

| # | Riesgo | Severidad | Mitigación |
| --- | --- | --- | --- |
| R1 | 6 fases tocando UI sin sistema → inconsistencia heredada | MEDIA | Este change entrega tokens + componentes + documentación como entregable explícito antes de F3; verify valida uso de tokens, no hex inline |
| R2 | "No parece IA" es subjetivo | MEDIA | Fijar anti-checklist concreto en el proposal (sin degradados púrpura, sin sombras exageradas, sin emojis, sin radius 999px, sin fuentes display, sin espacios gigantes) y revisión por pares con esa checklist en verify |
| R3 | Fuentes: `next/font/google` rompería build sin red | BAJA | Fuentes vendidas (WOFF2) + `next/font/local`; `font-display: swap` |
| R4 | Regresión funcional sin tests de UI | MEDIA | Gates: `next build` + checklist manual por ruta (login, permisos, CRUD, publicar/archivar, vista); documentar smoke manual en apply |
| R5 | Si se agregan deps sin lockfile → imagen no determinista | BAJA | Solo aplica si se elige Tailwind; de todos modos commitear `package-lock.json` |
| R6 | WCAG 2.2 AA no está documentado en el repo (docs/05 y 06 inexistentes) | INFO | El proposal debe escribir el objetivo de accesibilidad para que F3–F6 lo hereden |
| R7 | Vista del evaluado cambia de patrón (lista → matriz) y F3 podría reusarlo | INFO | Exponer el patrón ítem/opción como componente del design system, reutilizable por la sesión F3 |

---

## 6. next_recommended

`sdd-propose` con estos insumos ya decididos por la exploración:

1. **Alcance**: 6 rutas + convenciones (tokens, componentes ui, loading/error/not-found, fuentes, lockfile, docs de design system).
2. **Decisión técnica a ratificar**: tokens + CSS Modules + componentes propios (opción a); Tailwind v3.4 como alternativa si el equipo vota velocidad.
3. **Dirección de diseño**: paleta fría desaturada con un acento navy/teal (sin púrpura/degradados), Source Sans 3 vendida, densidad de herramienta, matriz Likert estilo O*NET en la vista, estados skeleton/error/vacío completos, micro-interacciones 150–300 ms con reduced-motion.
4. **Objetivo WCAG 2.2 AA por escrito** + corrección del verde `#1e8e3e` que hoy falla contraste.
5. **Herencia F3–F6**: el design system (tokens + componentes + docs) es entregable del change, no un medio.

Preguntas para el product owner en la fase de proposal: ¿home redirige por rol (evaluado → login; admin/psicólogo → catálogo) o se mantiene como página de estado? ¿Light mode only o dark mode desde el inicio? ¿Se define wordmark/marca mínima de TestPsico? ¿Presupuesto de líneas/PRs estimado (~1.000–1.500 líneas de CSS/TSX nuevos + docs)?

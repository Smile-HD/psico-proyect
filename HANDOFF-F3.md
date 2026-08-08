# HANDOFF-F3 — Sesión de evaluación (owner: Jhamil)

Documento de traspaso para quien continúe TestPsico con la **Fase 3 — Sesión de
evaluación**. Escrito al cierre de F2 (catálogo de instrumentos, owner Trevor) y
del rediseño UX del catálogo, con el repo en `master @ 03b6f62` y working tree
limpio.

> **Cómo usar este documento**: leelo completo una vez (10 min) y guardalo como
> referencia. Antes de tocar código, seguí el quick path de `AGENTS.md`: la
> memoria canónica del proyecto es OpenSpec, no este archivo. Este handoff es el
> puente entre esa memoria y vos.

---

## 1. Quick path (orden obligatorio de lectura antes de editar)

1. `openspec/config.yaml` — invariantes de dominio, fases/owners, testing (2 min).
2. `openspec/specs/catalog-api/spec.md` — spec ratificada del catálogo, incluido el
   contrato de handoff F3 (requisito "F3 Session Handoff Contract").
3. `packages/contracts/README.md` — convenciones vinculantes de todas las fases
   (§7.2 superficie de endpoints, §7.5 contrato F3, §3 eventos de auditoría).
4. `openspec/changes/archive/2026-08-08-f2-catalogo-instrumentos/` — el cambio
   F2 completo: proposal, specs, design (6 ADRs), tasks, verify-report.
5. `openspec/changes/archive/2026-08-08-f2-catalogo-ux-redesign/` — diseño system
   entregado para F3–F6 (patrón de ítem/opción evaluador).
6. `apps/web/docs/design-system.md` — referencia de herencia F3–F6 (tokens,
   tipografía, contrato visual, patrón `LikertMatrix`).

---

## 2. Estado del proyecto

| Área | Estado |
| --- | --- |
| F1 Fundación/acceso (Marces) | ✅ Archivado (`2026-08-05-f1-fundacion-acceso`) |
| F2 Catálogo de instrumentos (Trevor) | ✅ Archivado (`2026-08-08-f2-catalogo-instrumentos`) |
| F2b UX del catálogo (Trevor) | ✅ Archivado (`2026-08-08-f2-catalogo-ux-redesign`) |
| **F3 Sesión de evaluación (Jhamil)** | 🔲 **PRÓXIMA — este handoff** |
| F4 Motor de calificación (Juan Carlos) | Pendiente |
| F5 Perfiles/recomendación (Piere) | Pendiente |
| F6 Informes/integración (Ivan) | Pendiente |

**No hay cambios activos** en `openspec/changes/` — todo está en `archive/`.
El trabajo de F3 arranca con `exploration → proposal` de un change nuevo.

### Stack

- `apps/web` — Next.js 14.2.35, TypeScript, UI en español.
- `services/api` — FastAPI, Pydantic v2, SQLAlchemy 2, Alembic (migraciones 0001→0005).
- PostgreSQL + Redis vía Docker Compose. Puertos: 8000 (api), 5432 (db), 6379 (redis), 3000 (web).
- R + renv + Quarto para analítica offline (fuera del camino productivo del MVP).
- Todo el contenido es `synthetic` / `research-only` — sin normas UAGRM reales, sin datos reales.

---

## 3. Invariantes que NO se negocian (config.yaml + AGENTS.md)

1. **Versionado inmutable**: un instrumento publicado jamás se edita en sitio.
   Cualquier cambio crea una nueva `instrument_version_id`; las sesiones conservan
   la versión exacta con la que empezaron.
2. **Scoring puro** (F4, pero el contrato ya existe): respuestas + versión + referencia
   → puntajes. Sin acceso a DB, sin efectos secundarios.
3. **Recomendación declarativa** (F5): reglas en DB, no en código ni LLM.
4. **Sin LLM en el camino productivo** del MVP.
5. **Auditoría**: `audit_log` es append-only. Metadata agregada (ids, conteos,
   transiciones) — **nunca** contenido de ítems, claves ni tokens.
6. **Idempotencia**: todo endpoint mutante exige `Idempotency-Key`; retry con la
   misma key NO duplica efectos ni eventos de auditoría.

---

## 4. Lo que F2 ya entrega y F3 consume

### 4.1 Contrato F3 (fuente: `packages/contracts/README.md` §7.5)

> F3 (sesión) consume: el `instrument_version_id` copiado verbatim en cada sesión y
> nunca cambiado; el payload de lectura publicado para renderizar; la regla de
> congelamiento (las versiones publicadas nunca cambian; una versión nueva es un id
> nuevo); y errores estables para versiones draft/archivadas/inexistentes/inválidas.
> F4 consume la relación ítem ↔ escala ↔ opción con el mapeo 1–5 server-side vía
> una proyección de fixtures no pública.

### 4.2 Regla de disponibilidad (spec ratificada, `catalog-api/spec.md`)

> La sesión NO debe arrancar contra un `instrument_version_id` no publicado. Los
> casos de error estables para versiones draft, archivadas, inexistentes e inválidas
> están documentados. **La enforcement del gate de creación de sesión es propiedad
> explícita de F3**; F2 entrega la regla y los casos de error sin implementar ni
> alterar el comportamiento de sesión de F3.

Escenario de contrato (Given/When/Then):

```
GIVEN el contrato de handoff F2 y un instrument_version_id en draft
WHEN F3 implementa la creación de sesión según el contrato
THEN la creación rechaza el id no publicado con el error estable documentado
AND el comportamiento de F3 se verifica contra el contrato, no contra una
    implementación de sesión de F2
```

### 4.3 Superficie de endpoints relevante para F3 (todas bajo `/api/v1/catalog`)

| Endpoint | Roles | Nota para F3 |
| --- | --- | --- |
| `GET /published-versions/{version_id}` | admin, psicólogo, evaluado | Payload de evaluador solo-publicado (labels, sin valores). **Los ids no publicados (draft/archivado/inexistente) son indistinguibles: todos `NOT_FOUND`** — sin fuga de status/existencia. |

Endpoints de administración (NO los usa F3, pero el gate de sesión debe tratarlos
igual): `GET/POST /admin/instruments`, `POST /admin/instruments/{id}/versions`,
`GET /admin/versions/{version_id}`, `PUT /admin/versions/{id}/content`,
`POST /admin/versions/{id}/publish` (solo admin), `POST /admin/versions/{id}/archive`.
Todo endpoint mutante exige `Idempotency-Key`; toda ruta protegida usa
`require_roles(...)` (deny-by-default; `FORBIDDEN` + `auth.denied` antes de tocar
recursos).

### 4.4 Semántica que F3 debe respetar

- **`instrument_version_id` copy-and-never-change**: copiado verbatim en cada
  sesión, jamás mutado.
- **Congelamiento**: ciclo `draft → published → archived`, enforced por
  `CHECK` + triggers de DB (`catalog_version_immutability_guard` en
  `0005_catalog_four_level.py`). Publicado/archivado son inmutables: sin edición
  en sitio, sin delete, sin unarchive. **Dos versiones publicadas del mismo
  instrumento pueden coexistir y ambas son arrancables.**
- **Tipo de respuesta**: `likert_1_5` únicamente — cinco opciones ordenadas por
  ítem, valores server-side 1–5. El payload público expone SOLO labels de opción,
  nunca valores numéricos ni claves de respuesta.
- **Errores estables**: draft/archivado/inexistente/inválido → `NOT_FOUND` en la
  lectura publicada; `CONFLICT` para mutación inmutable o misma-key-distinto-body.
  Códigos de envelope: `VALIDATION_ERROR`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`,
  `UNAUTHORIZED`, `INTERNAL_ERROR` (+ `seed_catalog_read_only`).

### 4.5 Eventos de auditoría ya disponibles para F3 (§3 de contracts)

`session.started`, `session.completed`, `session.blocked_without_consent`,
`consent.granted`, `consent.revoked` — con deny-list de metadata: nunca respuestas,
tokens ni contenido de ítems.

### 4.6 Datos semilla relevantes

- Instrumento semilla: `TP-S-01:v1` (namespace UUID5 `psico-seed:`), **read-only
  en todas partes** (el service lo rechaza con `seed_catalog_read_only`).
- Cuenta dev `evaluado` / `psico-dev-evaluado` **sin consentimiento sembrado** →
  crear sesión devuelve `409 consent_required` (comportamiento esperado); el
  consentimiento se otorga con `POST /api/v1/consent/{id}/grant`.
- Semilla total: 20 ítems, 1 baremo, 30 perfiles, 30 sesiones, 30 consentimientos,
  600 respuestas, 5 escalas, 100 opciones (grafo `(5, 20, 100)`).

### 4.7 Proyección de fixtures (para F4, NO pública)

El mapeo ítem ↔ escala ↔ opción 1–5 server-side vive en
`services/api/app/modules/assessment_authoring/projections.py`. Es una proyección
no pública: la proyección de evaluador jamás debe llamarla.

---

## 5. Lo que F3 debe construir (alcance esperado — definirlo en el proposal)

Basado en la fase y el contrato F2, F3 cubre la **sesión de evaluación**:

1. **State machine de sesión** (p. ej. `created → in_progress → completed` /
   `blocked_without_consent`), persistida, con eventos de auditoría `session.*`.
2. **Gate de creación**: rechazar `instrument_version_id` no publicado con el
   error estable (`NOT_FOUND`), y `409 consent_required` cuando el evaluado no
   tiene consentimiento (comportamiento F1 ya existente).
3. **Renderizado de ítems** consumiendo el payload de evaluador publicado
   (labels only) — reutilizar el patrón `LikertMatrix` del diseño system.
4. **Registro de respuestas** (valores 1–5 server-side), autosave y resume de
   sesión; idempotencia en todo endpoint mutante.
5. **Cierre de sesión** (`session.completed`) sin puntuar (el scoring es F4).

> ⚠️ El alcance exacto, límites y no-goals se deciden en la proposal del change
> F3 con SDD (`/sdd-new`). No implementes directo: la cadena es
> `exploration → proposal → spec → design → tasks → apply → verify → archive`.

---

## 6. Arquitectura y estructura del repo

```
psico-proyect/
├── apps/web/                    # Next.js 14.2.35 (UI español)
│   ├── app/  components/  docs/  lib/  public/
│   └── docs/design-system.md    # herencia F3–F6: tokens + patrón LikertMatrix
├── services/api/                # FastAPI + SQLAlchemy 2 + Alembic
│   ├── alembic/                 # migraciones 0001…0005
│   ├── app/
│   │   ├── api/routes/catalog.py
│   │   ├── modules/assessment_authoring/  # domain, service, repository,
│   │   │                                 # projections, idempotency, errors
│   │   ├── schemas/catalog.py
│   │   ├── core/permissions.py
│   │   ├── models/instruments.py
│   │   └── seed/
│   ├── tests/                   # suite pytest (113 tests)
│   └── .venv/                   # LSP local (pyright)
├── packages/contracts/README.md # convenciones vinculantes F1–F6 (§1–§7.5)
├── openspec/
│   ├── config.yaml              # invariantes, fases/owners, testing
│   ├── specs/                   # 12 specs ratificadas (memoria canónica)
│   └── changes/archive/         # 3 cambios archivados (sin activos)
├── scripts/                     # init-env, test (.sh + .ps1)
├── AGENTS.md  ONBOARDING.md  README.md  HANDOFF-F3.md
└── docker-compose.yml
```

Ficheros F3-relevantes: `services/api/app/api/routes/catalog.py`,
`services/api/app/modules/assessment_authoring/*`,
`services/api/app/schemas/catalog.py`, `services/api/app/core/permissions.py`,
`services/api/app/models/instruments.py`,
`services/api/alembic/versions/0005_catalog_four_level.py`,
`services/api/tests/test_catalog_*.py`.

---

## 7. Setup y comandos

```bash
# 1. Bootstrap (crea .env desde .env.example si no existe)
scripts/init-env.ps1              # Windows  (o init-env.sh en Linux/macOS)

# 2. Build y arranque del stack
docker compose up -d --build

# 3. Esquema
docker compose run --rm api alembic upgrade head

# 4. Semilla (idempotente)
docker compose run --rm api python -m app.seed
#    Variante con preflight atómico: python -m app.seed --reset

# 5. Suite completa de tests
scripts/test.ps1                  # o scripts/test.sh
```

Web: `cd apps/web && npm install && npm run build` (typecheck + build).
API en `http://localhost:8000` (`/health`, `/api/v1/seed/status` públicos).
Web en `http://localhost:3000`.

**Windows (Git Bash)**: si `scripts/test.sh` falla por conversión de rutas MSYS,
usá `WINPWD=$(pwd -W) && MSYS_NO_PATHCONV=1 docker compose run --rm -v "${WINPWD}:/repo:ro" api pytest /repo/services/api/tests`.

---

## 8. Testing (estado actual)

- `strict_tdd: true`, runner: pytest (detectado 2026-08-08). Capas: unit ✅,
  integration ✅ (TestClient + PostgreSQL real en compose), e2e ❌ (no disponible).
- Suite F2: **113 tests, 32 warnings, ~75 s** — pasa dos veces seguidas (verificado
  el 08-08; warnings: deprecación Starlette/httpx, longitud de JWT dev key,
  `.pytest_cache` en mount `:ro`).
- Slices: `pytest -k scripts|schema|auth|audit|consent|seed|web`.
- Web: `npm run build` PASS (7 páginas estáticas, rutas de catálogo incluidas).
- **Repetibilidad**: el conftest dropea y recrea la BD `psico` por corrida; no
  conserves estado entre corridas.
- Cobertura/linter/formatter: no configurados. Type checker: `next build` + pyright
  (venv local en `services/api/.venv`).

---

## 9. Trampas conocidas (leer antes de debuggear)

1. **Imagen docker vieja**: tras tocar migraciones o código de `services/api`,
   corré `docker compose build api`. Los tests montan `/repo` (código nuevo) pero
   alembic y la app corren desde `/app` (copia de la imagen). Imagen vieja =
   fallos fantasma (ej. `relation "scales" does not exist`).
2. **Suite repetible**: registros de idempotencia persisten entre corridas; el
   conftest dropea/recrea `psico` por corrida — no dependas de estado previo.
3. **LSP local**: sin `services/api/.venv`, pyright reporta errores falsos
   (`itertools could not be resolved`).
4. **Seed read-only**: `TP-S-01:v1` no se edita ni versiona desde la UI →
   `seed_catalog_read_only`.
5. **E6 de ONBOARDING**: `POSTGRES_*` y `PSICO_DATABASE_URL` deben estar 1:1
   (`psico_app` / `psico_dev_password` / `psico`).
6. **Datos viejos**: `app.seed --reset` o `docker compose down -v` para limpiar.

---

## 10. Convenciones (vinculantes)

| Área | Regla |
| --- | --- |
| Textos de UI | Español (ej. `Guardar borrador`, `Publicar versión`) |
| Código, identificadores, specs | Inglés (tokens de contrato en inglés) |
| Idiomas de opciones | `locale: es` por defecto; Likert usa etiquetas, nunca valores visibles |
| Envelope de API | `{"error": {"code", "message", "request_id", "details"}}`; códigos: `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `INTERNAL_ERROR` |
| Permisos | Deny-by-default con `require_roles(...)`; psicólogo edita/archiva, admin publica, evaluado solo lee publicado |
| Commits | Conventional commits, unidades de trabajo revisables, sin atribución de IA |
| Auditoría | Append-only; metadata agregada, nunca contenido de ítems/claves/tokens |
| Idempotencia | Todo endpoint mutante exige `Idempotency-Key` (misma key + mismo body = replay sin duplicados; misma key + distinto body = `CONFLICT`) |

### Workflow OpenSpec (memoria del proyecto)

- Los specs ratificados son la fuente de verdad. Si código y spec difieren, es un
  bug de una de las dos partes.
- Ciclo de change: `exploration → proposal → spec → design → tasks → apply →
  verify → archive`. Al archivar, los deltas se fusionan en `openspec/specs/`.
- Decisiones nuevas van en un change, nunca en comentarios sueltos.
- Specs: Given/When/Then + palabras RFC 2119 (MUST/SHALL/SHOULD/MAY).
- Design: diagramas de secuencia para flujos complejos, ADRs con rationale.

---

## 11. Follow-ups pendientes (non-blocking, heredados)

1. `services/api/tests/test_catalog_db.py:305` usa `pytest.raises(Exception)`
   genérico — ajustar a la excepción DB específica.
2. `openspec/config.yaml` líneas 61–66: `apply.test_command`, `verify.test_command`
   y `build_command` quedaron vacíos aunque el gatekeeper de F2 los declaró
   cableados a `scripts/test.sh` y `npm run build`. **Conciliar al arrancar F3.**
3. `AGENTS.md` línea 28 ("Cambio activo actual") apunta a
   `openspec/changes/f2-catalogo-instrumentos/`, que ya está **archivado** —
   actualizar el puntero (sugerencia: "sin cambios activos — ver HANDOFF-F3.md").
4. Sin cobertura configurada; sin capa E2E/browser (0 tests E2E en F2).
5. `apps/web/app/login/error.tsx` y superficies de error comparten un CSS module
   raíz vía imports relativos profundos — F3 puede consolidar.

---

## 12. Checklist para cerrar una tarea (de AGENTS.md)

- [ ] Los specs que tocaste están actualizados (o hay un change activo que los modifica)
- [ ] La suite completa pasa dos veces seguidas (repetibilidad)
- [ ] Datos sintéticos: nada real se introdujo en seeds, fixtures o tests
- [ ] Ningún endpoint mutante quedó sin `Idempotency-Key`
- [ ] La auditoría no expone contenido de ítems
- [ ] Commit convencional, unidad de trabajo acotada

---

## 13. Fuentes de verdad (en orden de autoridad)

1. `openspec/config.yaml` — invariantes, fases/owners, testing.
2. `openspec/specs/` — 12 specs ratificadas (incl. `catalog-api` con el contrato F3).
3. `packages/contracts/README.md` — convenciones técnicas vinculantes (§7.5 handoff F3).
4. `openspec/changes/archive/2026-08-08-f2-catalogo-instrumentos/` — el porqué de F2.
5. `openspec/changes/archive/2026-08-08-f2-catalogo-ux-redesign/` — diseño system F3–F6.
6. `apps/web/docs/design-system.md` — tokens y patrones de UI heredados.
7. `AGENTS.md` / `ONBOARDING.md` / este `HANDOFF-F3.md` — guías operativas.

*Generado el 2026-08-08 a partir del estado del repo en `master @ 03b6f62`
(working tree limpio). Actualizar este archivo si el estado cambia o al cerrar F3.*

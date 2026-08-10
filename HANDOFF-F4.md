# HANDOFF-F4 — Motor de calificación (owner: Juan Carlos)

Documento de traspaso para quien continúe TestPsico con la **Fase 4 — Motor de
calificación**. Escrito al cierre de F3 (sesión de evaluación, owner Jhamil),
con el repo en `master @ bf37bd4` y working tree limpio.

> **Cómo usar este documento**: leelo completo una vez (10 min) y guardalo como
> referencia. Antes de tocar código, seguí el quick path de `AGENTS.md`: la
> memoria canónica del proyecto es OpenSpec, no este archivo. Este handoff es el
> puente entre esa memoria y vos.

---

## 1. Quick path (orden obligatorio de lectura antes de editar)

1. `openspec/config.yaml` — invariantes de dominio (el invariante nº 2 es **el
   motor puro de scoring de F4**), fases/owners, testing (2 min).
2. `packages/contracts/README.md` — convenciones vinculantes F1–F6: §2 envelope
   de error, §3 auditoría (deny-list), §6 access matrix ("View results" ya
   ratificado para las tres roles), §7.5 contrato de handoff, §7.6.4 boundary
   no-scoring y "F4 may consume the private mapping later".
3. `openspec/specs/data-schema/spec.md` — la familia scoring
   (`reference_sets`, `reference_values`, `score_runs`) y las invariantes de
   integridad de la familia de instrumentos.
4. `openspec/specs/sessions/spec.md` — lo que F3 entrega: sesiones
   `in_progress → completed`, respuestas inmutables (valor 1–5, upsert por
   `(session, item)`), cero puntajes en la superficie pública.
5. `openspec/specs/catalog-model/spec.md` — la relación ítem ↔ escala ↔ opción
   (valores server-side 1–5, solo en el contrato interno) y
   `catalog-api/spec.md` — payload de evaluador labels-only.
6. `openspec/changes/archive/2026-08-09-f3-sesion-evaluacion/` — el change F3
   completo: proposal, 5 specs delta, design (5 ADRs), tasks, verify-report
   (incluye el boundary F4 y la deuda heredada).
7. `services/api/app/modules/assessment_authoring/projections.py` — la
   **proyección de fixtures NO pública** (`fixture_projection`) con el mapeo
   opción → valor 1–5 que F4 consume.
8. `apps/web/docs/design-system.md` — herencia F3–F6: tokens, patrones, §6
   delivery freeze. **No tiene** sección de resultados/reportes (ver §5).
9. `openspec/specs/synthetic-seed/spec.md` — qué está sembrado para F4
   (baremo sintético, 30 perfiles con sesiones completadas y 600 respuestas).

---

## 2. Estado del proyecto

| Área | Estado |
| --- | --- |
| F1 Fundación/acceso (Marces) | ✅ Archivado (`2026-08-05-f1-fundacion-acceso`) |
| F2 Catálogo de instrumentos (Trevor) | ✅ Archivado (`2026-08-08-f2-catalogo-instrumentos`) |
| F2b UX del catálogo (Trevor) | ✅ Archivado (`2026-08-08-f2-catalogo-ux-redesign`) |
| F3 Sesión de evaluación (Jhamil) | ✅ Archivado (`2026-08-09-f3-sesion-evaluacion`) |
| **F4 Motor de calificación (Juan Carlos)** | 🔲 **PRÓXIMA — este handoff** |
| F5 Perfiles/recomendación (Piere) | Pendiente |
| F6 Informes/integración (Ivan) | Pendiente |

**No hay cambios activos** en `openspec/changes/` — solo `archive/`. El trabajo
de F4 arranca con `exploration → proposal` de un change nuevo (cadena SDD:
`exploration → proposal → spec → design → tasks → apply → verify → archive`).

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
   la versión exacta con la que empezaron (pin copy-and-never-change).
2. **Scoring puro** (ES F4): respuestas + versión de instrumento + referencia
   → puntajes (raw → direct → transformed: percentile/T/eneatype). **Sin acceso
   a DB, sin efectos secundarios.** La spec de diseño lo refuerza: "scoring
   engine must stay free of DB access and side effects".
3. **Recomendación declarativa** (F5): reglas en DB, no en código ni LLM.
4. **Sin LLM en el camino productivo** del MVP.
5. **Auditoría**: `audit_log` es append-only. Metadata agregada (ids, conteos,
   transiciones) — **nunca** contenido de ítems, respuestas, claves ni tokens.
   El catálogo de eventos está ratificado (§3 de contracts); F4 **no agrega
   eventos sin ratificar**.
6. **Idempotencia**: todo endpoint mutante exige `Idempotency-Key`; retry con la
   misma key NO duplica efectos ni eventos de auditoría.
7. **Datos sintéticos**: todo contenido es `synthetic` y `research-only`; no hay
   normas UAGRM reales ni datos reales.

---

## 4. Lo que F3 ya entrega y F4 consume

### 4.1 Contrato F3→F4 (fuente: `packages/contracts/README.md` §7.5 y §7.6)

> F4 consume la relación ítem ↔ escala ↔ opción con el mapeo 1–5 server-side vía
> una proyección de fixtures no pública (`assessment_authoring/projections.py`).

> §7.6.4 (Labels-only and no-scoring boundary): los valores numéricos de opción,
> claves de respuesta, puntajes, percentiles, resultados transformados y
> resultados del reference set **NO deben cruzar la API pública ni aparecer en
> la UI web**. F4 puede consumir el mapeo privado ("F4 may consume the private
> mapping later"); F3 devuelve solo estado de ciclo de vida al completar.

F3 entrega a F4, desde `GET /sessions/{id}` y las filas de BD:

- Sesiones `completed` con respuestas **inmutables**: filas `responses` con
  `value` 1–5 (CHECK `ck_value_1_to_5`), únicas por `(session_id, item_id)`,
  sin duplicados posibles por upsert.
- El `instrument_version_id` pinneado verbatim en cada sesión (nunca mutado;
  sobrevive al archivado de la versión).
- Sin puntajes: ni la sesión ni su proyección pública contienen scoring
  (verificado por `test_session_api.py` y el verify-report F3).

### 4.2 Regla de disponibilidad para F4 (propuesta — ratificarla en la spec F4)

```
GIVEN una sesión con status 'completed' y su instrument_version_id pinneado
WHEN el motor de F4 intenta calificar sus respuestas
THEN el scoring procede solo contra esa versión pinneada y el reference set elegido

GIVEN una sesión 'in_progress', incompleta o inexistente
WHEN se intenta calificarla
THEN el resultado es un error estable documentado (p. ej. CONFLICT / session_not_completed
     o NOT_FOUND indistinguible), sin fuga de contenido de respuestas
```

El detail público de F3 ya expone el estado; F4 debe decidir en la spec si el
rechazo es `CONFLICT` (estado visible) o `NOT_FOUND` (sin fuga). **Regla de
oro**: el scoring jamás califica `in_progress`; las respuestas de una sesión no
completada nunca se puntúan ni se exponen.

### 4.3 Superficie de endpoints existente (lo que F4 NO duplica)

| Área | Endpoints (hoy) |
| --- | --- |
| Catálogo | `GET /api/v1/catalog/published-versions`, `GET /api/v1/catalog/published-versions/{version_id}`, `GET/POST /api/v1/catalog/admin/instruments…`, `GET/PUT /api/v1/catalog/admin/versions…`, publish/archive |
| Sesiones | `POST /api/v1/sessions`, `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}`, `PUT /api/v1/sessions/{id}/responses`, `POST /api/v1/sessions/{id}/complete` |
| Consent | `POST /api/v1/consent/{version_id}/grant`, `POST /api/v1/consent/{version_id}/revoke` |
| Otros | `/health`, `/api/v1/seed/status`, login/auth, audit (admin) |

**No existe hoy ningún endpoint de scoring, resultados ni reference sets.** F4
crea su propia superficie (p. ej. bajo `/api/v1/scoring` o `/api/v1/results`,
decisión del design), siempre con roles según la access matrix: "View results"
está ratificado para `admin` ✅, `psicólogo` ✅, `evaluado` ✅ (own).

### 4.4 Tablas de baremo / reference (nombres reales verificados)

La familia scoring existe **desde la migración 0003** (creada en F1,
`0003_scoring_recommendation_reporting_audit_seed.py`), vacía hasta que el seed
la llena:

| Tabla | Modelo | Columnas relevantes |
| --- | --- | --- |
| `reference_sets` | `ReferenceSet` (`models/scoring.py:31`) | `id`, `key` (unique), `instrument_version_id` (FK nullable), `reference_status` (CHECK `synthetic`/`real`), `use` (default `research-only`), `norm_note` (Text) |
| `reference_values` | `ReferenceValue` (`models/scoring.py:51`) | `reference_set_id` (FK), `scale`, `value_type`, `raw_value` (Numeric 6,3), `transformed_value`, `percentile` (int), `t_score` (int), `eneatype` (int); UNIQUE `(reference_set_id, scale, value_type, raw_value)` |
| `score_runs` | `ScoreRun` (`models/scoring.py:72`) | `session_id` (FK), `reference_set_id` (FK), `status` (default `pending`), `raw` (JSONB), `computed_at` — **el destino natural del resultado de F4** |

**Conclusión**: F4 probablemente NO necesita migración — `score_runs` existe y
es espera ser usada. Si el design decide persistir `score_runs` con `status`
`pending → completed`, no hace falta tocar alembic. (Verificar en el design;
solo agregar migración si el proposal la justifica.)

### 4.5 Datos semilla relevantes para F4 (conteos reales verificados)

- **Instrumento** `TP-S-01:v1`: `seed_id("TP-S-01:v1")` (namespace UUID5
  `psico-seed:`), 5 escalas × 4 ítems = **20 ítems**, 100 opciones, publicado e
  inmutable, `locale=es`, todo `required=true`.
  - Escalas (labels reales): `Intereses`, `Aptitud verbal`, `Aptitud numérica`,
    `Razonamiento abstracto`, `Valores/preferencias`.
  - Claves de ítems: `TP-S-01:i1` … `TP-S-01:i20`; opciones
    `TP-S-01:i{index}:option:{value}` (value 1–5).
- **Baremo** `RS-TP-S-01` (`seed_id("RS-TP-S-01")`): `reference_status:
  synthetic`, `use: research-only`, `norm_note: "NO es una norma UAGRM. Datos
  inventados para desarrollo."` — **el disclaimer debe acompañar cualquier
  salida de resultados de F4 que use este baremo**.
  - 30 filas `reference_values`: 5 escalas × (mean, sd) = 10 filas de
    estadísticos (`raw_value` 3.4/0.9, 3.2/1.0, 3.0/1.1, 2.9/1.1, 3.4/0.8) +
    20 filas `overall` / `value_type=percentile` con `raw_value` 1–20 →
    `percentile` 2–97, `t_score` 30–67, `eneatype` 1–7.
- **30 perfiles** `evaluado_01` … `evaluado_30`: cada uno con consentimiento
  `granted`, **1 sesión `completed`** (`session:evaluado_{NN}`), y **20
  respuestas** (`response:{profile}:i{index}`, valor 1–5) → **30 sesiones, 600
  respuestas en total**.
- Dev accounts: `admin`, `psicologo`, `evaluado` (sin sesión sembrada;
  `psico-dev-*` passwords desde `.env`).

### 4.6 Proyección de fixtures (NO pública — la consume F4)

`services/api/app/modules/assessment_authoring/projections.py:51`:

```python
def fixture_projection(version: InstrumentVersion) -> dict[str, Any]:
    """Build the internal F4 fixture with the server-side 1–5 mapping."""
```

Devuelve `instrument_version_id` + escalas → ítems → `response_options`
`[{id, value}]` con el **valor numérico 1–5 server-side**. La proyección de
evaluador (`published_evaluator_projection`) y el payload público jamás la
llaman. La relación ítem ↔ escala ↔ opción vive en esta estructura
(escale → items → options con `id` + `value`).

### 4.7 Eventos de auditoría disponibles (F4 no agrega sin ratificar)

Catálogo ratificado (contracts §3): `auth.login`, `auth.denied`,
`user.role_changed`, `instrument.draft_created`, `instrument.draft_updated`,
`instrument.published`, `instrument.archived`, `consent.granted`,
`consent.revoked`, `session.started`, `session.completed`,
`session.blocked_without_consent`, `seed.executed`. Si F4 necesita auditar
corridas de scoring, el evento nuevo (p. ej. `scoring.run`) **debe ratificarse
en el change F4** — nunca añadirse en silencio. Metadata de auditoría: agregados
(ids, conteos), nunca valores de respuesta.

---

## 5. Lo que F4 debe construir (alcance esperado — definirlo en el proposal)

1. **Motor de calificación puro**: función pura
   `responses + instrument_version_id + reference → scores`, cadena
   **raw → direct → transformed (percentile/T/eneatype)**, sin acceso a DB, sin
   efectos secundarios, sin LLM. Es el invariante nº 2 de `config.yaml`; la
   regla de specs exige mantener el contrato explícito: inputs (respuestas +
   versión + referencia) y outputs (raw/direct/transformed).
2. **Consumo del contrato F3→F4**: sesiones `completed` con respuestas
   inmutables; mapeo opción → valor 1–5 vía `fixture_projection` (no pública);
   relación ítem ↔ escala ↔ opción para el raw por escala.
3. **Baremo / reference set**: consumir (y quizás exponer) el set sintético
   `RS-TP-S-01` (`reference_status='synthetic'`, `use='research-only'`,
   `norm_note` = "NO es una norma UAGRM. Datos inventados para desarrollo.").
   Persistir resultados en `score_runs` (tabla ya existente).
4. **Regla de disponibilidad**: scoring solo sobre sesiones `completed`;
   sesiones incompletas / `in_progress` / bloqueadas / inexistentes → error
   estable documentado; sin fuga de contenido.
5. **Superficie de API** (decisión del design): lectura de resultados por
   sesión para `admin`/`psicólogo`/`evaluado` (own) según la access matrix, con
   envelope de error único y `Idempotency-Key` si hay mutación (p. ej.
   disparar/registrar un score run).

### No-goals (NO tocar en F4)

- **Recomendación declarativa** (F5, Piere): reglas en DB, perfiles,
  fit score — fuera de alcance.
- **Informes / PDF / integración institucional** (F6, Ivan) — fuera de alcance.
- NO tocar el catálogo (F2), NO tocar sesiones (F3) — solo consumir.
- NO agregar eventos de auditoría sin ratificar (ver §4.7).
- NO exponer datos reales: todo synthetic / research-only; el `norm_note` del
  baremo acompañará cualquier salida de resultados.

> ⚠️ El alcance exacto, límites y no-goals se deciden en la proposal del change
> F4 con SDD. No implementes directo: la cadena es
> `exploration → proposal → spec → design → tasks → apply → verify → archive`.

---

## 6. Arquitectura y estructura del repo

```
psico-proyect/
├── apps/web/                    # Next.js 14.2.35 (UI español)
│   └── docs/design-system.md    # herencia F3–F6: tokens + delivery freeze
├── services/api/                # FastAPI + SQLAlchemy 2 + Alembic
│   ├── alembic/versions/        # 0001…0005 (F4 no requiere migración en principio)
│   ├── app/
│   │   ├── api/routes/          # audit, auth, catalog, consent, health, seed, sessions
│   │   ├── modules/
│   │   │   ├── assessment_authoring/  # domain, service, repository, errors,
│   │   │   │                         # idempotency, projections (fixture_projection NO pública)
│   │   │   └── session_runtime/       # domain, service, repository, errors (F3)
│   │   ├── models/              # instruments, sessions, scoring (reference_sets,
│   │   │                        # reference_values, score_runs), audit, consent, identity…
│   │   └── seed/                # loader.py + fixtures/ (items, reference, profiles/)
│   ├── tests/                   # suite pytest (149 collected)
│   └── .venv/                   # LSP local (pyright)
├── packages/contracts/README.md # convenciones vinculantes F1–F6 (§1–§7.6)
├── openspec/
│   ├── config.yaml              # invariantes, fases/owners, testing
│   ├── specs/                   # 14 specs ratificadas (memoria canónica)
│   └── changes/archive/         # 4 cambios archivados (sin activos)
├── scripts/                     # init-env, test (.sh + .ps1)
├── AGENTS.md  ONBOARDING.md  README.md  HANDOFF-F3.md  HANDOFF-F4.md
└── docker-compose.yml
```

**Patrón de módulo esperado (F2/F3)**: `app/modules/scoring/` (o `scoring/`)
con `domain.py` (la **función pura**: transiciones raw → direct → transformed,
sin DB ni I/O), `service.py` (orquestación: lee sesión+versión+reference vía
repository, invoca domain, persiste `score_runs`), `repository.py` (lectura de
respuestas/versión/reference + escritura de `score_runs`), `errors.py` (errores
estables del módulo). Ficheros F4-relevantes hoy:
`app/modules/assessment_authoring/projections.py`,
`app/models/scoring.py`, `app/models/sessions.py`,
`app/seed/loader.py` (+ `fixtures/reference.json`), `app/api/routes/sessions.py`.

---

## 7. Setup y comandos

```bash
# 1. Bootstrap (crea .env desde .env.example si no existe)
scripts/init-env.ps1              # Windows  (o init-env.sh en Linux/macOS)

# 2. Build y arranque del stack
docker compose up -d --build

# 3. Esquema
docker compose run --rm api alembic upgrade head

# 4. Semilla (idempotente) — siembra el baremo RS-TP-S-01 y los 30 perfiles
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
- Suite actual: **149 collected = 147 passed + 2 failed** (verificado por el
  verify-report F3, dos corridas repetidas, exit 0 por el wrapper). Los 2 fallos
  son **heredados de F2b**, en `services/api/tests/test_web.py`:
  `test_page_is_spanish` y `test_page_never_leaks_stack_trace` — aserciones
  F1-era sobre el `page.tsx` rediseñado. **NO los toques** (deuda documentada
  en archive-report F3).
- Warnings: ~59 por corrida (deprecación Starlette/httpx, longitud de JWT dev
  key, `.pytest_cache` en mount `:ro`).
- Slice F3 de referencia: `pytest -k "session or published_versions or consent"`
  → 37 passed / 112 deselected (20.73 s). F4 usará su propio slice
  (p. ej. `-k scoring or reference or results`).
- `config.yaml`: `apply.test_command` y `verify.test_command` =
  `powershell -ExecutionPolicy Bypass -File scripts/test.ps1`; `build_command` =
  `npm run build` (apps/web). **Ya reconciliados en F3** (commit `b676085`).
- Web: `npm run build` PASS (8 rutas generadas en F3). Sin runner de browser;
  evidencia = build + inspección estática + checklist manual del owner.
- **Repetibilidad**: el conftest dropea y recrea la BD `psico` por corrida; no
  conserves estado entre corridas (los registros de idempotencia persisten).
- Cobertura/linter/formatter: no configurados. Type checker: `next build` +
  pyright (venv local en `services/api/.venv`; el ejecutable no estaba
  disponible en el verify F3).

---

## 9. Trampas conocidas (leer antes de debuggear)

1. **Imagen docker vieja**: tras tocar código de `services/api`, corré
   `docker compose build api`. Los tests montan `/repo` (código nuevo) pero
   alembic y la app corren desde `/app` (copia de la imagen). Imagen vieja =
   fallos fantasma (ej. `relation "reference_values" does not exist`).
2. **Suite repetible**: el conftest dropea/recrea `psico` por corrida — no
   dependas de estado previo; los registros de idempotencia persisten.
3. **LSP local**: sin `services/api/.venv`, pyright reporta errores falsos
   (`itertools could not be resolved`).
4. **Seed read-only**: `TP-S-01:v1` no se edita ni versiona → `seed_catalog_read_only`.
5. **E6 de ONBOARDING**: `POSTGRES_*` y `PSICO_DATABASE_URL` deben estar 1:1
   (`psico_app` / `psico_dev_password` / `psico`).
6. **Datos viejos**: `app.seed --reset` o `docker compose down -v` para limpiar.
7. **`scripts/test.ps1` enmascara el exit code** de pytest (no propaga
   `$LASTEXITCODE`): el conteo de pasados/fallidos en la salida es la evidencia
   autoritativa, no el exit code del wrapper.
8. **No fugar el mapeo privado**: `fixture_projection` y los valores 1–5 jamás
   deben cruzar la API pública ni la UI — misma regla que F3 (verify-report F3
   revisa este boundary explícitamente).
9. **`docs/fase-3-sesion-evaluacion.md` NO existe** en el repo (la carpeta
   `docs/` no tiene archivos): el orquestador lo citaba como referencia, pero la
   fuente de cierre autoritativa de F3 es su `archive-report.md` + `verify-report.md`.

---

## 10. Convenciones (vinculantes)

| Área | Regla |
| --- | --- |
| Textos de UI | Español (p. ej. `Resultados`, `Sin puntaje disponible`) |
| Código, identificadores, specs | Inglés (tokens de contrato en inglés) |
| Envelope de API | `{"error": {"code", "message", "request_id", "details"}}`; códigos: `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `INTERNAL_ERROR` |
| Permisos | Deny-by-default con `require_roles(...)`; "View results": admin ✅, psicólogo ✅, evaluado ✅ (own) |
| Commits | Conventional commits, unidades de trabajo revisables, sin atribución de IA |
| Auditoría | Append-only; metadata agregada, nunca contenido de ítems/respuestas/claves/tokens; sin eventos nuevos sin ratificar |
| Idempotencia | Todo endpoint mutante exige `Idempotency-Key` (misma key + mismo body = replay; misma key + distinto body = `CONFLICT` / `idempotency_key_reused`) |
| Scoring | Motor puro: sin DB, sin side effects; `score_runs` es el destino de persistencia; el `norm_note` del baremo acompaña salidas de resultados |

### Workflow OpenSpec (memoria del proyecto)

- Los specs ratificados son la fuente de verdad. Si código y spec difieren, es un
  bug de una de las dos partes.
- Ciclo de change: `exploration → proposal → spec → design → tasks → apply →
  verify → archive`. Al archivar, los deltas se fusionan en `openspec/specs/`.
- Decisiones nuevas van en un change, nunca en comentarios sueltos.
- Specs: Given/When/Then + palabras RFC 2119 (MUST/SHALL/SHOULD/MAY).
- Design: diagramas de secuencia para flujos complejos, ADRs con rationale,
  amenazas/rollout; "scoring engine must stay free of DB access and side effects".
- Work units: commits acotados por comportamiento, tests con el código, docs con
  el cambio visible; si el forecast supera ~400 líneas, encadenar PRs.

---

## 11. Follow-ups pendientes (non-blocking, heredados)

1. **2 fallos heredados F2b en `test_web.py`** (`test_page_is_spanish`,
   `test_page_never_leaks_stack_trace`): aserciones F1-era contra el landing
   rediseñado; pertenecen a la remediación del landing F2b, **no a F4**. No
   tocarlos; documentar en el verify de F4 como deuda heredada.
2. **Sin browser/E2E runner**: la verificación web es build + inspección
   estática + checklist manual del owner (F3 dejó su checklist en el
   verify-report; F4 correrá su propio manual si toca web).
3. **`scripts/test.ps1` enmascara el exit code**: pytest output counts deben
   quedar visibles en la evidencia de verificación.
4. **Own-list triangulation**: el escenario own-list de `GET /sessions` debería
   agregar una aserción de segundo owner (sugerencia del verify F3).
5. **WARNING cosmético del judgment day F3** (ronda 2, no severo): feedback de
   guardado obsoleto en una ruta in-place inalcanzable; aceptado como
   no-bloqueante.
6. **`AGENTS.md` línea 28** ("Cambio activo actual") sigue apuntando a
   `openspec/changes/f2-catalogo-instrumentos/`, ya archivado — actualizar el
   puntero (sugerencia: "sin cambios activos — ver HANDOFF-F4.md"). También se
   puede reconciliar cuando F4 archive.
7. **TDD evidence por tarea** de los primeros slices F3 solo si se requiere
   auditabilidad estricta de las 20 tareas (no-bloqueante).
8. **Consolidación de CSS** de superficies de error (`login/error.tsx` y
   afines) — abierto desde F2-ux; no-bloqueante.
9. **F2b landing** y su deuda de aserciones quedan para quien remedie el
   landing; F4 no lo hace.

---

## 12. Checklist para cerrar una tarea (de AGENTS.md)

- [ ] Los specs que tocaste están actualizados (o hay un change activo que los modifica)
- [ ] La suite completa pasa dos veces seguidas (repetibilidad) — 149 collected,
      con los 2 fallos heredados documentados y sin nuevos
- [ ] El motor puro no accede a DB ni tiene efectos secundarios (invariante nº 2)
- [ ] El mapeo 1–5 y los resultados nunca cruzan la API pública ni la UI sin el
      `norm_note` del baremo sintético
- [ ] Datos sintéticos: nada real se introdujo en seeds, fixtures o tests
- [ ] Ningún endpoint mutante quedó sin `Idempotency-Key`
- [ ] La auditoría no expone contenido de ítems ni valores de respuesta
- [ ] Ningún evento de auditoría nuevo sin ratificar en la spec del change
- [ ] Commit convencional, unidad de trabajo acotada

---

## 13. Fuentes de verdad (en orden de autoridad)

1. `openspec/config.yaml` — invariantes (scoring puro), fases/owners, testing.
2. `openspec/specs/` — 14 specs ratificadas (data-schema: familia scoring;
   sessions; catalog-model; catalog-api; contracts; synthetic-seed; …).
3. `packages/contracts/README.md` — convenciones técnicas vinculantes
   (§7.5 handoff F3→F4, §7.6.4 boundary no-scoring, §3 auditoría).
4. `openspec/changes/archive/2026-08-09-f3-sesion-evaluacion/` — el porqué de
   F3: proposal, specs delta, design (ADRs), tasks, verify-report (boundary F4,
   deuda heredada), archive-report (handoff F4 explícito).
5. `openspec/changes/archive/2026-08-08-f2-catalogo-instrumentos/` +
   `2026-08-08-f2-catalogo-ux-redesign/` — el porqué de F2 y el diseño system.
6. `services/api/app/modules/assessment_authoring/projections.py` — la
   proyección de fixtures NO pública que F4 consume.
7. `services/api/app/models/scoring.py` — `reference_sets`, `reference_values`,
   `score_runs` (nombres reales).
8. `services/api/app/seed/loader.py` + `seed/fixtures/` — seed del baremo
   `RS-TP-S-01` y los 30 perfiles (conteos y claves UUID5).
9. `apps/web/docs/design-system.md` — tokens y patrones heredados F3–F6.
10. `AGENTS.md` / `ONBOARDING.md` / `HANDOFF-F3.md` / este `HANDOFF-F4.md` —
    guías operativas.

*Generado el 2026-08-09 a partir del estado del repo en `master @ bf37bd4`
(working tree limpio). Actualizar este archivo si el estado cambia o al cerrar F4.*

# F6 lista para planificar: informes trazables, PDF e integración sin inventar contratos

Este handoff prepara la **Fase 6 — Informes/integración** para Ivan. Su misión es
convertir resultados de scoring y recomendaciones ya persistidos en un informe
trazable, generar un PDF y, solo si se ratifica, entregarlo a una integración. La
base de datos contiene scaffolding para `reports` y `report_templates`, pero eso
**no ratifica** endpoints, audiencia, contenido, estados, renderer, almacenamiento,
retención ni destino de integración.

| Dato | Valor verificado |
| --- | --- |
| Owner F6 | Ivan (`openspec/config.yaml`) |
| Baseline | `master` @ `adc7ae6` (`docs(openspec): archive f5-profiles-recommendation change`) |
| Fecha del baseline y del handoff | 2026-08-11 |
| Estado SDD | F1–F5 archivados; ningún change activo; `gentle-ai sdd-status` recomienda `sdd-new` |
| Estado Git al iniciar este handoff | `master...origin/master [ahead 8]`; solo `usuarios.md` sin seguimiento |
| Estado de F6 | **No planificado ni implementado; ningún contrato F6 está ratificado todavía** |

## Cómo leer los estados

Este documento usa tres etiquetas. No son intercambiables:

| Etiqueta | Significado |
| --- | --- |
| **[CONTRATO EXISTENTE VERIFICADO]** | Está ratificado por OpenSpec y/o implementado y comprobado en archivos actuales. Puede consumirse sin redefinirlo. |
| **[BASE F6 PROPUESTA]** | Es una recomendación para iniciar proposal/spec/design. No obliga hasta que un change la ratifique. |
| **[DECISIÓN ABIERTA PARA SDD]** | Falta una decisión de producto o técnica. El agente debe detenerse antes de implementar esa parte. |

## Resumen ejecutivo

F1–F5 ya entregan la cadena previa completa:

| Fase | Entrega consumible por F6 |
| --- | --- |
| F1 | Compose, identidad, tres roles, envelope de errores, idempotencia base, auditoría append-only, consentimiento, migraciones y seed sintético. |
| F2 | Catálogo de cuatro niveles e instrumentos publicados inmutables; una sesión conserva su `instrument_version_id`. |
| F3 | Sesiones consentidas, respuestas y estado `in_progress → completed`; no scoring en la superficie de sesión. |
| F4 | Motor de scoring puro, `score_runs`, `POST /api/v1/results/{session_id}/score` y `GET /api/v1/results/{session_id}`. |
| F5 | Recomendación declarativa, `recommendation_results`, `POST /api/v1/recommendations/{session_id}/generate` y `GET /api/v1/recommendations/{session_id}`. |

**[CONTRATO EXISTENTE VERIFICADO]** El archive report F5 entrega F6 como
“reports/PDF/integration” y declara que consume `recommendation_results` y
`score_runs`. La selección exacta de generaciones, el formato del informe y la
integración no están ratificados.

**[BASE F6 PROPUESTA]** F6 debería componer un snapshot determinista desde una
sesión completada, un `ScoreRun` completado y una generación de recomendaciones;
persistir la identidad exacta de esas entradas y del template; renderizar el PDF
mediante un adapter reemplazable; y aislar almacenamiento/entrega externa del
dominio puro y de las transacciones largas.

**[DECISIÓN ABIERTA PARA SDD]** Antes de escribir código deben resolverse, como
mínimo, audiencia y ownership, trigger, contenido/redacciones, lifecycle del
template, versionado/regeneración, renderer PDF, almacenamiento/retención,
integración y alcance web.

## Ruta rápida para el próximo agente

### 1. Entrar y proteger el working tree

```powershell
Set-Location -LiteralPath "<REPO_ROOT>"
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
git status --short --branch
```

En el estado dejado por este handoff se esperan únicamente:

```text
?? HANDOFF-F6.md
?? usuarios.md
```

`usuarios.md` es ajeno a F6: **no leer, modificar, agregar al índice, borrar ni
incluir en commits**. Si aparece cualquier otra ruta, no la revierta; identifique
su owner y deténgase si colisiona con F6.

Comprobación PowerShell no destructiva:

```powershell
$unexpected = git status --short | Where-Object {
  $_ -notmatch '^\?\? (HANDOFF-F6\.md|usuarios\.md)$'
}
if ($unexpected) {
  $unexpected
  throw "Hay cambios fuera del baseline permitido; no continuar sin resolver su ownership."
}
```

### 2. Confirmar CodeGraph antes de explorar

```powershell
Test-Path -LiteralPath ".codegraph"
codegraph status
codegraph explore "F6 reports report_templates score_runs recommendation_results PDF integration"
codegraph impact Report
```

Baseline verificado: `.codegraph/` existe, el índice está `up to date`, con 155
archivos, 2.275 nodos y 5.411 aristas. Si el índice informa corrupción, siga la
política de `AGENTS.md`; no ejecute comandos administrativos o destructivos.

### 3. Leer en este orden

1. `AGENTS.md`.
2. Este `HANDOFF-F6.md` completo.
3. `openspec/config.yaml`.
4. `openspec/specs/data-schema/spec.md`.
5. `openspec/specs/results-api/spec.md` y `openspec/specs/scoring-engine/spec.md`.
6. `openspec/specs/recommendation-api/spec.md`.
7. `openspec/specs/contracts/spec.md`, `openspec/specs/audit-consent/spec.md` y `openspec/specs/synthetic-seed/spec.md`.
8. `packages/contracts/README.md`.
9. Los changes F4 y F5 completos indicados en la tabla de fuentes canónicas.
10. Modelos, migración, módulos, rutas, tests y seed enumerados en el mapa actual.

No use `usuarios.md` como fuente de verdad. El owner Ivan ya está ratificado en
`openspec/config.yaml`.

### 4. Entrar por SDD; no saltar a apply

En una sesión nueva del orquestador, la primera invocación es:

```text
/sdd-new <f6-change-name>
```

Antes de iniciar fases, el orquestador debe presentar el SDD Session Preflight con
cuatro elecciones: modo de ejecución, artifact store, estrategia de PRs encadenados
y presupuesto de revisión. **No seleccione valores por cuenta propia.** Responder
solo con decisiones reales del owner; los placeholders siguientes no son valores:

```text
execution_mode=<OWNER_SELECTION>
artifact_store=<OWNER_SELECTION>
delivery_strategy=<OWNER_SELECTION>
review_budget=<OWNER_SELECTION>
```

Tras recopilar las cuatro elecciones, el orquestador debe ejecutar el init guard:
consultar el registro `sdd-init/psico-proyect` y lanzar `sdd-init` solo si falta.
El proyecto ya contiene `openspec/config.yaml`, specs canónicas y registro de
skills; el guard no debe reescribirlos sin una necesidad comprobada. Después, la
invocación pendiente de `/sdd-new` ejecuta **explore → proposal**. Resuelva la
ronda de preguntas de producto antes de continuar. Después:

```text
/sdd-continue <f6-change-name>
```

Repita `/sdd-continue` según el dispatcher autoritativo para completar:

```text
proposal → [spec ∥ design] → tasks → apply → verify → archive
```

No invoque `apply` mientras haya `blockedReasons`, preguntas abiertas de producto
o un forecast de revisión sin resolver. Para inspección read-only:

```powershell
gentle-ai sdd-status --cwd "$(git rev-parse --show-toplevel)"
```

El dispatcher nativo `gentle-ai sdd-continue <change> --cwd <repo>` solo es
autoritativo para artifact store `openspec` o `hybrid`; `/sdd-continue` resuelve
la ruta correcta para el store elegido.

## Fuentes canónicas

| Fuente | Autoridad para F6 |
| --- | --- |
| `AGENTS.md` | Flujo obligatorio, invariantes, comandos, traps y cierre. |
| `openspec/config.yaml` | Fases/owners, stack, strict TDD, reglas de proposal/spec/design/tasks/apply/verify/archive. |
| `openspec/specs/data-schema/spec.md` | Familias actuales, reporting empty-but-migrated y formas ratificadas de `score_runs`/`recommendation_results`. |
| `openspec/specs/scoring-engine/spec.md` | Pureza y forma matemática del scoring que F6 no puede reinterpretar. |
| `openspec/specs/results-api/spec.md` | API, latest-run, `norm_note`, ownership y no-leak de resultados. |
| `openspec/specs/recommendation-api/spec.md` | Inputs F5, latest-generation, DTO, disclaimer, justificaciones y no-leak. |
| `openspec/specs/contracts/spec.md` | Envelope, idempotencia, errores y acceso actualmente ratificados. |
| `openspec/specs/audit-consent/spec.md` | Catálogo/deny-list append-only y contrato de resiliencia de auditoría. |
| `openspec/specs/synthetic-seed/spec.md` | Seed sintético, reset atómico, reference set y reglas/programas F5. |
| `openspec/specs/sessions/spec.md` | Ownership, sesión completada e invariantes que F6 consume sin modificar. |
| `packages/contracts/README.md` | Convenciones compartidas F1–F6, matriz vigente y catálogo de auditoría. |
| `openspec/changes/archive/2026-08-10-f4-scoring-engine/exploration.md` | Opciones evaluadas y límites F3→F4. |
| `openspec/changes/archive/2026-08-10-f4-scoring-engine/proposal.md` | Scope y contratos intencionales F4. |
| `openspec/changes/archive/2026-08-10-f4-scoring-engine/design.md` | ADRs de layering, transacción, API, auditoría y rollout. |
| `openspec/changes/archive/2026-08-10-f4-scoring-engine/tasks.md` | Slices TDD y rollback boundaries F4. |
| `openspec/changes/archive/2026-08-10-f4-scoring-engine/apply-progress.md` | Evidencia RED→GREEN y caveats del harness. |
| `openspec/changes/archive/2026-08-10-f4-scoring-engine/verify-report.md` | Verificación final F4 y deuda heredada. |
| `openspec/changes/archive/2026-08-10-f4-scoring-engine/archive-report.md` | Promoción final y resumen de decisiones F4. |
| `openspec/changes/archive/2026-08-10-f4-scoring-engine/specs/` | Deltas exactos que explican cómo se promovieron scoring/results/contracts/audit/schema/seed. |
| `openspec/changes/archive/2026-08-10-f5-profiles-recommendation/exploration.md` | Frontera post-F4 y alternativas F5. |
| `openspec/changes/archive/2026-08-10-f5-profiles-recommendation/proposal.md` | Scope F5 y exclusión explícita de F6. |
| `openspec/changes/archive/2026-08-10-f5-profiles-recommendation/design.md` | ADRs de recomendación, transacción, DTO y aislamiento. |
| `openspec/changes/archive/2026-08-10-f5-profiles-recommendation/tasks.md` | Slices y reservas de perfiles F5. |
| `openspec/changes/archive/2026-08-10-f5-profiles-recommendation/apply-progress.md` | Evidencia, remediación de aislamiento y corrección U+2265. |
| `openspec/changes/archive/2026-08-10-f5-profiles-recommendation/verify-report.md` | Autoridad final de tests/contratos F5. |
| `openspec/changes/archive/2026-08-10-f5-profiles-recommendation/archive-report.md` | Handoff explícito a F6 y promoción final. |
| `openspec/changes/archive/2026-08-10-f5-profiles-recommendation/specs/` | Deltas exactos F5 antes de promoción. |
| `README.md` y `ONBOARDING.md` | Operación del entorno; algunos conteos descriptivos son históricos, por lo que código/tests mandan. |
| `HANDOFF-F4.md` | Estilo y deuda histórica; no reutilizar sus conteos/baseline como estado actual. |

## Mapa actual verificado

### Persistencia disponible

**[CONTRATO EXISTENTE VERIFICADO]** Migración
`services/api/alembic/versions/0003_scoring_recommendation_reporting_audit_seed.py`
creó las familias F4–F6. El head actual es `0005_catalog_four_level`; la cadena
es lineal según `test_schema.py::test_linear_history`.

| Tabla / modelo | Garantías actuales exactas | Lo que NO garantiza |
| --- | --- | --- |
| `score_runs` / `ScoreRun` en `services/api/app/models/scoring.py` | PK UUID; `session_id` y `reference_set_id` FKs NOT NULL e indexadas; `status` String(16), default `pending`; `raw` JSONB nullable; `computed_at` nullable; `synthetic`/`source`; múltiples runs por sesión. | No FK desde `reports`; no CHECK de status; no unicidad por sesión. |
| `recommendation_results` / `RecommendationResult` en `services/api/app/models/recommendation.py` | PK UUID; FKs indexadas y NOT NULL a session/rule/program; `fit_score Numeric(5,2)`; `justification` Text; `created_at` server timestamp; runtime rows; múltiples generaciones agrupadas por timestamp. | No entidad `recommendation_generation`; no generation id único para pinning desde un report. |
| `report_templates` / `ReportTemplate` en `services/api/app/models/reporting.py` | `id` PK; `key String(64)` UNIQUE NOT NULL; `name String(255)` NOT NULL; `description` y `template_body` Text nullable; `synthetic` default false; `source` default runtime. | Sin versión, estado, locale, timestamps, inmutabilidad, checksum ni ownership. `template_body` puede editarse en sitio a nivel de schema. |
| `reports` / `Report` en `services/api/app/models/reporting.py` | `id` PK; `session_id` FK NOT NULL + `ix_reports_session_id`; `template_id` FK nullable + `ix_reports_template_id`; `format String(16)` default `pdf`; `status String(16)` default `pending`; `generated_at` nullable; `synthetic` default false; `source` default runtime. | Sin CHECK de format/status; sin source `score_run_id` o generación F5; sin template snapshot/version; sin URI/blob/checksum/size; sin error, created/updated timestamps, audience, retention o delivery state; sin unicidad. |

`test_schema.py::test_f5_f6_empty_but_migrated` comprueba que las cuatro tablas
F5/F6 existen vacías antes del seed. `test_seed.py::test_f5_f6_seed_state_after_seed`
comprueba el estado posterior: `recommendation_rules > 0`, mientras
`recommendation_results`, `reports` y `report_templates` permanecen en cero.
No existe un test dedicado a comportamiento de `Report` o `ReportTemplate`.

### APIs y DTOs que F6 puede consumir

| Superficie | Contrato actual |
| --- | --- |
| `POST /api/v1/results/{session_id}/score` | Mutación idempotente `session:{id}`; crea un nuevo run completado desde una sesión completada. |
| `GET /api/v1/results/{session_id}` | Devuelve el run completado más reciente por `computed_at DESC`, tie-break id DESC. |
| `ResultsResponse` | `session_id`, `run{id,status='completed',computed_at}`, `reference_set_id`, `norm_note`, `scales[]` con raw/z/percentile/T/eneatype y `overall`. |
| `POST /api/v1/recommendations/{session_id}/generate` | Mutación idempotente `session:{id}`; requiere score completado y persiste filas por regla. |
| `GET /api/v1/recommendations/{session_id}` | Devuelve la generación más reciente: anchor `created_at DESC`, id DESC; agrupa filas con el mismo `created_at`. |
| `RecommendationsResponse` | Exactamente `session_id`, `generated_at`, disclaimer e `items[{program_id,program_name,program_code,fit_score,justification}]`. |

Archivos: `services/api/app/api/routes/results.py`,
`services/api/app/schemas/results.py`,
`services/api/app/api/routes/recommendations.py` y
`services/api/app/schemas/recommendations.py`.

**No existe** `reports` router, schema, service, repository, dominio, PDF renderer,
storage adapter, outbox, worker ni cliente de integración. `services/api/app/api/router.py`
registra resultados y recomendaciones, pero ninguna ruta F6.

### Servicios, repositorios y dirección existente

| Módulo | Símbolos útiles | Boundary |
| --- | --- | --- |
| `services/api/app/modules/scoring/domain.py` | `score`, dataclasses frozen y transformaciones puras. | F6 consume resultados; no recalcula ni modifica scoring. |
| `services/api/app/modules/scoring/repository.py` | `ScoringRepository`, `latest_completed_run`, lecturas de contexto y runs. | DB adapter; la función de scoring permanece fuera. |
| `services/api/app/modules/scoring/service.py` | `ScoringService.score_session`, `latest_result`. | Ownership, idempotencia, auditoría y transacción F4. |
| `services/api/app/modules/recommendation/domain.py` | `evaluate_recommendations` y snapshots puros. | F6 consume resultados; no reevalúa reglas. |
| `services/api/app/modules/recommendation/repository.py` | `RecommendationRepository`, `latest_generation_anchor`, `list_generation_rows`, `latest_generation`. | Agrupa una generación mediante timestamp compartido. |
| `services/api/app/modules/recommendation/service.py` | `RecommendationService.generate_recommendations`, `latest_recommendations`. | Ownership, idempotencia, auditoría y transacción F5. |

**[DECISIÓN ABIERTA PARA SDD]** F6 debe decidir si fija las fuentes por IDs/anchor
en el momento de generar o si siempre proyecta “latest”. Para auditoría y
regeneración reproducible se recomienda pinning explícito, pero el schema actual
no puede expresarlo completamente.

### Permisos, ownership y errores

**[CONTRATO EXISTENTE VERIFICADO]** `services/api/app/core/permissions.py`
mantiene deny-by-default mediante `require_roles(...)`. Capacidades relevantes:

| Capacidad actual | admin | psicólogo | evaluado |
| --- | --- | --- | --- |
| `view_results` | Sí | Sí | Sí, sesión propia |
| `view_recommendations` | Sí | Sí | Sí, sesión propia |
| `view_audit` | Sí | No | No |

No existe capacidad de reports. F4/F5 permiten operación transversal a admin y
psicólogo y exigen ownership a evaluado en el service. F6 no puede extrapolar esa
matriz sin ratificarla.

Todos los errores usan:

```json
{"error":{"code":"<CODE>","message":"<token>","request_id":"<uuid4>","details":{}}}
```

Códigos permitidos: `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`,
`CONFLICT`, `INTERNAL_ERROR`. Tokens F4/F5 reutilizables solo cuando su semántica
coincide: `resource_not_found`, `session_not_completed`,
`idempotency_key_required`, `idempotency_key_reused`. Nuevos tokens F6 requieren
spec y tests; no se añaden de forma informal.

### Auditoría actual

**[CONTRATO EXISTENTE VERIFICADO]** `audit_log` es append-only por trigger. El
catálogo de `services/api/app/core/audit.py::EVENT_CATALOG` termina en
`scoring.run` y `recommendation.generated`; no existe evento F6. La deny-list
rechaza respuestas, answers, tokens, passwords, secretos, contenido de ítems,
email y PII. Los eventos F4/F5 contienen ids/conteos/timestamps, nunca scores,
fit ni justificaciones.

Catálogo exacto actual:

```text
auth.login, auth.denied, user.role_changed,
instrument.draft_created, instrument.draft_updated, instrument.published,
instrument.archived, consent.granted, consent.revoked, session.started,
session.completed, session.blocked_without_consent, seed.executed,
scoring.run, recommendation.generated
```

`test_auth.py::test_capability_matrix_matches_contract` y
`test_audit.py::test_event_catalog_matches_contract` exigen lockstep entre código,
contracts y tests. Cualquier capacidad o evento F6 debe cambiar en la misma
unidad:

- `services/api/app/core/permissions.py`;
- `services/api/app/core/audit.py`;
- `packages/contracts/README.md`;
- deltas OpenSpec correspondientes;
- `services/api/tests/test_auth.py` y `services/api/tests/test_audit.py`.

La spec canónica también exige timeout/buffer/retry y una política fail-open o
fail-closed para caída del audit store. El writer actual es una escritura directa
con commit opcional y no contiene buffer/retry. Es deuda heredada; F6 no debe
inventar una política local que contradiga esa spec.

### Seed, reset y fixtures

**[CONTRATO EXISTENTE VERIFICADO]** `services/api/app/seed/loader.py` usa
`SEED_VERSION = "1.1.0"`, UUID5, seed idempotente y reset atómico. El seed crea:

- `TP-S-01:v1`, 5 escalas, 20 ítems y 100 opciones;
- `RS-TP-S-01`, 30 reference rows y `norm_note` research-only;
- 30 perfiles `evaluado_01..30`, cada uno con consentimiento, sesión completada y 20 respuestas;
- cinco programas sintéticos y diez reglas F5 según el archive report final;
- cero `score_runs`, cero `recommendation_results`, cero `reports` y cero `report_templates` sembrados.

`score_runs`, `reports` y `report_templates` **no están** en `SEED_TABLES` ni en
`collect_counts`. El preflight de reset cubre runtime dependencies para catálogo,
sesiones, referencias y recomendaciones, pero no consulta `score_runs` ni
`reports`. Esto es una trampa real: un runtime report o run que apunte a una sesión
o referencia seed puede hacer fallar el delete por FK sin producir el error
estable anticipado. Si F6 genera reportes sobre perfiles seed o siembra templates,
proposal/spec/design deben ratificar el ownership y extender preflight/manifest/reset
con tests antes de asumir que `--reset` sigue siendo seguro.

Los 30 perfiles existen, pero no son un pool libre compartido:

| Tests | Reserva/uso actual |
| --- | --- |
| F4 repository/service | `evaluado_19`, `evaluado_20` |
| F5 API | `evaluado_21..26` |
| F5 repository | `evaluado_27..28` |
| F5 service | `evaluado_29..30` |

`seeded_db_session` es session-scoped. F6 debe crear runtime fixtures propias o
asignar perfiles realmente disjuntos después de auditar toda la suite; además
debe usar conteos before/after, no totales absolutos globales.

### Frontend e integración

**[CONTRATO EXISTENTE VERIFICADO]** `apps/web` usa Next.js 14 / React 18 y tiene
login, catálogo y evaluación. No hay página, cliente API ni componente de
resultados, recomendaciones, informes, descargas o integración. La pantalla de
sesión completada declara que esa etapa no muestra puntuaciones ni resultados.

No hay librería PDF en `services/api/pyproject.toml`, tampoco package de Redis en
Python, object storage, outbox o worker. Redis existe en Compose y Settings, pero
no es una implementación de delivery. No se debe elegir un vendor o renderer por
el solo hecho de que Redis esté levantado.

## Objetivo de producto y flujo F6

### Frontera de producto

| Estado | Regla |
| --- | --- |
| **[CONTRATO EXISTENTE VERIFICADO]** | Una sesión solo puede aportar scoring/recomendación después de completar sus workflows F4/F5. Las APIs actuales preservan ownership y no-leak. |
| **[BASE F6 PROPUESTA]** | Un actor autorizado solicita un informe para una sesión; F6 fija fuentes y template, compone un documento puro, persiste el intento, renderiza, almacena y expone/entrega el resultado sin recomputar scoring ni recomendaciones. |
| **[DECISIÓN ABIERTA PARA SDD]** | Quién puede solicitar, ver, descargar o recibir; si evaluado accede; si admin/psicólogo operan cualquier sesión; si existe UI. |

### Flujo end-to-end propuesto

1. **Autorización y ownership.** Validar rol/capacidad y dueño antes de revelar si
   hay fuentes, template o report.
2. **Idempotencia.** Validar `Idempotency-Key` para cualquier trigger mutante. La
   key representa un único intento de producto; scope y replay deben ratificarse.
3. **Precondiciones.** Cargar una sesión completada, un score run completado y una
   generación F5 completa. **No disparar F4/F5 en secreto**; si faltan, devolver el
   error ratificado sin crear report, PDF, auditoría de éxito ni delivery.
4. **Pinning.** Fijar la identidad exacta del score run, generación F5 y template
   version/snapshot usados. No consultar “latest” nuevamente a mitad del flujo.
5. **Composición pura.** Crear un `ReportDocument` determinista con secciones,
   datos permitidos, disclaimers y redacciones ya decididas. Sin DB, reloj, red,
   filesystem, renderer, vendor ni LLM.
6. **Persistencia de intención.** Crear/actualizar la fila report y el registro de
   idempotencia según la state machine ratificada.
7. **Render PDF.** Pasar el documento al renderer adapter. Fuentes, locale,
   metadata y timestamps deben estar controlados para reproducibilidad.
8. **Storage.** Guardar el artefacto mediante un adapter; persistir identificador,
   checksum, tamaño y metadata solo si la spec lo exige. No exponer paths internos.
9. **Finalización y auditoría.** Cambiar al estado terminal correspondiente y
   escribir un evento aggregate-only. Fallos no deben dejar un report “ready” sin
   artefacto ni duplicar eventos en replay.
10. **Descarga/entrega.** Autorizar nuevamente cada lectura/descarga. Si hay
    integración, publicar un intento desacoplado y reintentable; nunca mantener una
    transacción DB abierta durante I/O remoto.

### Seguridad y errores

**[BASE F6 PROPUESTA]**

- El report no debe contener option ids/values, response ids, el mapping 1–5,
  item content, tokens, secretos ni PII fuera de lo expresamente ratificado.
- El `norm_note` F4 y el disclaimer F5 tienen contratos distintos. SDD debe decidir
  cuáles aparecen y de qué forma; no sustituir uno por otro.
- Templates deben tratarse como datos, no como código: sin evaluación arbitraria,
  imports, shell, acceso a filesystem o red.
- Descarga y delivery deben aplicar la misma o una política más estricta que la
  lectura de metadata; una URL por sí sola no concede acceso.
- Missing/foreign/not-ready deben evitar existence leaks según la matriz ratificada.
- Fallos del renderer, storage, audit o integración no deben degradarse a éxito.
- Logs y audit metadata deben contener ids, estado, conteos, checksum/tamaño si se
  ratifica; nunca el cuerpo del report, scores, justificaciones o payload PDF.

## Scope y no-goals

### Dentro de una base F6 razonable

- Composición determinista de reportes desde outputs F4/F5 ya persistidos.
- Persistencia trazable del report y del template/version/snapshot utilizado.
- Renderer PDF detrás de una abstracción.
- Lectura/descarga autorizada y, si se ratifica, delivery por adapter.
- Idempotencia, auditoría, rollback y retry sin duplicados.
- Specs, tests y documentación de los contratos nuevos/modificados.

### Fuera de scope salvo delta explícito ratificado

- Modificar instrumentos publicados, sesiones, scoring o recomendación.
- Recalcular o reinterpretar F4/F5 dentro de reporting.
- Cambiar fórmulas, reglas, DTOs o no-leak boundaries F2/F3/F4/F5.
- Datos reales, normas psicométricas reales o afirmaciones UAGRM reales.
- LLM en composición, explicación, scoring, recomendación o template.
- Mostrar scores/recomendaciones ocultos a una audiencia no autorizada.
- Corregir los tests web heredados dentro de F6.
- Integrar prematuramente un vendor, correo, SIS/LMS, object storage o firma digital
  sin target, credenciales, delivery guarantee y retención ratificados.
- Sembrar reports runtime. Templates seed solo si la spec asigna ownership y reset.

## Arquitectura sugerida

Todo este apartado es **[BASE F6 PROPUESTA]**, no contrato vigente.

### Layering y seams

```text
HTTP route / future UI
        |
        v
reporting service  -----> authorization + idempotency + state orchestration
        |
        +-----> reporting repository -----> PostgreSQL
        |
        +-----> pure report composer -----> ReportDocument snapshot
        |
        +-----> PDF renderer adapter ------> bytes/stream + metadata
        |
        +-----> storage adapter -----------> artifact reference
        |
        `-----> integration adapter/outbox -> external target, only if ratified
```

| Seam propuesto | Responsabilidad | Dependencias prohibidas |
| --- | --- | --- |
| `services/api/app/modules/reporting/domain.py` | Inputs frozen, policy de secciones ya ratificada, composición `ReportInput → ReportDocument`. | SQLAlchemy, FastAPI, filesystem, renderer, clock, network, LLM. |
| `services/api/app/modules/reporting/errors.py` | Factories de errores mapeados; nombres solo después de spec. | Reglas de negocio o I/O. |
| `services/api/app/modules/reporting/repository.py` | Cargar sesión/fuentes/template; pinning; crear/transicionar reports; caller owns commit/rollback. | Render PDF o llamadas externas. |
| `services/api/app/modules/reporting/service.py` | Ownership, idempotencia, orquestación, auditoría y límites transaccionales. | Lógica de layout o reglas F4/F5 duplicadas. |
| `services/api/app/modules/reporting/pdf_renderer.py` | Interface/adapter de `ReportDocument` a PDF; metadata y fuentes controladas. | Queries DB, autorización, delivery. |
| `services/api/app/modules/reporting/storage.py` | Guardar/abrir/borrar artefacto por referencia opaca. | Composición, ownership. |
| `services/api/app/modules/reporting/integration.py` | Traducir un delivery command al target ratificado. Solo crear si F6 incluye integración real. | Transacciones largas o lectura libre de tablas. |
| `services/api/app/schemas/reports.py` y `services/api/app/api/routes/reports.py` | DTOs estrictos y adapters HTTP finos, si la API se ratifica. | Reglas, queries o vendor SDK directo. |

Los nombres anteriores son forecast de archivos, no tokens públicos ratificados.
Specs y design pueden ajustarlos manteniendo la dirección de dependencias.

### Boundary transaccional y fallos

1. La transacción DB debe fijar fuentes, template, estado e idempotencia de forma
   coherente. El repository no hace commits ocultos.
2. Renderer, storage y vendor son I/O potencialmente lento: no mantener row locks o
   una transacción DB abierta durante esas llamadas.
3. Si el flujo es staged, una primera transacción reclama el intento; el renderer
   y storage trabajan fuera; una segunda transacción finaliza y audita.
4. Si el artefacto se guarda pero falla la finalización DB, registrar/limpiar el
   orphan de forma idempotente; no marcar éxito por compensación implícita.
5. Si falla auditoría y la operación es fail-closed, report + idempotencia + outbox
   deben quedar coherentes con el fallo; la política debe derivar de la spec.
6. Delivery externo debe ocurrir desde un outbox/worker solo si se necesita
   garantía asíncrona. No crear outbox si la integración queda fuera de F6.
7. Reintentos deben converger en el mismo report/artefacto/evento para la misma
   key; una regeneración intencional necesita una nueva identidad según spec.

## Checklist de diseño contractual para el change F6

No pasar a tasks hasta que spec/design contesten cada punto.

### API y DTO

- [ ] Definir método y path de trigger; no asumir `/reports` por analogía.
- [ ] Definir lectura de metadata, listado, descarga y regeneración por separado.
- [ ] Definir si template se selecciona por key, id o versión y quién puede hacerlo.
- [ ] Definir request exacto y política `extra="forbid"`.
- [ ] Definir response exacto: ids, status, timestamps, links, errores y campos
      omitidos; no devolver path interno ni payload del vendor.
- [ ] Definir si un GET puede generar/almacenar; la base recomendada es que no tenga
      efectos laterales ocultos.

### State machine y concurrencia

- [ ] Ratificar vocabulario y transiciones; `pending` actual no ratifica estados
      adicionales. Preguntar si se necesitan processing/ready/failed/delivered.
- [ ] Definir estados terminales y si retry revive una fila o crea un intento nuevo.
- [ ] Definir concurrencia: dos keys, misma sesión/template, generación simultánea.
- [ ] Definir qué ve el cliente durante render/entrega y cómo hace polling.
- [ ] Añadir CHECKs solo después de fijar el vocabulario.

### Idempotencia

- [ ] Definir `operation` y `resource_scope`: ¿sesión, report, template version,
      audiencia o target forman parte del intent?
- [ ] Mismo key + mismo body debe replayar la misma respuesta sin duplicar fila,
      PDF, audit event ni delivery.
- [ ] Mismo key + body materialmente distinto debe usar `CONFLICT` y el token
      ratificado; no asumir que todos los campos son materiales.
- [ ] Definir semántica de nueva key: ¿regenera versión, reemplaza latest o crea
      report independiente?
- [ ] Definir replay después de fallo parcial y después de expiración/retención.

### Autorización y ownership

- [ ] Matriz separada para generate/list/read/download/deliver/manage-template.
- [ ] Definir audiencia del informe y dueño de la sesión/report.
- [ ] Definir alcance transversal de admin y psicólogo.
- [ ] Definir si evaluado ve PDF completo, redactado o nada.
- [ ] Ratificar nueva capacidad, si existe, en permissions/contracts/tests lockstep.
- [ ] Auditar `auth.denied` sin existence leak y sin metadata sensible.

### Auditoría y errores

- [ ] Ratificar eventos nuevos y metadata exacta aggregate-only en
      `audit-consent`, `EVENT_CATALOG`, contracts y tests simultáneamente.
- [ ] Decidir si se audita requested/generated/downloaded/delivery; no crear un
      evento por cada paso sin valor de auditoría.
- [ ] Definir fail-open/fail-closed para cada operación frente a caída de audit.
- [ ] Mapear missing prerequisites, invalid template, render failure, storage
      failure y delivery failure al envelope existente sin stack traces.
- [ ] No incluir body, scores, justificaciones, PDF bytes, tokens o URLs firmadas
      en audit/log metadata.

### Template e inmutabilidad

- [ ] Definir lifecycle: draft/published/retired u otro vocabulario ratificado.
- [ ] Definir versionado inmutable o snapshot por report. La `key` UNIQUE actual no
      evita edición de `template_body`.
- [ ] Decidir cómo se preserva render reproducible si cambia nombre/body/locale.
- [ ] Definir validación y sandbox de placeholders; unknown/missing placeholders.
- [ ] Definir ownership seed/runtime y reglas de reset.

### PDF, contenido y no-leak

- [ ] Elegir renderer con evaluación actual de compatibilidad/licencia/imagen.
- [ ] Fijar versión de dependencia, fuentes, embedding, timezone, locale, page size,
      metadata y clock inyectable.
- [ ] Definir contenido exacto, orden, labels, disclaimers y redacciones por audiencia.
- [ ] Decidir si se incluyen raw/z/T/eneatype/percentiles, fit y justificación.
- [ ] Mantener fuera option values/ids, responses, items, mapping 1–5 y secretos.
- [ ] Definir criterio de determinismo: documento lógico idéntico y PDF normalizado;
      no exigir bytes idénticos si el renderer introduce metadata variable.
- [ ] Definir accesibilidad del PDF y locale español si el PDF entra en MVP.

### Storage e integración

- [ ] Elegir storage backend, key scheme opaco, checksum, encryption, retención,
      borrado y autorización de descarga.
- [ ] Definir si descarga es stream autenticado o URL temporal y su expiración.
- [ ] Nombrar el target de integración; “integración” sin target no es scope.
- [ ] Definir sync/async, timeouts, retry/backoff, máximo de intentos y dead-letter.
- [ ] Definir delivery guarantee: at-most-once, at-least-once o exactamente-una-vez
      efectiva mediante idempotencia del receptor.
- [ ] Definir dedupe key/correlation id y qué información puede salir del sistema.
- [ ] Añadir outbox solo si esas garantías lo requieren.

## Checklist de datos y schema

### Lo que garantiza el schema actual

- [x] Hay una fila report por UUID con FK obligatoria a session.
- [x] Template es opcional y su key es única.
- [x] `format` y `status` tienen defaults de aplicación/migración.
- [x] Session/template tienen índices individuales.
- [x] Todas las filas poseen `synthetic`/`source`.

### Lo ausente que SDD debe evaluar

- [ ] Pin a `score_runs.id`.
- [ ] Pin inequívoco a una generación F5; hoy solo existe un grupo por timestamp.
- [ ] Template version/snapshot inmutable.
- [ ] CHECK de status y format.
- [ ] Timestamps created/updated/failed/completed según lifecycle.
- [ ] Artifact reference, checksum, media type, byte size y renderer version.
- [ ] Error/retry fields sin guardar stack traces.
- [ ] Audiencia/owner/locale/retention si el producto los necesita.
- [ ] Delivery/outbox data si integración entra en scope.
- [ ] Índices compuestos para queries ratificadas; no optimizar queries imaginarias.

### Implicaciones de migración

**[CONTRATO EXISTENTE VERIFICADO]** Las tablas existentes alcanzan solo para una
fila mínima `session/template/format/status/generated_at`. No alcanzan para
reproducibilidad, storage o delivery trazable.

**[DECISIÓN ABIERTA PARA SDD]** No declarar “sin migración” antes del design. Si
se ratifican pins, versionado, estados, storage u outbox, hace falta una migración
lineal posterior a `0005_catalog_four_level`, con modelos y migration/schema tests
en lockstep. Candidatos a evaluar, no decisiones:

- FKs a fuente F4 y representación estable de generación F5;
- UNIQUE/CHECK para template version y status/format;
- índices por session/status/generated timestamp según queries reales;
- checksum o artifact key UNIQUE si el backend lo requiere;
- outbox con dedupe key si delivery es at-least-once.

Una migración aplicada con runtime data no debe revertirse destructivamente; el
rollback operativo deshabilita rutas/workers y usa una corrección forward o un
snapshot restaurable según design.

### Seed y runtime

- Runtime reports deben ser UUID4, `synthetic=False`, `source='runtime'`.
- Reports no se siembran.
- Si se siembran templates sintéticos, deben ser UUID5, research-only y pertenecer
  a `SEED_TABLES`, manifest, checksum, reset y preflight.
- Un runtime report que referencia sesión/template seed exige preflight de reset.
- No borrar runtime artifacts durante `--reset`; definir cleanup separado y seguro.

## Estrategia de testing: strict TDD

`openspec/config.yaml` ratifica `strict_tdd: true`. Cada slice empieza RED,
alcanza GREEN, triangula casos y refactoriza sin mezclar capas.

### Comandos Windows/PowerShell

Bootstrap y stack:

```powershell
docker compose up -d --build
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.seed
```

Slice actual de regresión F4/F5:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test.ps1 -k "scoring or reference or results or recommendation or program"
```

Después de crear tests F6, selector sugerido:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test.ps1 -k "report or template or pdf or integration"
```

Runner local barato para dominio, si el archivo ya existe:

```powershell
& ".\services\api\.venv\Scripts\python.exe" -m pytest services/api/tests/test_reporting_domain.py
```

Runner Compose con exit code directo de pytest:

```powershell
docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_reporting_domain.py
docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests/test_reporting_repository.py tests/test_reporting_service.py tests/test_reports_api.py
```

Suite completa, dos veces:

```powershell
docker compose build api
docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests
docker compose run --rm --workdir /repo/services/api -v "${PWD}:/repo:ro" api pytest tests
```

Si F6 toca web:

```powershell
npm --prefix apps/web install
npm --prefix apps/web run build
```

### Orden cheapest-first

1. **Pure domain RED→GREEN.** Documento lógico, secciones, orden, redacciones,
   disclaimers, source pins, determinismo e input immutability; milisegundos, sin DB.
2. **Template/parser unit.** Placeholders permitidos, unknown/missing, escaping y
   rechazo de ejecución arbitraria.
3. **Repository + PostgreSQL.** FKs, constraints, state transitions, pins,
   concurrencia, rollback y runtime flags.
4. **Service integration.** Ownership, prerequisites, idempotencia, audit failure,
   renderer/storage failure y replays.
5. **API/TestClient.** DTO exacto, envelope, roles, no-leak, download authorization,
   missing/not-ready/foreign indistinguibles según spec.
6. **PDF.** Parsear estructura, páginas, texto permitido, fonts/metadata y checksum
   normalizado. Evitar comparar bytes completos salvo que se elimine/normalice toda
   metadata variable.
7. **Storage/integration.** Timeout, retry, dedupe, outbox, poison messages,
   recovery y rollback/cleanup de orphan.
8. **Web solo si entra en scope.** Estados loading/error/empty/ready, roles,
   accesibilidad y descarga; build no sustituye browser E2E inexistente.
9. **Regresiones y suite completa ×2.** Citar summary de pytest, no solo exit code.

### Matriz mínima de pruebas F6

| Riesgo | Prueba necesaria |
| --- | --- |
| Reinterpretar F4/F5 | Composer consume snapshots persistidos y no importa/invoca engines para recalcular. |
| Fuente cambiante | Report conserva pins; un run/generation nuevo no altera report histórico. |
| Template mutable | Report histórico conserva version/snapshot aunque cambie el template activo. |
| Doble generación | Same key replaya; distinto body conflictúa; nueva key sigue semántica ratificada. |
| Fuga | Scan recursivo de DTO, PDF text/metadata, audit y logs contra responses/items/options/secrets. |
| Ownership | Evaluado foreign, admin/psicólogo y cada operación de download/delivery. |
| Renderer/storage failure | No estado ready, no audit success duplicado, retry converge, orphan controlado. |
| Integración | Timeout/retry/dedupe/delivery guarantee y payload redacted. |
| Seed reset | Runtime report/run sobre seed provoca preflight estable y cero deletes; templates seed se recrean sin tocar runtime. |
| Determinismo PDF | Mismo `ReportDocument` produce estructura/texto/metadata normalizados equivalentes. |

## Plan de implementación revisable

Es un forecast, no trabajo realizado. `sdd-tasks` debe recalcularlo con los specs
ratificados y declarar el riesgo frente al presupuesto de revisión elegido en el
preflight. Si lo supera, aplicar la estrategia de entrega seleccionada; no prometer
conteos arbitrarios.

| Unidad | Dependencias | Archivos esperados | Foco RED→GREEN | Commit convencional recomendado | Rollback y gate de aceptación |
| --- | --- | --- | --- | --- | --- |
| 0. Ratificación SDD | Preguntas de producto resueltas | `openspec/changes/<f6-change>/proposal.md`, specs, `design.md`, `tasks.md` | Scenarios Given/When/Then y ADRs antes de código | Sin commit de implementación | Gate: endpoints, matriz, content, state, PDF, storage e integración sin placeholders abiertos. |
| 1. Dominio puro | Unidad 0 | Nuevos `modules/reporting/domain.py`, `errors.py`, `test_reporting_domain.py` | Composición determinista, pins, redacción, pureza | `feat(api): add pure report composition domain` | Eliminar módulo/test. Gate: unit suite green sin DB/I/O/clock. |
| 2. Schema y repository | 1 + data design | `models/reporting.py`, nueva migración si procede, `repository.py`, schema/repository tests | Constraints, source pins, template version, states, runtime flags, rollback, reset preflight | `feat(db): persist traceable report generations` | Antes de aplicar: revert migration; después: disable + forward fix. Gate: fresh/head/idempotent migration y PG tests. |
| 3. Renderer y storage seams | 1; stack elegido | `pdf_renderer.py`, `storage.py`, dependencia ratificada, tests PDF/storage | Estructura, normalización, metadata, failures, cleanup | `feat(api): add deterministic PDF rendering adapter` | Remover adapter/dependency sin tocar DB. Gate: renderer contract green y sin paths secretos. |
| 4. Service + lockstep | 2–3 | `service.py`, permissions/audit/contracts y tests lockstep | Ownership, prerequisites, idempotencia, transaction stages, failure isolation | `feat(api): orchestrate report generation and ratify access` | Revert service/ratificaciones juntas. Gate: audit/auth/idempotency/failure suites green. |
| 5. API | 4 | `schemas/reports.py`, `api/routes/reports.py`, `api/router.py`, `test_reports_api.py` | DTO exacto, trigger/read/download, envelope/no-leak | `feat(api): expose the ratified reports API` | Remover rutas/schemas y registro. Gate: TestClient + PG green. |
| 6. Integración | 4–5 y target ratificado | `integration.py`, posible outbox/worker/migration, tests retry | Dedupe, retry, timeout, delivery guarantee, redacción | `feat(api): deliver reports through the ratified integration` | Deshabilitar worker/adapter, conservar outbox. Gate: recovery/failure tests y no doble entrega efectiva. |
| 7. Web opcional | API estable y scope ratificado | Rutas/componentes/lib/tests bajo `apps/web` | Estados UX, roles, descarga, accesibilidad | `feat(web): add the report workflow` | Remover navegación/superficie sin tocar API. Gate: tests disponibles + `next build` + checklist manual. |
| 8. Verify/archive | Todas | `apply-progress.md`, `verify-report.md`, archive/promotion | Slice, boundaries, full ×2, diff, spec trace | Commit docs solo si se solicita | Gate: verify válido, cero blockers F6, promoción mecánica y no active change. |

Cada PR/slice debe empezar y terminar en un estado autónomo, incluir sus tests y
tener rollback claro. No separar tests del comportamiento que protegen.

## Definition of Done

### Antes de apply

- [ ] Preflight e init guard resueltos con elecciones reales del owner.
- [ ] Proposal aprobada y preguntas de producto cerradas.
- [ ] Specs/design ratifican API, estados, datos, audiencia, content, PDF, storage,
      idempotencia, auditoría, integración y rollback.
- [ ] Tasks contienen forecast frente al presupuesto configurado y estrategia de entrega resuelta.
- [ ] No se modifican contratos F2/F3/F4/F5 salvo delta explícito.

### Implementación y verificación

- [ ] Strict TDD RED→GREEN documentado por unidad.
- [ ] Composer puro sin DB/I/O/clock/random/LLM.
- [ ] Report pinnea fuentes y template/version/snapshot exactos.
- [ ] Migración y modelos coinciden; fresh upgrade, head repetido y linear history pasan.
- [ ] Idempotencia no duplica report, PDF, audit ni delivery.
- [ ] Auth/ownership y event catalog están en lockstep.
- [ ] PDF, DTO, audit, logs e integración cumplen no-leak.
- [ ] Fallos renderer/storage/audit/integration tienen recuperación y rollback probado.
- [ ] Seed/reset separa seed-owned de runtime y preflights F6/F4 dependencies.
- [ ] Suite F6 y boundaries F3/F4/F5 pasan.
- [ ] Suite completa corre dos veces con summaries idénticos; solo deuda heredada
      previamente documentada puede permanecer, sin fallos F6 nuevos.
- [ ] `git diff --check` limpio y diff limitado al change ratificado.

### Verify y archive

- [ ] `verify-report.md` cubre todas las requirements/scenarios y pasa la admisión
      del flujo SDD antes de persistirse.
- [ ] Cero blockers/critical findings F6; deuda heredada separada.
- [ ] Deltas se promueven mecánicamente a `openspec/specs/` sin perder requisitos.
- [ ] `tasks.md` queda completamente reconciliado.
- [ ] El change se mueve a `openspec/changes/archive/`.
- [ ] `gentle-ai sdd-status --cwd <repo>` vuelve a indicar sin change activo.
- [ ] No se toca `usuarios.md`; no hay commit/push salvo solicitud expresa.

## Matriz de trazabilidad propuesta

| Capacidad F6 propuesta | Evidencia de origen | Artifact SDD requerido | Tests esperados | Gate final |
| --- | --- | --- | --- | --- |
| Composición desde F4/F5 | Specs `results-api`, `recommendation-api`; archive reports F4/F5 | Nueva capability con input/output/no-leak | `test_reporting_domain.py` | Sources pinned; no recompute. |
| Persistencia/versionado | `data-schema` + modelo reporting actual | Delta `data-schema` y design ADR | migration/schema/repository tests | Historia reproducible y constraints reales. |
| Templates | `ReportTemplate` scaffolding, sin lifecycle | Capability/requirements de template | domain/repository/template tests | Inmutabilidad o snapshot probado. |
| Trigger/read/download | Envelope, idempotencia y patterns F4/F5 | Capability API + delta `contracts` | `test_reports_api.py` | DTO, errors, replay y ownership exactos. |
| Auditoría | `audit-consent`, append-only, deny-list | Delta `audit-consent` | `test_audit.py`, service/API | Lockstep y metadata aggregate-only. |
| PDF | Solo `format='pdf'` como scaffolding | Requirements + renderer ADR | PDF structure/normalized determinism | Artefacto válido, estable y sin fuga. |
| Storage/retención | Ausente | Requirements/ADR si entra en scope | storage integration/failure tests | Acceso, cleanup y retention ratificados. |
| Integración/delivery | Handoff F5 nombra integración, sin target | Capability/ADR solo tras elegir target | retry/dedupe/outbox tests | Garantía de entrega demostrada. |
| Web opcional | No hay UI F4/F5/F6 | Delta web solo si producto lo aprueba | component/build/manual; E2E si se añade | Accesible, responsive y role-safe. |

Los nombres concretos de capabilities y test files deben cerrarse en proposal/tasks;
los anteriores describen la cobertura, no un contrato público ya existente.

## Deuda heredada y trampas

| Tema | Estado verificado 2026-08-11 | Tratamiento F6 |
| --- | --- | --- |
| Dos fallos web F2b | Ejecutado en esta tarea: `test_page_is_spanish` y `test_page_never_leaks_stack_trace` siguen fallando; 2 failed, 217 deselected. | Deuda heredada, no blocker F6 ni permiso para tocar web. Si UI F6 entra, mantenerlos separados. |
| `scripts/test.ps1` | Invoca Docker/pytest pero no `exit $LASTEXITCODE`; el comando anterior terminó con wrapper-success pese a dos failures. | Citar summary de pytest o usar direct Compose command. No confiar en exit del wrapper. |
| Imagen/mount Docker | Dockerfile copia API a `/app`; scripts montan repo read-only en `/repo`. App/Alembic no montados pueden usar imagen vieja. | `docker compose build api` tras dependencias/migraciones/código y antes de evidencia final. |
| Cache read-only | Pytest advierte que no puede escribir `.pytest_cache` en `/repo`. | Warning conocido; no confundir con fallo funcional. |
| E2E/browser | `openspec/config.yaml`: no disponible. | No afirmar cobertura E2E. Si web entra, decidir si se añade runner. |
| Coverage | Sin herramienta ni comando; threshold 0. | No inventar porcentaje. Añadir solo mediante change ratificado. |
| Linter/formatter | No configurados. | No declarar lint green. |
| Typecheck API | Pyright configurado en `services/api/pyproject.toml`; Python local existe, binary pyright no. | Verificar disponibilidad en la sesión; no tratar ausencia como pass. |
| Typecheck web | `next build`; no script lint/test en `apps/web/package.json`. | Ejecutar solo si web cambia; build no reemplaza tests de interacción. |
| Aislamiento F5 | Session-scoped DB; API 21–26, repository 27–28, service 29–30. | Runtime fixtures propias + deltas; no reutilizar perfiles silenciosamente. |
| Reset dependencies | Preflight omite `score_runs` y `reports`; reporting tampoco pertenece a SEED_TABLES. | Ratificar y probar la ampliación antes de reports sobre sesiones seed/templates seed. |
| Auditoría resiliente | Spec exige buffer/retry/policy; writer actual es directo. | Resolver como deuda/decisión transversal; no inventar política F6 aislada. |
| ONBOARDING histórico | Describe cadena/conteos F1 anteriores al head actual. | Usar migraciones/tests actuales; no copiar conteos viejos. |
| Frontend F6 | No existe reports/results/recommendations UI. | Tratar web como decisión de scope, no como trabajo implícito. |

## Preguntas obligatorias para proposal/spec/design

Estas preguntas deben responderse; no son sugerencias opcionales.

1. **Audiencia y ownership:** ¿el informe es para evaluado, psicólogo, admin,
   institución u otra audiencia? ¿Quién puede generar, listar, leer, descargar y
   entregar, y sobre qué sesiones?
2. **Trigger y precondiciones:** ¿la generación es manual, automática al completar
   F5 o batch? Si falta score o recomendación, ¿falla sin efectos o se permite
   disparar explícitamente dependencias?
3. **Lifecycle del template:** ¿quién crea/publica/retira templates? ¿son
   versionados e inmutables, o cada report guarda snapshot? ¿hay template default?
4. **Contenido y redacción:** ¿qué campos F4/F5 aparecen por audiencia? ¿se incluyen
   raw/z/T/eneatype/percentiles, fit, justificación, ambos disclaimers y datos de
   identidad? ¿qué se redacta?
5. **PDF stack:** ¿qué renderer cumple licencia, fuentes, Unicode, imagen Docker,
   accesibilidad y determinismo? ¿HTML→PDF, composición directa u otra opción?
6. **Storage, retención y descarga:** ¿DB, filesystem dev, object storage u otro?
   ¿retención, borrado, cifrado, checksum, URL temporal o stream autenticado?
7. **Target de integración:** ¿qué sistema concreto recibe el informe y qué datos
   acepta? ¿sync/async, autenticación, timeout y delivery guarantee?
8. **Regeneración/versionado:** ¿una nueva key crea una versión histórica, reemplaza
   latest o solo reintenta? ¿qué pasa si cambia score, recomendación o template?
9. **Locale y accesibilidad:** ¿solo `es`, timezone/fecha institucional, PDFs
   etiquetados, orden de lectura, contraste y fuentes embebidas?
10. **Alcance frontend:** ¿F6 incluye UI de generar/listar/descargar/estado o es
    API-only? Si incluye UI, ¿qué rol y journeys se entregan en el MVP?

## Prompt de lanzamiento para el agente implementador

Copiar este bloque en una sesión nueva y reemplazar solo placeholders con decisiones
reales. No completar placeholders por inferencia.

```text
Trabaja en TestPsico F6 desde la raíz Git del repositorio. Tu objetivo es planificar
y luego implementar informes/PDF/integración sin inventar contratos.

BASELINE ESPERADO
- Branch/commit de referencia: master @ adc7ae6, 2026-08-11.
- F1–F5 están archivados y no hay change OpenSpec activo.
- HANDOFF-F6.md y usuarios.md pueden estar untracked. usuarios.md es ajeno: no lo
  leas, modifiques, borres, stages ni incluyas en commits.

PROCESO OBLIGATORIO
1. Lee AGENTS.md y HANDOFF-F6.md.
2. Resuelve la raíz Git y confirma .codegraph + `codegraph status` antes de búsquedas
   amplias. Usa CodeGraph para estructura, dependencias e impacto.
3. Ejecuta el SDD Session Preflight y DETENTE para pedir decisiones reales:
   execution_mode=<OWNER_SELECTION>
   artifact_store=<OWNER_SELECTION>
   delivery_strategy=<OWNER_SELECTION>
   review_budget=<OWNER_SELECTION>
   No elijas valores por el usuario.
4. Pasa el init guard. El proyecto ya tiene OpenSpec: no reescribas init/config sin
   explicar el delta y recibir confirmación.
5. Ejecuta `/sdd-new <f6-change-name>` para explore y proposal. NO saltes a apply.
6. Lee como canon `openspec/config.yaml`, specs de data-schema/scoring-engine/
   results-api/recommendation-api/contracts/audit-consent/synthetic-seed/sessions,
   packages/contracts/README.md y los changes archivados F4/F5 completos.
7. Resuelve las preguntas de audiencia, trigger, template, contenido/redacciones,
   PDF, storage/retención, integración, regeneración, locale/accesibilidad y web.
   Si una queda sin respuesta, detente; no adivines.
8. Continúa por spec/design/tasks/apply/verify/archive usando `/sdd-continue` y el
   dispatcher autoritativo. Mantén strict TDD RED→GREEN y el workload guard.

INVARIANTES
- No modifiques contratos F2/F3/F4/F5 salvo delta explícito ratificado.
- No edites instrumentos publicados ni cambies sesiones/scoring/recomendación.
- Consume score_runs y recommendation_results persistidos; no recalcules engines.
- Todo es synthetic/research-only; sin normas reales, datos reales ni LLM.
- No filtres scores/recomendaciones a audiencias no autorizadas.
- Mutaciones idempotentes; audit append-only aggregate-only; mismo retry no duplica
  report, PDF, audit ni delivery.
- Código, identificadores, specs y tokens técnicos en inglés por defecto; UI humana
  en español siguiendo el proyecto.
- Tests primero. Usa PostgreSQL real para repository/service/API; prueba PDF sin
  byte snapshots frágiles salvo normalización completa; suite completa dos veces.
- No hagas commits ni push salvo solicitud expresa. Si luego se solicitan, usa
  conventional commits y unidades revisables; chain si supera el presupuesto.

DETENTE ante cualquier decisión de producto no ratificada, conflicto de working
tree o contradicción entre código y spec. Reporta evidencia exacta; no inventes
endpoints, eventos, capabilities, status, fields, vendor, renderer ni retention.
```

## Apéndice de evidencia

### Estado Git y CodeGraph observado

```text
Git root: <REPO_ROOT>
Branch: master
HEAD: adc7ae634ee6343a77952e59e2fb55f31b4d6578 (adc7ae6)
Subject: docs(openspec): archive f5-profiles-recommendation change
Commit date: 2026-08-11
Initial status: ## master...origin/master [ahead 8]; ?? usuarios.md
CodeGraph: up to date; 155 files; 2,275 nodes; 5,411 edges
Native SDD status: no active OpenSpec change; nextRecommended=sdd-new
```

### Comandos read-only/targeted ejecutados para este handoff

```text
git rev-parse --show-toplevel
git status --short --branch
git log -1 --format=...
codegraph status
codegraph query "Report"
codegraph explore "reports report_templates recommendation_results score_runs PDF integration"
codegraph explore "Report ReportTemplate reporting migration"
codegraph explore "recommendation generate get route service repository idempotency audit"
codegraph explore "score_runs score_results results API scoring service repository"
codegraph explore "permissions audit EVENT_CATALOG require_roles capabilities"
codegraph callers Report
codegraph impact Report
codegraph affected services/api/app/models/reporting.py
gentle-ai --help
gentle-ai sdd-status --cwd <repo>
powershell -ExecutionPolicy Bypass -File scripts/test.ps1 -k
  "test_page_is_spanish or test_page_never_leaks_stack_trace"
```

El targeted test actual produjo **2 failed, 217 deselected, 3 warnings**. Fallaron
exactamente:

- `services/api/tests/test_web.py::test_page_is_spanish`;
- `services/api/tests/test_web.py::test_page_never_leaks_stack_trace`.

No se ejecutó la suite completa para redactar documentación. La última evidencia
completa es **histórica**, no una afirmación actual: verify F5 en revision
`1517ec7`, 2026-08-11, registró dos corridas de 219 collected / 217 passed / 2
failed, con esos mismos fallos heredados. El HEAD actual solo añade el archive F5,
pero una implementación F6 debe volver a medir la suite.

### Archivos inspeccionados

- Canon completo: `AGENTS.md`, `openspec/config.yaml`, specs relevantes y
  `packages/contracts/README.md`.
- Operación: `README.md`, `ONBOARDING.md`, scripts, Compose, Dockerfile y manifests
  Python/Node.
- F4 y F5: exploration, proposal, todos los delta specs, design, tasks,
  apply-progress, verify-report y archive-report.
- Código: modelos reporting/scoring/recommendation/session, migración 0003,
  routers/DTOs, módulos F4/F5, permisos, auditoría y seed/reset.
- Tests: schema, seed, auth, audit, fixtures session-scoped, F4/F5 contracts,
  aislamiento F5 y web debt.

---

Este handoff es una guía de entrada, no una ratificación F6. Ante cualquier
divergencia, mandan las specs canónicas y el change F6 aprobado.

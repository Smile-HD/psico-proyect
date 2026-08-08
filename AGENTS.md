# AGENTS.md — TestPsico

Guía para que un agente de IA (Claude Code, OpenCode, Codex, Cursor, etc.) trabaje
en este repositorio. El objetivo: **OpenSpec es la memoria del proyecto** — leela
antes de tocar código y nunca inventes decisiones que ya están ratificadas.

---

## Quick path (flujo obligatorio antes de editar)

1. Lee `openspec/config.yaml` — invariantes de dominio, reglas por fase y estado
   de testing (2 min).
2. Lee `openspec/specs/<dominio>/spec.md` del área que vas a tocar — es la
   **especificación ratificada** (memoria canónica del proyecto).
3. Revisa `openspec/changes/` — los cambios activos definen el trabajo en curso;
   los archivados (`archive/`) explican decisiones pasadas y su porqué.
4. Implementa con pruebas (RED → GREEN → REFACTOR si el runner existe; la suite
   actual corre con `scripts/test.sh`).
5. Documenta cualquier decisión nueva en un change de OpenSpec, no en un
   comentario suelto.

## Estado del proyecto

| Área | Dónde está |
| ------ | ----------- |
| Invariantes y reglas | `openspec/config.yaml` |
| Especificaciones ratificadas | `openspec/specs/` (contratos, schema, identidad, auditoría, seed, catálogo) |
| Cambio activo actual | `openspec/changes/f2-catalogo-instrumentos/` (propuesta, specs, diseño, tareas) |
| Contrato técnico | `packages/contracts/README.md` |
| Arranque del entorno | `ONBOARDING.md` y `README.md` |

## Invariantes que NO se negocian

- **Versionado inmutable**: un instrumento publicado jamás se edita en sitio.
  Cualquier cambio crea una nueva `instrument_version_id`; las sesiones conservan
  la versión exacta con la que empezaron.
- **Datos sintéticos**: todo contenido es `synthetic` y `research-only`. No hay
  normas UAGRM reales, ni personas ni datos reales.
- **Scoring puro**: respuestas + versión + referencia → puntajes. Sin acceso a DB,
  sin efectos secundarios.
- **Recomendación declarativa**: reglas en DB, no en código ni LLM.
- **Sin LLM en el camino productivo**: crear, puntuar o explicar ítems con un
  modelo no es una opción en el MVP.
- **Auditoría**: `audit_log` es append-only. Metadata agregada (ids, conteos,
  transiciones) — nunca contenido de ítems, claves ni tokens.
- **Idempotencia**: todo endpoint mutante exige `Idempotency-Key`; retry con la
  misma key NO duplica efectos ni eventos de auditoría.

## Cómo usar OpenSpec como memoria

- **Los specs ratificados son la fuente de verdad.** Si el código y la spec
  difieren, es un bug de una de las dos partes: corregí la que esté mal y
  documentá el cambio.
- **Un cambio (change) tiene ciclo**: `exploration → proposal → spec → design →
  tasks → apply → verify → archive`. Las specs de un change son deltas; al
  archivar, los deltas se fusionan en `openspec/specs/`.
- **Para decisiones nuevas**: creá un change y escribí la propuesta antes de
  implementar. No saltees la cadena.
- **Rastro de decisiones**: el archivo `archive/` conserva el porqué. Antes de
  "corregir" algo raro, buscá la decisión original en el change que lo introdujo.

## Convenciones de código y docs

| Área | Regla |
| ------ | ------- |
| Textos de UI | Español (ej: `Guardar borrador`, `Publicar versión`) |
| Código, identificadores, specs | Inglés (tokens de contrato en inglés) |
| Idiomas de opciones | `locale: es` por defecto; las opciones Likert usan etiquetas, nunca valores visibles |
| Envelope de API | `{"error": {"code", "message", "request_id", "details"}}` — códigos: `VALIDATION_ERROR`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `UNAUTHORIZED`, `INTERNAL_ERROR` |
| Permisos | Deny-by-default con `require_roles(...)`; `psicólogo` edita/archiva, `admin` publica, `evaluado` solo lee publicado |
| Commits | Conventional commits, unidades de trabajo revisables, sin atribución de IA |

## Comandos que usan los agentes

```bash
# Stack y tests
docker compose up -d --build
scripts/test.sh                    # suite completa (pytest en el contenedor)
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.seed        # idempotente
docker compose run --rm api python -m app.seed --reset # preflight atómico

# Web (Next.js)
cd apps/web && npm install && npm run build   # typecheck + build

# Nota Windows (Git Bash): si scripts/test.sh falla por conversión de rutas:
#   WINPWD=$(pwd -W) && MSYS_NO_PATHCONV=1 docker compose run --rm \
#     -v "${WINPWD}:/repo:ro" api pytest /repo/services/api/tests
```

## Trampas conocidas (lea antes de debuggear)

- **Imagen docker vieja**: después de tocar migraciones o código de `services/api`,
  corré `docker compose build api`. Los tests montan `/repo` (código nuevo) pero
  alembic y la app corren desde `/app` (copia de la imagen) — una imagen vieja
  produce fallos fantasma (ej: `relation "scales" does not exist`).
- **Suite repetible**: el conftest dropea y recrea la BD `psico` por corrida.
  No conserves estado entre corridas; los registros de idempotencia persisten.
- **LSP local**: el venv vive en `services/api/.venv` (config pyright en
  `pyproject.toml`). Sin él, pyright reporta errores falsos (`itertools could not
  be resolved`, etc.).
- **Seed read-only**: el instrumento semilla `TP-S-01:v1` no se edita ni se
  versiona desde la UI; el service lo rechaza con `seed_catalog_read_only`.

## Checklist para cerrar una tarea

- [ ] Los specs que tocaste están actualizados (o hay un change activo que los modifica)
- [ ] La suite completa pasa dos veces seguidas (repetibilidad)
- [ ] Datos sintéticos: nada real se introdujo en seeds, fixtures o tests
- [ ] Ningún endpoint mutante quedó sin `Idempotency-Key`
- [ ] La auditoría no expone contenido de ítems
- [ ] Commit convencional, unidad de trabajo acotada

## Siguiente paso

Leé `ONBOARDING.md` si sos nuevo en el repo, y `packages/contracts/README.md`
antes de tocar la API. Para el estado del trabajo en curso, mirá
`openspec/changes/` y el `tasks.md` del change activo.

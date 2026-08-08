# TestPsico

Sistema de tests psicotécnicos para orientación vocacional/educativa exploratoria
(bloques base para UAGRM y despliegue multi-institucional). Todo el contenido del
repositorio es **sintético y solo para investigación** — sin normas reales de
UAGRM, sin personas reales ni datos reales.

La F1 (esta base) hace que un clon nuevo sea ejecutable en menos de 10 minutos en
cualquier máquina con Docker Engine + Compose v2 (Windows, macOS, Linux): un
servicio FastAPI, PostgreSQL, Redis, un esquema migrado de nueve familias, una
semilla sintética idempotente y una página web mínima en español que prueba la red
de Compose.

```
psico/
├── docker-compose.yml        # stack dev: api + db + redis (+ web)
├── .env.example              # defaults dev seguros PSICO_* (espejados por Settings)
├── scripts/                  # wrappers multiplataforma (.sh + .ps1)
├── packages/contracts/       # convenciones vinculantes para todas las fases (EN)
├── services/api/             # FastAPI + SQLAlchemy 2 + Alembic
├── apps/web/                 # página Next.js en español (salud + semilla)
└── openspec/                 # artefactos de planificación SDD
```

## Requisitos previos

- Docker Engine + Compose v2
- Puertos libres 8000 (api), 5432 (db), 6379 (redis), 3000 (web)

> **¿Trabajás con un agente de IA?** Leé [AGENTS.md](./AGENTS.md) primero:
> explica cómo usar OpenSpec como memoria del proyecto, las invariantes que no
> se negocian y las trampas conocidas del entorno.

## Inicio rápido

```bash
# 1. Bootstrap del entorno (crea .env a partir de .env.example si no existe)
scripts/init-env.sh            # Windows: scripts\init-env.ps1

# 2. Build y arranque del stack (funciona SIN .env: defaults dev-only)
docker compose up -d --build

# 3. Aplicar el esquema
docker compose run --rm api alembic upgrade head

# 4. Sembrar datos sintéticos (idempotente; ejecutalo dos veces y los conteos quedan iguales)
docker compose run --rm api python -m app.seed

# 5. Correr la suite de tests
scripts/test.sh            # Windows: scripts\test.ps1
```

La página web está en <http://localhost:3000> (salud + estado de la semilla, UI en
español). La API está en <http://localhost:8000> (`/health`, `/api/v1/seed/status`
son públicos).

## Comandos oficiales

| Tarea | Comando |
| --- | --- |
| Up (api + db + redis + web) | `docker compose up -d --build` |
| Migrar | `docker compose run --rm api alembic upgrade head` |
| Sembrar (idempotente) | `docker compose run --rm api python -m app.seed` |
| Reset solo de la semilla (filas seed-owned) | `docker compose run --rm api python -m app.seed --reset` |
| Limpiar entorno dev (borra volúmenes) | `docker compose down -v` |
| Tests mínimos | `scripts/test` (`.sh` o `.ps1`; monta el repo read-only en `/repo`) |
| Bootstrap de env | `scripts/init-env` (`.sh` o `.ps1`) |

Cada tarea tiene su wrapper equivalente en `scripts/` (pares `.sh` + `.ps1` que
ejecutan exactamente el mismo comando de `docker compose`).

## Entorno

- La config de la app usa el prefijo `PSICO_*`; la infraestructura usa
  `POSTGRES_*` / `REDIS_*`.
- `.env.example` contiene defaults dev-only seguros y está commiteado; `.env`
  está gitignored. `app/core/config.py` (pydantic-settings) espeja el ejemplo
  exactamente para que contenedor y host nunca diverjan.
- Compose usa `${VAR:-default}` en todos lados, así que `up` a secas funciona —
  pero los defaults son dev-only; la API loguea un warning al arranque cuando los
  detecta. Nunca los lleves a un entorno real.
- Ejecutá `scripts/init-env` una vez para crear un `.env` propio que puedas
  sobreescribir.

## Convenciones (consumidas por todas las fases)

Ver `packages/contracts/README.md` — reglas vinculantes para IDs (UUID4 en
runtime, claves UUID5 `psico-seed:`), el envelope único de errores y la
deny-list de auditoría.

- Los tokens técnicos del contrato (códigos, IDs, campos) están en inglés.
- Los textos UI dirigidos a personas están en español.
- Las versiones publicadas de instrumentos son inmutables (aplicado por esquema).
- `audit_log` es append-only (trigger de DB rechaza UPDATE/DELETE).
- No hay reglas de scoring/recomendación en el cliente; sin LLM en el camino
  del MVP.

## Notas de desarrollo

- Las migraciones son solo de esquema y forman UNA cadena lineal de Alembic.
- La semilla es determinística (UUID5) y aditiva; `--reset` borra solo las filas
  seed-owned.
- Tests: `pytest -k scripts|schema|auth|audit|consent|seed|web` para correr un
  slice puntual.

## Verificar que la semilla es segura (sin datos reales, sin secretos)

El repositorio NO trae normas reales de UAGRM, personas reales ni secretos
reales. Estos checks lo confirman en cualquier clon:

1. **Marcadores de fixture** — toda fila sembrada lleva `synthetic = true` y
   `source = 'seed'` donde esas columnas existen. El set de referencia es
   `reference_status = 'synthetic'`, `use = 'research-only'`, y su `norm_note`
   es el disclaimer visible:
   `"NO es una norma UAGRM. Datos inventados para desarrollo."`
2. **Nombres** — los 30 perfiles usan personas ficticias (`evaluado_01` …
   `evaluado_30`, "Perfil Sintetico NN"); no aparecen nombres reales de
   estudiantes, terapeutas ni instituciones en `app/seed/fixtures/`.
3. **Secretos** — `.env.example` tiene defaults dev-only (contraseñas dev
   débiles, `psico_dev_password_*`, placeholder de JWT). Las credenciales reales
   van solo en tu `.env` local gitignored; nunca commitees `.env`.
4. **Deny-list de auditoría** — `audit_log.metadata` nunca guarda respuestas,
   tokens, contraseñas ni contenido de instrumentos (aplicado por convención y
   aseverado en `tests/test_audit.py`).
5. **Prueba automatizada** — la suite asevera todo lo anterior:
   `scripts/test` (o `scripts\test.ps1`), luego `pytest -k seed|scripts`.
   `test_reference_fixture_research_only` y los tests de deny-list fallan si un
   valor con apariencia real o un secreto se cuela en los fixtures.

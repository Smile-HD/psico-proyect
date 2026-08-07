# TestPsico — Guía de puesta en marcha (Fase 1)

Guía para que cualquier integrante del equipo pueda clonar, levantar y trabajar
sobre el proyecto en menos de 10 minutos. Cubre la instalación paso a paso y los
errores más comunes con su solución.

- **Sistema objetivo**: Windows (PowerShell) o Linux/macOS (bash).
- **Tiempo esperado**: 5–10 minutos la primera vez (la primera construcción
  descarga las imágenes de Docker).
- **Resultado esperado**: entorno levantado, esquema aplicado, semilla cargada,
  login con los tres roles (admin / psicólogo / evaluado).

---

## 1. Requisitos previos

| Requisito | Cómo verificarlo |
|---|---|
| Docker Engine + Compose v2 | `docker version` y `docker compose version` (debe mostrar `Docker Compose version v2.x`) |
| Puertos libres: 8000 (api), 5432 (db), 6379 (redis), 3000 (web) | Ver sección [Errores comunes](#errores-comunes), E1 |

> **Windows**: Docker Desktop debe estar en modo **Linux containers** (el default
> al instalar). No es necesario instalar Python, Node ni PostgreSQL en tu máquina:
> todo corre dentro de contenedores.

---

## 2. Cómo funciona (no creas nada a mano)

La base de datos se crea sola en tres capas. No ejecutes `CREATE DATABASE` ni
`CREATE TABLE` manualmente:

1. **La base `psico` y el rol `psico_app`** → los crea automáticamente el
   contenedor de PostgreSQL en su primer arranque, usando las variables
   `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` del `.env`.
2. **Las tablas (esquema)** → las crea Alembic con `alembic upgrade head`
   (cadena de migraciones 0001 → 0004, 23 tablas).
3. **Los datos (semilla)** → los inserta `python -m app.seed`: test de 20 ítems,
   baremo sintético, 30 perfiles, 3 usuarios dev, sesiones y consentimientos.

Los datos viven en los volúmenes `psico_db_data` y `psico_redis_data` (el disco
de los contenedores), no en archivos visibles del proyecto.

---

## 3. Pasos

### Paso 1 — Clonar el repositorio

```powershell
git clone <URL-del-repo> psico
cd psico
```

### Paso 2 — Crear el `.env` local

```powershell
# Windows
scripts\init-env.ps1

# Linux / macOS
scripts/init-env.sh
```

El script copia `.env.example` a `.env` (solo si no existe). El `.env` está
gitignored: **nunca lo commitees**.

> **Verificación**: aparece un archivo `.env` en la raíz del proyecto.

### Paso 3 — Levantar el stack

```powershell
docker compose up -d --build
```

Construye y arranca los 4 servicios: `db` (PostgreSQL), `redis`, `api` (FastAPI)
y `web` (Next.js). La primera vez descarga las imágenes y puede tardar unos
minutos.

> **Verificación**: `docker compose ps` muestra los 4 servicios con estado
> `running` / `healthy`.

### Paso 4 — Aplicar el esquema

```powershell
docker compose run --rm api alembic upgrade head
```

> **Verificación**: termina sin errores. Si lo ejecutás de nuevo, responde que
> no hay nada nuevo que aplicar.

### Paso 5 — Cargar la semilla

```powershell
docker compose run --rm api python -m app.seed
```

> **Verificación**: el resumen muestra los conteos: **20 ítems, 1 set de
> referencia (baremo), 30 perfiles, 30 sesiones, 30 consentimientos y
> 600 respuestas**. Es idempotente: ejecutalo de nuevo y los conteos no cambian.

### Paso 6 — Ver la semilla cargada

- **Web**: abrí http://localhost:3000 → muestra "Salud de la API" y
  "Semilla (datos sintéticos)" con los conteos.
- **API**: http://localhost:8000/health y http://localhost:8000/api/v1/seed/status

### Paso 7 — Iniciar sesión con los tres roles

Usuarios dev sembrados (contraseñas por defecto; si las cambiaste en tu `.env`,
usá las tuyas):

| Rol | Usuario | Contraseña por defecto |
|---|---|---|
| Admin | `admin` | `psico-dev-admin` |
| Psicólogo | `psicologo` | `psico-dev-psicologo` |
| Evaluado | `evaluado` | `psico-dev-evaluado` |

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/auth/login `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"psico-dev-admin"}'
$login.access_token
```

El comando devuelve un JWT (`access_token`). Con él se prueban los permisos:

```powershell
$token = $login.access_token
$headers = @{ Authorization = "Bearer $token" }

# Admin: puede leer el registro de auditoría → 200 OK
Invoke-RestMethod -Uri http://localhost:8000/api/v1/audit -Headers $headers

# Evaluado: el mismo endpoint debe dar 403 (deny-by-default) — es lo esperado
```

> **Nota sobre la cuenta `evaluado`**: no tiene consentimiento sembrado (solo
> los 30 perfiles lo tienen). Si intentás crear una sesión con ese rol, vas a
> recibir `409 consent_required`. Es el comportamiento esperado: primero hay que
> conceder el consentimiento con `POST /api/v1/consent/{id}/grant`.

### Paso 8 — Suite de tests (opcional pero recomendado)

```powershell
# Windows
scripts\test.ps1

# Linux / macOS
scripts/test.sh
```

Monta el repositorio en modo lectura dentro del contenedor `api` y corre toda la
suite (schema, auth, audit, consent, seed, web, scripts).

### Paso 9 — Detener / limpiar

```powershell
docker compose down        # detiene todo, conserva los datos
docker compose down -v     # detiene y borra los volúmenes (reset total)
```

Para restaurar la semilla a su estado inicial sin borrar todo:

```powershell
docker compose run --rm api python -m app.seed --reset
```

---

## 4. Errores comunes

### E1 — "port is already allocated" / puerto ocupado

Uno de los puertos 8000, 5432, 6379 o 3000 está en uso por otro programa
(otro contenedor, PostgreSQL local, etc.).

```powershell
# Windows: ver qué proceso usa el puerto
Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess

# Linux / macOS
lsof -i :8000
```

**Solución**: detené el proceso que ocupa el puerto, o cambiá el puerto en tu
`.env` (p. ej. `API_PORT=8001`, `POSTGRES_PORT=5433`).

### E2 — "Cannot connect to the Docker daemon"

Docker Desktop no está corriendo (o el motor no arrancó).

**Solución**: iniciá Docker Desktop y esperá a que el indicador esté verde.
En Windows, verificá que esté en modo **Linux containers**.

### E3 — El script `.ps1` no se ejecuta ("running scripts is disabled")

La política de ejecución de PowerShell bloquea scripts.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\init-env.ps1
```

o habilitá de forma persistente para tu usuario:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### E4 — El API no conecta con la base ("connection refused")

El contenedor `db` todavía no está listo cuando el API intenta conectar.

```powershell
docker compose ps          # ¿db está healthy?
docker compose logs db     # ¿logs de arranque de PostgreSQL?
```

**Solución**: esperá unos segundos y reintentá (`docker compose up -d`, después
`docker compose run --rm api alembic upgrade head`). Si `db` está `restarting`
o el volumen quedó corrupto, hacé un reset completo: `docker compose down -v` y
volvé al Paso 3.

### E5 — Login devuelve 401 (credenciales inválidas)

Las contraseñas del seed se leen de las variables `PSICO_DEV_PASSWORD_*` del
`.env` en el momento de sembrar. Si cambiaste una contraseña **después** de
sembrar, el usuario sembrado sigue teniendo la anterior.

**Solución**: usá las contraseñas de tu `.env` actual, o volvé a sembrar después
de cambiarlas: `docker compose run --rm api python -m app.seed` (es idempotente).

### E6 — "database does not exist" al migrar o sembrar

Suele pasar cuando `POSTGRES_*` y `PSICO_DATABASE_URL` quedaron **inconsistentes**.
Los defaults se corresponden 1:1:

- `POSTGRES_USER=psico_app` ↔ usuario de `PSICO_DATABASE_URL`
- `POSTGRES_PASSWORD=psico_dev_password` ↔ contraseña de `PSICO_DATABASE_URL`
- `POSTGRES_DB=psico` ↔ base de `PSICO_DATABASE_URL`

**Solución**: si cambiás `POSTGRES_PASSWORD` (u otro valor), actualizá
`PSICO_DATABASE_URL` con el mismo valor y reiniciá el stack
(`docker compose down -v` + `up -d --build`).

### E7 — La web muestra "API: No disponible"

El contenedor `api` no está healthy todavía, o la web no lo alcanza.

**Solución**: esperá a que `docker compose ps` muestre `api` como `healthy` y
recargá la página. Si persiste, mirá los logs:

```powershell
docker compose logs api
docker compose logs web
```

### E8 — `docker compose up` falla en Windows con errores de manifest/imagen

Docker Desktop está en modo **Windows containers**.

**Solución**: Docker Desktop → Settings → General → **Use Docker Compose V2** y
contenedores **Linux**. Si no aparece, reiniciá Docker Desktop.

### E9 — El build es lento o "COPY . ." copia basura local

Los archivos `.dockerignore` de `services/api` y `apps/web` excluyen `.env`,
`.venv`, `node_modules`, `.next`, `.pytest_cache`, etc. del contexto de build.
Si ejecutaste `npm install` o creaste un venv local, no afectan a la imagen.

### E10 — Datos viejos / semilla inconsistente tras cambios

El volumen conserva datos de corridas anteriores.

**Solución**:
```powershell
docker compose run --rm api python -m app.seed --reset   # solo filas de la semilla
docker compose down -v                                   # reset total (borra todo)
```

---

## 5. Checklist de cierre (Fase 1)

La puesta en marcha fue exitosa si:

- [ ] `docker compose ps` muestra los 4 servicios `running` / `healthy`.
- [ ] `alembic upgrade head` terminó sin errores.
- [ ] El seed reportó 20 ítems, 1 baremo, 30 perfiles (600 respuestas).
- [ ] http://localhost:3000 muestra salud y conteos de la semilla.
- [ ] Login OK con `admin`, `psicologo` y `evaluado`.
- [ ] `scripts\test.ps1` (o `scripts/test.sh`) pasa completo.

---

## 6. Referencias

- `README.md` — visión general, comandos oficiales y convenciones.
- `packages/contracts/README.md` — contrato técnico entre fases (IDs, envelope
  de errores, deny-list de auditoría).
- `.env.example` — documentación de cada variable de entorno.

# Documento de Cierre: Fase 3 — Sesión de Evaluación y Entrega (F3)

## 1. Objetivo General
Proporcionar un mecanismo completo y robusto para la entrega y aplicación de evaluaciones psicotécnicas sintéticas a usuarios con el rol `evaluado`. El sistema garantiza el control de tiempo desde el servidor, guardado silencioso e idempotente por cada ítem respondido, y la reanudación transparente ante desconexiones de red o recargas de página.

---

## 2. Modelos de Datos Utilizados
- **`sessions`** (`Session`): Mantiene el ciclo de vida de la sesión (`status`: `in_progress`, `completed`, `cancelled`), la versión inmutable de la prueba (`instrument_version_id`), la marca de tiempo de inicio (`started_at`), de finalización (`completed_at`) y el consentimiento firmado (`consent_grant_id`).
- **`responses`** (`Response`): Almacena las respuestas individuales por ítem (`item_id`, `value`). Garantiza unicidad mediante la restricción `(session_id, item_id)`.
- **`audit_log`** (`AuditLog`): Registro append-only que almacena eventos de ciclo de vida (`session.started`, `session.resumed`, `session.response_saved`, `session.completed`) sin exponer contenido confidencial ni tokens.

---

## 3. Endpoints Expuestos

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `POST` | `/api/v1/sessions` | Crea e inicia la sesión bloqueando la versión publicada de la prueba (`instrument_version_id`). Exige consentimiento otorgado previo (`409 CONFLICT`). |
| `GET` | `/api/v1/sessions/{id}/resume` | Recupera el progreso de la sesión (respuestas guardadas) y el tiempo restante calculado en servidor. |
| `POST` | `/api/v1/sessions/{id}/responses` | Guarda silenciosamente una respuesta por ítem con el encabezado `Idempotency-Key` para prevenir duplicados. |
| `POST` | `/api/v1/sessions/{id}/submit` | Congela las respuestas, marca la sesión como `completed` y desactiva posteriores ediciones. |

---

## 4. Decisiones de Diseño y Trade-offs

1. **El servidor como autoridad del tiempo**:
   - El temporizador y el tiempo restante (`remaining_seconds`) son calculados en el backend basándose en `started_at` y la duración del instrumento. Los valores del cliente no alteran la vigencia de la sesión.
2. **Reanudación transparente mediante `sessionStorage`**:
   - El identificador de la sesión activa se conserva en el `sessionStorage` del navegador. Al recargar la página o perder la conexión, el frontend consulta `GET /sessions/{id}/resume` y restaura el estado exacto sin perder información.
3. **Bloqueo inmutable de versión al iniciar**:
   - Toda sesión queda vinculada permanentemente a la `instrument_version_id` con la que inició. Cambios posteriores en el catálogo no afectan la validez ni el contenido de sesiones existentes.
4. **Idempotencia en autoguardado**:
   - Cada envío de respuesta requiere la cabecera `Idempotency-Key`. Reintentos con la misma clave devuelven `created=false` y el registro original sin duplicar eventos de auditoría.

---

## 5. Instrucciones de Verificación

### Pruebas Automatizadas
Ejecutar la suite completa de integración mediante Docker Compose:
```powershell
.\scripts\test.ps1
```
Todas las pruebas unitarias e integrales (`tests/test_sessions.py`) deben finalizar con un 100% de éxito (142 passed).

### Verificación Manual en la UI (Next.js)
1. Iniciar sesión como evaluado (`evaluado` / credenciales dev).
2. Navegar a `/sesion` en el navegador.
3. Otorgar el consentimiento informado inline ("Aceptar y Comenzar").
4. Responder las preguntas presentadas de a **1 ítem por pantalla** observando la barra de progreso, el guardado automático y el temporizador.
5. Completar y enviar la prueba (`POST /submit`) verificando la pantalla final de éxito.

---

## 6. Handoff a la Fase 4 (Scoring e Interpretación)
La Fase 3 queda formalmente **CERRADA Y RATIFICADA**. Las sesiones completadas (`status = 'completed'`) con sus respuestas inmutables asociadas quedan listas para ser consumidas por el motor de Scoring puro y Recomendación declarativa de la **Fase 4**.

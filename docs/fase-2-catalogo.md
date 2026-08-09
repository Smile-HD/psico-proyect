# Cierre de Fase 2 — Catálogo de Instrumentos

## Resumen Ejecutivo
La Fase 2 implementa la gestión del catálogo de instrumentos sintéticos psicotécnicos, soportando autoría, versionado inmutable y consulta pública/privada de pruebas.

## Modelo de Dominio de 4 Niveles
- **Instrument** (`instruments`): Representa la prueba psicotécnica (clave, título, descripción).
- **InstrumentVersion** (`instrument_versions`): Versión específica de un instrumento.
- **Scale** (`scales`): Escalas de medición asociadas a una versión.
- **InstrumentItem** (`items`): Ítems/preguntas asociadas a las escalas.
- **ResponseOption** (`response_options`): Opciones de respuesta Likert 1-5.

## Reglas de Dominio e Invariantes
1. **Versionado Inmutable**: Una versión publicada (`published`) jamás se edita in-situ. Toda modificación requiere la creación de un nuevo borrador (`draft`).
2. **Acceso de Evaluados**: Los usuarios con rol `evaluado` pueden consultar instrumentos publicados mediante los endpoints de lectura `/api/v1/catalog/published-versions/{version_id}` o por clave sintética (`TP-S-01:v1`).

## Estado de Verificación
- **Pruebas de API y Migraciones**: `services/api/tests/test_catalog_api.py`, `test_catalog_db.py`, `test_catalog_migration.py`.
- **Estado de la Fase**: **COMPLETADA / RATIFICADA**

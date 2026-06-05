# Review — Feature 7: pipelines_parallel_exec

> Reviewer: agente reviewer
> Fecha: 2026-06-05
> Spec: `specs/pipelines_parallel_exec/`
> Implementación: `progress/impl_pipelines_parallel_exec.md`

---

## 1. Trazabilidad Requirements → Tests ✅

| R<n> | Test(s) | Estado |
|------|---------|--------|
| R1 — Ejecución paralela con `asyncio.gather` | `test_operations_launched_in_parallel` | ✅ |
| R2 — `max_concurrency` configurable | `test_semaphore_limits_concurrency`, `test_default_max_concurrency_is_10` | ✅ |
| R3 — Default `max_concurrency` = 10 | `test_default_max_concurrency_is_10`, `test_default_constant_value` | ✅ |
| R4 — Configurable desde `Settings` | `test_default_max_concurrency_is_10` (indirecto; wiring verificado en `main.py:459`) | ✅ |
| R5 — 50+ operaciones concurrentes | `test_supports_high_concurrency` | ✅ |
| R6 — Preservación del orden de `operation_ids` | `test_operations_launched_in_parallel`, `test_operation_ids_order_preserved` | ✅ |
| R7 — Propagación de errores parciales | `test_partial_launch_failure_skips_failed_operation` | ✅ |
| R8 — Polling sin cambios de semántica | `test_polling_and_timeout_unaffected` | ✅ |

**Observación:** R4 queda cubierto por inspección del código de `main.py` (línea 459) y la existencia del campo en `settings.py` (línea 54). No hay un test de integración que inyecte un valor distinto vía Settings. No se considera defecto porque el wiring es directo y verificable estáticamente.

---

## 2. Trazabilidad Tasks → Código ✅

| Task | Archivo | Línea(s) | Estado |
|------|---------|----------|--------|
| T1 — Constante `_DEFAULT_MAX_CONCURRENCY` | `execute_pipeline_operations.py` | 36 | ✅ |
| T2 — Parámetro `max_concurrency` en `__init__` | `execute_pipeline_operations.py` | 59, 69 | ✅ |
| T3 — Método `_launch_all_operations` | `execute_pipeline_operations.py` | 135–182 | ✅ |
| T4 — Reemplazo del bucle secuencial | `execute_pipeline_operations.py` | 92–94 | ✅ |
| T5 — Verificación sin cambios en polling/timeout | — (sin cambios necesarios) | — | ✅ |
| T6 — Campo `PIPELINE_MAX_CONCURRENCY` en Settings | `app/config/settings.py` | 54 | ✅ |
| T7 — Wiring en `main.py` | `main.py` | 459 | ✅ |
| T8 — Test `test_operations_launched_in_parallel` | `test_execute_pipeline_parallel.py` | 110–150 | ✅ |
| T9 — Test `test_semaphore_limits_concurrency` | `test_execute_pipeline_parallel.py` | 207–239 | ✅ |
| T10 — Test `test_default_max_concurrency_is_10` | `test_execute_pipeline_parallel.py` | 279–294 | ✅ |
| T11 — Test `test_partial_launch_failure_skips_failed_operation` | `test_execute_pipeline_parallel.py` | 305–345 | ✅ |
| T12 — Test `test_operation_ids_order_preserved` | `test_execute_pipeline_parallel.py` | 152–201 | ✅ |
| T13 — Test `test_polling_and_timeout_unaffected` | `test_execute_pipeline_parallel.py` | 352–388 | ✅ |

---

## 3. Checklist de checkpoints

### C17 — Logger con `get_logger(__name__)` ✅
- `execute_pipeline_operations.py:32`: import `from app.v1.shared.infrastructure.logger import get_logger`
- `execute_pipeline_operations.py:39`: `logger = get_logger(__name__)`
- NO usa `logging.getLogger`.

### C18 — Sin `print()` de debug ✅
- No se encontró ninguna llamada a `print()` en los archivos modificados.

### C24 — openapi.yaml actualizado ⏭️ (skip)
- La feature no toca routes ni schemas de API. No aplica.

---

## 4. Calidad de tests ✅

- Todos los tests usan `@pytest.mark.asyncio` y `AsyncMock`.
- No hay fixtures compartidas entre clases de test no relacionadas; cada clase usa `make_task()` factory local.
- Los 8 tests cubren explícitamente R1–R8 según la tabla de trazabilidad.
- El test `test_semaphore_limits_concurrency` (R2, R5) usa un tracker de concurrencia que incrementa al entrar y decrementa al salir del launch, verificando que el pico nunca supera `max_concurrency`.
- El test `test_supports_high_concurrency` (R5) lanza 50 operaciones concurrentes sin degradación.

---

## 5. Revisión de código

### `_launch_all_operations` (`execute_pipeline_operations.py:135–182`)

| Aspecto | Verificación |
|---------|-------------|
| Semaphore creado internamente | `asyncio.Semaphore(self._max_concurrency)` en línea 148 ✅ |
| `asyncio.gather` con `return_exceptions=True` | Línea 169 ✅ |
| Manejo de errores parciales (R7) | Cada resultado se inspecciona; `BaseException` se loguea como `pipeline_launch_operation_failed` con `operation_idx`; solo `str` válidos se incluyen en `operation_ids` (líneas 171–180) ✅ |
| Preservación de orden (R6) | El producto cartesiano `server_ids × kits` se construye en el mismo orden que el bucle original; `asyncio.gather` preserva el orden de entrada ✅ |
| Captura de variables de bucle | Usa default arguments `sid: str = server_id, kc = kit_config` para capturar el valor de cada iteración — patrón estándar correcto en Python ✅ |

### `main.py` wiring (`main.py:451–460`)

- `max_concurrency=settings.PIPELINE_MAX_CONCURRENCY` se pasa explícitamente en la construcción de `ExecutePipelineOperations` ✅

### Settings (`settings.py:54`)

- `PIPELINE_MAX_CONCURRENCY: int = 10` con tipo explícito y default 10 ✅

---

## 6. Defectos encontrados

**Ninguno.**

Observaciones menores (no blocking):
- R4 no tiene un test de integración que verifique la inyección desde Settings. La trazabilidad lo marca como "indirecto". Aceptable porque el wiring es verificable estáticamente en `main.py` y la cobertura es suficiente para el propósito de la feature.
- El patrón de captura de variables con default arguments en `_bounded_launch` (líneas 154–166) es técnicamente correcto pero sutil; podría beneficiarse de un comentario breve. No se requiere cambio.

---

## 7. Tests: resultado de ejecución

```
tests/v1/pipelines/test_use_cases/test_execute_pipeline_parallel.py ... 8 passed
tests/v1/pipelines/                                              ... 193 passed (0 regresiones)
```

---

## 8. Veredicto final

**APPROVED**

La implementación cumple todos los requirements (R1–R8), las 13 tasks están completas, los checkpoints pasan, los tests son verdes y no hay regresiones. El código sigue el diseño especificado y las convenciones del proyecto.

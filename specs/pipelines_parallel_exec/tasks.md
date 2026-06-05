# Tasks — pipelines_parallel_exec

> Checklist ejecutable. Cada task referencia al menos un R<n> del requirements.md.
> El implementer marca `[x]` al completar.

---

## Application layer

- [ ] T1 — Añadir constante `_DEFAULT_MAX_CONCURRENCY: int = 10` a nivel de módulo en `execute_pipeline_operations.py`, junto a `_POLL_INTERVAL_SECONDS` y `_DEFAULT_TIMEOUT_SECONDS`. Cubre: R3.

- [ ] T2 — Añadir parámetro `max_concurrency: int = _DEFAULT_MAX_CONCURRENCY` al constructor de `ExecutePipelineOperations`. Almacenarlo como `self._max_concurrency`. Cubre: R2, R3.

- [ ] T3 — Crear método privado `_launch_all_operations(self, server_ids: list[str], pipeline, user_id: str) -> list[str]` en `ExecutePipelineOperations`. El método DEBE: construir el producto cartesiano `server_ids × pipeline.kits` en el mismo orden que el bucle original, crear un `asyncio.Semaphore(self._max_concurrency)`, definir una corrutina interna `_bounded_launch` que adquiera el semáforo y llame a `self._launcher.launch`, ejecutar todas las corrutinas con `asyncio.gather(..., return_exceptions=True)`, loguear cada excepción como `pipeline_launch_operation_failed`, y devolver solo los `str` válidos (omitir los fallos). Cubre: R1, R2, R5, R6, R7.

- [ ] T4 — Reemplazar el doble bucle `for server_id / for kit_config` en el método `execute()` de `ExecutePipelineOperations` por una llamada a `await self._launch_all_operations(server_ids, pipeline, execution.user_id)`. Cubre: R1.

- [ ] T5 — Verificar que `_poll_until_all_terminal`, `_cancel_pending_operations` y el bloque `except Exception` de `execute()` no requieren cambios (no hay regresión sobre el comportamiento de polling y timeout). Documentar en el comentario del PR si se detecta algún ajuste menor. Cubre: R8.

## Config layer

- [ ] T6 — Añadir campo `PIPELINE_MAX_CONCURRENCY: int = 10` a la clase `Settings` en `app/config/settings.py`. Cubre: R3, R4.

## Composition Root

- [ ] T7 — Actualizar la closure `_execute_pipeline_fn` en `main.py` para pasar `max_concurrency=settings.PIPELINE_MAX_CONCURRENCY` al construir `ExecutePipelineOperations`. Cubre: R4.

## Tests

- [ ] T8 — Crear `tests/v1/pipelines/test_use_cases/test_execute_pipeline_parallel.py`. Añadir test `test_operations_launched_in_parallel`: verifica que con 3 servers × 2 kits = 6 operaciones, `_launcher.launch` se invoca 6 veces y `operation_ids` tiene 6 elementos en el orden correcto. Cubre: R1, R6.

- [ ] T9 — Añadir test `test_semaphore_limits_concurrency`: usa un `AsyncMock` con un contador de concurrencia que incrementa al entrar y decrementa al salir; verifica que el pico de concurrencia nunca supera `max_concurrency`. Cubre: R2, R5.

- [ ] T10 — Añadir test `test_default_max_concurrency_is_10`: instancia `ExecutePipelineOperations` sin `max_concurrency` y verifica que `self._max_concurrency == 10`. Cubre: R3.

- [ ] T11 — Añadir test `test_partial_launch_failure_skips_failed_operation`: simula que el segundo `launch` lanza `Exception`; verifica que `operation_ids` solo contiene los ids válidos, y que la ejecución no aborta (continúa con el resto). Cubre: R7.

- [ ] T12 — Añadir test `test_operation_ids_order_preserved`: lanza 2 servers × 3 kits con `AsyncMock` que devuelve ids predecibles (`"op-{i}"`); verifica que el orden de `operation_ids` coincide con el orden del doble bucle `server × kit`. Cubre: R6.

- [ ] T13 — Añadir test `test_polling_and_timeout_unaffected`: ejecuta el flujo completo con `max_concurrency=2` y verifica que el polling detecta correctamente operaciones terminales (sin regresión sobre el comportamiento previo). Cubre: R8.

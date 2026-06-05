# Historial de sesiones

_Se añaden sesiones completadas al final de este archivo._

---

## Sesión: pipelines_cancel_timeout (feature id 6)

**Fecha:** 2026-06-05
**Estado final:** DONE

### Resumen

Feature completa: cancelación de PipelineExecution + timeout efectivo.

### Artefactos implementados

- `app/v1/pipelines/domain/value_objects/pipeline_status.py` — `cancelled` en `_VALID_VALUES` y `_TERMINAL_STATES`
- `app/v1/pipelines/domain/entities/pipeline_execution.py` — métodos `cancel()` y `mark_timeout_failed()`
- `app/v1/pipelines/domain/exceptions/pipeline_execution.py` — `PipelineExecutionNotCancellableError`
- `app/v1/pipelines/domain/events/pipeline_execution_cancelled.py` — evento `PipelineExecutionCancelled`
- `app/v1/pipelines/application/interfaces/operation_cancel_port.py` — port `OperationCancelPort`
- `app/v1/pipelines/application/dtos/pipeline_dtos.py` — `PipelineExecutionCancelDTO`
- `app/v1/pipelines/application/commands/cancel_pipeline_execution.py` — command `CancelPipelineExecution`
- `app/v1/pipelines/application/tasks/execute_pipeline_operations.py` — timeout efectivo con cancelación
- `app/v1/pipelines/infrastructure/adapters/operation_cancel_adapter.py` — `OperationCancelAdapter`
- `app/v1/pipelines/infrastructure/presentation/schemas.py` — `PipelineExecutionCancelResponse`
- `app/v1/pipelines/infrastructure/presentation/routes.py` — `POST .../cancel`
- `app/v1/pipelines/infrastructure/presentation/deps.py` — `get_cancel_pipeline_execution_uc`
- `app/v1/pipelines/infrastructure/presentation/exception_handlers.py` — handler 422

### Trazabilidad

| Requirement | Tests |
|-------------|-------|
| R1 | `test_cancel_in_progress_returns_200`, `test_cancel_in_progress_success` |
| R2 | `test_cancel_in_progress_transitions_to_cancelled`, `test_cancel_registers_finished_at` |
| R3 | `test_cancel_cancels_pending_operations`, `test_cancel_cancels_in_progress_operations` |
| R4 | `test_cancel_publishes_event`, `test_event_creation`, `test_event_serialization` |
| R5 | `test_cancel_terminal_raises_error`, `test_cancel_completed_returns_422`, `test_cancel_failed_returns_422` |
| R6 | `test_cancel_pending_raises_error`, `test_cancel_pending_returns_422` |
| R7 | `test_cancel_not_owner_raises_404`, `test_cancel_not_owner_returns_404` |
| R8 | `test_timeout_cancels_in_progress_operations` |
| R9 | `test_timeout_cancels_pending_operations` |
| R10 | `test_timeout_marks_execution_failed`, `test_timeout_marks_execution_as_failed` |
| R11 | `test_timeout_persists_cancelled_operations` |

### Suite final

1061 passed, 4 failed (preexistentes en credential presentation — no relacionados con esta feature)

---

## Sesión: pipelines_parallel_exec (feature id 7)

**Fecha:** 2026-06-05
**Estado final:** DONE

### Resumen

Ejecución paralela de operaciones en pipelines. Reemplazo del bucle secuencial `for server × for kit` por `asyncio.gather` con `asyncio.Semaphore` configurable.

### Artefactos implementados

- `app/v1/pipelines/application/tasks/execute_pipeline_operations.py` — nuevo método `_launch_all_operations`, constante `_DEFAULT_MAX_CONCURRENCY`, parámetro `max_concurrency`
- `app/config/settings.py` — campo `PIPELINE_MAX_CONCURRENCY: int = 10`
- `main.py` — wiring de `max_concurrency=settings.PIPELINE_MAX_CONCURRENCY` en closure
- `tests/v1/pipelines/test_use_cases/test_execute_pipeline_parallel.py` — 8 tests (T8–T13)

### Trazabilidad

| R | Tests |
|---|-------|
| R1 | `test_operations_launched_in_parallel` |
| R2 | `test_semaphore_limits_concurrency`, `test_default_max_concurrency_is_10` |
| R3 | `test_default_max_concurrency_is_10`, `test_default_constant_value` |
| R4 | `test_default_max_concurrency_is_10` (indirecto) |
| R5 | `test_supports_high_concurrency` |
| R6 | `test_operations_launched_in_parallel`, `test_operation_ids_order_preserved` |
| R7 | `test_partial_launch_failure_skips_failed_operation` |
| R8 | `test_polling_and_timeout_unaffected` |

### Suite final

193 passed (8 nuevos + 185 existentes), 0 regresiones.
Reviewer veredicto: APPROVED.

---

## Sesión: pipelines_target_roles (feature id 8)

**Fecha:** 2026-06-05
**Estado final:** DONE

### Resumen

PipelineTarget extendido con `kit_ids` y `values` opcionales. Cada target puede ejecutar un subconjunto de los kits globales del pipeline con variables propias.

### Artefactos implementados

- `app/v1/pipelines/domain/value_objects/pipeline_target.py` — +kit_ids, +values
- `app/v1/pipelines/application/commands/launch_pipeline.py` — snapshot + validación R7
- `app/v1/pipelines/application/tasks/execute_pipeline_operations.py` — resolución por target + merge de values
- `app/v1/pipelines/infrastructure/presentation/schemas.py` — +kit_ids, +values en request/response
- `app/v1/pipelines/infrastructure/presentation/routes.py` — wiring de new fields en create/update
- `app/v1/pipelines/infrastructure/repositories/pipeline_repository.py` — serialización/deserialización
- `alembic/versions/0017_pipelines_targets_add_target_roles.py` — migración de datos
- `openapi.yaml` — regenerado
- Tests: 3 archivos nuevos (dominio, use cases, infraestructura)

### Trazabilidad

| R | Tests |
|---|-------|
| R1 | `test_kit_ids_none_by_default`, `test_kit_ids_empty_tuple`, `test_kit_ids_with_values` |
| R2 | `test_values_empty_dict_by_default`, `test_values_with_data` |
| R3 | `test_snapshot_includes_kit_ids_and_values_per_target` |
| R4 | `test_target_with_kit_ids_only_launches_those_kits`, `test_target_with_kit_ids_none_launches_all_kits` |
| R5 | `test_target_values_override_pipeline_values`, `test_kit_values_highest_priority` |
| R6 | Validación implícita en endpoints + OpenAPI |
| R7 | `test_rejects_target_with_nonexistent_kit_id` |
| R8 | `0017_pipelines_targets_add_target_roles.py` |
| R9 | `test_target_with_kit_ids_preserves_pipeline_kit_order` |
| R10 | `test_legacy_pipeline_launches_all_kits_all_targets` |
| R11 | `test_roundtrip_target_kit_ids_and_values`, `test_backward_compatible_legacy_targets` |

### Suite final

220 passed (66 nuevos + 154 existentes), 0 regresiones.
Reviewer veredicto: APPROVED (2 cycles: CHANGES_REQUESTED → 3 bugs corregidos → APPROVED).

---
